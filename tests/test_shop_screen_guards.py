from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
from spirecomm.ai.priorities import IroncladPriority
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyRelicAction,
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
    agent._shop_bought_card_this_shop = False
    agent._shop_purged_this_shop = False
    agent._leaving_shop_room = False
    agent._shop_exit_waits = 0
    agent.game = SimpleNamespace(**game_overrides)
    return agent


def _shop_card(card_id, price):
    return SimpleNamespace(card_id=card_id, name=card_id, price=price, upgrades=0)


def _upgraded_shop_card(card_id, price):
    card = _shop_card(card_id, price)
    card.name = f"{card_id}+"
    card.upgrades = 1
    return card


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


def test_shop_screen_buys_supported_perfected_strike_before_early_act1_purge():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Perfected Strike", price=47)],
            relics=[],
            potions=[],
            purge_available=True,
            purge_cost=75,
        ),
        gold=112,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Headbutt", price=0),
        ],
        act=1,
        floor=2,
        in_combat=False,
        current_hp=68,
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

    assert isinstance(action, BuyCardAction)
    assert action.name == "Perfected Strike"


def test_shop_screen_keeps_purge_before_unsupported_perfected_strike():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Perfected Strike", price=47)],
            relics=[],
            potions=[],
            purge_available=True,
            purge_cost=75,
        ),
        gold=112,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Headbutt", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Carnage", price=0),
            _shop_card("Perfected Strike", price=0),
        ],
        act=1,
        floor=6,
        in_combat=False,
        current_hp=68,
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

    assert isinstance(action, ChooseAction)
    assert action.name == "purge"


def test_shop_screen_buys_membership_card_before_paid_purge():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Flex", price=60), _shop_card("Havoc", price=50)],
            relics=[SimpleNamespace(name="Membership Card", price=168)],
            potions=[],
            purge_available=True,
            purge_cost=75,
        ),
        gold=185,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Whirlwind", price=0),
            _shop_card("Shrug It Off+", price=0),
            _shop_card("Pommel Strike", price=0),
            _shop_card("Anger", price=0),
            _shop_card("Sever Soul", price=0),
            _shop_card("Ghostly Armor", price=0),
        ],
        act=1,
        floor=14,
        in_combat=False,
        current_hp=62,
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

    assert isinstance(action, BuyRelicAction)
    assert action.name == "Membership Card"


def test_shop_screen_leaves_after_purge_when_only_non_priority_card_remains():
    screen = SimpleNamespace(
        cards=[_shop_card("Shrug It Off", price=56)],
        relics=[],
        potions=[],
        purge_available=True,
        purge_cost=75,
    )
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold=156,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Pommel Strike", price=0),
        ],
        act=1,
        floor=2,
        in_combat=False,
        current_hp=68,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    first = agent.handle_screen()

    assert isinstance(first, ChooseAction)
    assert first.name == "purge"

    agent.game.gold = 81
    screen.purge_available = False

    second = agent.handle_screen()

    assert isinstance(second, CancelAction)


def test_shop_screen_skips_strength_potion_when_no_priority_purchase_is_available():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Twin Strike", price=23),
                _shop_card("Dropkick", price=73),
                _shop_card("Entrench", price=80),
                _shop_card("Limit Break", price=142),
                _shop_card("Inflame", price=74),
                _shop_card("Deep Breath", price=94),
                _shop_card("Sadistic Nature", price=173),
            ],
            relics=[
                SimpleNamespace(name="Blue Candle", price=238),
                SimpleNamespace(name="Singing Bowl", price=252),
                SimpleNamespace(name="Chemical X", price=143),
            ],
            potions=[
                SimpleNamespace(name="Swift Potion", price=50),
                SimpleNamespace(name="Flex Potion", price=50),
                SimpleNamespace(name="Strength Potion", price=50),
            ],
            purge_available=True,
            purge_cost=100,
        ),
        gold=73,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Inflame", price=0),
            _shop_card("Whirlwind", price=0),
            _shop_card("Seeing Red", price=0),
        ],
        act=1,
        floor=8,
        in_combat=False,
        current_hp=62,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "leave", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, LeaveAction)


