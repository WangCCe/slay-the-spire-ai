from types import SimpleNamespace

from spirecomm.ai.heuristics.card_hits import fixed_attack_hit_count


def _card(name, upgrades=0):
    return SimpleNamespace(card_id=name, name=name, upgrades=upgrades)


def test_fixed_attack_hit_count_covers_static_multi_hit_cards():
    assert fixed_attack_hit_count(_card("Twin Strike")) == 2
    assert fixed_attack_hit_count(_card("Sword Boomerang")) == 3
    assert fixed_attack_hit_count(_card("Pummel")) == 4


def test_fixed_attack_hit_count_uses_upgrade_count_for_static_multi_hit_cards():
    assert fixed_attack_hit_count(_card("Sword Boomerang+1", upgrades=1)) == 4
    assert fixed_attack_hit_count(_card("Pummel+1", upgrades=1)) == 5
    assert fixed_attack_hit_count(_card("Sword Boomerang", upgrades=None)) == 3


def test_fixed_attack_hit_count_returns_none_for_contextual_or_single_hit_cards():
    assert fixed_attack_hit_count(_card("Bane")) is None
    assert fixed_attack_hit_count(_card("Skewer")) is None
    assert fixed_attack_hit_count(_card("Fiend Fire")) is None
    assert fixed_attack_hit_count(_card("Strike_R")) is None
