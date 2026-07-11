import collections
import json
import queue
from types import SimpleNamespace

import pytest

from spirecomm.communication.action import (
    CardSelectAction,
    ChooseAction,
    ChooseMapNodeAction,
    CancelAction,
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


def _card_json(name, uuid):
    return {
        "id": name,
        "name": name,
        "type": "SKILL",
        "rarity": "COMMON",
        "upgrades": 0,
        "has_target": False,
        "cost": 1,
        "uuid": uuid,
    }


def _hand_select_state_message(hand, selected, available_commands):
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": True,
            "available_commands": available_commands,
            "game_state": {
                "screen_type": "HAND_SELECT",
                "room_phase": "COMBAT",
                "class": "IRONCLAD",
                "current_action": "discard",
                "screen_state": {
                    "hand": hand,
                    "selected": selected,
                    "max_cards": 2,
                    "can_pick_zero": False,
                },
            },
        }
    )


def _grid_state_message(
    cards,
    selected,
    confirm_up,
    available_commands,
    choice_list=False,
    num_cards=1,
):
    game_state = {
        "screen_type": "GRID",
        "room_phase": "COMPLETE",
        "class": "IRONCLAD",
        "screen_state": {
            "cards": cards,
            "selected_cards": selected,
            "num_cards": num_cards,
            "any_number": False,
            "confirm_up": confirm_up,
            "for_upgrade": False,
            "for_transform": False,
            "for_purge": True,
            "card_positions": [],
        },
    }
    if choice_list:
        game_state["choice_list"] = [card["name"] for card in cards]
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": True,
            "available_commands": available_commands,
            "game_state": game_state,
        }
    )


