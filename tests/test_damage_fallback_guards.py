from types import SimpleNamespace

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


def test_chosen_opening_and_phase_probabilities_predict_moves():
    database = EnhancedMonsterDatabase()

    opening = database.predict_next_moves("Chosen", current_turn=1, monster_hp_percent=1.0)
    phase = database.predict_next_moves("Chosen", current_turn=3, monster_hp_percent=1.0)

    assert [prediction["move"]["name"] for prediction in opening[:2]] == ["Poke", "Hex"]
    assert {prediction["move"]["name"] for prediction in phase[:2]} == {"Debilitate", "Drain"}
