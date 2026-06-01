from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.priorities import IroncladPriority
from spirecomm.communication.action import (
    CardSelectAction,
    ChooseAction,
    CombatRewardAction,
    PlayCardAction,
)
from spirecomm.spire.card import CardType
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


def _playable_card(card_id, card_type, cost, cost_for_turn=None):
    return SimpleNamespace(
        card_id=card_id,
        name=card_id,
        type=card_type,
        cost=cost,
        cost_for_turn=cost if cost_for_turn is None else cost_for_turn,
        is_playable=True,
        has_target=False,
        exhausts=False,
    )


class _PreferCostlyAttackPriority:
    def is_card_aoe(self, card):
        return False

    def is_card_defensive(self, card):
        return False

    def get_best_card_to_play(self, cards):
        for card in cards:
            if getattr(card, "type", None) == CardType.ATTACK:
                return card
        return cards[0]


class _FirstPlayablePriority:
    def is_card_aoe(self, card):
        return False

    def is_card_defensive(self, card):
        return False

    def get_best_card_to_play(self, cards):
        return cards[0]


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


def test_upgrade_candidate_treats_none_upgrades_as_unupgraded():
    agent = _agent(deck=[])
    base_card = _card("Pommel Strike", upgrades=0)
    unknown_upgrade_card = _card("Pommel Strike", upgrades=None)

    assert agent._score_upgrade_candidate(unknown_upgrade_card) == agent._score_upgrade_candidate(
        base_card
    )


def test_upgrade_bonus_accepts_string_attack_type():
    agent = _agent(deck=[])
    string_attack = _playable_card("Mystery Attack", "ATTACK", cost=1)
    enum_attack = _playable_card("Mystery Attack", CardType.ATTACK, cost=1)

    assert agent._get_upgrade_bonus(string_attack) == agent._get_upgrade_bonus(enum_attack)


def test_play_card_action_treats_turn_cost_zero_non_attack_as_free():
    free_inflame = _playable_card("Inflame", CardType.POWER, cost=1, cost_for_turn=0)
    strike = _playable_card("Strike_R", CardType.ATTACK, cost=1, cost_for_turn=1)
    agent = _agent(
        hand=[free_inflame, strike],
        monsters=[],
        player=SimpleNamespace(block=0, energy=1),
        act=1,
    )
    agent.priorities = _PreferCostlyAttackPriority()

    action = agent.get_play_card_action()

    assert isinstance(action, PlayCardAction)
    assert action.card is free_inflame


def test_play_card_action_targets_low_hp_with_string_attack_type():
    strike = _playable_card("Strike_R", "ATTACK", cost=1)
    strike.has_target = True
    low_hp = SimpleNamespace(
        current_hp=1,
        max_hp=10,
        half_dead=False,
        is_gone=False,
        intent="DEFEND",
        move_adjusted_damage=0,
    )
    high_hp = SimpleNamespace(
        current_hp=20,
        max_hp=20,
        half_dead=False,
        is_gone=False,
        intent="DEFEND",
        move_adjusted_damage=0,
    )
    agent = _agent(
        hand=[strike],
        monsters=[high_hp, low_hp],
        player=SimpleNamespace(block=0, energy=1),
        act=1,
    )
    agent.priorities = _FirstPlayablePriority()

    action = agent.get_play_card_action()

    assert isinstance(action, PlayCardAction)
    assert action.card is strike
    assert action.target_monster is low_hp


def test_combat_reward_skips_string_potion_type_when_slots_are_full():
    potion_reward = SimpleNamespace(reward_type="POTION")
    gold_reward = SimpleNamespace(reward_type="GOLD")
    agent = _agent(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        floor=3,
        are_potions_full=lambda: True,
    )
    agent.skipped_cards = False

    action = agent.handle_screen()

    assert isinstance(action, CombatRewardAction)
    assert action.combat_reward is gold_reward


def test_combat_reward_skips_potion_when_potion_space_is_blocked():
    potion_reward = SimpleNamespace(reward_type="POTION")
    gold_reward = SimpleNamespace(reward_type="GOLD")
    agent = _agent(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        floor=3,
        are_potions_full=lambda: False,
        has_potion_space=lambda: False,
    )
    agent.skipped_cards = False

    action = agent.handle_screen()

    assert isinstance(action, CombatRewardAction)
    assert action.combat_reward is gold_reward


def test_combat_reward_skips_string_card_type_after_card_reward_skip():
    card_reward = SimpleNamespace(reward_type="CARD")
    gold_reward = SimpleNamespace(reward_type="GOLD")
    agent = _agent(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[card_reward, gold_reward]),
        floor=3,
        are_potions_full=lambda: False,
    )
    agent.skipped_cards = True

    action = agent.handle_screen()

    assert isinstance(action, CombatRewardAction)
    assert action.combat_reward is gold_reward
