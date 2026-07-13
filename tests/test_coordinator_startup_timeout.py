import pytest
from types import SimpleNamespace

import spirecomm.communication.coordinator as coordinator_module
from spirecomm.communication.coordinator import Coordinator
from spirecomm.communication.action import RestAction, WaitAction
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.screen import RestOption, ScreenType


def test_startup_state_wait_is_longer_than_in_game_stuck_guard():
    assert Coordinator.STATE_WAIT_SECONDS == 2.0
    assert Coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT >= 45
    assert Coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT == 10
    assert (
        Coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT
        > Coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT
    )


def test_coordinator_can_defer_stdin_thread_until_rl_import_completes(monkeypatch):
    started_targets = []

    class FakeThread:
        def __init__(self, *, target, args):
            self.target = target
            self.args = args
            self.daemon = False
            self.started = False

        def start(self):
            self.started = True
            started_targets.append(self.target.__name__)

        def is_alive(self):
            return self.started

    monkeypatch.setattr(coordinator_module.threading, "Thread", FakeThread)

    coordinator = Coordinator(start_input_thread=False)

    assert started_targets == ["write_stdout"]
    assert not coordinator.input_thread.is_alive()
    assert coordinator.output_thread.is_alive()

    coordinator.start_input_thread()
    coordinator.start_input_thread()

    assert started_targets == ["write_stdout", "read_stdin"]
    assert coordinator.input_thread.is_alive()


def test_startup_wait_requests_state_when_main_menu_does_not_push_initial_state():
    coordinator = object.__new__(Coordinator)
    coordinator.game_is_ready = False
    coordinator.in_game = False
    coordinator.last_game_state = None
    coordinator.pending_seed = None
    coordinator.game_over_state = None
    coordinator.STARTUP_MAX_WAIT_ATTEMPTS = 3
    coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT = 3
    sent_messages = []

    coordinator.clear_actions = lambda: None
    coordinator.receive_game_state_update = (
        lambda block=False, perform_callbacks=True: False
    )
    coordinator.send_message = (
        lambda message, wait_for_response=True: sent_messages.append(
            (message, wait_for_response)
        )
    )

    with pytest.raises(Exception, match="Communication Mod not responding"):
        coordinator.play_one_game(PlayerClass.IRONCLAD, ascension_level=0)

    assert ("state", False) in sent_messages


def test_idle_in_game_wait_requests_state_for_event_result_pages():
    coordinator = object.__new__(Coordinator)
    coordinator.last_game_state = SimpleNamespace(screen_type=ScreenType.EVENT)
    coordinator.action_queue = []
    sent_messages = []
    coordinator.send_message = (
        lambda message, wait_for_response=True: sent_messages.append(
            (message, wait_for_response)
        )
    )

    coordinator._request_state_during_idle_wait(1)

    assert sent_messages == [("state", False)]


def test_stuck_state_diagnostics_include_screen_action_queue_and_screen_fields():
    coordinator = object.__new__(Coordinator)
    coordinator.game_is_ready = False
    coordinator.in_game = True
    coordinator.action_queue = [RestAction(RestOption.SMITH), WaitAction(timeout=1)]
    coordinator._last_sent_message = "choose SMITH"
    coordinator._sent_message_count = 7
    coordinator._last_command_error = "Invalid command: choose"
    coordinator.last_game_state = SimpleNamespace(
        floor=17,
        turn=0,
        screen_type=ScreenType.REST,
        available_commands=["choose", "state"],
        screen=SimpleNamespace(
            rest_options=[RestOption.REST, RestOption.SMITH],
            has_rested=False,
        ),
    )

    details = coordinator._describe_stuck_state(consecutive_timeouts=10)

    assert "screen=ScreenType.REST" in details
    assert "floor=17" in details
    assert "queue_size=2" in details
    assert "next_action=RestAction" in details
    assert "last_sent=choose SMITH" in details
    assert "last_error=Invalid command: choose" in details
    assert "available_commands=['choose', 'state']" in details
    assert "rest_options=['REST', 'SMITH']" in details


def test_play_one_game_ignores_transient_out_of_game_without_game_over():
    coordinator = object.__new__(Coordinator)
    coordinator.game_is_ready = True
    coordinator.in_game = True
    coordinator.last_game_state = SimpleNamespace(screen_type=ScreenType.COMBAT_REWARD)
    coordinator.pending_seed = None
    coordinator.game_over_state = None
    coordinator.action_queue = []
    coordinator.STARTUP_MAX_WAIT_ATTEMPTS = 3
    coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT = 3
    coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT = 3
    sent_messages = []
    executed_actions = []
    states = ["transient", "resumed", "game_over"]

    coordinator.state_change_callback = lambda game_state: None
    coordinator.clear_actions = lambda: coordinator.action_queue.clear()
    coordinator.check_communication_threads = lambda: True
    coordinator.execute_next_action_if_ready = (
        lambda: executed_actions.append(coordinator.action_queue.pop(0))
        if coordinator.action_queue
        else None
    )
    coordinator.execute_next_action = lambda: None
    coordinator._run_deferred_state_callback_if_idle = lambda: False
    coordinator.send_message = (
        lambda message, wait_for_response=True: sent_messages.append(
            (message, wait_for_response)
        )
    )

    def receive_game_state_update(block=False, perform_callbacks=True):
        state = states.pop(0)
        if state == "transient":
            coordinator.in_game = False
            coordinator.last_game_state = SimpleNamespace(
                screen_type=ScreenType.COMBAT_REWARD
            )
            coordinator.action_queue.append("stale_start_game")
        elif state == "resumed":
            coordinator.in_game = True
            coordinator.last_game_state = SimpleNamespace(screen_type=ScreenType.MAP)
        else:
            coordinator.in_game = False
            coordinator.last_game_state = SimpleNamespace(
                screen_type=ScreenType.GAME_OVER,
                screen=SimpleNamespace(victory=True),
            )
        return True

    coordinator.receive_game_state_update = receive_game_state_update

    assert coordinator.play_one_game(PlayerClass.IRONCLAD, ascension_level=0) is True
    assert ("state", False) in sent_messages
    assert executed_actions == []
