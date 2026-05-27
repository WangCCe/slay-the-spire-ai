from types import SimpleNamespace
import json
from pathlib import Path
import re

import spirecomm.ai.heuristics.ironclad_combat as ironclad_combat
import spirecomm.ai.heuristics.simulation as simulation
import spirecomm.data.loader as data_loader
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.simulation import FastCombatSimulator
from spirecomm.ai.heuristics.timing.turn_classifier import TurnTimingClassifier
from spirecomm.ai.heuristics.enhanced_monster_database import EnhancedMonsterDatabase
from spirecomm.spire.card import Card, CardRarity, CardType


def _unknown_attack():
    card = Card(
        card_id="UnknownAttack",
        name="Unknown Attack",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
    )
    card.damage = None
    return card


def test_fast_simulator_falls_back_when_card_damage_parse_returns_none(monkeypatch):
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal unknown damage."},
    )
    monkeypatch.setattr(
        simulation.game_data_loader,
        "_parse_card_damage",
        lambda card_data: None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 20,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
            }
        ],
        player_strength=0,
        player_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        _unknown_attack(),
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 6


def test_fast_simulator_falls_back_when_x_damage_calculation_returns_none(monkeypatch):
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: None,
    )
    monkeypatch.setattr(
        FastCombatSimulator,
        "_calculate_x_damage",
        lambda self, card, state, context: None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 20,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
            }
        ],
        player_strength=0,
        player_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        _unknown_attack(),
        target=None,
        target_index=0,
        context=SimpleNamespace(energy_available=3),
    )

    assert state.total_damage_dealt == 6


def test_block_parser_ignores_upgrade_pairs_unrelated_to_block():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "burning pact": {
            "name": "Burning Pact",
            "text": "#Exhaust 1 card.\nDraw [2|3] cards.",
        }
    }

    block = loader._parse_card_block(
        {
            "name": "Burning Pact",
            "description": "Exhaust 1 card. Draw 2 cards.",
        }
    )

    assert block is None


def test_block_parser_reads_upgrade_pairs_from_block_sentence():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "shrug it off": {
            "name": "Shrug It Off",
            "text": "Gain [8|11] #Block.\nDraw 1 card.",
        },
        "power through": {
            "name": "Power Through",
            "text": "Add 2 *Wounds into your hand.\nGain [15|20] #Block.",
        },
    }

    assert loader._parse_card_block({"name": "Shrug It Off"}) == 8
    assert loader._parse_card_block({"name": "Power Through+"}) == 20


def test_damage_parser_reads_reaper_static_damage_despite_healing_text():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "reaper": {
            "name": "Reaper",
            "text": "Deal [4|5] damage to ALL enemies. Heal HP equal to unblocked damage.\n#Exhaust.",
        }
    }

    assert loader._parse_card_damage({"name": "Reaper"}) == 4
    assert loader._parse_card_damage({"name": "Reaper+"}) == 5


def test_damage_parser_ignores_upgrade_pairs_for_debuff_stacks():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "uppercut": {
            "name": "Uppercut",
            "text": "Deal 13 damage.\nApply [1|2] #Weak.\nApply [1|2] #Vulnerable.",
        }
    }

    assert loader._parse_card_damage({"name": "Uppercut", "description": "Deal 13 damage."}) == 13
    assert loader._parse_card_damage({"name": "Uppercut+", "description": "Deal 13 damage."}) == 13


def test_damage_parser_ignores_upgrade_pairs_for_hit_counts():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "pummel": {
            "name": "Pummel",
            "text": "Deal 2 damage [4|5] times.\n#Exhaust.",
        }
    }

    assert loader._parse_card_damage({"name": "Pummel", "description": "Deal 2 damage 4 times."}) == 2
    assert loader._parse_card_damage({"name": "Pummel+", "description": "Deal 2 damage 5 times."}) == 2


def test_damage_parser_ignores_additional_damage_scaling_pairs():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "perfected strike": {
            "name": "Perfected Strike",
            "text": "Deal 6 damage.\nDeals [2|3] additional damage for ALL your cards containing \"Strike\".",
        }
    }

    assert loader._parse_card_damage({"name": "Perfected Strike", "description": "Deal 6 damage."}) == 6
    assert loader._parse_card_damage({"name": "Perfected Strike+", "description": "Deal 6 damage."}) == 6


def test_damage_parser_keeps_heavy_blade_base_damage_static():
    loader = data_loader.GameDataLoader(auto_load=False)

    assert loader._parse_card_damage({"name": "Heavy Blade", "description": "Deal 14 damage."}) == 14
    assert loader._parse_card_damage({"name": "Heavy Blade+", "description": "Deal 14 damage."}) == 14


