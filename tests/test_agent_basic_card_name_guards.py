from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.priorities import IroncladPriority
from spirecomm.communication.action import CardSelectAction, ChooseAction
from spirecomm.spire.screen import ScreenType


def _card(card_id, price=0, upgrades=0):
    return SimpleNamespace(
        card_id=card_id,
        name=card_id,
        price=price,
        upgrades=upgrades,
    )


def _agent(**game_overrides):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.priorities = IroncladPriority()
    agent.choose_good_card = False
    agent.shop_purchase_made = False
    agent._leaving_shop_room = False
    agent._shop_exit_waits = 0
    agent.game = SimpleNamespace(**game_overrides)
    return agent


def test_shop_purges_upgraded_strike_before_buying_good_card():
    agent = _agent(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=SimpleNamespace(
            cards=[_card("Offering", price=50)],
            relics=[],
            potions=[],
            purge_available=True,
            purge_cost=75,
        ),
        gold=200,
        deck=[_card("Strike_R+1", upgrades=1)],
        cancel_available=False,
        proceed_available=False,
        available_commands=["choose", "potion", "key", "click", "wait", "state"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.name == "purge"


def test_grid_removal_prioritizes_upgraded_strike_before_defend():
    upgraded_strike = _card("Strike_R+1", upgrades=1)
    defend = _card("Defend_R")
    carnage = _card("Carnage")
    agent = _agent(
        screen_type=ScreenType.GRID,
        choice_available=True,
        available_commands=["choose", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=[carnage, defend, upgraded_strike],
            selected_cards=[],
            num_cards=1,
            confirm_up=False,
            for_upgrade=False,
        ),
    )

    action = agent.handle_screen()

    assert isinstance(action, CardSelectAction)
    assert action.cards == [upgraded_strike]


def test_count_copies_in_deck_counts_upgraded_and_display_name_variants():
    agent = _agent(
        deck=[
            _card("Pommel Strike+1", upgrades=1),
            _card("Pommel_Strike"),
            _card("Shrug It Off"),
        ]
    )
    offered = _card("Pommel Strike")

    assert agent.count_copies_in_deck(offered) == 2


def test_upgrade_candidate_priority_uses_normalized_display_name():
    agent = _agent(deck=[])
    display_name_card = _card("Pommel Strike")
    internal_id_card = _card("Pommel_Strike")
    internal_id_card.name = "Pommel Strike"

    assert agent._score_upgrade_candidate(internal_id_card) == agent._score_upgrade_candidate(
        display_name_card
    )