def test_shop_screen_skips_fire_potion_after_purge_when_no_priority_purchase_is_available():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Sword Boomerang", price=50),
                _shop_card("Iron Wave", price=49),
                _shop_card("True Grit", price=22),
                _shop_card("Dual Wield", price=82),
                _shop_card("Berserk", price=153),
                _shop_card("Purity", price=85),
                _shop_card("Violence", price=165),
            ],
            relics=[
                SimpleNamespace(name="Frozen Egg", price=241),
                SimpleNamespace(name="Bottled Flame", price=257),
                SimpleNamespace(name="Hand Drill", price=149),
            ],
            potions=[
                SimpleNamespace(name="Dexterity Potion", price=50),
                SimpleNamespace(name="Skill Potion", price=50),
                SimpleNamespace(name="Fire Potion", price=50),
            ],
            purge_available=False,
            purge_cost=100,
        ),
        gold=70,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Shockwave", price=0),
            _shop_card("Reckless Charge", price=0),
            _shop_card("Shockwave", price=0),
            _shop_card("Iron Wave", price=0),
        ],
        act=1,
        floor=4,
        in_combat=False,
        current_hp=56,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "leave", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()
    agent._shop_purged_this_shop = True

    action = agent.handle_screen()

    assert isinstance(action, LeaveAction)


def test_shop_screen_buys_act1_frontload_after_purge_before_block_potion():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Carnage", price=69),
                _shop_card("Twin Strike", price=26),
                _shop_card("Flame Barrier", price=77),
                _shop_card("Bloodletting", price=78),
                _shop_card("Rupture", price=75),
                _shop_card("Panacea", price=81),
                _shop_card("Apotheosis", price=197),
            ],
            relics=[
                SimpleNamespace(name="Wing Boots", price=309),
                SimpleNamespace(name="Bird-Faced Urn", price=312),
                SimpleNamespace(name="Orrery", price=151),
            ],
            potions=[
                SimpleNamespace(name="Fairy in a Bottle", price=101),
                SimpleNamespace(name="Block Potion", price=48),
                SimpleNamespace(name="Block Potion", price=50),
            ],
            purge_available=False,
            purge_cost=100,
        ),
        gold=70,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Flex", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Hemokinesis", price=0),
        ],
        act=1,
        floor=4,
        in_combat=False,
        current_hp=71,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()
    agent._shop_purged_this_shop = True

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name in {"Carnage", "Twin Strike"}


def test_shop_screen_skips_paid_bandage_up_when_no_priority_purchase_is_available():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Bandage Up", price=85)],
            relics=[],
            potions=[],
            purge_available=False,
            purge_cost=100,
        ),
        gold=98,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Reckless Charge", price=0),
            _shop_card("Shrug It Off+", price=0),
            _shop_card("True Grit", price=0),
            _shop_card("Clothesline", price=0),
        ],
        act=1,
        floor=12,
        in_combat=False,
        current_hp=57,
        max_hp=85,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert not isinstance(action, BuyCardAction)
    assert isinstance(action, (CancelAction, LeaveAction))


def test_shop_screen_buys_supported_perfected_strike_over_bandage_up():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Bandage Up", price=85),
                _shop_card("Perfected Strike", price=51),
            ],
            relics=[],
            potions=[],
            purge_available=True,
            purge_cost=100,
        ),
        gold=151,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Headbutt+", price=0),
            _shop_card("Anger+", price=0),
        ],
        act=1,
        floor=11,
        in_combat=False,
        current_hp=56,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Perfected Strike"


def test_shop_screen_skips_paid_blood_for_blood_without_self_damage_support():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Blood for Blood", price=78)],
            relics=[],
            potions=[],
            purge_available=False,
            purge_cost=100,
        ),
        gold=146,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Shrug It Off", price=0),
        ],
        act=1,
        floor=13,
        in_combat=False,
        current_hp=58,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert not isinstance(action, BuyCardAction)
    assert isinstance(action, (CancelAction, LeaveAction))


def test_shop_screen_skips_paid_burning_pact_without_exhaust_payoff():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Burning Pact", price=78)],
            relics=[],
            potions=[],
            purge_available=False,
            purge_cost=100,
        ),
        gold=142,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Pommel Strike", price=0),
            _shop_card("Twin Strike", price=0),
        ],
        act=1,
        floor=13,
        in_combat=False,
        current_hp=60,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert not isinstance(action, BuyCardAction)
    assert isinstance(action, (CancelAction, LeaveAction))