def test_grid_selection_and_confirm_ignore_stale_frames_until_fifo_barriers():
    coordinator = _coordinator_without_threads()
    card = SimpleNamespace(name="Strike_R")
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=[card],
            selected_cards=[],
            num_cards=1,
            any_number=False,
            confirm_up=False,
            card_positions=[],
        ),
    )
    callbacks = []
    coordinator.state_change_callback = (
        lambda game: callbacks.append(game.screen_type) or None
    )

    coordinator.action_queue.append(CardSelectAction([card]))
    coordinator.execute_next_action_if_ready()
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "choose 0"
    assert coordinator.game_is_ready is False

    strike = _card_json("Strike_R", "strike-1")
    coordinator.input_queue.put(
        _grid_state_message(
            [strike],
            [],
            False,
            ["choose", "potion", "cancel", "key", "click", "wait", "state"],
            choice_list=True,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike],
            [strike],
            True,
            ["potion", "confirm", "cancel", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike],
            [strike],
            True,
            ["potion", "confirm", "cancel", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"
    assert coordinator.game_is_ready is False
    assert not coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == []

    coordinator.input_queue.put(_event_state_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == [ScreenType.EVENT]
    assert coordinator.output_queue.empty()


def _serialized_grid_confirm_coordinator():
    coordinator = _coordinator_without_threads()
    card = _card_json("Strike_R", "strike-1")
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["confirm", "wait", "state"],
        screen=SimpleNamespace(
            cards=[SimpleNamespace(name="Strike_R")],
            selected_cards=[SimpleNamespace(name="Strike_R")],
            num_cards=1,
            any_number=False,
            confirm_up=True,
            card_positions=[],
        ),
    )
    callbacks = []
    coordinator.state_change_callback = (
        lambda game: callbacks.append(game.screen_type) or None
    )
    coordinator.action_queue.append(
        OptionalCardSelectConfirmAction(
            requires_game_ready=True,
            wait_for_response=True,
            settle_after_confirm=True,
        )
    )
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator._card_select_confirm_in_flight is True
    return coordinator, card, callbacks


def test_grid_timeout_does_not_repeat_serialized_confirm_before_first_response():
    coordinator, _, callbacks = _serialized_grid_confirm_coordinator()

    coordinator._request_state_during_action_wait(1)
    recovered = coordinator._handle_legacy_screen_timeout_recovery(1)

    assert coordinator.output_queue.get_nowait() == "state"
    assert coordinator.output_queue.empty()
    assert recovered is False
    assert callbacks == []


def test_grid_timeout_does_not_repeat_confirm_while_settle_barrier_waits():
    coordinator, card, callbacks = _serialized_grid_confirm_coordinator()
    coordinator.input_queue.put(
        _grid_state_message(
            [card],
            [card],
            True,
            ["confirm", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"
    assert coordinator._card_select_confirm_in_flight is True
    assert callbacks == []

    coordinator._request_state_during_action_wait(1)
    recovered = coordinator._handle_legacy_screen_timeout_recovery(1)

    assert coordinator.output_queue.get_nowait() == "state"
    assert coordinator.output_queue.empty()
    assert recovered is False
    assert callbacks == []


def test_grid_confirm_settle_response_clears_timeout_suppression():
    coordinator, card, callbacks = _serialized_grid_confirm_coordinator()
    stale_grid = _grid_state_message(
        [card],
        [card],
        True,
        ["confirm", "wait", "state"],
    )
    coordinator.input_queue.put(stale_grid)
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"
    assert callbacks == []

    coordinator.input_queue.put(stale_grid)
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator._run_deferred_state_callback_if_idle()

    assert callbacks == [ScreenType.GRID]
    assert coordinator._handle_legacy_screen_timeout_recovery(1) is True
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator.output_queue.empty()


def test_clear_actions_abandons_serialized_confirm_marker():
    coordinator = _coordinator_without_threads()
    coordinator._card_select_confirm_in_flight = True
    coordinator.action_queue.append(WaitAction(timeout=1))

    coordinator.clear_actions()

    assert coordinator.action_queue == collections.deque()
    assert coordinator._card_select_confirm_in_flight is False


def test_command_error_discard_abandons_serialized_confirm_marker():
    coordinator = _coordinator_without_threads()
    coordinator._card_select_confirm_in_flight = True
    coordinator.action_queue.append(WaitAction(timeout=1))
    coordinator.input_queue.put(_command_error_message())

    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert coordinator._card_select_confirm_in_flight is False
    assert coordinator.action_queue == collections.deque()
    assert coordinator.output_queue.get_nowait() == "state"


def test_serialized_confirm_send_exception_rolls_back_marker():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["confirm", "wait", "state"],
        screen=SimpleNamespace(confirm_up=True),
    )
    action = OptionalCardSelectConfirmAction(settle_after_confirm=True)

    def raise_send(*args, **kwargs):
        raise RuntimeError("send failed")

    coordinator.send_message = raise_send

    with pytest.raises(RuntimeError, match="send failed"):
        action.execute(coordinator)

    assert coordinator._card_select_confirm_in_flight is False
    assert coordinator.action_queue == collections.deque()


def test_serialized_confirm_barrier_exception_rolls_back_marker():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["confirm", "wait", "state"],
        screen=SimpleNamespace(confirm_up=True),
    )
    action = OptionalCardSelectConfirmAction(settle_after_confirm=True)

    def raise_queue(action_to_queue):
        raise RuntimeError("queue failed")

    coordinator.add_action_to_queue = raise_queue

    with pytest.raises(RuntimeError, match="queue failed"):
        action.execute(coordinator)

    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator._card_select_confirm_in_flight is False
    assert coordinator.action_queue == collections.deque()


def test_grid_timeout_exact_over_selection_does_not_confirm():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        screen=SimpleNamespace(
            selected_cards=[SimpleNamespace(), SimpleNamespace()],
            num_cards=1,
            any_number=False,
            confirm_up=True,
        ),
    )

    assert coordinator._handle_legacy_screen_timeout_recovery(1) is False
    assert coordinator.output_queue.empty()


def test_grid_timeout_any_number_over_selection_still_confirms():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        screen=SimpleNamespace(
            selected_cards=[SimpleNamespace(), SimpleNamespace()],
            num_cards=1,
            any_number=True,
            confirm_up=True,
        ),
    )

    assert coordinator._handle_legacy_screen_timeout_recovery(1) is True
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator.output_queue.empty()


def test_two_card_grid_selection_serializes_each_selector_and_confirm():
    coordinator = _coordinator_without_threads()
    cards = [
        SimpleNamespace(name="Strike_R"),
        SimpleNamespace(name="Defend_R"),
    ]
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=cards,
            selected_cards=[],
            num_cards=2,
            any_number=False,
            confirm_up=False,
            card_positions=[],
        ),
    )
    callbacks = []
    coordinator.state_change_callback = (
        lambda game: callbacks.append(game.screen_type) or None
    )
    commands = []

    coordinator.action_queue.append(CardSelectAction(cards))
    coordinator.execute_next_action_if_ready()
    coordinator.execute_next_action_if_ready()
    commands.append(coordinator.output_queue.get_nowait())
    assert commands[-1] == "choose 1"
    assert coordinator.game_is_ready is False

    strike = _card_json("Strike_R", "strike-1")
    defend = _card_json("Defend_R", "defend-1")
    selector_commands = ["choose", "potion", "cancel", "key", "click", "wait", "state"]
    confirm_commands = ["potion", "confirm", "cancel", "key", "click", "wait", "state"]

    coordinator.input_queue.put(
        _grid_state_message(
            [strike, defend],
            [],
            False,
            selector_commands,
            choice_list=True,
            num_cards=2,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    commands.append(coordinator.output_queue.get_nowait())
    assert commands[-1] == "wait 1"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike, defend],
            [defend],
            False,
            selector_commands,
            num_cards=2,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    commands.append(coordinator.output_queue.get_nowait())
    assert commands[-1] == "choose 0"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike, defend],
            [defend],
            False,
            selector_commands,
            num_cards=2,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    commands.append(coordinator.output_queue.get_nowait())
    assert commands[-1] == "wait 1"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike, defend],
            [strike, defend],
            True,
            confirm_commands,
            num_cards=2,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    commands.append(coordinator.output_queue.get_nowait())
    assert commands[-1] == "confirm"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike, defend],
            [strike, defend],
            True,
            confirm_commands,
            num_cards=2,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    commands.append(coordinator.output_queue.get_nowait())
    assert commands[-1] == "wait 1"
    assert coordinator.game_is_ready is False
    assert not coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == []

    assert commands == [
        "choose 1",
        "wait 1",
        "choose 0",
        "wait 1",
        "confirm",
        "wait 1",
    ]
    assert commands.count("choose 1") == 1
    assert commands.count("choose 0") == 1
    assert commands.count("confirm") == 1

    coordinator.input_queue.put(_event_state_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == [ScreenType.EVENT]
    assert coordinator.output_queue.empty()


def test_hand_select_confirm_waits_for_final_key_response_without_stale_callback():
    coordinator = _coordinator_without_threads()
    cards = [
        SimpleNamespace(name="Card 1"),
        SimpleNamespace(name="Card 2"),
    ]
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.HAND_SELECT,
        available_commands=["choose", "confirm", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=cards,
            selected_cards=[],
            num_cards=2,
            can_pick_zero=False,
        ),
    )
    callbacks = []
    coordinator.state_change_callback = (
        lambda game: callbacks.append(game.screen_type) or ChooseAction(0)
    )

    coordinator.action_queue.append(CardSelectAction(cards))
    coordinator.execute_next_action_if_ready()
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "key CARD_2"

    first = _card_json("Card 1", "card-1")
    second = _card_json("Card 2", "card-2")
    coordinator.input_queue.put(
        _hand_select_state_message(
            [first, second],
            [second],
            ["choose", "confirm", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(
        block=False,
        perform_callbacks=True,
    )
    assert callbacks == []

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "key CARD_1"
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.empty()

    coordinator.input_queue.put(
        _hand_select_state_message(
            [first, second],
            [first, second],
            ["confirm", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(
        block=False,
        perform_callbacks=True,
    )
    assert callbacks == []

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator.output_queue.empty()
    assert not coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == []


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
    coordinator._card_select_confirm_in_flight = True
    coordinator.action_queue.append(WaitAction(timeout=1))
    coordinator.out_of_game_callback = lambda: StartGameAction(PlayerClass.IRONCLAD)
    coordinator.input_queue.put(_out_of_game_start_ready_message())

    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)

    assert len(coordinator.action_queue) == 1
    assert isinstance(coordinator.action_queue[0], StartGameAction)
    assert coordinator._card_select_confirm_in_flight is False


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


def test_duplicate_shop_screen_after_exit_command_does_not_call_shop_callback_again():
    coordinator = _coordinator_without_threads()
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.SHOP_SCREEN,
        available_commands=["leave", "choose", "key", "click", "wait", "state"],
        screen=SimpleNamespace(),
    )
    calls = []

    def callback(game):
        calls.append(game.screen_type)
        return CancelAction()

    coordinator.state_change_callback = callback
    coordinator._queue_state_change_callback_action()
    coordinator.execute_next_action_if_ready()

    assert coordinator.output_queue.get_nowait() == "leave"

    coordinator.game_is_ready = True
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"

    coordinator._queue_state_change_callback_action()

    assert calls == [ScreenType.SHOP_SCREEN]
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
