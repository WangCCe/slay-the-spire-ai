from types import SimpleNamespace

import pytest

from spirecomm.ai.heuristics.simulation import HeuristicCombatPlanner


def _card(cost, cost_for_turn=None):
    return SimpleNamespace(
        cost=cost,
        cost_for_turn=cost if cost_for_turn is None else cost_for_turn,
        is_playable=True,
    )


def test_confidence_energy_efficiency_uses_turn_cost():
    context = SimpleNamespace(
        playable_cards=[
            _card(cost=2, cost_for_turn=0),
            _card(cost=1, cost_for_turn=1),
        ],
        monsters_alive=[],
        energy_available=1,
    )

    confidence = HeuristicCombatPlanner().get_confidence(context)

    assert confidence == pytest.approx(0.8)


def test_confidence_accepts_missing_is_playable_on_playable_cards():
    context = SimpleNamespace(
        playable_cards=[
            SimpleNamespace(name="Strike", cost=1, cost_for_turn=1),
        ],
        monsters_alive=[],
        energy_available=1,
    )

    confidence = HeuristicCombatPlanner().get_confidence(context)

    assert confidence == pytest.approx(0.8)


def test_confidence_accepts_numeric_string_monster_hp():
    context = SimpleNamespace(
        playable_cards=[
            _card(cost=1),
        ],
        monsters_alive=[
            SimpleNamespace(current_hp="14"),
        ],
        energy_available=1,
    )

    confidence = HeuristicCombatPlanner().get_confidence(context)

    assert confidence == pytest.approx(1.0)


def test_planner_adaptive_depth_counts_string_zero_turn_cost(monkeypatch):
    planner = HeuristicCombatPlanner()
    context = SimpleNamespace(
        act=1,
        turn=1,
        playable_cards=[_card(cost=1, cost_for_turn="0") for _ in range(4)],
        energy_available=3,
        game=SimpleNamespace(get_real_potions=lambda: []),
    )
    monkeypatch.setattr(planner, "_beam_search_plan", lambda _context: [])

    planner.plan_turn(context)

    assert planner.max_depth == 4
