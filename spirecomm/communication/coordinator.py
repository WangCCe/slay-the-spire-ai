import sys
import queue
import threading
import json
import collections
import time

from spirecomm.spire.game import Game
from spirecomm.spire.screen import ScreenType
from spirecomm.communication.action import Action, StartGameAction


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

    def execute_next_action(self):
        """Immediately execute the next action in the action queue

        :return: None
        """
        action = self.action_queue.popleft()
        import logging

        logging.info(
            f"[ACTION_QUEUE] Executing {action.__class__.__name__}, queue_size={len(self.action_queue)}"
        )
        action.execute(self)

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
                return self.input_queue.get(timeout=10.0)  # Increased to 10 seconds
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
        message = self.get_next_raw_message(block)
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
                # Always update last_game_state, even when in_game=False (e.g., Neow screen)
                self.last_game_state = Game.from_json(
                    game_state, communication_state.get("available_commands")
                )
            if perform_callbacks:
                if self.last_error is not None:
                    self.action_queue.clear()
                    new_action = self.error_callback(self.last_error)
                    if new_action is not None:
                        self.add_action_to_queue(new_action)
                    else:
                        import logging

                        logging.warning("error_callback returned None - ignoring")
                elif self.in_game:
                    if len(self.action_queue) == 0:
                        import logging
                        logging.info(
                            f"[CALLBACK] in_game=True, queue empty, calling state_change_callback. "
                            f"Screen: {getattr(self.last_game_state, 'screen_type', 'Unknown') if self.last_game_state else 'None'}"
                        )
                        new_action = self.state_change_callback(self.last_game_state)
                        if new_action is not None:
                            self.add_action_to_queue(new_action)
                            import logging
                            logging.info(f"[CALLBACK] Got action: {type(new_action).__name__}")
                        else:
                            import logging

                            logging.warning(
                                "state_change_callback returned None - ignoring"
                            )
                elif self.stop_after_run:
                    self.clear_actions()
                else:
                    new_action = self.out_of_game_callback()
                    if new_action is not None:
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

        # Wait for ready state (with timeout to prevent hanging)
        timeout_counter = 0
        consecutive_timeouts = 0
        max_wait = 50  # Increased from 20 to allow more attempts
        max_consecutive_timeouts = 10  # Increased from 3 to 10

        while not self.game_is_ready and timeout_counter < max_wait:
            received = self.receive_game_state_update(
                block=True, perform_callbacks=False
            )
            if received:
                consecutive_timeouts = 0  # Reset timeout counter on successful receive
            else:
                consecutive_timeouts += 1
                if consecutive_timeouts >= max_consecutive_timeouts:
                    # Only fail if we get MANY consecutive timeouts
                    raise Exception(
                        f"Communication Mod not responding (timeout after {consecutive_timeouts} attempts)"
                    )
            timeout_counter += 1

        if not self.game_is_ready:
            raise Exception("Communication Mod not ready for new game")

        # Start new game if not already in one
        if not self.in_game:
            StartGameAction(player_class, ascension_level, seed).execute(self)
            # Wait for game to actually start
            timeout_counter = 0
            consecutive_timeouts = 0
            while not self.in_game and timeout_counter < max_wait:
                received = self.receive_game_state_update(block=True)
                if received:
                    consecutive_timeouts = (
                        0  # Reset timeout counter on successful receive
                    )
                else:
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        # Only fail if we get MANY consecutive timeouts
                        raise Exception(
                            f"Communication Mod not responding when starting game (timeout after {consecutive_timeouts} attempts)"
                        )
                timeout_counter += 1

            if not self.in_game:
                raise Exception("Failed to start new game")

        # Play until game ends
        last_update_time = time.time()
        consecutive_timeouts = 0
        max_consecutive_timeouts = 6  # 6 * 10 seconds = 60 seconds total

        while self.in_game:
            # Check if communication threads are still alive (detect game crashes)
            if not self.check_communication_threads():
                raise EOFError("Communication Mod connection lost (game crashed)")

            import logging

            logging.info(
                f"[MAIN_LOOP] execute_next_action_if_ready, queue_size={len(self.action_queue)}, game_is_ready={self.game_is_ready}"
            )
            self.execute_next_action_if_ready()

            # Use blocking call with timeout to detect hangs
            state_update = self.receive_game_state_update(
                block=True, perform_callbacks=True
            )
            logging.info(
                f"[MAIN_LOOP] after receive, state_update={state_update is not None}, queue_size={len(self.action_queue)}, game_is_ready={self.game_is_ready}"
            )
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

            # Use blocking call with timeout to detect hangs
            state_update = self.receive_game_state_update(
                block=True, perform_callbacks=True
            )
            logging.info(
                f"[MAIN_LOOP] after receive, state_update={state_update is not None}, queue_size={len(self.action_queue)}, game_is_ready={self.game_is_ready}"
            )
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

            # Try non-blocking first to avoid unnecessary delays
            state_update = self.receive_game_state_update(
                block=False, perform_callbacks=True
            )
            if state_update is None:
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
            self.execute_next_action_if_ready()

            # Try non-blocking first to avoid unnecessary delays
            state_update = self.receive_game_state_update(
                block=False, perform_callbacks=True
            )
            if state_update is None:
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

            # Track last successful update
            if state_update is not None:
                last_update_time = time.time()
                consecutive_timeouts = 0
            else:
                consecutive_timeouts += 1
                if consecutive_timeouts >= max_consecutive_timeouts:
                    raise Exception(
                        f"Game appears stuck (no state update for {consecutive_timeouts * 10} seconds). "
                        f"Last action may have caused the game to hang."
                    )

        # Return victory status (handle case where screen isn't GAME_OVER)
        if hasattr(self.last_game_state, "screen_type"):
            if self.last_game_state.screen_type == ScreenType.GAME_OVER:
                return self.last_game_state.screen.victory
            else:
                # Game ended but not at GAME_OVER screen
                # Assume defeat if we're out of game
                return False
        else:
            return False
