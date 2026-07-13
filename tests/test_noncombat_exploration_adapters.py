from copy import deepcopy
from types import SimpleNamespace

import pytest

from spirecomm.ai.noncombat_exploration import (
    build_card_reward_proposal,
    build_event_shadow_proposal,
    build_route_shadow_proposal,
    build_shop_proposal,
)
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyRelicAction,
    CancelAction,
    CardRewardAction,
    ChooseAction,
    ChooseMapNodeAction,
    EventOptionAction,
    LeaveAction,
    ProceedAction,
    WaitAction,
)
from spirecomm.spire.map import Node
from spirecomm.spire.screen import ScreenType


def _item(name, *, price=0, item_id=None):
    return SimpleNamespace(
        name=name,
        card_id=item_id or name,
        relic_id=item_id or name,
        potion_id=item_id or name,
        price=price,
        upgrades=0,
    )


def _base_game(screen_type, screen, *, commands):
    return SimpleNamespace(
        screen_type=screen_type,
        screen=screen,
        available_commands=list(commands),
        cancel_available=any(
            command in commands for command in ("cancel", "leave", "return", "skip")
        ),
        proceed_available=any(command in commands for command in ("proceed", "confirm")),
        in_combat=False,
        floor=7,
        act=1,
        room_type="MonsterRoom",
        gold=150,
        current_hp=62,
        max_hp=80,
        deck=[_item("Strike_R")],
        relics=[],
        potions=[],
        hand=[],
        monsters=[],
        player=SimpleNamespace(current_hp=62, max_hp=80, block=0, energy=3),
    )


def _card_reward_game(cards, *, can_skip=True, can_bowl=False, commands=None):
    if commands is None:
        commands = ["choose", "cancel", "state"]
    return _base_game(
        ScreenType.CARD_REWARD,
        SimpleNamespace(cards=cards, can_skip=can_skip, can_bowl=can_bowl),
        commands=commands,
    )


def _shop_game(
    *,
    cards=None,
    relics=None,
    potions=None,
    purge_available=False,
    commands=None,
):
    if commands is None:
        commands = ["choose", "leave", "state"]
    return _base_game(
        ScreenType.SHOP_SCREEN,
        SimpleNamespace(
            cards=list(cards or []),
            relics=list(relics or []),
            potions=list(potions or []),
            purge_available=purge_available,
            purge_cost=75,
        ),
        commands=commands,
    )


def _shop_agent(game):
    return SimpleNamespace(
        game=game,
        visited_shop=True,
        shop_purchase_made=True,
        _shop_purchase_signature=(150, False, 1, 0, 0),
        _shop_bought_card_this_shop=True,
        _shop_purged_this_shop=False,
        _leaving_shop_room=False,
        _shop_exit_waits=0,
    )


def _shop_state(agent):
    return deepcopy(
        {
            "visited_shop": agent.visited_shop,
            "shop_purchase_made": agent.shop_purchase_made,
            "purchase_signature": agent._shop_purchase_signature,
            "bought_card": agent._shop_bought_card_this_shop,
            "purged": agent._shop_purged_this_shop,
            "leaving": agent._leaving_shop_room,
            "exit_waits": agent._shop_exit_waits,
            "game": vars(agent.game),
        }
    )


def test_card_reward_proposes_only_current_card_and_immediate_skip_as_executable():
    anger = _item("Anger")
    shrug = _item("Shrug It Off")
    game = _card_reward_game([anger, shrug], can_bowl=True)
    current = CardRewardAction(anger)
    before = deepcopy(vars(game))

    result = build_card_reward_proposal(game, current)

    assert result.current_action is current
    assert result.ineligibility_reason == ""
    assert result.proposal is not None
    assert result.proposal.execution_eligible is True
    assert result.proposal.rollout_mode == "executable"
    assert result.proposal.baseline_action_id == "card_reward:take:anger"
    assert result.proposal.alternative_action_id == "card_reward:skip"
    by_id = {candidate.action_id: candidate for candidate in result.proposal.candidates}
    assert set(by_id) == {
        "card_reward:take:anger",
        "card_reward:take:shrug_it_off",
        "card_reward:bowl",
        "card_reward:skip",
    }
    assert by_id["card_reward:take:anger"].executable is True
    assert by_id["card_reward:skip"].executable is True
    assert by_id["card_reward:take:shrug_it_off"].executable is False
    assert by_id["card_reward:bowl"].executable is False
    assert result.materialize_or_current("card_reward:take:anger") is current
    assert isinstance(result.materialize_or_current("card_reward:skip"), CancelAction)
    assert vars(game) == before


