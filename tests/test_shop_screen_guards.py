from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.communication.action import ChooseShopkeeperAction, LeaveAction, ProceedAction
from spirecomm.spire.screen import ScreenType


def _agent_for_shop(**game_overrides):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.visited_shop = False
    agent.shop_purchase_made = False
    agent.game = SimpleNamespace(**game_overrides)
    return agent


def test_shop_screen_exit_uses_leave_instead_of_stale_cancel_flag():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(cards=[], relics=[], potions=[], purge_available=False),
        gold=64,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "leave", "key", "click", "wait", "state"],
    )
    agent.shop_purchase_made = True

    action = agent.handle_screen()

    assert isinstance(action, LeaveAction)


def test_shop_screen_exit_uses_proceed_when_that_is_the_available_exit():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(cards=[], relics=[], potions=[], purge_available=False),
        gold=64,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "proceed", "key", "click", "wait", "state"],
    )
    agent.shop_purchase_made = True

    action = agent.handle_screen()

    assert isinstance(action, ProceedAction)


def test_shop_room_does_not_reenter_after_exit_on_duplicate_room_state():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_ROOM,
        choice_available=True,
        available_commands=["proceed", "wait", "state"],
    )
    agent.visited_shop = True

    first = agent.handle_screen()
    second = agent.handle_screen()

    assert isinstance(first, ProceedAction)
    assert isinstance(second, ProceedAction)
    assert not isinstance(second, ChooseShopkeeperAction)
