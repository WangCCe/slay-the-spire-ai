from types import SimpleNamespace

from spirecomm.communication.action import (
    CancelAction,
    EndTurnAction,
    LeaveAction,
    PlayCardAction,
    ProceedAction,
    WaitAction,
)
from spirecomm.spire.screen import ScreenType


def test_play_card_action_requests_state_when_uuid_card_left_hand():
    stale_card = SimpleNamespace(uuid="gone-card", name="Burning Pact")
    current_card = SimpleNamespace(uuid="other-card", name="Strike")
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(hand=[current_card]),
        send_message=sent_messages.append,
    )

    PlayCardAction(card=stale_card, card_index=0).execute(coordinator)

    assert sent_messages == ["state"]


def test_play_card_action_requests_state_when_play_command_is_stale():
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=["potion", "proceed", "key", "click", "wait", "state"],
            hand=[SimpleNamespace(uuid="strike", name="Strike")],
            screen_type=ScreenType.COMBAT_REWARD,
        ),
        send_message=sent_messages.append,
    )

    PlayCardAction(card_index=0, target_index=0).execute(coordinator)

    assert sent_messages == ["state"]


def test_play_card_action_queues_ready_wait_after_successful_play():
    sent_messages = []
    queued_actions = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=["play", "potion", "end", "key", "wait", "state"],
            hand=[SimpleNamespace(uuid="strike", name="Strike")],
            screen_type=ScreenType.NONE,
        ),
        send_message=sent_messages.append,
        add_action_to_queue=queued_actions.append,
    )

    PlayCardAction(card_index=0, target_index=0).execute(coordinator)

    assert sent_messages == ["play 1 0"]
    assert len(queued_actions) == 1
    assert isinstance(queued_actions[0], WaitAction)
    assert queued_actions[0].timeout == 1
    assert queued_actions[0].requires_game_ready is True


def test_end_turn_action_requests_state_when_turn_snapshot_is_stale():
    sent_messages = []
    action = EndTurnAction()
    action.expected_floor = 20
    action.expected_turn = 1
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            floor=20,
            turn=2,
            player=SimpleNamespace(energy=3),
            hand=[SimpleNamespace(name="Strike")],
            available_commands=["play", "end", "state"],
        ),
        send_message=sent_messages.append,
    )

    action.execute(coordinator)

    assert sent_messages == ["state"]


def test_cancel_action_uses_current_return_command_alias():
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "return",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_ROOM,
        ),
        send_message=sent_messages.append,
    )

    CancelAction().execute(coordinator)

    assert sent_messages == ["return"]


def test_cancel_action_queues_ready_wait_after_successful_exit_alias():
    sent_messages = []
    queued_actions = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "leave",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_SCREEN,
        ),
        send_message=sent_messages.append,
        add_action_to_queue=queued_actions.append,
    )

    CancelAction().execute(coordinator)

    assert sent_messages == ["leave"]
    assert len(queued_actions) == 1
    assert isinstance(queued_actions[0], WaitAction)
    assert queued_actions[0].timeout == 1
    assert queued_actions[0].requires_game_ready is True


def test_cancel_action_requests_state_when_cancel_group_is_stale():
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "proceed",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_SCREEN,
        ),
        send_message=sent_messages.append,
    )

    CancelAction().execute(coordinator)

    assert sent_messages == ["state"]


def test_leave_action_requests_state_when_leave_command_is_stale():
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "proceed",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_SCREEN,
        ),
        send_message=sent_messages.append,
    )

    LeaveAction().execute(coordinator)

    assert sent_messages == ["state"]


def test_leave_action_queues_ready_wait_after_successful_leave():
    sent_messages = []
    queued_actions = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "leave",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_SCREEN,
        ),
        send_message=sent_messages.append,
        add_action_to_queue=queued_actions.append,
    )

    LeaveAction().execute(coordinator)

    assert sent_messages == ["leave"]
    assert len(queued_actions) == 1
    assert isinstance(queued_actions[0], WaitAction)
    assert queued_actions[0].timeout == 1
    assert queued_actions[0].requires_game_ready is True


def test_proceed_action_requests_state_when_proceed_is_stale():
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "return",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_ROOM,
        ),
        send_message=sent_messages.append,
    )

    ProceedAction().execute(coordinator)

    assert sent_messages == ["state"]


def test_proceed_action_queues_ready_wait_after_successful_proceed():
    sent_messages = []
    queued_actions = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            available_commands=[
                "choose",
                "potion",
                "proceed",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen_type=ScreenType.SHOP_ROOM,
        ),
        send_message=sent_messages.append,
        add_action_to_queue=queued_actions.append,
    )

    ProceedAction().execute(coordinator)

    assert sent_messages == ["proceed"]
    assert len(queued_actions) == 1
    assert isinstance(queued_actions[0], WaitAction)
    assert queued_actions[0].timeout == 1
    assert queued_actions[0].requires_game_ready is True
