import json
from pathlib import Path
from types import SimpleNamespace

from spirecomm.ai.heuristics.enhanced_monster_database import EnhancedMonsterDatabase
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


def test_act3_elites_bosses_source_contains_only_act3_elites_and_bosses():
    path = Path("spirecomm/data/monster_wiki_data/act3_elites_bosses.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert set(data) == {
        "Awakened One",
        "Giant Head",
        "Nemesis",
        "Reptomancer",
        "Time Eater",
        "Donu & Deca",
    }


def test_enhanced_database_keeps_native_chosen_and_sentry_records():
    database = EnhancedMonsterDatabase()

    assert database.get_monster_data("Chosen")["monster_type"] == "normal"
    assert database.get_monster_data("Sentry")["hp_ranges"]["normal"] == {
        "min": 38,
        "max": 42,
    }


def test_enhanced_database_returns_duo_boss_member_hp_ranges():
    database = EnhancedMonsterDatabase()

    assert database.get_hp_range("Donu") == (250, 250)
    assert database.get_hp_range("Deca", ascension_level=9) == (265, 265)


def test_donu_deca_wiki_data_matches_vanilla_moves():
    database = EnhancedMonsterDatabase()

    data = database.get_monster_data("Donu & Deca")
    moves_by_member = {
        (move["monster"], move["name"]): move
        for move in data["moves"]
    }

    assert set(moves_by_member) == {
        ("Donu", "Circle of Power"),
        ("Donu", "Beam"),
        ("Deca", "Beam"),
        ("Deca", "Square of Protection"),
    }

    circle = moves_by_member[("Donu", "Circle of Power")]
    assert circle["intent"] == "BUFF"
    assert circle["all_enemies_strength_gain"] == 3

    donu_beam = moves_by_member[("Donu", "Beam")]
    assert donu_beam["intent"] == "ATTACK"
    assert donu_beam["damage"] == 10
    assert donu_beam["hits"] == 2
    assert donu_beam["ascension_modifiers"]["4+"]["damage"] == 12

    deca_beam = moves_by_member[("Deca", "Beam")]
    assert deca_beam["intent"] == "ATTACK_DEBUFF"
    assert deca_beam["damage"] == 10
    assert deca_beam["hits"] == 2
    assert deca_beam["dazed"] == 2
    assert deca_beam["ascension_modifiers"]["4+"]["damage"] == 12

    square = moves_by_member[("Deca", "Square of Protection")]
    assert square["intent"] == "DEFEND"
    assert square["all_enemies_block_gain"] == 16
    assert square["ascension_modifiers"]["19+"]["all_enemies_plated_armor_gain"] == 3


def test_donu_deca_member_predictions_follow_fixed_alternating_patterns():
    database = EnhancedMonsterDatabase()

    donu_predictions = database.predict_next_moves("Donu", current_turn=1, monster_hp_percent=1.0)
    deca_predictions = database.predict_next_moves("Deca", current_turn=1, monster_hp_percent=1.0)

    assert [prediction["move"]["name"] for prediction in donu_predictions] == [
        "Circle of Power",
        "Beam",
        "Circle of Power",
    ]
    assert [prediction["move"]["monster"] for prediction in donu_predictions] == [
        "Donu",
        "Donu",
        "Donu",
    ]
    assert [prediction["move"]["name"] for prediction in deca_predictions] == [
        "Beam",
        "Square of Protection",
        "Beam",
    ]
    assert [prediction["move"]["monster"] for prediction in deca_predictions] == [
        "Deca",
        "Deca",
        "Deca",
    ]
