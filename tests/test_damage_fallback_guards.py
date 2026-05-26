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

    predictions = database.predict_next_moves("Chosen", current_turn=1, monster_hp_percent=1.0)

    assert predictions
    assert {prediction["move"]["name"] for prediction in predictions} <= {"Slash", "Hex", "Protect"}
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
