import collections
from types import SimpleNamespace

from spirecomm.communication.action import (
    CardSelectAction,
    ClickAction,
    ChooseAction,
    KeyAction,
    OptionalCardSelectConfirmAction,
    WaitAction,
)
from spirecomm.spire.screen import ScreenType


class FakeCoordinator:
    def __init__(self, game_state):
        self.last_game_state = game_state
        self.action_queue = collections.deque()
        self.game_is_ready = True
        self.sent_messages = []

    def add_action_to_queue(self, action):
        self.action_queue.append(action)

    def send_message(self, message, wait_for_response=True):
        self.sent_messages.append(message)
        if wait_for_response:
            self.game_is_ready = False


def test_grid_choose_selection_queues_response_barriers_before_confirm():
    card = SimpleNamespace(name="Defend_R")
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.GRID,
            available_commands=["choose", "cancel", "key", "click", "wait", "state"],
            screen=SimpleNamespace(
                cards=[card],
                selected_cards=[],
                num_cards=1,
                any_number=False,
                confirm_up=False,
                card_positions=[],
            ),
        )
    )

    CardSelectAction([card]).execute(coordinator)
    selector, settle, confirm = list(coordinator.action_queue)

    assert isinstance(selector, ChooseAction)
    assert selector.requires_game_ready is True
    assert selector.wait_for_response is True
    assert isinstance(settle, WaitAction)
    assert settle.requires_game_ready is True
    assert settle.wait_for_response is True
    assert settle.timeout == 1
    assert isinstance(confirm, OptionalCardSelectConfirmAction)
    assert confirm.requires_game_ready is True
    assert confirm.wait_for_response is True
    assert confirm.settle_after_confirm is True


def test_grid_click_and_key_selectors_use_response_barriers():
    card = SimpleNamespace(name="Defend_R")

    click_coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.GRID,
            available_commands=["click", "key", "wait", "state"],
            screen=SimpleNamespace(
                cards=[card],
                selected_cards=[],
                num_cards=1,
                any_number=False,
                confirm_up=False,
                card_positions=[{"x": 100, "y": 200}],
            ),
        )
    )
    CardSelectAction([card]).execute(click_coordinator)
    click_selector, click_settle, _ = list(click_coordinator.action_queue)
    assert isinstance(click_selector, ClickAction)
    assert click_selector.requires_game_ready is True
    assert click_selector.wait_for_response is True
    assert isinstance(click_settle, WaitAction)
    assert click_settle.wait_for_response is True
    click_selector.execute(click_coordinator)
    assert click_coordinator.sent_messages == ["click 100 200"]
    assert click_coordinator.game_is_ready is False

    key_coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.GRID,
            available_commands=["key", "wait", "state"],
            screen=SimpleNamespace(
                cards=[card],
                selected_cards=[],
                num_cards=1,
                any_number=False,
                confirm_up=False,
                card_positions=[],
            ),
        )
    )
    CardSelectAction([card]).execute(key_coordinator)
    key_selector, key_settle, _ = list(key_coordinator.action_queue)
    assert isinstance(key_selector, KeyAction)
    assert key_selector.requires_game_ready is True
    assert key_selector.wait_for_response is True
    assert isinstance(key_settle, WaitAction)
    assert key_settle.wait_for_response is True
    key_selector.execute(key_coordinator)
    assert key_coordinator.sent_messages == ["key CARD_1"]
    assert key_coordinator.game_is_ready is False


def test_shared_action_serialization_defaults_remain_unchanged():
    click = ClickAction("proceed")
    choose = ChooseAction(0)
    wait = WaitAction(timeout=1)
    confirm = OptionalCardSelectConfirmAction()

    assert click.requires_game_ready is False
    assert click.wait_for_response is False
    assert choose.requires_game_ready is True
    assert choose.wait_for_response is False
    assert wait.requires_game_ready is False
    assert wait.wait_for_response is False
    assert confirm.requires_game_ready is False
    assert confirm.wait_for_response is False
    assert confirm.settle_after_confirm is False


def test_hand_select_card_select_waits_between_keys_and_confirm():
    cards = [SimpleNamespace(name=f"Card {index}") for index in range(3)]
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.HAND_SELECT,
            available_commands=["choose", "confirm", "key", "click", "wait", "state"],
            screen=SimpleNamespace(
                cards=cards,
                selected_cards=[],
                num_cards=2,
                any_number=False,
                confirm_up=False,
            ),
        )
    )

    CardSelectAction(cards[:2]).execute(coordinator)
    queued_actions = list(coordinator.action_queue)

    assert [type(action) for action in queued_actions] == [
        KeyAction,
        KeyAction,
        OptionalCardSelectConfirmAction,
    ]
    assert all(action.requires_game_ready for action in queued_actions)
    assert all(action.wait_for_response for action in queued_actions[:2])


def test_stale_card_select_confirm_does_not_fire_for_hand_select_without_confirm():
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.HAND_SELECT,
            available_commands=["play", "end", "key", "click", "wait", "state"],
            screen=SimpleNamespace(confirm_up=False),
        )
    )

    OptionalCardSelectConfirmAction(allow_stale_selection=True).execute(coordinator)

    assert coordinator.sent_messages == []


def test_stale_card_select_confirm_fires_for_hand_select_with_confirm_available():
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.HAND_SELECT,
            available_commands=[
                "choose",
                "potion",
                "confirm",
                "key",
                "click",
                "wait",
                "state",
            ],
            screen=SimpleNamespace(confirm_up=False),
        )
    )

    OptionalCardSelectConfirmAction(allow_stale_selection=True).execute(coordinator)

    assert coordinator.sent_messages == ["confirm"]


def test_stale_card_select_confirm_skips_after_screen_changes():
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.EVENT,
            available_commands=["choose", "wait", "state"],
            screen=SimpleNamespace(confirm_up=False),
        )
    )

    OptionalCardSelectConfirmAction(allow_stale_selection=True).execute(coordinator)

    assert coordinator.sent_messages == []


def test_choose_action_requests_state_when_choose_command_is_stale():
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.REST,
            available_commands=["potion", "proceed", "key", "click", "wait", "state"],
            screen=SimpleNamespace(),
        )
    )

    ChooseAction(choice_index=0).execute(coordinator)

    assert coordinator.sent_messages == ["state"]
