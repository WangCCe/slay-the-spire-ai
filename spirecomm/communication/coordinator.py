import sys
import queue
import threading
import json
import collections
import time

from spirecomm.spire.game import Game
from spirecomm.spire.screen import ScreenType
from spirecomm.communication.action import Action, StartGameAction, WaitAction


def read_stdin(input_queue):
    """Read lines from stdin and write them to a queue

    :param input_queue: A queue, to which lines from stdin will be written
    :type input_queue: queue.Queue
    :return: None
    """
    try:
        while True:
            stdin_input = ""
            while True:
                input_char = sys.stdin.read(1)
                # Detect broken pipe (game crash)
                if input_char == "" and len(stdin_input) == 0:
                    import logging

                    logging.critical(
                        "STDIN PIPE BROKEN: Communication Mod or Slay the Spire crashed. "
                        "This is likely caused by:"
                    )
                    logging.critical(
                        "  1. Communication Mod crash (check mod compatibility)"
                    )
                    logging.critical("  2. Slay the Spire crash (check game logs)")
                    logging.critical("  3. SuperFastMode + Communication Mod conflict")
                    logging.critical(
                        "Try running without SuperFastMode to isolate the issue."
                    )
                    raise EOFError(
                        "Communication Mod pipe broken - game likely crashed"
                    )
                if input_char == "\n":
                    break
                else:
                    stdin_input += input_char
            input_queue.put(stdin_input)
    except Exception as e:
        import logging

        logging.critical(f"read_stdin thread crashed: {e}")
        raise


def write_stdout(output_queue):
    """Read lines from a queue and write them to stdout

    :param output_queue: A queue, from which this function will receive lines of text
    :type output_queue: queue.Queue
    :return: None
    """
    try:
        while True:
            output = output_queue.get()
            try:
                print(output, end="\n", flush=True)
            except BrokenPipeError:
                import logging

                logging.critical(
                    "STDOUT PIPE BROKEN: Cannot write to Communication Mod. "
                    "Game likely crashed or closed."
                )
                raise
    except Exception as e:
        import logging

        logging.critical(f"write_stdout thread crashed: {e}")
        raise


