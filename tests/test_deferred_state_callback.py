import collections
import json
import queue
from types import SimpleNamespace

from spirecomm.communication.action import ChooseAction, OptionalCardSelectConfirmAction
from spirecomm.communication.coordinator import Coordinator
from spirecomm.spire.screen import ScreenType


def _coordinator_without_threads():
    coordinator = Coordinator.__new__(Coordinator)
    coordinator.input_queue = queue.Queue()
    coordinator.output_queue = queue.Queue()
    coordinator.action_queue = collections.deque()
    coordinator.game_is_ready = True
    coordinator.stop_after_run = False
    coordinator.in_game = True
    coordinator.last_game_state = None
    coordinator.last_error = None
    coordinator.game_over_state = None
    coordinator._last_screen_type = None
    coordinator._stability_wait_done = False
    coordinator._stability_wait_screens = set()
    coordinator._stability_wait_timeout = 5
    coordinator.pending_seed = None
    coordinator.error_callback = lambda error: None
    coordinator.out_of_game_callback = lambda: None
    return coordinator


def _event_state_message():
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": True,
            "available_commands": ["choose", "wait", "state"],
            "game_state": {
                "screen_type": "EVENT",
                "room_phase": "EVENT",
                "choice_list": ["Continue"],
                "screen_state": {
                    "event_name": "Note For Yourself",
                    "event_id": "NoteForYourself",
                    "body_text": "",
                    "options": [
                        {
                            "text": "Continue",
                            "label": "Continue",
                            "disabled": False,
                        }
                    ],
                },
            },
        }
    )


def test_deferred_callback_runs_after_noop_optional_confirm_drains_queue():
    coordinator = _coordinator_without_threads()
    coordinator.action_queue.append(OptionalCardSelectConfirmAction())
    calls = []

    def callback(game):
        calls.append(game.screen_type)
        return ChooseAction(0)

    coordinator.state_change_callback = callback
    coordinator.input_queue.put(_event_state_message())

    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    assert calls == []

    coordinator.execute_next_action_if_ready()
    coordinator._run_deferred_state_callback_if_idle()

    assert len(calls) == 1
    assert isinstance(coordinator.action_queue[0], ChooseAction)


def test_deferred_callback_waits_when_optional_confirm_sent_command():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["confirm", "wait", "state"],
        screen=SimpleNamespace(confirm_up=True),
    )
    coordinator.action_queue.append(OptionalCardSelectConfirmAction())
    coordinator._deferred_state_callback_pending = True
    coordinator._deferred_state_callback_message_count = 0
    coordinator._sent_message_count = 0
    calls = []

    def callback(game):
        calls.append(game.screen_type)
        return ChooseAction(0)

    coordinator.state_change_callback = callback

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "confirm"

    assert not coordinator._run_deferred_state_callback_if_idle()
    assert calls == []
    assert len(coordinator.action_queue) == 0


def test_waiting_ready_required_action_polls_state():
    coordinator = _coordinator_without_threads()
    coordinator.game_is_ready = False
    coordinator.last_game_state = SimpleNamespace(screen_type=ScreenType.EVENT)
    coordinator.action_queue.append(ChooseAction(0))

    coordinator._request_state_during_action_wait(1)

    assert coordinator.output_queue.get_nowait() == "state"


def test_event_choose_can_execute_when_choice_command_is_available_but_ready_false():
    coordinator = _coordinator_without_threads()
    coordinator.game_is_ready = False
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.EVENT,
        available_commands=["choose", "state", "wait"],
    )
    coordinator.action_queue.append(ChooseAction(0))

    coordinator.execute_next_action_if_ready()

    assert coordinator.output_queue.get_nowait() == "choose 0"
    assert len(coordinator.action_queue) == 0
