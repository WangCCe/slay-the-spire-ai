import json
from pathlib import Path
from types import SimpleNamespace

from spirecomm.data.loader import GameDataLoader
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


def test_monster_predictions_use_ascension_opening_overrides():
    database = EnhancedMonsterDatabase()

    normal_chosen = database.predict_next_moves("Chosen", current_turn=1, monster_hp_percent=1.0)
    asc17_chosen = database.predict_next_moves(
        "Chosen",
        current_turn=1,
        monster_hp_percent=1.0,
        ascension_level=17,
    )
    asc17_acid_slime = database.predict_next_moves(
        "Acid Slime (S)",
        current_turn=1,
        monster_hp_percent=1.0,
        ascension_level=17,
    )

    assert normal_chosen[0]["move"]["name"] == "Poke"
    assert asc17_chosen[0]["move"]["name"] == "Hex"
    assert asc17_acid_slime[0]["move"]["name"] == "Lick"


def test_ascension_small_acid_slime_alternates_after_forced_opening():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves(
        "Acid Slime (S)",
        current_turn=1,
        monster_hp_percent=1.0,
        ascension_level=17,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in predictions
    ] == [
        (1, "Lick", 1.0),
        (2, "Tackle", 1.0),
        (3, "Lick", 1.0),
    ]


def test_looter_and_mugger_predict_turn_three_options():
    database = EnhancedMonsterDatabase()

    assert [
        prediction["move"]["name"]
        for prediction in database.predict_next_moves("Looter", current_turn=3, monster_hp_percent=1.0)
    ] == ["Lunge", "Smoke Bomb"]
    assert [
        prediction["move"]["name"]
        for prediction in database.predict_next_moves("Mugger", current_turn=3, monster_hp_percent=1.0)
    ] == ["Lunge", "Smoke Bomb"]


def test_looter_and_mugger_keep_turn_three_options_in_opening_window():
    database = EnhancedMonsterDatabase()

    looter_opening = database.predict_next_moves(
        "Looter",
        current_turn=1,
        monster_hp_percent=1.0,
    )
    mugger_opening = database.predict_next_moves(
        "Mugger",
        current_turn=1,
        monster_hp_percent=1.0,
    )

    assert [
        prediction["move"]["name"]
        for prediction in looter_opening
        if prediction["turn"] == 3
    ] == ["Lunge", "Smoke Bomb"]
    assert [
        prediction["move"]["name"]
        for prediction in mugger_opening
        if prediction["turn"] == 3
    ] == ["Lunge", "Smoke Bomb"]


def test_probability_predictions_keep_boundary_ties_within_turn():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves(
        "Acid Slime (M)",
        current_turn=1,
        monster_hp_percent=1.0,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in predictions
    ] == [
        (1, "Tackle", 0.4),
        (1, "Corrosive Spit", 0.3),
        (1, "Lick", 0.3),
    ]


def test_initial_move_probabilities_start_after_opening_turn():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves(
        "Gremlin Nob",
        current_turn=1,
        monster_hp_percent=1.0,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"])
        for prediction in predictions
    ] == [
        (1, "Bellow"),
        (2, "Bull Rush"),
        (2, "Skull Bash"),
    ]


def test_initial_move_is_not_duplicated_when_opening_already_predicts_it():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves(
        "The Collector",
        current_turn=1,
        monster_hp_percent=1.0,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"])
        for prediction in predictions
    ] == [(1, "Spawn")]


def test_collector_without_minion_context_uses_probability_table():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves(
        "The Collector",
        current_turn=2,
        monster_hp_percent=1.0,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in predictions
    ] == [
        (2, "Fireball", 0.7),
        (2, "Buff", 0.3),
    ]


def test_red_slaver_predicts_pre_entangle_sequence_after_opening():
    database = EnhancedMonsterDatabase()

    below_a17 = database.predict_next_moves(
        "Red Slaver",
        current_turn=2,
        monster_hp_percent=1.0,
        ascension_level=0,
    )
    asc17 = database.predict_next_moves(
        "Red Slaver",
        current_turn=2,
        monster_hp_percent=1.0,
        ascension_level=17,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in below_a17
    ] == [
        (2, "Scrape", 0.75),
        (2, "Entangle", 0.25),
        (3, "Scrape", 0.75),
        (3, "Entangle", 0.25),
    ]
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in asc17
    ] == [
        (2, "Scrape", 0.75),
        (2, "Entangle", 0.25),
        (3, "Stab", 0.75),
        (3, "Entangle", 0.25),
    ]


