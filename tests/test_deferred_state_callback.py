import collections
import json
import queue
from types import SimpleNamespace

from spirecomm.communication.action import (
    ChooseAction,
    ChooseMapNodeAction,
    OptionalCardSelectConfirmAction,
    PlayCardAction,
    PotionAction,
    StartGameAction,
    WaitAction,
)
from spirecomm.communication.coordinator import Coordinator
from spirecomm.spire.character import PlayerClass
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
    coordinator._last_command_error = None
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


def _command_error_message(error="Invalid command: confirm"):
    return json.dumps(
        {
            "ready_for_command": False,
            "in_game": True,
            "error": error,
            "available_commands": ["play", "end", "wait", "state"],
        }
    )


def _out_of_game_start_ready_message():
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": False,
            "available_commands": ["start", "state"],
            "game_state": {},
        }
    )


def _stale_none_combat_message():
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": True,
            "available_commands": ["play", "end", "potion", "wait", "state"],
            "game_state": {
                "screen_type": "NONE",
                "room_phase": "COMBAT",
                "floor": 18,
                "act": 2,
                "class": "IRONCLAD",
            },
        }
    )


def test_repeated_command_error_is_handled_once_and_resyncs_state():
    coordinator = _coordinator_without_threads()
    errors = []
    coordinator.error_callback = lambda error: errors.append(error) or None
    coordinator.input_queue.put(_command_error_message())
    coordinator.input_queue.put(_command_error_message())

    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert errors == ["Invalid command: confirm"]
    assert coordinator.last_error is None
    assert [coordinator.output_queue.get_nowait(), coordinator.output_queue.get_nowait()] == [
        "state",
        "state",
    ]


def test_late_play_error_on_combat_reward_resyncs_without_error_callback():
    coordinator = _coordinator_without_threads()
    errors = []
    coordinator.error_callback = lambda error: errors.append(error) or None
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.COMBAT_REWARD,
        available_commands=["proceed", "key", "click", "wait", "state"],
    )
    coordinator.input_queue.put(
        _command_error_message(
            "Invalid command: play. Possible commands: [proceed, key, click, wait, state]"
        )
    )

    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert errors == []
    assert coordinator.last_error is None
    assert coordinator.output_queue.get_nowait() == "state"


def test_out_of_game_update_clears_stale_ready_wait_before_start_action():
    coordinator = _coordinator_without_threads()
    coordinator.action_queue.append(WaitAction(timeout=1))
    coordinator.out_of_game_callback = lambda: StartGameAction(PlayerClass.IRONCLAD)
    coordinator.input_queue.put(_out_of_game_start_ready_message())

    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert len(coordinator.action_queue) == 1
    assert isinstance(coordinator.action_queue[0], StartGameAction)


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


def test_duplicate_map_frame_after_map_choice_does_not_call_route_callback_again():
    coordinator = _coordinator_without_threads()
    node = SimpleNamespace(x=3, y=1, symbol="?")
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.MAP,
        available_commands=["choose", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            current_node=SimpleNamespace(x=0, y=0, symbol="M"),
            next_nodes=[node],
            boss_available=False,
        ),
    )
    calls = []

    def callback(game):
        calls.append(game.screen_type)
        return ChooseMapNodeAction(node)

    coordinator.state_change_callback = callback
    coordinator._queue_state_change_callback_action()
    coordinator.execute_next_action_if_ready()

    assert coordinator.output_queue.get_nowait() == "choose 0"

    coordinator._queue_state_change_callback_action()

    assert calls == [ScreenType.MAP]
    assert len(coordinator.action_queue) == 1
    assert isinstance(coordinator.action_queue[0], WaitAction)


def test_stale_none_combat_frame_after_play_waits_instead_of_calling_agent():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.NONE,
        available_commands=["play", "end", "potion", "wait", "state"],
        hand=[],
        floor=18,
        turn=3,
        in_combat=True,
    )
    calls = []

    def callback(game):
        calls.append(game.screen_type)
        return ChooseAction(0)

    coordinator.state_change_callback = callback
    coordinator.action_queue.append(PlayCardAction(card_index=0))

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "play 1"
    assert isinstance(coordinator.action_queue[0], WaitAction)

    coordinator.input_queue.put(_stale_none_combat_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    assert calls == []

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"

    coordinator.input_queue.put(_stale_none_combat_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert calls == []
    assert len(coordinator.action_queue) == 1
    assert isinstance(coordinator.action_queue[0], WaitAction)


def test_escape_potion_waits_until_stale_combat_frame_clears():
    coordinator = _coordinator_without_threads()
    smoke_bomb = SimpleNamespace(
        name="Smoke Bomb",
        potion_id="Smoke Bomb",
        effect_type="escape",
    )
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.NONE,
        available_commands=["play", "end", "potion", "wait", "state"],
        potions=[smoke_bomb],
        hand=[],
        floor=14,
        turn=1,
        in_combat=True,
    )
    calls = []

    def callback(game):
        calls.append(game.screen_type)
        return ChooseAction(0)

    coordinator.state_change_callback = callback
    coordinator.action_queue.append(PotionAction(True, potion=smoke_bomb))

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "potion use 0"
    assert isinstance(coordinator.action_queue[0], WaitAction)

    coordinator.input_queue.put(_stale_none_combat_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    assert calls == []

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"

    coordinator.input_queue.put(_stale_none_combat_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    assert calls == []
    assert len(coordinator.action_queue) == 1
    assert isinstance(coordinator.action_queue[0], WaitAction)

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"

    coordinator.input_queue.put(_stale_none_combat_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert calls == []
    assert len(coordinator.action_queue) == 1
    assert isinstance(coordinator.action_queue[0], WaitAction)