def test_aoe_parser_does_not_treat_generic_all_as_all_enemies():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "sever soul": {
            "name": "Sever Soul",
            "text": "Exhaust all non-Attack cards in your hand.\nDeal [16|22] damage.",
        },
        "thunderclap": {
            "name": "Thunderclap",
            "text": "Deal [4|7] damage and apply 1 #Vulnerable to ALL enemies.",
        },
    }

    assert not loader._is_card_aoe(
        {
            "name": "Sever Soul",
            "description": "Exhaust all non-Attack cards in your hand. Deal 16 damage.",
        }
    )
    assert loader._is_card_aoe(
        {
            "name": "Thunderclap",
            "description": "Deal 4 damage and apply 1 Vulnerable to ALL enemies.",
        }
    )


def test_ironclad_prune_targets_falls_back_when_damage_parse_returns_none(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal unknown damage."},
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: None,
    )
    monster = SimpleNamespace(current_hp=20, block=0)
    context = SimpleNamespace(strength=0, monsters_alive=[monster])
    state = SimpleNamespace(monsters=[{"hp": 20, "block": 0, "is_gone": False}])

    pruned = IroncladCombatPlanner()._prune_targets(
        _unknown_attack(),
        [(monster, 0, 10)],
        context,
        state,
    )

    assert pruned == [(monster, 0, 10)]


def test_damage_curve_handles_hexaghost_divider_formula_without_warning(caplog):
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=36, ascension_level=0),
        ascension_level=0,
    )
    hexaghost = SimpleNamespace(name="Hexaghost", current_hp=250, max_hp=250, strength=0)

    damage_curve = classifier._calculate_damage_curve(
        context,
        [hexaghost],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [24]
    assert "[DAMAGE_CURVE] Calculation failed" not in caplog.text


def test_nested_monster_probability_tables_predict_moves_without_dict_sort_error():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves("Reptomancer", current_turn=1, monster_hp_percent=1.0)

    assert predictions
    assert {prediction["move"]["name"] for prediction in predictions} <= {"Summon", "Snake Strike", "Big Bite"}
    assert all(isinstance(prediction["confidence"], (int, float)) for prediction in predictions)


def test_safe_window_detection_handles_null_attack_damage_without_warning(monkeypatch, caplog):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {"move": {"name": "Unknown Attack", "intent": "ATTACK", "damage": None, "hits": 2}}
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)

    windows = classifier._detect_safe_windows(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert len(windows) == 1
    assert windows[0].expected_damage == 0
    assert "[SAFE_WINDOWS] Detection failed" not in caplog.text


def test_spike_imminent_handles_monster_damage_ranges_without_warning(monkeypatch, caplog):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {"move": {"name": "Heavy Bite", "intent": "ATTACK", "damage": {"min": 16, "max": 22}, "hits": 1}}
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=80, ascension_level=0),
        turn=1,
        monsters_alive=[SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)],
    )

    assert classifier._spike_imminent(context) is True
    assert "[SPIKE_IMMINENT] Check failed" not in caplog.text


def test_enhanced_monster_database_loads_act2_normal_monsters():
    database = EnhancedMonsterDatabase()

    snake_plant = database.get_monster_data("Snake Plant")
    predictions = database.predict_next_moves("Snake Plant", current_turn=1, monster_hp_percent=1.0)

    assert snake_plant is not None
    assert {prediction["move"]["name"] for prediction in predictions} == {
        "Chomp",
        "Enfeebling Spores",
    }


def test_enhanced_monster_database_loads_jaw_worm_opening_and_moves():
    database = EnhancedMonsterDatabase()

    jaw_worm = database.get_monster_data("Jaw Worm")
    opening = database.predict_next_moves("Jaw Worm", current_turn=1, monster_hp_percent=1.0)
    later = database.predict_next_moves("Jaw Worm", current_turn=2, monster_hp_percent=1.0)

    assert jaw_worm is not None
    assert [move["name"] for move in jaw_worm["moves"]] == ["Chomp", "Thrash", "Bellow"]
    assert opening[0]["move"]["name"] == "Chomp"
    assert {prediction["move"]["name"] for prediction in later[:2]} == {"Bellow", "Thrash"}


def test_chosen_opening_and_phase_probabilities_predict_moves():
    database = EnhancedMonsterDatabase()

    opening = database.predict_next_moves("Chosen", current_turn=1, monster_hp_percent=1.0)
    phase = database.predict_next_moves("Chosen", current_turn=3, monster_hp_percent=1.0)

    assert [prediction["move"]["name"] for prediction in opening[:2]] == ["Poke", "Hex"]
    assert {prediction["move"]["name"] for prediction in phase[:2]} == {"Debilitate", "Drain"}


