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