def test_shop_screen_buys_discounted_act1_perfected_strike_before_purge():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Perfected Strike", price=26),
                _shop_card("Pommel Strike", price=49),
                _shop_card("Havoc", price=50),
            ],
            relics=[],
            potions=[SimpleNamespace(name="Block Potion", price=51)],
            purge_available=True,
            purge_cost=100,
        ),
        gold=225,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Trip+", price=0),
            _shop_card("Disarm", price=0),
            _shop_card("Uppercut", price=0),
            _shop_card("Flame Barrier", price=0),
            _shop_card("True Grit", price=0),
            _shop_card("Hemokinesis", price=0),
            _shop_card("Burning Pact", price=0),
        ],
        act=1,
        floor=10,
        in_combat=False,
        current_hp=56,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Perfected Strike"


def test_shop_screen_buys_supported_act1_perfected_strike_before_purge_trace():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Perfected Strike", price=51),
                _shop_card("Dropkick", price=80),
                _shop_card("Entrench", price=81),
                _shop_card("Havoc", price=47),
            ],
            relics=[],
            potions=[],
            purge_available=True,
            purge_cost=75,
        ),
        gold=149,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Twin Strike", price=0),
            _shop_card("Seeing Red", price=0),
            _shop_card("Anger+", price=0),
            _shop_card("Twin Strike", price=0),
            _shop_card("Twin Strike", price=0),
            _shop_card("Burning Pact", price=0),
        ],
        act=1,
        floor=11,
        in_combat=False,
        current_hp=58,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Perfected Strike"


def test_shop_screen_buys_supported_act1_perfected_strike_after_purge_trace():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Perfected Strike", price=51),
                _shop_card("Dropkick", price=80),
                _shop_card("Entrench", price=81),
                _shop_card("Havoc", price=47),
            ],
            relics=[],
            potions=[],
            purge_available=False,
            purge_cost=75,
        ),
        gold=74,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Twin Strike", price=0),
            _shop_card("Seeing Red", price=0),
            _shop_card("Anger+", price=0),
            _shop_card("Twin Strike", price=0),
            _shop_card("Twin Strike", price=0),
            _shop_card("Burning Pact", price=0),
        ],
        act=1,
        floor=11,
        in_combat=False,
        current_hp=58,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Perfected Strike"


def test_shop_screen_buys_discounted_supported_perfected_strike_after_act2_purge_trace():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _upgraded_shop_card("Heavy Blade", price=18),
                _upgraded_shop_card("Perfected Strike", price=38),
                _shop_card("Havoc", price=38),
                _shop_card("True Grit", price=37),
                _shop_card("Dark Embrace", price=62),
                _upgraded_shop_card("Swift Strike", price=77),
                _shop_card("Magnetism", price=135),
            ],
            relics=[
                SimpleNamespace(name="Eternal Feather", price=210),
                SimpleNamespace(name="Ginger", price=233),
                SimpleNamespace(name="Prismatic Shard", price=121),
            ],
            potions=[],
            purge_available=False,
            purge_cost=100,
        ),
        gold=191,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _upgraded_shop_card("Bash", price=0),
            _upgraded_shop_card("Second Wind", price=0),
            _upgraded_shop_card("True Grit", price=0),
            _upgraded_shop_card("Bloodletting", price=0),
            _upgraded_shop_card("Clothesline", price=0),
            _upgraded_shop_card("Havoc", price=0),
            _upgraded_shop_card("Feed", price=0),
            _upgraded_shop_card("Immolate", price=0),
            _shop_card("Curse of the Bell", price=0),
            _upgraded_shop_card("Thunderclap", price=0),
            _shop_card("Bloodletting", price=0),
            _upgraded_shop_card("Cleave", price=0),
        ],
        act=2,
        floor=27,
        in_combat=False,
        current_hp=51,
        max_hp=91,
        relics=[
            "Burning Blood",
            "Neow's Lament",
            "Molten Egg",
            "Mercury Hourglass",
            "Calling Bell",
            "Strawberry",
            "The Courier",
            "Peace Pipe",
            "Lizard Tail",
        ],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: True,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()
    agent.shop_purchase_made = True
    agent._shop_purged_this_shop = True
    agent._shop_purchase_signature = (271, True, 7, 3, 0)

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert "Perfected Strike" in action.name


