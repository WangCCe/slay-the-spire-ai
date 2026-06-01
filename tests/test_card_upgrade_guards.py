from types import SimpleNamespace

from spirecomm.ai.heuristics.card_upgrades import (
    card_upgrade_count,
    is_card_upgraded,
    known_damage_upgrade_bonus,
)
from spirecomm.spire.card import Card


def _card(name, upgrades=0):
    return SimpleNamespace(card_id=name, name=name, upgrades=upgrades)


def test_card_upgrade_count_uses_display_suffix_when_upgrade_field_is_zero():
    bash_plus = _card("Bash+")

    assert card_upgrade_count(bash_plus) == 1
    assert is_card_upgraded(bash_plus) is True


def test_card_upgrade_count_uses_counted_display_suffix():
    searing_blow_plus_two = _card("Searing Blow+2")

    assert card_upgrade_count(searing_blow_plus_two) == 2
    assert known_damage_upgrade_bonus(searing_blow_plus_two, "Searing Blow") == 9


def test_card_from_json_infers_counted_upgrade_suffix():
    card = Card.from_json(
        {
            "id": "Searing Blow",
            "name": "Searing Blow+2",
            "type": "ATTACK",
            "rarity": "UNCOMMON",
            "upgrades": 0,
            "has_target": True,
            "cost": 2,
            "uuid": "searing-1",
        }
    )

    assert card.upgrades == 2