def test_monster_multi_hit_damage_fields_are_per_hit():
    root = Path("spirecomm/data/monster_wiki_data")
    with (root / "act1_normal_monsters.json").open(encoding="utf-8") as f:
        act1_normal = json.load(f)
    with (root / "act2_normal_monsters.json").open(encoding="utf-8") as f:
        act2_normal = json.load(f)

    spheric_guardian = next(monster for monster in act1_normal if monster["name"] == "Spheric Guardian")
    chosen = next(monster for monster in act2_normal if monster["name"] == "Chosen")

    spheric_slam = next(move for move in spheric_guardian["moves"] if move["name"] == "Slam")
    chosen_poke = next(move for move in chosen["moves"] if move["name"] == "Poke")

    assert spheric_slam["damage"] == 10
    assert spheric_slam["hits"] == 2
    assert chosen_poke["damage"] == 5
    assert chosen_poke["hits"] == 2


def test_monster_multi_hit_effects_match_damage_and_hits_fields():
    root = Path("spirecomm/data/monster_wiki_data")
    patterns = [
        re.compile(r"Deals? (\d+)\s*x\s*(\d+) damage", re.IGNORECASE),
        re.compile(r"Deals? (\d+) damage (\d+) times", re.IGNORECASE),
    ]
    mismatches = []

    for data_file in root.glob("*.json"):
        with data_file.open(encoding="utf-8") as f:
            data = json.load(f)
        monsters = data.values() if isinstance(data, dict) else data

        for monster in monsters:
            for move in monster.get("moves", []):
                effect = move.get("effect", "") or ""
                expected = None
                for pattern in patterns:
                    match = pattern.search(effect)
                    if match:
                        expected = (int(match.group(1)), int(match.group(2)))
                        break
                if expected and (move.get("damage"), move.get("hits")) != expected:
                    mismatches.append(
                        (
                            data_file.name,
                            monster.get("name"),
                            move.get("name"),
                            move.get("damage"),
                            move.get("hits"),
                            expected,
                        )
                    )

    assert mismatches == []


def test_damage_curve_uses_first_prediction_for_each_target_turn(monkeypatch):
    def fake_predict_monster_moves(_monster_name, current_turn, _hp_percent):
        return [
            {
                "move": {
                    "name": f"Turn {current_turn}",
                    "intent": "ATTACK",
                    "damage": current_turn,
                    "hits": 1,
                }
            },
            {
                "move": {
                    "name": f"Skipped {current_turn}",
                    "intent": "ATTACK",
                    "damage": current_turn + 10,
                    "hits": 1,
                }
            },
        ]

    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        fake_predict_monster_moves,
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Scripted", current_hp=20, max_hp=20, strength=0)

    damage_curve = classifier._calculate_damage_curve(
        context,
        [monster],
        current_turn=1,
        look_ahead=2,
    )

    assert damage_curve == [2, 3]


def test_opening_then_alternating_patterns_predict_full_sequence():
    database = EnhancedMonsterDatabase()

    predictions = database.predict_next_moves("Spheric Guardian", current_turn=1, monster_hp_percent=1.0)

    assert [prediction["move"]["name"] for prediction in predictions] == [
        "Activate",
        "Attack/Debuff",
        "Slam",
    ]


def test_small_slime_patterns_predict_future_damage_for_timing_classifier():
    database = EnhancedMonsterDatabase()

    spike_predictions = database.predict_next_moves("Spike Slime (S)", current_turn=2, monster_hp_percent=1.0)
    acid_predictions = database.predict_next_moves("Acid Slime (S)", current_turn=2, monster_hp_percent=1.0)

    assert [prediction["move"]["name"] for prediction in spike_predictions] == [
        "Tackle",
        "Tackle",
        "Tackle",
    ]
    assert [prediction["move"]["name"] for prediction in acid_predictions] == [
        "Tackle",
        "Lick",
        "Tackle",
    ]

    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=55, ascension_level=0), ascension_level=0)
    monsters = [
        SimpleNamespace(name="Acid Slime (S)", current_hp=12, max_hp=12, strength=0),
        SimpleNamespace(name="Spike Slime (S)", current_hp=13, max_hp=13, strength=0),
        SimpleNamespace(name="Spike Slime (S)", current_hp=14, max_hp=14, strength=0),
        SimpleNamespace(name="Spike Slime (S)", current_hp=12, max_hp=12, strength=0),
    ]

    assert classifier._calculate_damage_curve(context, monsters, current_turn=1, look_ahead=2) == [18, 15]