def test_enhanced_database_accepts_live_slaver_ids():
    database = EnhancedMonsterDatabase()

    assert database.get_monster_data("SlaverRed")["name"] == "Red Slaver"
    assert database.get_monster_data("SlaverBlue")["name"] == "Blue Slaver"
    assert [
        prediction["move"]["name"]
        for prediction in database.predict_next_moves("SlaverRed", 2, 1.0)
    ][:2] == ["Scrape", "Entangle"]
    assert {
        prediction["move"]["name"]
        for prediction in database.predict_next_moves("SlaverBlue", 1, 1.0)
    } == {"Stab", "Rake"}


def test_enhanced_database_accepts_normalized_live_monster_ids():
    database = EnhancedMonsterDatabase()

    assert database.get_monster_data("AcidSlimeL")["name"] == "Acid Slime (L)"
    assert database.get_monster_data("TheCollector")["name"] == "The Collector"
    assert database.get_monster_data("TimeEater")["name"] == "Time Eater"
    assert [
        prediction["move"]["name"]
        for prediction in database.predict_next_moves("AcidSlimeL", 1, 1.0)
    ] == ["Tackle", "Corrosive Spit", "Lick"]
    assert [
        prediction["move"]["name"]
        for prediction in database.predict_next_moves("TheCollector", 1, 1.0)
    ][:1] == ["Spawn"]


def test_gremlin_leader_predicts_from_enemy_count_probabilities():
    database = EnhancedMonsterDatabase()

    no_minions = database.predict_next_moves(
        "Gremlin Leader",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_count=0,
    )
    full_minions = database.predict_next_moves(
        "Gremlin Leader",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_count=2,
    )
    ambiguous_one_minion = database.predict_next_moves(
        "Gremlin Leader",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_count=1,
    )

    assert [
        (prediction["move"]["name"], prediction["confidence"])
        for prediction in no_minions
    ] == [("Rally!", 0.75), ("Stab", 0.25)]
    assert [
        (prediction["move"]["name"], prediction["confidence"])
        for prediction in full_minions
    ] == [("Encourage", 0.66), ("Stab", 0.34)]
    assert ambiguous_one_minion == []


def test_shield_gremlin_predicts_from_enemy_count_modes():
    database = EnhancedMonsterDatabase()

    with_allies = database.predict_next_moves(
        "Shield Gremlin",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_count=2,
    )
    alone = database.predict_next_moves(
        "Shield Gremlin",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_count=0,
    )

    assert [
        prediction["move"]["name"]
        for prediction in with_allies
    ] == ["Protect"]
    assert [
        prediction["move"]["name"]
        for prediction in alone
    ] == ["Shield Bash"]


def test_gremlin_wizard_predicts_charge_and_blast_sequence():
    database = EnhancedMonsterDatabase()

    opening = database.predict_next_moves(
        "Gremlin Wizard",
        current_turn=1,
        monster_hp_percent=1.0,
    )
    later = database.predict_next_moves(
        "Gremlin Wizard",
        current_turn=4,
        monster_hp_percent=1.0,
    )
    asc17_later = database.predict_next_moves(
        "Gremlin Wizard",
        current_turn=4,
        monster_hp_percent=1.0,
        ascension_level=17,
    )

    assert [
        prediction["move"]["name"]
        for prediction in opening
    ] == ["Charging", "Charging", "Ultimate Blast"]
    assert [
        prediction["move"]["name"]
        for prediction in later
    ] == ["Charging", "Charging", "Charging"]
    assert [
        prediction["move"]["name"]
        for prediction in asc17_later
    ] == ["Ultimate Blast", "Ultimate Blast", "Ultimate Blast"]


def test_champ_phase_one_predicts_probabilities_and_taunt_turns():
    database = EnhancedMonsterDatabase()

    phase_one = database.predict_next_moves(
        "The Champ",
        current_turn=1,
        monster_hp_percent=1.0,
    )
    taunt_window = database.predict_next_moves(
        "The Champ",
        current_turn=3,
        monster_hp_percent=1.0,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in phase_one[:2]
    ] == [
        (1, "Heavy Slash", 0.45),
        (1, "Face Slap", 0.25),
    ]
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in taunt_window
        if prediction["turn"] == 4
    ] == [(4, "Taunt", 1.0)]