@pytest.mark.parametrize(
    ("game", "current", "reason"),
    [
        (
            _card_reward_game([_item("Anger")], can_skip=False),
            CardRewardAction(_item("Anger")),
            "card_reward_skip_not_available",
        ),
        (
            _card_reward_game([_item("Anger")], commands=["choose", "state"]),
            CardRewardAction(_item("Anger")),
            "card_reward_skip_not_immediately_legal",
        ),
        (
            _card_reward_game([_item("Anger"), _item("Anger")]),
            CardRewardAction(_item("Anger")),
            "current_card_mapping_ambiguous",
        ),
        (
            _card_reward_game([_item("Anger")]),
            CancelAction(),
            "current_action_already_abstention",
        ),
    ],
)
def test_card_reward_ineligible_states_preserve_current_action(game, current, reason):
    before = deepcopy(vars(game))

    result = build_card_reward_proposal(game, current)

    assert result.current_action is current
    assert result.proposal is None
    assert result.ineligibility_reason == reason
    assert result.materialize_or_current("card_reward:skip") is current
    assert vars(game) == before


def test_card_reward_combat_choice_is_not_exploration_eligible():
    anger = _item("Anger")
    game = _card_reward_game([anger])
    game.in_combat = True
    current = CardRewardAction(anger)

    result = build_card_reward_proposal(game, current)

    assert result.proposal is None
    assert result.ineligibility_reason == "in_combat_card_reward"
    assert result.materialize_or_current("card_reward:skip") is current


@pytest.mark.parametrize(
    ("inventory", "action_factory", "expected_id"),
    [
        ("cards", BuyCardAction, "shop:buy_card:perfected_strike"),
        ("relics", BuyRelicAction, "shop:buy_relic:bag_of_marbles"),
        ("potions", BuyPotionAction, "shop:buy_potion:swift_potion"),
    ],
)
def test_shop_purchase_proposes_immediate_leave_without_mutating_agent(
    inventory, action_factory, expected_id
):
    names = {
        "cards": "Perfected Strike",
        "relics": "Bag of Marbles",
        "potions": "Swift Potion",
    }
    selected = _item(names[inventory], price=50)
    game = _shop_game(**{inventory: [selected]})
    agent = _shop_agent(game)
    current = action_factory(selected)
    before = _shop_state(agent)

    result = build_shop_proposal(game, current, agent=agent)

    assert result.current_action is current
    assert result.proposal is not None
    assert result.proposal.execution_eligible is True
    assert result.proposal.baseline_action_id == expected_id
    assert result.proposal.alternative_action_id == "shop:leave"
    assert result.materialize_or_current(expected_id) is current
    assert isinstance(result.materialize_or_current("shop:leave"), LeaveAction)
    assert _shop_state(agent) == before


def test_shop_purge_proposes_cancel_group_leave_without_mutating_agent():
    game = _shop_game(purge_available=True, commands=["choose", "cancel", "state"])
    agent = _shop_agent(game)
    current = ChooseAction(name="purge")
    before = _shop_state(agent)

    result = build_shop_proposal(game, current, agent=agent)

    assert result.proposal is not None
    assert result.proposal.baseline_action_id == "shop:purge"
    assert result.proposal.alternative_action_id == "shop:leave"
    assert isinstance(result.materialize_or_current("shop:leave"), CancelAction)
    assert _shop_state(agent) == before