def test_timing_analysis_clamps_negative_live_move_damage_to_zero():
    classifier = TurnTimingClassifier()
    monster = SimpleNamespace(
        name="Spike Slime (M)",
        current_hp=25,
        max_hp=25,
        strength=0,
        intent="Intent.DEBUFF",
        move_adjusted_damage=-1,
        move_hits=3,
    )
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))

    analysis = classifier._analyze_monster_timing(context, [monster], current_turn=7)

    assert analysis["current_damage"] == 0


def test_hp_threshold_modes_predict_guardian_sequence():
    database = EnhancedMonsterDatabase()

    high_hp = database.predict_next_moves("The Guardian", current_turn=1, monster_hp_percent=1.0)
    low_hp = database.predict_next_moves("The Guardian", current_turn=1, monster_hp_percent=0.4)

    assert [prediction["move"]["name"] for prediction in high_hp] == [
        "Charging Up",
        "Fierce Bash",
        "Vent Steam",
    ]
    assert [prediction["move"]["name"] for prediction in low_hp] == [
        "Defensive Mode",
        "Roll Attack",
        "Twin Slam",
    ]

    moves = {move["name"]: move for move in database.get_moves("The Guardian")}
    assert moves["Charging Up"]["block_gain"] == 9
    assert moves["Fierce Bash"]["damage"] == 32
    assert moves["Vent Steam"]["weak_applied"] == 2
    assert moves["Vent Steam"]["vulnerable_applied"] == 2
    assert moves["Whirlwind"]["damage"] == 5
    assert moves["Whirlwind"]["hits"] == 4
    assert moves["Defensive Mode"]["sharp_hide_gain"] == 3
    assert moves["Roll Attack"]["damage"] == 9
    assert moves["Twin Slam"]["damage"] == 8
    assert moves["Twin Slam"]["hits"] == 2


def test_enhanced_monster_database_covers_common_act2_threats():
    database = EnhancedMonsterDatabase()

    expected_moves = {
        "Shell Parasite": {"Double Strike", "Suck"},
        "Shelled Parasite": {"Double Strike", "Suck"},
        "Byrd": {"Swoop", "Peck"},
        "Spire Growth": {"Quick Tackle", "Smash"},
        "Centurion": {"Slash"},
        "Mystic": {"Heal", "Attack"},
        "Healer": {"Heal", "Attack"},
        "Bronze Automaton": {"Spawn Orbs"},
        "Automaton": {"Spawn Orbs"},
        "Bronze Orb": {"Stasis", "Beam"},
    }

    for monster_name, moves in expected_moves.items():
        monster_data = database.get_monster_data(monster_name)
        predictions = database.predict_next_moves(monster_name, current_turn=1, monster_hp_percent=1.0)

        assert monster_data is not None, monster_name
        assert {prediction["move"]["name"] for prediction in predictions} & moves, monster_name


def test_collector_data_uses_torch_heads_and_mega_debuff():
    database = EnhancedMonsterDatabase()

    collector = database.get_monster_data("The Collector")
    moves = {move["name"]: move for move in database.get_moves("The Collector")}
    turn_one = database.predict_next_moves("The Collector", current_turn=1, monster_hp_percent=1.0)
    turn_four = database.predict_next_moves("The Collector", current_turn=4, monster_hp_percent=1.0)
    torch_head = database.get_monster_data("Torch Head")
    torch_predictions = database.predict_next_moves("Torch Head", current_turn=2, monster_hp_percent=1.0)

    assert collector["hp_ranges"]["normal"] == {"min": 282, "max": 282}
    assert set(moves) == {"Spawn", "Fireball", "Buff", "Mega Debuff"}
    assert moves["Spawn"]["summons"] == ["Torch Head", "Torch Head"]
    assert moves["Fireball"]["damage"] == 18
    assert moves["Buff"]["strength_gain"] == 3
    assert moves["Buff"]["block_gain"] == 15
    assert moves["Mega Debuff"]["weak_applied"] == 3
    assert moves["Mega Debuff"]["vulnerable_applied"] == 3
    assert moves["Mega Debuff"]["frail_applied"] == 3
    assert turn_one[0]["move"]["name"] == "Spawn"
    assert turn_four[0]["move"]["name"] == "Mega Debuff"
    assert torch_head is not None
    assert torch_predictions[0]["move"]["name"] == "Tackle"
    assert torch_predictions[0]["move"]["damage"] == 7
