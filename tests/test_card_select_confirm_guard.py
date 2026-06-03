import collections
from types import SimpleNamespace

from spirecomm.communication.action import (
    CardSelectAction,
    OptionalCardSelectConfirmAction,
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


def test_card_select_confirms_grid_selection_even_without_confirm_state_update():
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
    while coordinator.action_queue:
        coordinator.action_queue.popleft().execute(coordinator)

    assert coordinator.sent_messages == ["choose 0", "confirm"]


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
