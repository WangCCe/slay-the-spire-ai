from types import SimpleNamespace

from spirecomm.ai.heuristics.card_hits import (
    fiend_fire_exhaust_count,
    fixed_attack_hit_count,
    strike_card_count,
)


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


def test_fiend_fire_exhaust_count_uses_game_hand_and_excludes_played_card():
    fiend_fire = _card("Fiend Fire")
    context = SimpleNamespace(
        game=SimpleNamespace(
            hand=[
                _card("Strike_R"),
                fiend_fire,
                _card("Defend_R"),
            ]
        )
    )

    assert fiend_fire_exhaust_count(fiend_fire, context) == 2


def test_fiend_fire_exhaust_count_falls_back_to_playable_cards_and_uuid():
    fiend_fire = SimpleNamespace(card_id="Fiend Fire", name="Fiend Fire", upgrades=0, uuid="ff-1")
    playable_copy = SimpleNamespace(card_id="Fiend Fire", name="Fiend Fire", upgrades=0, uuid="ff-1")
    context = SimpleNamespace(
        game=SimpleNamespace(hand=[]),
        playable_cards=[
            _card("Strike_R"),
            playable_copy,
            _card("Defend_R"),
        ],
    )

    assert fiend_fire_exhaust_count(fiend_fire, context) == 2


def test_strike_card_count_uses_deck_names_and_ids():
    context = SimpleNamespace(
        game=SimpleNamespace(
            deck=[
                _card("Strike_R"),
                SimpleNamespace(card_id="Twin Strike", name="Twin Strike", upgrades=0),
                SimpleNamespace(card_id="PerfectedStrike", name="Perfected Strike", upgrades=0),
                _card("Defend_R"),
            ]
        )
    )

    assert strike_card_count(context) == 3


def test_strike_card_count_handles_missing_deck():
    assert strike_card_count(SimpleNamespace(game=SimpleNamespace(deck=[]))) == 0
    assert strike_card_count(SimpleNamespace()) == 0