def test_shop_duplicate_offer_is_ineligible_and_preserves_current_action():
    first = _item("Swift Potion", price=60)
    second = _item("Swift Potion", price=65)
    game = _shop_game(potions=[first, second])
    agent = _shop_agent(game)
    current = BuyPotionAction(first)
    before = _shop_state(agent)

    result = build_shop_proposal(game, current, agent=agent)

    assert result.proposal is None
    assert result.ineligibility_reason == "current_shop_offer_mapping_ambiguous"
    assert result.materialize_or_current("shop:leave") is current
    assert _shop_state(agent) == before


@pytest.mark.parametrize(
    ("current", "reason"),
    [
        (WaitAction(), "shop_transition_in_progress"),
        (LeaveAction(), "current_action_already_abstention"),
        (CancelAction(), "current_action_already_abstention"),
        (ProceedAction(), "current_action_already_abstention"),
    ],
)
def test_shop_transitional_or_abstention_action_is_never_replaced(current, reason):
    game = _shop_game()
    result = build_shop_proposal(game, current)

    assert result.proposal is None
    assert result.ineligibility_reason == reason
    assert result.materialize_or_current("shop:leave") is current


def test_shop_requires_an_immediate_exit_command():
    anger = _item("Anger", price=50)
    game = _shop_game(cards=[anger], commands=["choose", "state"])
    current = BuyCardAction(anger)

    result = build_shop_proposal(game, current)

    assert result.proposal is None
    assert result.ineligibility_reason == "shop_leave_not_immediately_legal"
    assert result.materialize_or_current("shop:leave") is current


def test_shop_proceed_exit_is_materialized_only_after_selection():
    anger = _item("Anger", price=50)
    game = _shop_game(cards=[anger], commands=["choose", "proceed", "state"])
    current = BuyCardAction(anger)

    result = build_shop_proposal(game, current)

    assert result.proposal is not None
    first = result.materialize_or_current("shop:leave")
    second = result.materialize_or_current("shop:leave")
    assert isinstance(first, ProceedAction)
    assert isinstance(second, ProceedAction)
    assert first is not second


def test_event_proposal_is_shadow_only_and_cannot_replace_current_action():
    options = [
        SimpleNamespace(text="Pray", label="Pray", disabled=False, choice_index=0),
        SimpleNamespace(text="Desecrate", label="Desecrate", disabled=False, choice_index=1),
    ]
    game = _base_game(
        ScreenType.EVENT,
        SimpleNamespace(event_name="Golden Shrine", event_id="GoldenShrine", options=options),
        commands=["choose", "state"],
    )
    current = EventOptionAction(options[1])

    result = build_event_shadow_proposal(game, current)

    assert result.proposal is not None
    assert result.proposal.rollout_mode == "shadow"
    assert result.proposal.execution_eligible is False
    assert result.proposal.baseline_action_id == "event:choice:1"
    assert result.ineligibility_reason == "category_shadow_only"
    assert result.materialize_or_current("event:choice:0") is current
    assert result.materialize_or_current("event:choice:1") is current


def test_route_proposal_is_shadow_only_and_cannot_replace_current_action():
    rest = Node(1, 1, "R")
    elite = Node(2, 1, "E")
    game = _base_game(
        ScreenType.MAP,
        SimpleNamespace(current_node=Node(0, 0, "M"), next_nodes=[rest, elite], boss_available=False),
        commands=["choose", "state"],
    )
    current = ChooseMapNodeAction(elite)

    result = build_route_shadow_proposal(game, current)

    assert result.proposal is not None
    assert result.proposal.rollout_mode == "shadow"
    assert result.proposal.execution_eligible is False
    assert result.proposal.baseline_action_id == "route:choice:1"
    assert result.ineligibility_reason == "category_shadow_only"
    assert result.materialize_or_current("route:choice:0") is current
    assert result.materialize_or_current("route:choice:1") is current
