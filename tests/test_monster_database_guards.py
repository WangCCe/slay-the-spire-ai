from types import SimpleNamespace

from spirecomm.ai.heuristics.monster_database import (
    evaluate_monster_threat,
    get_monster_info,
)
from spirecomm.spire.character import Intent


def test_monster_database_threat_ignores_non_attack_stale_damage():
    monster = SimpleNamespace(
        monster_id="Louse",
        intent=Intent.DEBUFF,
        move_adjusted_damage=20,
    )
    context = SimpleNamespace(player_hp_pct=1.0)

    assert evaluate_monster_threat(monster, context) == 1


def test_monster_database_threat_scales_live_gremlin_nob_id():
    monster = SimpleNamespace(
        name="Gremlin Nob",
        monster_id="GremlinNob",
        intent=Intent.ATTACK,
        move_adjusted_damage=14,
    )
    context = SimpleNamespace(player_hp_pct=1.0, turn=4)

    assert evaluate_monster_threat(monster, context) == 11


def test_monster_database_info_accepts_normalized_live_ids():
    assert get_monster_info("FungiBeast")["recommended_strategy"] == "apply_weak"
    assert get_monster_info("Slime_Boss")["recommended_strategy"] == "kill_all_small"


def test_monster_database_info_accepts_named_live_aliases():
    assert get_monster_info("FuzzyLouseNormal")["threat_level"] == 1
    assert get_monster_info("FuzzyLouseDefensive")["recommended_strategy"] == "focus_down"
    assert get_monster_info("AwakenedOne")["threat_level"] == 5


def test_monster_database_info_accepts_canonical_slaver_names():
    assert get_monster_info("Red Slaver")["recommended_strategy"] == "priority_target"
    assert get_monster_info("Blue Slaver")["recommended_strategy"] == "priority_target"


def test_monster_database_threat_recognizes_live_red_slaver_id():
    monster = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        intent=Intent.ATTACK_DEBUFF,
        move_adjusted_damage=13,
    )
    context = SimpleNamespace(player_hp_pct=1.0)

    assert get_monster_info("SlaverRed")["recommended_strategy"] == "priority_target"
    assert evaluate_monster_threat(monster, context) == 6
