from types import SimpleNamespace

from spirecomm.ai.heuristics.card_costs import (
    effective_card_cost,
    effective_card_cost_after_refund,
    playable_card_cost_after_refund,
    raw_card_cost,
)


def _card(name="Dropkick", cost=1):
    return SimpleNamespace(name=name, card_id=name, cost=cost, cost_for_turn=cost)


def test_playable_card_cost_after_refund_requires_upfront_energy():
    assert playable_card_cost_after_refund(_card(), available_energy=0, energy_refund=1) == 1


def test_playable_card_cost_after_refund_returns_net_cost_when_affordable():
    assert playable_card_cost_after_refund(_card(), available_energy=1, energy_refund=1) == 0


def test_raw_card_cost_accepts_decimal_string_cost_for_turn():
    card = _card(cost="2.0")

    assert raw_card_cost(card) == 2
    assert effective_card_cost(card, available_energy=3) == 2


def test_x_cost_effective_card_cost_accepts_decimal_string_available_energy():
    card = _card(name="Whirlwind", cost="-1.0")

    assert effective_card_cost(card, available_energy="3.0") == 3


def test_effective_card_cost_after_refund_accepts_decimal_string_inputs():
    card = _card(cost="2.0")

    assert effective_card_cost_after_refund(
        card,
        available_energy="2.0",
        energy_refund="1.0",
    ) == 1
