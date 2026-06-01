from types import SimpleNamespace

from spirecomm.ai.heuristics.card_upgrades import (
    card_upgrade_count,
    heavy_blade_strength_multiplier,
    is_card_upgraded,
    known_block_upgrade_bonus,
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


def test_known_block_upgrade_bonus_uses_shared_mapping_and_upgrade_count():
    shrug_plus = _card("Shrug It Off+1", upgrades=1)

    assert known_block_upgrade_bonus(shrug_plus, "Shrug It Off") == 3
    assert known_block_upgrade_bonus(_card("Shrug It Off"), "Shrug It Off") == 0


def test_heavy_blade_strength_multiplier_uses_upgrade_count():
    assert heavy_blade_strength_multiplier(_card("Heavy Blade")) == 3
    assert heavy_blade_strength_multiplier(_card("Heavy Blade+1", upgrades=1)) == 5
    assert heavy_blade_strength_multiplier(_card("Heavy Blade", upgrades=None)) == 3


def test_upgrade_bonus_tables_are_owned_by_card_upgrades_not_simulation():
    from spirecomm.ai.heuristics import simulation

    assert "DAMAGE_UPGRADE_BONUS" not in simulation.__dict__
    assert "BLOCK_UPGRADE_BONUS" not in simulation.__dict__
    assert "_known_damage_upgrade_bonus" not in simulation.__dict__
    assert "_known_block_upgrade_bonus" not in simulation.__dict__


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


def test_card_from_json_normalizes_string_zero_before_suffix_inference():
    card = Card.from_json(
        {
            "id": "Bash",
            "name": "Bash+",
            "type": "ATTACK",
            "rarity": "BASIC",
            "upgrades": "0",
            "has_target": True,
            "cost": 2,
            "uuid": "bash-1",
        }
    )

    assert card.upgrades == 1