def test_champ_ascension_nineteen_replaces_gloat_with_defensive_stance():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves(
        "The Champ",
        current_turn=1,
        monster_hp_percent=1.0,
        ascension_level=19,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in predictions[:2]
    ] == [
        (1, "Heavy Slash", 0.45),
        (1, "Defensive Stance", 0.3),
    ]


def test_time_eater_below_half_hp_predicts_haste():
    database = EnhancedMonsterDatabase()

    above_half = database.predict_next_moves(
        "Time Eater",
        current_turn=1,
        monster_hp_percent=0.51,
    )
    below_half = database.predict_next_moves(
        "Time Eater",
        current_turn=1,
        monster_hp_percent=0.49,
    )

    assert above_half[0]["move"]["name"] != "Haste"
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in below_half
    ] == [
        (1, "Haste", 1.0),
        (2, "Reverberate", 0.45),
        (2, "Head Slam", 0.35),
    ]


def test_slime_split_threshold_predicts_split_move():
    database = EnhancedMonsterDatabase()

    above_threshold = database.predict_next_moves(
        "Acid Slime (L)",
        current_turn=1,
        monster_hp_percent=0.51,
    )
    at_threshold = database.predict_next_moves(
        "Acid Slime (L)",
        current_turn=1,
        monster_hp_percent=0.5,
    )
    slime_boss_below_threshold = database.predict_next_moves(
        "Slime Boss",
        current_turn=2,
        monster_hp_percent=0.49,
    )

    assert above_threshold[0]["move"]["name"] != "Split"
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in at_threshold
    ] == [(1, "Split", 1.0)]
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in slime_boss_below_threshold
    ] == [(2, "Split", 1.0)]


def test_giant_head_ascension_eighteen_starts_it_is_time_on_turn_four():
    database = EnhancedMonsterDatabase()

    below_a18 = database.predict_next_moves(
        "Giant Head",
        current_turn=4,
        monster_hp_percent=1.0,
        ascension_level=17,
    )
    asc18 = database.predict_next_moves(
        "Giant Head",
        current_turn=4,
        monster_hp_percent=1.0,
        ascension_level=18,
    )

    assert [
        prediction["move"]["name"]
        for prediction in below_a18
        if prediction["turn"] == 4
    ] == ["Count", "Glare"]
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in asc18
    ] == [
        (4, "It Is Time", 1.0),
        (5, "It Is Time", 1.0),
        (6, "It Is Time", 1.0),
    ]


def test_reptomancer_uses_four_dagger_probability_table():
    database = EnhancedMonsterDatabase()

    normal = database.predict_next_moves(
        "Reptomancer",
        current_turn=2,
        monster_hp_percent=1.0,
        other_enemy_names=["Dagger", "Dagger", "Dagger"],
    )
    full_daggers = database.predict_next_moves(
        "Reptomancer",
        current_turn=2,
        monster_hp_percent=1.0,
        other_enemy_names=["Dagger", "Dagger", "Dagger", "Dagger"],
    )

    assert [
        prediction["move"]["name"]
        for prediction in normal
        if prediction["turn"] == 2
    ] == ["Summon", "Snake Strike", "Big Bite"]
    assert [
        (prediction["move"]["name"], prediction["confidence"])
        for prediction in full_daggers
        if prediction["turn"] == 2
    ] == [("Snake Strike", 0.67), ("Big Bite", 0.33)]


def test_opening_with_move_probabilities_predicts_opening_first():
    database = EnhancedMonsterDatabase()

    opening = database.predict_next_moves(
        "Snecko",
        current_turn=1,
        monster_hp_percent=1.0,
    )
    later = database.predict_next_moves(
        "Snecko",
        current_turn=2,
        monster_hp_percent=1.0,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in opening
    ] == [
        (1, "Perplexing Glare", 1.0),
        (2, "Bite", 0.6),
        (2, "Tail Whip", 0.4),
    ]
    assert [
        (prediction["turn"], prediction["move"]["name"], prediction["confidence"])
        for prediction in later
    ] == [
        (2, "Bite", 0.6),
        (2, "Tail Whip", 0.4),
    ]


