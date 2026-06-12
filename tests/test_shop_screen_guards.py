from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
from spirecomm.ai.priorities import IroncladPriority
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    CancelAction,
    ChooseShopkeeperAction,
    ChooseAction,
    LeaveAction,
    ProceedAction,
    WaitAction,
)
from spirecomm.spire.screen import ScreenType


def _agent_for_shop(**game_overrides):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.visited_shop = False
    agent.shop_purchase_made = False
    agent._leaving_shop_room = False
    agent._shop_exit_waits = 0
    agent.game = SimpleNamespace(**game_overrides)
    return agent


def _shop_card(card_id, price):
    return SimpleNamespace(card_id=card_id, name=card_id, price=price, upgrades=0)


class _BuyEverythingPriority:
    def should_skip(self, _card):
        return False

    def get_sorted_cards(self, cards):
        return cards


class _BuyEverythingUnsortedPriority:
    def should_skip(self, _card):
        return False


class _SkipCardsPriority:
    def should_skip(self, _card):
        return True

    def get_sorted_cards(self, cards):
        return cards


def test_shop_screen_exit_uses_leave_when_not_in_purchase_transition():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(cards=[], relics=[], potions=[], purge_available=False),
        gold=64,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "leave", "key", "click", "wait", "state"],
    )

    action = agent.handle_screen()

    assert isinstance(action, LeaveAction)


def test_shop_screen_purge_accepts_string_gold_and_purge_cost():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Offering", price="50")],
            relics=[],
            potions=[],
            purge_available=True,
            purge_cost="75",
        ),
        gold="200",
        deck=[_shop_card("Strike_R", price=0)],
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )
    agent.priorities = _BuyEverythingPriority()

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.name == "purge"


def test_shop_screen_continues_buying_after_purge_state_updates():
    screen = SimpleNamespace(
        cards=[_shop_card("Offering", price=100)],
        relics=[],
        potions=[],
        purge_available=True,
        purge_cost=75,
    )
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold=250,
        deck=[_shop_card("Strike_R", price=0)],
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = _BuyEverythingPriority()

    first = agent.handle_screen()

    assert isinstance(first, ChooseAction)
    assert first.name == "purge"

    agent.game.gold = 175
    screen.purge_available = False

    second = agent.handle_screen()

    assert isinstance(second, BuyCardAction)
    assert second.name == "Offering"


def test_shop_screen_skips_low_reliability_act1_cards_after_purge():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Havoc", price=22),
                _shop_card("Deep Breath", price=22),
            ],
            relics=[],
            potions=[],
            purge_available=False,
        ),
        gold=128,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Whirlwind", price=0),
            _shop_card("Anger", price=0),
            _shop_card("Second Wind", price=0),
        ],
        act=1,
        floor=10,
        in_combat=False,
        current_hp=39,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, CancelAction)


def test_shop_screen_buy_card_accepts_string_gold_and_price():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Offering", price="50")],
            relics=[],
            potions=[],
            purge_available=False,
        ),
        gold="200",
        deck=[],
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )
    agent.priorities = _BuyEverythingPriority()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Offering"


def test_shop_screen_buy_card_accepts_string_gold_without_sorted_priority():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Offering", price="50")],
            relics=[],
            potions=[],
            purge_available=False,
        ),
        gold="200",
        deck=[],
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )
    agent.priorities = _BuyEverythingUnsortedPriority()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Offering"


def test_shop_screen_buy_potion_accepts_string_gold_and_price():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Skip Me", price="1")],
            relics=[],
            potions=[SimpleNamespace(name="Fire Potion", price="75")],
            purge_available=False,
        ),
        gold="200",
        deck=[],
        are_potions_full=lambda: False,
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )
    agent.priorities = _SkipCardsPriority()

    action = agent.handle_screen()

    assert isinstance(action, BuyPotionAction)
    assert action.name == "Fire Potion"


def test_shop_relic_helper_accepts_string_gold_and_price():
    agent = _agent_for_shop()
    relic = SimpleNamespace(name="Burning Blood", price="100")

    assert agent._should_buy_relic(relic, gold="200") is True


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


def test_shop_room_exit_uses_cancel_group_when_return_is_available():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_ROOM,
        choice_available=True,
        available_commands=["choose", "potion", "return", "key", "click", "wait", "state"],
    )
    agent._leaving_shop_room = True

    action = agent.handle_screen()

    assert isinstance(action, CancelAction)


def test_shop_screen_waits_after_purchase_when_only_cancel_is_visible():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(cards=[], relics=[], potions=[], purge_available=False),
        gold=0,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.shop_purchase_made = True

    action = agent.handle_screen()

    assert isinstance(action, WaitAction)


def test_shop_screen_waits_after_purchase_when_only_leave_is_visible():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(cards=[], relics=[], potions=[], purge_available=False),
        gold=0,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "leave", "key", "click", "wait", "state"],
    )
    agent.shop_purchase_made = True

    action = agent.handle_screen()

    assert isinstance(action, WaitAction)


def test_shop_screen_post_purchase_wait_is_bounded_when_cancel_stays_visible():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(cards=[], relics=[], potions=[], purge_available=False),
        gold=43,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )
    agent.shop_purchase_made = True

    first = agent.handle_screen()
    second = agent.handle_screen()
    third = agent.handle_screen()

    assert isinstance(first, WaitAction)
    assert isinstance(second, WaitAction)
    assert isinstance(third, CancelAction)


def test_shop_room_exit_uses_cancel_group_from_cancel_available_flag():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_ROOM,
        choice_available=True,
        cancel_available=True,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )
    agent._leaving_shop_room = True

    action = agent.handle_screen()

    assert isinstance(action, CancelAction)
