from types import SimpleNamespace

from spirecomm.ai.heuristics.card_costs import (
    playable_card_cost_after_refund,
)


def _card(name="Dropkick", cost=1):
    return SimpleNamespace(name=name, card_id=name, cost=cost, cost_for_turn=cost)


def test_playable_card_cost_after_refund_requires_upfront_energy():
    assert playable_card_cost_after_refund(_card(), available_energy=0, energy_refund=1) == 1


def test_playable_card_cost_after_refund_returns_net_cost_when_affordable():
    assert playable_card_cost_after_refund(_card(), available_energy=1, energy_refund=1) == 0