def test_transient_predictions_stop_after_fading_turns():
    database = EnhancedMonsterDatabase()

    normal_turn_four = database.predict_next_moves(
        "Transient",
        current_turn=4,
        monster_hp_percent=1.0,
        ascension_level=0,
    )
    normal_turn_six = database.predict_next_moves(
        "Transient",
        current_turn=6,
        monster_hp_percent=1.0,
        ascension_level=0,
    )
    asc17_turn_five = database.predict_next_moves(
        "Transient",
        current_turn=5,
        monster_hp_percent=1.0,
        ascension_level=17,
    )

    assert [
        (prediction["turn"], prediction["move"]["name"])
        for prediction in normal_turn_four
    ] == [(4, "Attack"), (5, "Attack")]
    assert normal_turn_six == []
    assert [
        (prediction["turn"], prediction["move"]["name"])
        for prediction in asc17_turn_five
    ] == [(5, "Attack"), (6, "Attack")]


def test_game_data_loader_forwards_other_enemy_count_to_monster_predictions():
    loader = GameDataLoader(auto_load=False)

    predictions = loader.predict_monster_moves(
        "Gremlin Leader",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_count=0,
    )

    assert [
        prediction["move"]["name"]
        for prediction in predictions
    ] == ["Rally!", "Stab"]


def test_game_data_loader_forwards_other_enemy_names_to_monster_predictions():
    loader = GameDataLoader(auto_load=False)

    predictions = loader.predict_monster_moves(
        "The Collector",
        current_turn=2,
        monster_hp_percent=1.0,
        other_enemy_names=["Torch Head", "Torch Head"],
    )

    assert [
        prediction["move"]["name"]
        for prediction in predictions
    ] == ["Fireball", "Buff"]


def test_game_data_loader_forwards_same_monster_index_to_monster_predictions():
    loader = GameDataLoader(auto_load=False)

    predictions = loader.predict_monster_moves(
        "Sentry",
        current_turn=1,
        monster_hp_percent=1.0,
        same_monster_index=1,
    )

    assert [
        prediction["move"]["name"]
        for prediction in predictions
    ] == ["Beam", "Bolt", "Beam"]


def test_collector_uses_torch_head_state_for_probabilities():
    database = EnhancedMonsterDatabase()

    both_alive = database.predict_next_moves(
        "The Collector",
        current_turn=2,
        monster_hp_percent=1.0,
        other_enemy_names=["Torch Head", "Torch Head"],
    )
    one_dead = database.predict_next_moves(
        "The Collector",
        current_turn=2,
        monster_hp_percent=1.0,
        other_enemy_names=["Torch Head"],
    )
    turn_four = database.predict_next_moves(
        "The Collector",
        current_turn=4,
        monster_hp_percent=1.0,
        other_enemy_names=["Torch Head", "Torch Head"],
    )

    assert [
        (prediction["move"]["name"], prediction["confidence"])
        for prediction in both_alive
    ] == [("Fireball", 0.7), ("Buff", 0.3)]
    assert [
        (prediction["move"]["name"], prediction["confidence"])
        for prediction in one_dead
    ] == [("Fireball", 0.45), ("Buff", 0.3), ("Spawn", 0.25)]
    assert [
        (prediction["turn"], prediction["move"]["name"])
        for prediction in turn_four
    ] == [(4, "Mega Debuff")]


def test_sentry_predicts_position_dependent_alternating_pattern():
    database = EnhancedMonsterDatabase()

    first_sentry = database.predict_next_moves(
        "Sentry",
        current_turn=1,
        monster_hp_percent=1.0,
        same_monster_index=0,
    )
    middle_sentry = database.predict_next_moves(
        "Sentry",
        current_turn=1,
        monster_hp_percent=1.0,
        same_monster_index=1,
    )
    spheric_event_sentry = database.predict_next_moves(
        "Sentry",
        current_turn=1,
        monster_hp_percent=1.0,
        other_enemy_names=["Spheric Guardian"],
    )

    assert [
        prediction["move"]["name"]
        for prediction in first_sentry
    ] == ["Bolt", "Beam", "Bolt"]
    assert [
        prediction["move"]["name"]
        for prediction in middle_sentry
    ] == ["Beam", "Bolt", "Beam"]
    assert [
        prediction["move"]["name"]
        for prediction in spheric_event_sentry
    ] == ["Bolt", "Beam", "Bolt"]