class Coordinator:
    """An object to coordinate communication with Slay the Spire"""

    STATE_WAIT_SECONDS = 2.0
    STARTUP_MAX_WAIT_ATTEMPTS = 60
    STARTUP_CONSECUTIVE_TIMEOUT_LIMIT = 45
    IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT = 10
    TRANSIENT_OUT_OF_GAME_UPDATE_LIMIT = 5

    def __init__(self):
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.input_thread = threading.Thread(
            target=read_stdin, args=(self.input_queue,)
        )
        self.output_thread = threading.Thread(
            target=write_stdout, args=(self.output_queue,)
        )
        self.input_thread.daemon = True
        self.input_thread.start()
        self.output_thread.daemon = True
        self.output_thread.start()
        self.action_queue = collections.deque()
        self.state_change_callback = None
        self.out_of_game_callback = None
        self.error_callback = None
        self.game_is_ready = False
        self.stop_after_run = False
        self.in_game = False
        self.last_game_state = None
        self.last_error = None
        # Save game state when GAME_OVER screen appears (before clicking proceed)
        self.game_over_state = None
        # Delay actions on sensitive screens to let combat cleanup finish
        self._last_screen_type = None
        self._stability_wait_done = False
        self._stability_wait_screens = {ScreenType.COMBAT_REWARD, ScreenType.MAP}
        self._stability_wait_timeout = 5
        self._deferred_state_callback_pending = False
        self._deferred_state_callback_message_count = 0
        self._sent_message_count = 0
        self._last_sent_message = None
        self._combat_action_settle_pending = False
        self._combat_action_settle_timeout = 1
        self._last_command_error = None
        self.pending_seed = None

    def _maybe_queue_stability_wait(self):
        screen_type = getattr(self.last_game_state, "screen_type", None)
        if screen_type in self._stability_wait_screens and not self._stability_wait_done:
            import logging

            logging.info(
                "[STABILITY_WAIT] screen=%s, inserting wait=%s",
                screen_type,
                self._stability_wait_timeout,
            )
            self._stability_wait_done = True
            self.add_action_to_queue(WaitAction(timeout=self._stability_wait_timeout))
            return True
        return False

    @staticmethod
    def _invalid_command_name(error):
        if not isinstance(error, str):
            return None
        prefix = "Invalid command: "
        if not error.startswith(prefix):
            return None
        command = error[len(prefix):].split(".", 1)[0].strip()
        return command or None

    def _is_transition_late_command_error(self, error):
        command = self._invalid_command_name(error)
        if command != "play":
            return False

        game = getattr(self, "last_game_state", None)
        if getattr(game, "screen_type", None) != ScreenType.COMBAT_REWARD:
            return False

        available_commands = getattr(game, "available_commands", None) or []
        return command not in available_commands

    @staticmethod
    def _sent_combat_action_command(message):
        if not isinstance(message, str):
            return False
        command = message.split(" ", 1)[0]
        return command in {"play", "potion"}

    def _mark_combat_action_settle_if_needed(self, sent_before):
        if getattr(self, "_sent_message_count", 0) <= sent_before:
            return
        if not self._sent_combat_action_command(
            getattr(self, "_last_sent_message", None)
        ):
            return
        self._combat_action_settle_pending = True

    def _maybe_queue_combat_action_settle_wait(self):
        if not getattr(self, "_combat_action_settle_pending", False):
            return False

        game = getattr(self, "last_game_state", None)
        screen_type = getattr(game, "screen_type", None)
        if not self.in_game or not getattr(game, "in_combat", False):
            self._combat_action_settle_pending = False
            return False
        if screen_type not in (None, ScreenType.NONE):
            self._combat_action_settle_pending = False
            return False

        import logging

        self._combat_action_settle_pending = False
        timeout = getattr(self, "_combat_action_settle_timeout", 1)
        logging.info(
            "[COMBAT_ACTION_SETTLE] screen=%s floor=%s turn=%s; inserting wait=%s",
            screen_type,
            getattr(game, "floor", None),
            getattr(game, "turn", None),
            timeout,
        )
        self.add_action_to_queue(WaitAction(timeout=timeout))
        return True

    def _describe_stuck_state(self, consecutive_timeouts=None):
        game = getattr(self, "last_game_state", None)
        screen = getattr(game, "screen", None)
        action_queue = list(getattr(self, "action_queue", []) or [])
        next_action = action_queue[0] if action_queue else None
        fields = [
            f"screen={getattr(game, 'screen_type', None)}",
            f"floor={getattr(game, 'floor', None)}",
            f"turn={getattr(game, 'turn', None)}",
            f"in_game={getattr(self, 'in_game', None)}",
            f"game_is_ready={getattr(self, 'game_is_ready', None)}",
            f"queue_size={len(action_queue)}",
            f"next_action={type(next_action).__name__ if next_action is not None else None}",
            f"last_sent={getattr(self, '_last_sent_message', None)}",
            f"sent_count={getattr(self, '_sent_message_count', None)}",
            f"last_error={getattr(self, '_last_command_error', None)}",
            f"available_commands={getattr(game, 'available_commands', None)}",
        ]
        if consecutive_timeouts is not None:
            fields.append(f"consecutive_timeouts={consecutive_timeouts}")
        if screen is not None:
            fields.extend(self._describe_screen_fields(screen))
        return "; ".join(fields)

    @staticmethod
    def _describe_screen_fields(screen):
        fields = []
        for attr in ("confirm_up", "num_cards", "has_rested", "can_pick_zero"):
            if hasattr(screen, attr):
                fields.append(f"{attr}={getattr(screen, attr)}")
        if hasattr(screen, "selected_cards"):
            fields.append(
                f"selected_cards={len(getattr(screen, 'selected_cards') or [])}"
            )
        if hasattr(screen, "rest_options"):
            options = []
            for option in getattr(screen, "rest_options") or []:
                options.append(getattr(option, "name", str(option)))
            fields.append(f"rest_options={options}")
        return fields

    def check_communication_threads(self):
        """Check if stdin/stdout communication threads are still alive.

        :return: True if threads are alive, False if crashed
        :rtype: bool
        """
        if not self.input_thread.is_alive():
            import logging

            logging.critical(
                "STDIN THREAD DIED: Communication Mod or Slay the Spire crashed."
            )
            return False
        if not self.output_thread.is_alive():
            import logging

            logging.critical(
                "STDOUT THREAD DIED: Communication Mod or Slay the Spire crashed."
            )
            return False
        return True

    def signal_ready(self):
        """Indicate to Communication Mod that setup is complete

        Must be used once, before any other commands can be sent.
        :return: None
        """
        self.send_message("ready")

    def send_message(self, message, wait_for_response=True):
        """Send a command to Communication Mod and start waiting for a response

        :param message: the message to send
        :type message: str
        :param wait_for_response: whether to wait for response (sets game_is_ready=False)
        :type wait_for_response: bool
        :return: None
        """
        import logging

        logging.info(
            f"[SEND_MESSAGE] {message}, game_is_ready was={self.game_is_ready}, wait_for_response={wait_for_response}"
        )
        self._sent_message_count = getattr(self, "_sent_message_count", 0) + 1
        self._last_sent_message = message
        self.output_queue.put(message)
        if wait_for_response:
            self.game_is_ready = False

    def add_action_to_queue(self, action):
        """Queue an action to perform when ready

        :param action: the action to queue
        :type action: Action
        :return: None
        """
        self.action_queue.append(action)

    def clear_actions(self):
        """Remove all actions from the action queue

        :return: None
        """
        self.action_queue.clear()

    def _request_state_during_startup_wait(self, consecutive_timeouts, phase):
        if consecutive_timeouts == 1 or consecutive_timeouts % 5 == 0:
            import logging

            logging.info(
                "[STARTUP_STATE_POLL] phase=%s consecutive_timeouts=%s; requesting state",
                phase,
                consecutive_timeouts,
            )
            self.send_message("state", wait_for_response=False)

    def _request_state_during_idle_wait(self, consecutive_timeouts):
        if consecutive_timeouts == 1 or consecutive_timeouts % 3 == 0:
            import logging

            logging.info(
                "[IDLE_STATE_POLL] screen=%s consecutive_timeouts=%s; requesting state",
                getattr(self.last_game_state, "screen_type", None),
                consecutive_timeouts,
            )
            self.send_message("state", wait_for_response=False)

    def _request_state_during_action_wait(self, consecutive_timeouts):
        if len(self.action_queue) == 0:
            self._request_state_during_idle_wait(consecutive_timeouts)
            return

        next_action = self.action_queue[0]
        if (
            getattr(next_action, "requires_game_ready", False)
            and not self.game_is_ready
        ):
            import logging

            logging.info(
                "[READY_WAIT_STATE_POLL] action=%s screen=%s consecutive_timeouts=%s; requesting state",
                type(next_action).__name__,
                getattr(self.last_game_state, "screen_type", None),
                consecutive_timeouts,
            )
            self._request_state_during_idle_wait(consecutive_timeouts)

    def _current_game_over_state(self):
        for game_state in (
            getattr(self, "game_over_state", None),
            getattr(self, "last_game_state", None),
        ):
            if getattr(game_state, "screen_type", None) == ScreenType.GAME_OVER:
                return game_state
        return None

    def _queue_state_change_callback_action(self, deferred=False):
        import logging

        logging.info(
            "[CALLBACK] in_game=True, queue empty, calling state_change_callback%s. Screen: %s",
            " (deferred)" if deferred else "",
            getattr(self.last_game_state, "screen_type", "Unknown")
            if self.last_game_state
            else "None",
        )
        new_action = self.state_change_callback(self.last_game_state)
        if new_action is not None:
            if not self._maybe_queue_stability_wait():
                self.add_action_to_queue(new_action)
                logging.info("[CALLBACK] Got action: %s", type(new_action).__name__)
        else:
            logging.warning("state_change_callback returned None - ignoring")

    def _run_deferred_state_callback_if_idle(self):
        if not getattr(self, "_deferred_state_callback_pending", False):
            return False
        if (
            self.last_error is not None
            or not self.in_game
            or len(self.action_queue) > 0
        ):
            return False
        if getattr(self, "_sent_message_count", 0) != getattr(
            self, "_deferred_state_callback_message_count", 0
        ):
            self._deferred_state_callback_pending = False
            return False

        self._deferred_state_callback_pending = False
        self._queue_state_change_callback_action(deferred=True)
        return True

    def execute_next_action(self):
        """Immediately execute the next action in the action queue

        :return: None
        """
        action = self.action_queue.popleft()
        import logging

        logging.info(
            f"[ACTION_QUEUE] Executing {action.__class__.__name__}, queue_size={len(self.action_queue)}"
        )
        sent_before = getattr(self, "_sent_message_count", 0)
        action.execute(self)
        self._mark_combat_action_settle_if_needed(sent_before)

    def execute_next_action_if_ready(self):
        """Immediately execute the next action in the action queue, if ready to do so

        :return: None
        """
        # Skip any None values in the queue (defensive programming)
        while len(self.action_queue) > 0 and self.action_queue[0] is None:
            import logging

            logging.warning("Removing None from action_queue")
            self.action_queue.popleft()

        if len(self.action_queue) > 0 and self.action_queue[0].can_be_executed(self):
            self.execute_next_action()

    def register_state_change_callback(self, new_callback):
        """Register a function to be called when a message is received from Communication Mod

        :param new_callback: the function to call
        :type new_callback: function(game_state: Game) -> Action
        :return: None
        """
        self.state_change_callback = new_callback

    def register_command_error_callback(self, new_callback):
        """Register a function to be called when an error is received from Communication Mod

        :param new_callback: the function to call
        :type new_callback: function(error: str) -> Action
        :return: None
        """
        self.error_callback = new_callback

    def register_out_of_game_callback(self, new_callback):
        """Register a function to be called when Communication Mod indicates we are in the main menu

        :param new_callback: the function to call
        :type new_callback: function() -> Action
        :return: None
        """
        self.out_of_game_callback = new_callback

    def get_next_raw_message(self, block=False):
        """Get the next message from Communication Mod as a string

        :param block: set to True to wait for the next message
        :type block: bool
        :return: the message from Communication Mod, or None if timeout/empty
        :rtype: str or None
        """
        if block:
            # Blocking call with timeout
            try:
                return self.input_queue.get(timeout=self.STATE_WAIT_SECONDS)
            except queue.Empty:
                return None
        elif not self.input_queue.empty():
            # Non-blocking call - return immediately if data available
            # No timeout needed for non-blocking calls
            try:
                return self.input_queue.get_nowait()
            except queue.Empty:
                return None
        else:
            # Queue is empty and not blocking
            return None

    def receive_game_state_update(self, block=False, perform_callbacks=True):
        """Using the next message from Communication Mod, update the stored game state

        :param block: set to True to wait for the next message
        :type block: bool
        :param perform_callbacks: set to True to perform callbacks based on the new game state
        :type perform_callbacks: bool
        :return: whether a message was received
        """
        import logging
        logging.info(f"[RECEIVE_START] block={block}, perform_callbacks={perform_callbacks}")
        message = self.get_next_raw_message(block)
        logging.info(f"[RECEIVE_AFTER] message is None: {message is None}")
        if message is not None:
            communication_state = json.loads(message)
            self.last_error = communication_state.get("error", None)
            old_ready = self.game_is_ready
            self.game_is_ready = communication_state.get("ready_for_command")
            import logging

            logging.info(
                f"[STATE_UPDATE] game_is_ready: {old_ready}→{self.game_is_ready}, action_queue_size={len(self.action_queue)}"
            )
            if self.last_error is None:
                self._last_command_error = None
                self.in_game = communication_state.get("in_game")
                # Get game_state (may be empty dict when not in game, e.g., Neow screen)
                game_state = communication_state.get("game_state", {})
                if self.in_game:
                    # Handle GRID screen logging when in game
                    if game_state.get("screen_type") == "GRID":
                        import logging

                        screen_state = game_state.get("screen_state") or {}
                        if isinstance(screen_state, dict):
                            logging.debug(
                                "GRID screen_state keys=%s",
                                sorted(screen_state.keys()),
                            )
                            logging.debug(
                                "GRID state: cards=%s, selected=%s, num_cards=%s, any_number=%s, confirm_up=%s, for_upgrade=%s, for_transform=%s, for_purge=%s, available=%s",
                                len(screen_state.get("cards") or []),
                                len(screen_state.get("selected_cards") or []),
                                screen_state.get("num_cards"),
                                screen_state.get("any_number"),
                                screen_state.get("confirm_up"),
                                screen_state.get("for_upgrade"),
                                screen_state.get("for_transform"),
                                screen_state.get("for_purge"),
                                communication_state.get("available_commands"),
                            )
                            logging.debug(
                                "GRID choice_list present: %s",
                                "choice_list" in game_state,
                            )
                        else:
                            logging.debug(
                                "GRID screen_state type=%s",
                                type(screen_state).__name__,
                            )

                # Save GAME_OVER state before it gets overwritten by menu state
                if game_state.get("screen_type") == "GAME_OVER" and self.in_game:
                    # Mark that we're processing GAME_OVER (will save after from_json)
                    self._saving_game_over = True

                # Always update last_game_state, even when in_game=False (e.g., Neow screen)
                self.last_game_state = Game.from_json(
                    game_state, communication_state.get("available_commands")
                )
                # Track screen transitions to reset stability waits
                current_screen = getattr(self.last_game_state, "screen_type", None)
                if current_screen != self._last_screen_type:
                    self._stability_wait_done = False
                    self._last_screen_type = current_screen

                # Save the parsed GAME_OVER state (after from_json, before callbacks)
                if hasattr(self, '_saving_game_over'):
                    # We just processed GAME_OVER screen, save the parsed state
                    self.game_over_state = self.last_game_state
                    delattr(self, '_saving_game_over')
                    import logging
                    logging.info(f"[GAME_OVER] Saved state with HP: current={self.game_over_state.current_hp}/{self.game_over_state.max_hp}")
            import logging
            callback_error = self.last_error
            if self._is_transition_late_command_error(callback_error):
                callback_error = "<transition-late command error>"
            logging.info(
                f"[CALLBACK_CHECK] perform_callbacks={perform_callbacks}, "
                f"last_error={callback_error}, "
                f"in_game={self.in_game}, "
                f"queue_size={len(self.action_queue)}, "
                f"screen={getattr(self.last_game_state, 'screen_type', 'None') if self.last_game_state else 'None'}"
            )
            if perform_callbacks:
                if self.last_error is not None:
                    self._deferred_state_callback_pending = False
                    self.action_queue.clear()
                    current_error = self.last_error
                    repeated_error = current_error == self._last_command_error
                    transition_late_error = self._is_transition_late_command_error(
                        current_error
                    )
                    self._last_command_error = current_error
                    self.last_error = None
                    new_action = None
                    if transition_late_error:
                        command = self._invalid_command_name(current_error)
                        logging.warning(
                            "[TRANSITION_LATE_COMMAND_ERROR] command=%s screen=%s; requesting state",
                            command,
                            getattr(self.last_game_state, "screen_type", None),
                        )
                    elif repeated_error:
                        logging.warning(
                            "[COMMAND_ERROR] Suppressing repeated error: %s",
                            current_error,
                        )
                    else:
                        new_action = self.error_callback(current_error)
                    if new_action is not None:
                        self.add_action_to_queue(new_action)
                    elif transition_late_error or repeated_error:
                        self.send_message("state", wait_for_response=False)
                    else:
                        logging.warning("error_callback returned None - requesting state")
                        self.send_message("state", wait_for_response=False)
                elif self.in_game:
                    if len(self.action_queue) == 0:
                        import logging
                        self._deferred_state_callback_pending = False
                        if not self._maybe_queue_combat_action_settle_wait():
                            self._queue_state_change_callback_action()
                    else:
                        import logging

                        self._deferred_state_callback_pending = True
                        self._deferred_state_callback_message_count = getattr(
                            self, "_sent_message_count", 0
                        )
                        logging.info(
                            "[CALLBACK] Deferring state callback until queue drains. "
                            "queue_size=%s screen=%s",
                            len(self.action_queue),
                            getattr(self.last_game_state, "screen_type", "Unknown")
                            if self.last_game_state
                            else "None",
                        )
                elif self.stop_after_run:
                    self._deferred_state_callback_pending = False
                    self.clear_actions()
                else:
                    self._deferred_state_callback_pending = False
                    if len(self.action_queue) > 0:
                        logging.info(
                            "[OUT_OF_GAME] Clearing %s stale queued actions before start callback",
                            len(self.action_queue),
                        )
                        self.clear_actions()
                    new_action = self.out_of_game_callback()
                    if new_action is not None:
                        if (
                            isinstance(new_action, StartGameAction)
                            and new_action.seed is None
                            and self.pending_seed is not None
                        ):
                            new_action.seed = self.pending_seed
                        self.add_action_to_queue(new_action)
                    else:
                        import logging

                        logging.warning("out_of_game_callback returned None - ignoring")
            return True
        return False

    def run(self):
        """Start executing actions forever

        :return: None
        """
        while True:
            self.execute_next_action_if_ready()
            self.receive_game_state_update(perform_callbacks=True)

    def play_one_game(self, player_class, ascension_level=0, seed=None):
        """

        :param player_class: the class to play
        :type player_class: PlayerClass
        :param ascension_level: the ascension level to use
        :type ascension_level: int
        :param seed: the alphanumeric seed to use
        :type seed: str
        :return: True if the game was a victory, else False
        :rtype: bool
        """
        # Clear any pending actions from previous game
        self.clear_actions()

        # Reset saved game over state from previous game
        self.game_over_state = None
        self.pending_seed = seed

        # Wait for ready state (with timeout to prevent hanging)
        timeout_counter = 0
        consecutive_timeouts = 0
        max_wait = self.STARTUP_MAX_WAIT_ATTEMPTS
        max_consecutive_timeouts = self.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT

        while not self.game_is_ready and timeout_counter < max_wait:
            received = self.receive_game_state_update(
                block=True, perform_callbacks=False
            )
            if received:
                consecutive_timeouts = 0  # Reset timeout counter on successful receive
            else:
                consecutive_timeouts += 1
                self._request_state_during_startup_wait(
                    consecutive_timeouts,
                    "initial_ready",
                )
                if consecutive_timeouts >= max_consecutive_timeouts:
                    # Only fail if we get MANY consecutive timeouts
                    raise Exception(
                        f"Communication Mod not responding (timeout after {consecutive_timeouts} attempts)"
                    )
            timeout_counter += 1

        if not self.game_is_ready:
            raise Exception("Communication Mod not ready for new game")

        # Start new game if not already in one
        import logging
        logging.info(f"[PLAY_ONE_GAME] Before start check, in_game={self.in_game}, screen={getattr(self.last_game_state, 'screen_type', 'None') if self.last_game_state else 'None'}")
        if not self.in_game:
            StartGameAction(player_class, ascension_level, seed).execute(self)
            # Wait for game to actually start
            timeout_counter = 0
            consecutive_timeouts = 0
            import logging
            while not self.in_game and timeout_counter < max_wait:
                received = self.receive_game_state_update(block=True)
                # Debug logging to diagnose Neow screen hanging
                logging.info(
                    f"[WAIT_FOR_GAME] received={received}, in_game={self.in_game}, "
                    f"screen={getattr(self.last_game_state, 'screen_type', 'None') if self.last_game_state else 'None'}, "
                    f"timeout={timeout_counter}/{max_wait}"
                )
                if received:
                    consecutive_timeouts = (
                        0  # Reset timeout counter on successful receive
                    )
                else:
                    consecutive_timeouts += 1
                    self._request_state_during_startup_wait(
                        consecutive_timeouts,
                        "start_game",
                    )
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        # Only fail if we get MANY consecutive timeouts
                        raise Exception(
                            f"Communication Mod not responding when starting game (timeout after {consecutive_timeouts} attempts)"
                        )
                timeout_counter += 1

            if not self.in_game:
                raise Exception("Failed to start new game")
        else:
            import logging
            logging.info(f"[PLAY_ONE_GAME] Skipping start because already in_game, screen={getattr(self.last_game_state, 'screen_type', 'None') if self.last_game_state else 'None'}")

            # Force callback to handle the current screen (EVENT/NEOW/etc.)
            # This fixes deadlock when Communication Mod won't send updates
            # until AI acts on the current screen
            if self.last_game_state is not None and len(self.action_queue) == 0:
                logging.info("[PLAY_ONE_GAME] Forcing callback for current screen...")
                new_action = self.state_change_callback(self.last_game_state)
                if new_action is not None:
                    self.add_action_to_queue(new_action)
                    logging.info(f"[PLAY_ONE_GAME] Added action: {type(new_action).__name__}")

        # Play until game ends
        last_update_time = time.time()
        consecutive_timeouts = 0
        max_consecutive_timeouts = self.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT

        import logging
        logging.info(f"[PLAY_ONE_GAME] Entering main game loop, in_game={self.in_game}, screen={getattr(self.last_game_state, 'screen_type', 'None') if self.last_game_state else 'None'}")

        transient_out_of_game_updates = 0
        while True:
            if not self.in_game:
                if self._current_game_over_state() is not None:
                    break

                transient_out_of_game_updates += 1
                if (
                    transient_out_of_game_updates
                    > self.TRANSIENT_OUT_OF_GAME_UPDATE_LIMIT
                ):
                    raise Exception(
                        "Game reported out-of-game without GAME_OVER for "
                        f"{transient_out_of_game_updates} consecutive updates. "
                        "Refusing to count a non-terminal run."
                    )

                logging.warning(
                    "[PLAY_ONE_GAME] Ignoring transient out-of-game state without "
                    "GAME_OVER. screen=%s attempt=%s/%s; requesting state",
                    getattr(self.last_game_state, "screen_type", None),
                    transient_out_of_game_updates,
                    self.TRANSIENT_OUT_OF_GAME_UPDATE_LIMIT,
                )
                self._deferred_state_callback_pending = False
                if len(self.action_queue) > 0:
                    logging.info(
                        "[PLAY_ONE_GAME] Clearing %s queued actions from "
                        "non-terminal out-of-game transition",
                        len(self.action_queue),
                    )
                    self.clear_actions()
                self.send_message("state", wait_for_response=False)
                state_update = self.receive_game_state_update(
                    block=True,
                    perform_callbacks=True,
                )
                if state_update:
                    last_update_time = time.time()
                    consecutive_timeouts = 0
                else:
                    consecutive_timeouts += 1
                continue

            transient_out_of_game_updates = 0
            # Check if communication threads are still alive (detect game crashes)
            if not self.check_communication_threads():
                raise EOFError("Communication Mod connection lost (game crashed)")

            import logging

            # Execute any pending actions first
            self.execute_next_action_if_ready()

            # Try non-blocking first to avoid unnecessary delays
            state_update = self.receive_game_state_update(
                block=False, perform_callbacks=True
            )
            if not state_update:
                # No immediate update, block with timeout
                logging.info(
                    "[MAIN_LOOP] No immediate update, blocking with timeout..."
                )
                state_update = self.receive_game_state_update(
                    block=True, perform_callbacks=True
                )
            logging.info(
                f"[MAIN_LOOP] after receive, state_update={state_update is not None}, queue_size={len(self.action_queue)}, game_is_ready={self.game_is_ready}"
            )

            if not self.in_game:
                logging.warning(
                    "[MAIN_LOOP] Received out-of-game update; deferring queued "
                    "actions until terminal or transient state is resolved"
                )
                continue

            # Execute action after receiving update
            self.execute_next_action_if_ready()

            # Continue executing queued actions if available (for multi-step actions like card selection)
            while (
                len(self.action_queue) > 0
                and not self.action_queue[0].requires_game_ready
            ):
                logging.info(
                    f"[MAIN_LOOP] Executing queued action without waiting, queue_size={len(self.action_queue)}"
                )
                self.execute_next_action()

            self._run_deferred_state_callback_if_idle()

            # Track last successful update
            if state_update:
                last_update_time = time.time()
                consecutive_timeouts = 0
            else:
                consecutive_timeouts += 1
                self._request_state_during_action_wait(consecutive_timeouts)

                # Special handling for screens that may not send state updates after selections
                # COMBAT_REWARD: especially in chest rooms with mutually exclusive rewards
                # GRID: event screens for card removal/battle circle where selection doesn't trigger update
                if consecutive_timeouts >= 1:
                    if self.last_game_state and hasattr(self.last_game_state, 'screen_type'):
                        screen_type = self.last_game_state.screen_type

                        # Handle COMBAT_REWARD screen
                        if screen_type == ScreenType.COMBAT_REWARD:
                            logging.warning(
                                f"[COMBAT_REWARD] No state update after {consecutive_timeouts * 2} seconds, "
                                f"sending proceed to continue"
                            )
                            self.send_message("proceed", wait_for_response=False)
                            consecutive_timeouts = 0
                            continue

                        # Handle GRID screen (card removal/upgrade events) - check if cards are selected
                        elif screen_type == ScreenType.GRID:
                            screen = self.last_game_state.screen
                            if (hasattr(screen, 'selected_cards') and hasattr(screen, 'num_cards')
                                and len(screen.selected_cards) >= screen.num_cards
                                and screen.confirm_up):
                                # Cards have been selected but no state update - send confirm
                                logging.warning(
                                    f"[GRID] No state update after {consecutive_timeouts * 2} seconds, "
                                    f"sending confirm to complete selection"
                                )
                                self.send_message("confirm", wait_for_response=False)
                                consecutive_timeouts = 0
                                continue

                if consecutive_timeouts >= max_consecutive_timeouts:
                    stuck_details = self._describe_stuck_state(
                        consecutive_timeouts=consecutive_timeouts
                    )
                    raise Exception(
                        f"Game appears stuck (no state update for {consecutive_timeouts * 2} seconds). "
                        f"Last action may have caused the game to hang. {stuck_details}"
                    )

        # Return the saved terminal state if a later menu transition overwrote
        # last_game_state.
        game_over_state = self._current_game_over_state()
        if game_over_state is not None:
            return game_over_state.screen.victory
        return False