def test_shop_screen_buys_deep_discount_perfected_strike_over_carnage_trace():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Carnage", price=78),
                _shop_card("Perfected Strike", price=23),
                _shop_card("Havoc", price=54),
                _shop_card("Flex", price=45),
                _shop_card("Feel No Pain", price=77),
                _shop_card("Finesse", price=94),
                _shop_card("Secret Weapon", price=162),
            ],
            relics=[
                SimpleNamespace(name="Ornamental Fan", price=238),
                SimpleNamespace(name="Lizard Tail", price=312),
                SimpleNamespace(name="Lee's Waffle", price=155),
            ],
            potions=[
                SimpleNamespace(name="Duplication Potion", price=78),
                SimpleNamespace(name="Duplication Potion", price=77),
                SimpleNamespace(name="Explosive Potion", price=52),
            ],
            purge_available=False,
            purge_cost=125,
        ),
        gold=259,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Twin Strike", price=0),
            _upgraded_shop_card("Pommel Strike", price=0),
            _shop_card("Berserk", price=0),
            _shop_card("Heavy Blade", price=0),
            _shop_card("Pommel Strike", price=0),
            _shop_card("Anger", price=0),
            _shop_card("Offering", price=0),
            _shop_card("Combust", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("True Grit", price=0),
            _shop_card("Clothesline", price=0),
            _shop_card("Impervious", price=0),
            _upgraded_shop_card("Headbutt", price=0),
            _shop_card("Clothesline", price=0),
            _upgraded_shop_card("Thunderclap", price=0),
            _shop_card("Uppercut", price=0),
            _shop_card("Normality", price=0),
        ],
        act=2,
        floor=28,
        in_combat=False,
        current_hp=43,
        max_hp=80,
        relics=[
            "Burning Blood",
            "Tiny Chest",
            "Neow's Lament",
            "Sundial",
            "Toxic Egg",
            "Thread and Needle",
            "The Courier",
            "Red Skull",
            "Lizard Tail",
        ],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Perfected Strike"


def test_shop_screen_skips_low_gold_block_potion_without_priority_purchase_trace():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Body Slam", price=50),
                _shop_card("Sword Boomerang", price=25),
                _shop_card("Armaments", price=46),
                _shop_card("Limit Break", price=142),
                _shop_card("Inflame", price=79),
                _shop_card("Mind Blast", price=82),
                _shop_card("Transmutation", price=183),
            ],
            relics=[
                SimpleNamespace(name="The Boot", price=143),
                SimpleNamespace(name="Art of War", price=155),
                SimpleNamespace(name="Membership Card", price=147),
            ],
            potions=[
                SimpleNamespace(name="Block Potion", price=48),
                SimpleNamespace(name="Attack Potion", price=48),
                SimpleNamespace(name="Swift Potion", price=51),
            ],
            purge_available=False,
            purge_cost=100,
        ),
        gold=57,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _upgraded_shop_card("Bash", price=0),
            _shop_card("Heavy Blade", price=0),
            _shop_card("Headbutt", price=0),
        ],
        act=1,
        floor=5,
        in_combat=False,
        current_hp=62,
        max_hp=80,
        relics=["Burning Blood", "Orichalcum"],
        player=SimpleNamespace(energy=3, powers=[]),
        are_potions_full=lambda: False,
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()

    action = agent.handle_screen()

    assert isinstance(action, CancelAction)


def test_shop_screen_does_not_buy_second_card_after_card_purchase_updates():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Shrug It Off", price=45)],
            relics=[],
            potions=[],
            purge_available=False,
        ),
        gold=100,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Pommel Strike", price=0),
            _shop_card("Disarm", price=0),
            _shop_card("Corruption", price=0),
        ],
        act=2,
        floor=31,
        in_combat=False,
        current_hp=54,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=4, powers=[]),
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()
    agent.shop_purchase_made = True
    agent._shop_bought_card_this_shop = True
    agent._shop_purchase_signature = (150, False, 2, 0, 0)

    action = agent.handle_screen()

    assert isinstance(action, CancelAction)


def test_shop_screen_can_buy_relic_after_card_purchase_updates():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Shrug It Off", price=45)],
            relics=[SimpleNamespace(name="Burning Blood", price=50)],
            potions=[],
            purge_available=False,
        ),
        gold=100,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Pommel Strike", price=0),
            _shop_card("Disarm", price=0),
            _shop_card("Corruption", price=0),
        ],
        act=2,
        floor=31,
        in_combat=False,
        current_hp=54,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=4, powers=[]),
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()
    agent.shop_purchase_made = True
    agent._shop_bought_card_this_shop = True
    agent._shop_purchase_signature = (150, False, 2, 1, 0)

    action = agent.handle_screen()

    assert isinstance(action, BuyRelicAction)
    assert action.name == "Burning Blood"


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


