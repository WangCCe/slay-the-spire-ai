from types import SimpleNamespace

import spirecomm.ai.heuristics.timing.timing_planner as timing_planner
from spirecomm.ai.heuristics.timing.models import BalanceWeights, TimingContext, TurnTiming
from spirecomm.ai.heuristics.timing.timing_planner import TimingAwareCombatPlanner
from spirecomm.data.loader import GameDataLoader
from spirecomm.spire.card import Card, CardRarity, CardType


def _card(card_id, name, card_type=CardType.ATTACK, cost=1, has_target=True):
    return Card(
        card_id=card_id,
        name=name,
        card_type=card_type,
        rarity=CardRarity.BASIC,
        cost=cost,
        has_target=has_target,
        is_playable=True,
    )


def _loader_with_basic_ironclad_cards():
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
        "defend": {
            "name": "Defend",
            "description": "Gain 5 Block.",
        },
    }
    return loader


def test_timing_lethal_check_uses_parsed_damage_for_plain_cards(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = _card("Strike_R", "Strike")
    strike_a.uuid = "strike-a"
    strike_b = _card("Strike_R", "Strike")
    strike_b.uuid = "strike-b"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike_a, strike_b],
        monsters_alive=[SimpleNamespace(current_hp=12, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_fallback_scores_parsed_damage_and_block_for_plain_cards(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False)
    defend.uuid = "defend"
    strike = _card("Strike_R", "Strike")
    strike.uuid = "strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[defend, strike],
        monsters_alive=[SimpleNamespace(current_hp=30, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is strike