def test_shop_screen_skips_forethought_before_act1_boss():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Forethought", price=75)],
            relics=[],
            potions=[],
            purge_available=False,
        ),
        gold=140,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Cleave", price=0),
            _shop_card("Headbutt", price=0),
            _shop_card("Shockwave", price=0),
            _shop_card("Shrug It Off", price=0),
            _shop_card("Burning Pact", price=0),
            _shop_card("Second Wind", price=0),
        ],
        act=1,
        floor=14,
        act_boss="Slime Boss",
        in_combat=False,
        current_hp=61,
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


def test_shop_screen_skips_paid_rage_when_no_high_attack_density_support():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Rage", price=60)],
            relics=[],
            potions=[],
            purge_available=False,
        ),
        gold=117,
        deck=[
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Strike_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Defend_R", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Shrug It Off", price=0),
            _shop_card("Anger", price=0),
            _shop_card("True Grit", price=0),
        ],
        act=1,
        floor=5,
        in_combat=False,
        current_hp=64,
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


def test_shop_screen_buys_offering_over_blood_vial_trace():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[
                _shop_card("Feed", price=72),
                _shop_card("Pummel", price=71),
                _shop_card("Offering", price=136),
                _shop_card("Warcry", price=50),
                _shop_card("Evolve", price=76),
                _shop_card("Impatience", price=97),
                _shop_card("Panache", price=163),
            ],
            relics=[
                SimpleNamespace(name="Toxic Egg", price=259),
                SimpleNamespace(name="Blood Vial", price=152),
                SimpleNamespace(name="Frozen Eye", price=151),
            ],
            potions=[
                SimpleNamespace(name="Fear Potion", price=51),
                SimpleNamespace(name="Heart of Iron", price=101),
                SimpleNamespace(name="Explosive Potion", price=51),
            ],
            purge_available=False,
            purge_cost=125,
        ),
        gold=236,
        deck=[
            _upgraded_shop_card("Defend", price=0),
            _upgraded_shop_card("Defend", price=0),
            _upgraded_shop_card("Defend", price=0),
            _shop_card("Bash", price=0),
            _shop_card("Rage", price=0),
            _shop_card("Combust", price=0),
            _shop_card("Thunderclap", price=0),
            _upgraded_shop_card("Pommel Strike", price=0),
            _upgraded_shop_card("Anger", price=0),
            _shop_card("True Grit", price=0),
            _shop_card("Anger", price=0),
            _upgraded_shop_card("Shrug It Off", price=0),
            _upgraded_shop_card("Impervious", price=0),
            _shop_card("Shrug It Off", price=0),
            _shop_card("True Grit", price=0),
            _shop_card("Immolate", price=0),
            _upgraded_shop_card("Armaments", price=0),
            _shop_card("Shrug It Off", price=0),
            _shop_card("Pommel Strike", price=0),
        ],
        act=2,
        floor=29,
        in_combat=False,
        current_hp=17,
        max_hp=80,
        relics=[],
        player=SimpleNamespace(energy=3, powers=[]),
        cancel_available=True,
        proceed_available=False,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
    )
    agent.priorities = IroncladPriority()
    agent.deck_strategy = IroncladDeckStrategy()
    agent._shop_purged_this_shop = True

    action = agent.handle_screen()

    assert isinstance(action, BuyCardAction)
    assert action.name == "Offering"


def test_shop_screen_buy_potion_accepts_string_gold_and_price():
    agent = _agent_for_shop(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_shop_card("Skip Me", price="1")],
            relics=[],
            potions=[SimpleNamespace(name="Healing Potion", price="75")],
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
    assert action.name == "Healing Potion"


def test_shop_relic_helper_accepts_string_gold_and_price():
    agent = _agent_for_shop()
    relic = SimpleNamespace(name="Burning Blood", price="100")

    assert agent._should_buy_relic(relic, gold="200") is True


def test_shop_relic_helper_rejects_prismatic_shard_generic_budget():
    agent = _agent_for_shop()
    relic = SimpleNamespace(name="Prismatic Shard", price=121)

    assert agent._should_buy_relic(relic, gold=191) is False


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
