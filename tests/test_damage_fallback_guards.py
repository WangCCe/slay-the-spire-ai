from types import SimpleNamespace
import json
from pathlib import Path
import re

import spirecomm.ai.heuristics.ironclad_combat as ironclad_combat
import spirecomm.ai.heuristics.simulation as simulation
import spirecomm.data.loader as data_loader
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.simulation import FastCombatSimulator, HeuristicCombatPlanner
from spirecomm.ai.heuristics.timing.turn_classifier import TurnTimingClassifier
from spirecomm.communication.action import PlayCardAction, PotionAction
from spirecomm.ai.heuristics.enhanced_monster_database import EnhancedMonsterDatabase
from spirecomm.spire.card import Card, CardRarity, CardType
from spirecomm.spire.character import Intent
from spirecomm.spire.potion import Potion


def test_champ_phase_transition_predicts_anger_then_execute():
    db = EnhancedMonsterDatabase()

    predictions = db.predict_next_moves(
        "The Champ",
        current_turn=8,
        monster_hp_percent=206 / 420,
    )

    assert [(p["turn"], p["move"]["name"]) for p in predictions[:2]] == [
        (8, "Anger"),
        (9, "Execute"),
    ]


def test_damage_curve_counts_champ_execute_after_transition_strength():
    classifier = TurnTimingClassifier()
    champ = SimpleNamespace(
        name="The Champ",
        current_hp=206,
        max_hp=420,
        strength=0,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=50, ascension_level=0),
        ascension_level=0,
    )

    damage_curve = classifier._calculate_damage_curve(
        context,
        [champ],
        current_turn=8,
        look_ahead=2,
    )

    assert damage_curve[0] == 32


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


def test_fast_simulator_does_not_apply_generic_damage_upgrade_for_unknown_cards(monkeypatch):
    card = Card(
        card_id="Tactical Jab",
        name="Tactical Jab",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Tactical Jab",
        "description": "Deal 8 damage. Apply [1|2] Weak.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Tactical Jab" else None,
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
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 8
    assert state.monsters[0]["weak"] == 2


def test_skill_simulation_applies_targeted_debuff_to_selected_monster(monkeypatch):
    card = Card(
        card_id="Leg Sweep",
        name="Leg Sweep",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=2,
    )
    card_data = {
        "name": "Leg Sweep",
        "description": "Apply 2 Weak.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Leg Sweep" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "artifact": 0,
            },
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "artifact": 0,
            },
        ],
        player_block=0,
        player_energy=0,
        player_strength=0,
        energy_gained=0,
        exhaust_events=0,
        cards_drawn=0,
    )

    FastCombatSimulator(None)._apply_skill(state, card, target_index=1)

    assert state.monsters[0]["weak"] == 0
    assert state.monsters[1]["weak"] == 2


def test_attack_simulation_applies_poison_card_effect(monkeypatch):
    card = Card(
        card_id="Poisoned Stab",
        name="Poisoned Stab",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
    )
    card_data = {
        "name": "Poisoned Stab",
        "description": "Deal 6 damage. Apply 3 Poison.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Poisoned Stab" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 20,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "poison": 0,
                "artifact": 0,
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
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 6
    assert state.monsters[0]["poison"] == 3


def test_skill_simulation_applies_targeted_poison(monkeypatch):
    card = Card(
        card_id="Deadly Poison",
        name="Deadly Poison",
        card_type=CardType.SKILL,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
    )
    card_data = {
        "name": "Deadly Poison",
        "description": "Apply 5 Poison.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Deadly Poison" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "poison": 0,
                "artifact": 0,
            }
        ],
        player_block=0,
        player_energy=0,
        player_strength=0,
        energy_gained=0,
        exhaust_events=0,
        cards_drawn=0,
    )

    FastCombatSimulator(None)._apply_skill(state, card, target_index=0)

    assert state.monsters[0]["poison"] == 5


def test_fast_simulator_uses_display_name_for_basic_card_ids(monkeypatch):
    card = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Strike",
        "description": "Deal 6 damage.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Strike" else None,
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
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 9


def test_target_estimation_uses_known_upgrade_damage_for_basic_card_ids(monkeypatch):
    card = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Strike",
        "description": "Deal 6 damage.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Strike" else None,
    )
    killable = SimpleNamespace(current_hp=8, block=0)
    dangerous = SimpleNamespace(current_hp=30, block=0)
    context = SimpleNamespace(
        monsters_alive=[killable, dangerous],
        player=SimpleNamespace(strength=0),
        compute_threat=lambda monster: 100 if monster is dangerous else 1,
    )

    target = HeuristicCombatPlanner()._find_best_target(card, context)

    assert target is killable


def test_damage_potion_target_prefers_lethal_before_threat():
    potion = SimpleNamespace(effect_type="damage", effect_value=20)
    killable = SimpleNamespace(current_hp=15)
    dangerous = SimpleNamespace(current_hp=80)
    context = SimpleNamespace(
        monsters_alive=[killable, dangerous],
        compute_threat=lambda monster: 100 if monster is dangerous else 1,
    )

    target = HeuristicCombatPlanner()._find_best_potion_target(potion, context)

    assert target is killable


def test_fast_simulator_applies_all_searing_blow_upgrades(monkeypatch):
    card = Card(
        card_id="Searing Blow",
        name="Searing Blow+2",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=2,
        upgrades=2,
    )
    card_data = {
        "name": "Searing Blow",
        "description": "Deal 12 damage. Can be Upgraded any number of times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Searing Blow" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
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
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 21


def test_fast_simulator_counts_upgraded_sword_boomerang_hits_with_counted_suffix(monkeypatch):
    card = Card(
        card_id="Sword Boomerang+1",
        name="Sword Boomerang+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Sword Boomerang",
        "description": "Deal 3 damage to a random enemy 3 times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Sword Boomerang" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
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
        card,
        target=None,
        target_index=None,
        context=None,
    )

    assert state.damage_instances == 4
    assert state.total_damage_dealt == 12


def test_fast_simulator_reaper_healing_uses_counted_upgrade_suffix(monkeypatch):
    card = Card(
        card_id="Reaper+1",
        name="Reaper+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.RARE,
        has_target=False,
        cost=2,
        upgrades=1,
    )
    card_data = {
        "name": "Reaper",
        "description": "Deal 4 damage to ALL enemies. Heal HP equal to unblocked damage.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Reaper" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
            },
            {
                "hp": 40,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
            },
        ],
        player_strength=0,
        player_hp=40,
        player_max_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
        exhaust_events=0,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        card,
        target=None,
        target_index=None,
        context=None,
    )

    assert state.total_damage_dealt == 10
    assert state.player_hp == 50


def test_fast_simulator_dropkick_resource_effect_uses_counted_upgrade_suffix(monkeypatch):
    card = Card(
        card_id="Dropkick+1",
        name="Dropkick+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Dropkick",
        "description": "Deal 5 damage. If the enemy has Vulnerable, gain 1 energy and draw 1 card.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Dropkick" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
                "block": 0,
                "is_gone": False,
                "vulnerable": 1,
                "weak": 0,
                "thorns": 0,
            }
        ],
        player_strength=0,
        player_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
        player_energy=1,
        energy_gained=0,
        cards_drawn=0,
        draw_blocked=False,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert state.energy_gained == 1
    assert state.player_energy == 2
    assert state.cards_drawn == 1


def test_fast_simulator_iron_wave_block_uses_counted_upgrade_suffix(monkeypatch):
    card = Card(
        card_id="Iron Wave+1",
        name="Iron Wave+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Iron Wave",
        "description": "Gain 5 Block. Deal 5 damage.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Iron Wave" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
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
        player_block=0,
        player_frail=0,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 7
    assert state.player_block == 7


def test_fast_simulator_fiend_fire_exhaust_uses_counted_upgrade_suffix(monkeypatch):
    fiend_fire = Card(
        card_id="Fiend Fire+1",
        name="Fiend Fire+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.RARE,
        has_target=True,
        cost=2,
        upgrades=1,
        uuid="fiend-fire",
    )
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        has_target=True,
        cost=1,
        uuid="strike",
    )
    defend = Card(
        card_id="Defend_R",
        name="Defend",
        card_type=CardType.SKILL,
        rarity=CardRarity.BASIC,
        has_target=False,
        cost=1,
        uuid="defend",
    )
    card_data = {
        "name": "Fiend Fire",
        "description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Fiend Fire" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 100,
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
        exhaust_events=0,
        played_card_uuids=set(),
    )
    context = SimpleNamespace(
        game=SimpleNamespace(hand=[fiend_fire, strike, defend]),
        playable_cards=[fiend_fire, strike, defend],
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        fiend_fire,
        target=None,
        target_index=0,
        context=context,
    )

    assert state.exhaust_events == 3
    assert {"strike", "defend"} <= state.played_card_uuids


def test_fast_simulator_body_slam_damage_uses_counted_upgrade_suffix(monkeypatch):
    card = Card(
        card_id="Body Slam+1",
        name="Body Slam+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: {"name": "Body Slam"} if card_name == "Body Slam" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
            }
        ],
        player_strength=0,
        player_hp=80,
        player_block=18,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        card,
        target=None,
        target_index=0,
        context=SimpleNamespace(energy_available=1),
    )

    assert state.total_damage_dealt == 18


def test_game_data_parser_applies_counted_searing_blow_upgrade_suffix():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {}

    damage = loader._parse_card_damage(
        {
            "name": "Searing Blow+2",
            "description": "Deal 12 damage. Can be Upgraded any number of times.",
        }
    )

    assert damage == 21


def test_fast_score_values_upgraded_rage_block_per_attack():
    attacks = [
        Card(
            card_id="Strike_R",
            name="Strike",
            card_type=CardType.ATTACK,
            rarity=CardRarity.BASIC,
            has_target=True,
            cost=1,
        )
        for _ in range(2)
    ]
    state = SimpleNamespace(
        monsters=[{"is_gone": False}],
        player_hp=50,
        player_energy=3,
    )
    context = SimpleNamespace(
        playable_cards=attacks,
        player_class="IRONCLAD",
        turn=1,
    )
    base_rage = Card(
        card_id="Rage",
        name="Rage",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=False,
        cost=0,
    )
    upgraded_rage = Card(
        card_id="Rage",
        name="Rage+",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=False,
        cost=0,
        upgrades=1,
    )
    planner = HeuristicCombatPlanner()

    base_score = planner.fast_score_action(base_rage, state, context)
    upgraded_score = planner.fast_score_action(upgraded_rage, state, context)

    assert upgraded_score == base_score + 6


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


def test_block_parser_handles_counted_upgrade_suffixes():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "power through": {
            "name": "Power Through",
            "text": "Gain [15|20] #Block.\nAdd 2 #Wounds into your hand.",
        },
    }

    assert loader._parse_card_block({"name": "Power Through+1"}) == 20


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


def test_aoe_parser_handles_counted_upgrade_suffixes():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "cleave": {
            "name": "Cleave",
            "text": "Deal [8|11] damage to ALL enemies.",
        },
    }

    assert loader._is_card_aoe({"name": "Cleave+1"}) is True


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


def test_ironclad_fallback_damage_uses_canonical_name_for_counted_upgrades(monkeypatch):
    card = Card(
        card_id="Cleave+1",
        name="Cleave+1",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=False,
        cost=1,
        upgrades=1,
    )
    card.damage = None

    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 11 damage."} if card_name == "Cleave" else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 11,
    )
    context = SimpleNamespace(strength=0)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(card, context)

    assert damage == 11


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


def test_safe_window_detection_applies_ascension_damage_modifiers(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "move": {
                    "name": "Heavy Bite",
                    "intent": "ATTACK",
                    "damage": 8,
                    "hits": 1,
                    "ascension_modifiers": {"2+": {"damage": 12}},
                }
            }
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=2))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)

    windows = classifier._detect_safe_windows(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert windows == []


def test_safe_window_detection_counts_monster_strength(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {"move": {"name": "Bite", "intent": "ATTACK", "damage": 8, "hits": 1}}
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=3)

    windows = classifier._detect_safe_windows(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert windows == []


def test_safe_window_detection_counts_scripted_strength_gain_before_attack(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "turn": 2,
                "move": {
                    "name": "Grow",
                    "intent": "BUFF",
                    "strength_gain": 3,
                },
            },
            {
                "turn": 3,
                "move": {
                    "name": "Bite",
                    "intent": "ATTACK",
                    "damage": 8,
                    "hits": 1,
                },
            },
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)

    windows = classifier._detect_safe_windows(
        context,
        [monster],
        current_turn=2,
        look_ahead=2,
    )

    assert [(window.start_turn, window.end_turn, window.expected_damage) for window in windows] == [
        (2, 2, 0)
    ]


def test_safe_window_detection_uses_target_turn_for_damage_and_hits_formulas(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "turn": 5,
                "move": {
                    "name": "Scaling Strike",
                    "intent": "ATTACK",
                    "damage_formula": {
                        "type": "linear_by_turn",
                        "base": 0,
                        "per_turn": 1,
                    },
                    "hits_formula": {
                        "type": "ceil_turn_divisor",
                        "divisor": 3,
                    },
                },
            }
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)

    windows = classifier._detect_safe_windows(
        context,
        [monster],
        current_turn=5,
        look_ahead=1,
    )

    assert windows == []


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


def test_spike_imminent_applies_ascension_damage_modifiers(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "move": {
                    "name": "Heavy Strike",
                    "intent": "ATTACK",
                    "damage": 18,
                    "hits": 1,
                    "ascension_modifiers": {"2+": {"damage": 20}},
                }
            }
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=80, ascension_level=2),
        turn=1,
        monsters_alive=[SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)],
    )

    assert classifier._spike_imminent(context) is True


def test_spike_imminent_counts_monster_strength(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {"move": {"name": "Heavy Strike", "intent": "ATTACK", "damage": 18, "hits": 1}}
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=80, ascension_level=0),
        turn=1,
        monsters_alive=[SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=2)],
    )

    assert classifier._spike_imminent(context) is True


def test_spike_imminent_counts_scripted_strength_gain_before_attack(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "turn": 2,
                "move": {
                    "name": "Grow",
                    "intent": "BUFF",
                    "strength_gain": 3,
                },
            },
            {
                "turn": 3,
                "move": {
                    "name": "Heavy Strike",
                    "intent": "ATTACK",
                    "damage": 18,
                    "hits": 1,
                },
            },
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=80, ascension_level=0),
        turn=1,
        monsters_alive=[SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)],
    )

    assert classifier._spike_imminent(context) is True


def test_spike_imminent_ignores_non_attack_moves_with_high_strength(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "turn": 2,
                "move": {
                    "name": "Grow",
                    "intent": "BUFF",
                    "strength_gain": 3,
                },
            }
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=80, ascension_level=0),
        turn=1,
        monsters_alive=[SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=25)],
    )

    assert classifier._spike_imminent(context) is False


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


def test_damage_curve_applies_absolute_ascension_damage_modifiers(monkeypatch):
    def fake_predict_monster_moves(_monster_name, _current_turn, _hp_percent):
        return [
            {
                "move": {
                    "name": "Heavy Strike",
                    "intent": "ATTACK",
                    "damage": 12,
                    "hits": 1,
                    "ascension_modifiers": {"2+": {"damage": 14}},
                }
            }
        ]

    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        fake_predict_monster_moves,
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=2))
    monster = SimpleNamespace(name="Scripted", current_hp=20, max_hp=20, strength=0)

    damage_curve = classifier._calculate_damage_curve(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [14]


def test_damage_curve_applies_absolute_ascension_hit_modifiers(monkeypatch):
    def fake_predict_monster_moves(_monster_name, _current_turn, _hp_percent):
        return [
            {
                "move": {
                    "name": "Twin Tackle",
                    "intent": "ATTACK",
                    "damage": 5,
                    "hits": 1,
                    "ascension_modifiers": {"4+": {"hits": 2}},
                }
            }
        ]

    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        fake_predict_monster_moves,
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=4))
    monster = SimpleNamespace(name="Scripted", current_hp=20, max_hp=20, strength=0)

    damage_curve = classifier._calculate_damage_curve(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [10]


def test_damage_curve_keeps_lower_ascension_damage_when_higher_modifier_changes_debuff(monkeypatch):
    def fake_predict_monster_moves(_monster_name, _current_turn, _hp_percent):
        return [
            {
                "move": {
                    "name": "Rake",
                    "intent": "ATTACK_DEBUFF",
                    "damage": 7,
                    "hits": 1,
                    "ascension_modifiers": {
                        "2+": {"damage": 8},
                        "17+": {"weak_applied": 2},
                    },
                }
            }
        ]

    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        fake_predict_monster_moves,
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=17))
    monster = SimpleNamespace(name="Gremlin Nob", current_hp=82, max_hp=82, strength=0)

    damage_curve = classifier._calculate_damage_curve(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [8]


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


def test_timing_analysis_ignores_non_attack_current_intents():
    classifier = TurnTimingClassifier()
    buffing = SimpleNamespace(
        name="Spike Slime (M)",
        current_hp=25,
        max_hp=25,
        strength=0,
        intent="Intent.DEBUFF",
        move_adjusted_damage=12,
        move_hits=1,
    )
    attacking = SimpleNamespace(
        name="Jaw Worm",
        current_hp=40,
        max_hp=40,
        strength=0,
        intent="Intent.ATTACK",
        move_adjusted_damage=7,
        move_hits=2,
    )
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))

    analysis = classifier._analyze_monster_timing(context, [buffing, attacking], current_turn=7)

    assert analysis["current_damage"] == 14


def test_timing_analysis_does_not_mark_non_attack_stale_damage_as_spike():
    classifier = TurnTimingClassifier()
    buffing = SimpleNamespace(
        name="Spike Slime (M)",
        current_hp=25,
        max_hp=25,
        strength=0,
        intent="Intent.BUFF",
        move_adjusted_damage=30,
        move_hits=1,
    )
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))

    analysis = classifier._analyze_monster_timing(context, [buffing], current_turn=7)

    assert analysis["current_damage"] == 0
    assert analysis["spike_monster_count"] == 0


def test_safe_intent_detection_accepts_enum_string_names():
    classifier = TurnTimingClassifier()
    hints = SimpleNamespace(is_safe_turn=lambda _intent: False)

    assert classifier._is_safe_intent("Intent.BUFF", "Intent.ATTACK", hints) is True


def test_heuristic_incoming_damage_clamps_negative_live_move_damage_to_zero():
    monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp=25,
        is_gone=False,
        half_dead=False,
        intent="Intent.DEBUFF",
        move_id=2,
        move_adjusted_damage=-1,
        move_hits=3,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=1,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 0


def test_heuristic_incoming_damage_ignores_non_attack_intents():
    monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp=25,
        is_gone=False,
        half_dead=False,
        intent="Intent.DEBUFF",
        move_id=2,
        move_adjusted_damage=12,
        move_hits=2,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=1,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 0


def test_heuristic_incoming_damage_estimates_unknown_intent_by_act():
    monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp=25,
        is_gone=False,
        half_dead=False,
        intent=Intent.UNKNOWN,
        move_id=2,
        move_adjusted_damage=None,
        move_hits=1,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=2,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 10


def test_heuristic_incoming_damage_clamps_negative_live_move_hits_to_one():
    monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp=25,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=2,
        move_adjusted_damage=7,
        move_hits=-2,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=1,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 7


def test_heuristic_incoming_damage_ignores_zero_hp_stale_monsters():
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        current_hp=0,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=1,
        move_adjusted_damage=12,
        move_hits=1,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=1,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 0


def test_damage_potion_score_ignores_zero_hp_stale_monsters():
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        current_hp=0,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=1,
        move_adjusted_damage=12,
        move_hits=1,
    )
    potion = SimpleNamespace(effect_type="damage", effect_value=20)
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster], room_type="Monster"),
        act=1,
        vulnerable_stacks={0: 0},
    )
    state = SimpleNamespace(player_hp=80, player_max_hp=80)

    assert HeuristicCombatPlanner()._score_potion(potion, context, state) == 0


def test_damage_potion_score_does_not_treat_vulnerable_as_lethal():
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        current_hp=25,
        is_gone=False,
        half_dead=False,
        intent=Intent.SLEEP,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    potion = SimpleNamespace(effect_type="damage", effect_value=20)
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster], room_type="Monster"),
        act=1,
        vulnerable_stacks={0: 2},
    )
    state = SimpleNamespace(player_hp=80, player_max_hp=80)

    assert HeuristicCombatPlanner()._score_potion(potion, context, state) == 0


def test_poison_potion_score_does_not_treat_poison_as_immediate_lethal():
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        current_hp=6,
        is_gone=False,
        half_dead=False,
        intent=Intent.SLEEP,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    potion = SimpleNamespace(effect_type="poison", effect_value=6)
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster], room_type="Monster"),
        act=1,
        vulnerable_stacks={0: 0},
    )
    state = SimpleNamespace(player_hp=80, player_max_hp=80)

    assert HeuristicCombatPlanner()._score_potion(potion, context, state) == 0


def test_beam_search_can_use_potion_when_no_cards_are_playable():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 18,
    )

    sequence = HeuristicCombatPlanner().plan_turn(context)

    assert len(sequence) == 1
    assert isinstance(sequence[0], PotionAction)
    assert sequence[0].potion is potion


def test_beam_search_damage_potion_updates_damage_events():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        max_hp=50,
        current_hp=15,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=6,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 6,
    )
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed.append(
                {
                    "hp": final_state.monsters[0]["hp"],
                    "is_gone": final_state.monsters[0]["is_gone"],
                    "damage": final_state.total_damage_dealt,
                    "kills": final_state.monsters_killed,
                    "instances": final_state.damage_instances,
                }
            )
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed == [
        {
            "hp": 0,
            "is_gone": True,
            "damage": 15,
            "kills": 1,
            "instances": 1,
        }
    ]


def test_beam_search_speed_potion_improves_later_card_block():
    potion = Potion(
        potion_id="SpeedPotion",
        name="Speed Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    defend = Card(
        card_id="Defend_R",
        name="Defend",
        card_type=CardType.SKILL,
        rarity=CardRarity.BASIC,
        has_target=False,
        cost=1,
        uuid="defend",
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            hand=[defend],
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=1,
        strength=0,
        player_hp_pct=0.5,
        incoming_damage=18,
        card_synergies={},
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[defend],
        compute_threat=lambda monster: 18,
    )
    planner = HeuristicCombatPlanner()
    observed_block = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if (
            len(sequence) == 2
            and isinstance(sequence[0], PotionAction)
            and isinstance(sequence[1], PlayCardAction)
        ):
            observed_block.append(final_state.player_block)
        return final_state.player_block

    planner.simulator.calculate_outcome_score = score

    planner.plan_turn(context)

    assert observed_block == [10]


def test_beam_search_simulates_debuff_potion_effect():
    potion = Potion(
        potion_id="FearPotion",
        name="Fear Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    expensive_cards = [
        SimpleNamespace(
            card_id=f"Expensive{i}",
            name=f"Expensive {i}",
            cost=99,
            cost_for_turn=99,
            has_target=False,
        )
        for i in range(3)
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=1,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=expensive_cards,
    )
    planner = HeuristicCombatPlanner()
    observed_vulnerable = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed_vulnerable.append(final_state.monsters[0]["vulnerable"])
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed_vulnerable == [3]


def test_beam_search_does_not_simulate_poison_potion_as_immediate_damage():
    potion = Potion(
        potion_id="PoisonPotion",
        name="Poison Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=50,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 18,
    )
    planner = HeuristicCombatPlanner()
    observed_hp = []
    observed_poison = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed_hp.append(final_state.monsters[0]["hp"])
            observed_poison.append(final_state.monsters[0].get("poison", 0))
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed_hp == [50]
    assert observed_poison == [6]


def test_beam_search_poison_potion_consumes_monster_artifact():
    potion = Potion(
        potion_id="PoisonPotion",
        name="Poison Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=50,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[SimpleNamespace(power_name="Artifact", amount=1)],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 18,
    )
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed.append(
                {
                    "poison": final_state.monsters[0].get("poison", 0),
                    "artifact": final_state.monsters[0].get("artifact", 0),
                }
            )
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed == [{"poison": 0, "artifact": 0}]


def test_beam_search_simulates_plated_armor_potion_as_end_turn_block():
    potion = Potion(
        potion_id="EssenceOfSteel",
        name="Essence of Steel",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=30,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 30,
    )
    planner = HeuristicCombatPlanner()
    observed_current_block = []
    observed_end_turn_block = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed_current_block.append(final_state.player_block)
            observed_end_turn_block.append(final_state.end_turn_block)
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed_current_block == [0]
    assert observed_end_turn_block == [4]


def test_beam_search_simulates_liquid_bronze_as_player_thorns():
    potion = Potion(
        potion_id="LiquidBronze",
        name="Liquid Bronze",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 18,
    )
    planner = HeuristicCombatPlanner()
    observed_thorns = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed_thorns.append(getattr(final_state, "player_thorns", 0))
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed_thorns == [3]


def test_outcome_score_values_player_thorns_against_current_attackers():
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        max_hp=50,
        current_hp=50,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=6,
        move_hits=2,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
        ),
        act=1,
        turn=1,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    simulator = FastCombatSimulator(None)
    weights = simulation.get_combat_mode_weights(simulation.CombatMode.BALANCED)
    initial_state = simulation.SimulationState(context)
    no_thorns = initial_state.clone()
    with_thorns = initial_state.clone()
    with_thorns.player_thorns = 3

    base_score = simulator.calculate_outcome_score(
        initial_state,
        no_thorns,
        current_act=1,
        weights=weights,
        context=None,
        sequence=[],
    )
    thorns_score = simulator.calculate_outcome_score(
        initial_state,
        with_thorns,
        current_act=1,
        weights=weights,
        context=None,
        sequence=[],
    )

    assert thorns_score - base_score == 6 * weights["DAMAGE_WEIGHT"]


def test_beam_search_simulates_ghost_in_a_jar_as_player_intangible():
    potion = Potion(
        potion_id="GhostInAJar",
        name="Ghost in a Jar",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=30,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=20,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 30,
    )
    planner = HeuristicCombatPlanner()
    observed_intangible = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed_intangible.append(getattr(final_state, "player_intangible", 0))
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed_intangible == [1]


def test_outcome_score_uses_intangible_for_current_incoming_damage():
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=30,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=20,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
        ),
        act=1,
        turn=1,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    simulator = FastCombatSimulator(None)
    weights = simulation.get_combat_mode_weights(simulation.CombatMode.BALANCED)
    initial_state = simulation.SimulationState(context)
    no_intangible = initial_state.clone()
    with_intangible = initial_state.clone()
    with_intangible.player_intangible = 1

    base_score = simulator.calculate_outcome_score(
        initial_state,
        no_intangible,
        current_act=1,
        weights=weights,
        context=None,
        sequence=[],
    )
    intangible_score = simulator.calculate_outcome_score(
        initial_state,
        with_intangible,
        current_act=1,
        weights=weights,
        context=None,
        sequence=[],
    )

    assert base_score == float("-inf")
    assert intangible_score > float("-inf")


def test_beam_search_simulates_ancient_potion_as_player_artifact():
    potion = Potion(
        potion_id="AncientPotion",
        name="Ancient Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
        compute_threat=lambda monster: 18,
    )
    planner = HeuristicCombatPlanner()
    observed_artifact = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            observed_artifact.append(getattr(final_state, "player_artifact", 0))
        return 0

    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert observed_artifact == [1]


def test_beam_search_preserves_candidate_shape_across_depths():
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    cards = [
        SimpleNamespace(
            card_id=f"Strike{i}",
            name=f"Strike {i}",
            cost=1,
            cost_for_turn=1,
            has_target=False,
        )
        for i in range(3)
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=3,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=cards,
    )
    planner = HeuristicCombatPlanner()
    planner.fast_score_action = lambda _card, _state, _context: 1
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0
    planner.simulator.simulate_card_play = (
        lambda state, _card, _target, context=None: state.clone()
    )
    planner.simulator.calculate_outcome_score = (
        lambda _initial_state, _final_state, _act, _weights, _context, _sequence: 0
    )

    sequence = planner.plan_turn(context)

    assert len(sequence) >= 1


def test_beam_search_can_spend_energy_gained_from_potion():
    potion = Potion(
        potion_id="EnergyPotion",
        name="Energy Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    expensive_attack = SimpleNamespace(
        card_id="ExpensiveAttack",
        name="Expensive Attack",
        cost=4,
        cost_for_turn=4,
        has_target=False,
    )
    filler_cards = [
        SimpleNamespace(
            card_id=f"Filler{i}",
            name=f"Filler {i}",
            cost=99,
            cost_for_turn=99,
            has_target=False,
        )
        for i in range(2)
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=3,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[expensive_attack, *filler_cards],
    )
    planner = HeuristicCombatPlanner()
    planner.fast_score_action = lambda card, _state, _context: (
        10 if card is expensive_attack else 0
    )
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0
    planner.simulator.calculate_outcome_score = (
        lambda _initial_state, _final_state, _act, _weights, _context, sequence: len(sequence) * 10
    )

    sequence = planner.plan_turn(context)

    assert isinstance(sequence[0], PotionAction)
    assert sequence[1].card is expensive_attack


def test_beam_search_treats_corruption_skills_as_playable_without_energy():
    monster = SimpleNamespace(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=100,
        current_hp=100,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
        strength=0,
        powers=[],
    )
    skills = [
        Card(
            card_id=f"Defend{i}",
            name=f"Defend {i}",
            card_type=CardType.SKILL,
            rarity=CardRarity.BASIC,
            cost=1,
            cost_for_turn=1,
            has_target=False,
            uuid=f"defend-{i}",
        )
        for i in range(3)
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(
                block=0,
                powers=[SimpleNamespace(power_name="Corruption", amount=1)],
            ),
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=0,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=skills,
    )
    planner = HeuristicCombatPlanner()
    planner._simple_plan = lambda _context: []
    planner.fast_score_action = lambda _card, _state, _context: 1
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0
    planner.simulator.calculate_outcome_score = (
        lambda _initial_state, _final_state, _act, _weights, _context, sequence: len(sequence) * 10
    )

    sequence = planner.plan_turn(context)

    assert len(sequence) >= 2
    assert all(isinstance(action, PlayCardAction) for action in sequence[:2])


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


def test_awakened_one_data_models_opening_phase_two_and_live_move():
    database = EnhancedMonsterDatabase()

    awakened = database.get_monster_data("AwakenedOne")
    moves = {move["name"]: move for move in database.get_moves("Awakened One")}
    opening = database.predict_next_moves("Awakened One", current_turn=1, monster_hp_percent=1.0)
    phase_one = database.predict_next_moves("Awakened One", current_turn=3, monster_hp_percent=0.8)
    live_move = FastCombatSimulator(None)._current_monster_move(
        {
            "monster_id": "AwakenedOne",
            "name": "Awakened One",
            "move_id": 1,
            "intent": "Intent.ATTACK",
            "move_adjusted_damage": 20,
            "move_base_damage": 20,
            "move_hits": 1,
        }
    )

    assert awakened is not None
    assert awakened["hp_ranges"]["normal"] == {"min": 300, "max": 300}
    assert set(moves) == {"Slash", "Soul Strike", "Rebirth", "Dark Echo", "Sludge", "Tackle"}
    assert opening[0]["move"]["name"] == "Slash"
    assert {prediction["move"]["name"] for prediction in phase_one[:2]} == {"Slash", "Soul Strike"}
    assert moves["Soul Strike"]["damage"] == 6
    assert moves["Soul Strike"]["hits"] == 4
    assert moves["Dark Echo"]["damage"] == 40
    assert moves["Tackle"]["damage"] == 10
    assert moves["Tackle"]["hits"] == 3
    assert moves["Sludge"]["void_cards_added"] == 1
    assert awakened["special_mechanics"]["type"] == "phase_change"
    assert awakened["special_mechanics"]["revive_hp"] == 300
    assert awakened["special_mechanics"]["curiosity_strength_gain"]["normal"] == 1
    assert live_move["name"] == "Slash"


def test_enhanced_monster_database_covers_remaining_act3_threats():
    database = EnhancedMonsterDatabase()

    expected_moves = {
        "Giant Head": {"Count", "Glare", "It Is Time"},
        "Nemesis": {"Debuff", "Attack", "Scythe"},
        "Darkling": {"Nip", "Chomp", "Harden", "Reincarnate", "Regrow"},
        "The Maw": {"Roar", "Drool", "Slam", "Nom"},
    }

    for monster_name, moves in expected_moves.items():
        monster_data = database.get_monster_data(monster_name)
        assert monster_data is not None, monster_name
        assert {move["name"] for move in database.get_moves(monster_name)} == moves

    giant_head_time = database.predict_next_moves("Giant Head", current_turn=5, monster_hp_percent=1.0)
    nemesis_later = database.predict_next_moves("Nemesis", current_turn=2, monster_hp_percent=1.0)
    darkling_opening = database.predict_next_moves("Darkling", current_turn=1, monster_hp_percent=1.0)
    maw_opening = database.predict_next_moves("The Maw", current_turn=1, monster_hp_percent=1.0)
    maw_later = database.predict_next_moves("The Maw", current_turn=2, monster_hp_percent=1.0)

    assert giant_head_time[0]["move"]["name"] == "It Is Time"
    assert giant_head_time[0]["move"]["damage_formula"]["base"] == 30
    assert {prediction["move"]["name"] for prediction in nemesis_later[:3]} == {"Debuff", "Attack", "Scythe"}
    assert {prediction["move"]["name"] for prediction in darkling_opening[:2]} == {"Nip", "Harden"}
    assert maw_opening[0]["move"]["name"] == "Roar"
    assert {prediction["move"]["name"] for prediction in maw_later[:2]} == {"Nom", "Slam"}
    assert database.get_special_mechanics("Darkling")["type"] == "life_link"


def test_formula_monster_damage_and_hits_use_target_turn():
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0), ascension_level=0)
    transient = SimpleNamespace(name="Transient", current_hp=999, max_hp=999, strength=0)
    transient_move = EnhancedMonsterDatabase().get_moves("Transient")[0]
    maw_nom = {
        "name": "Nom",
        "intent": "ATTACK",
        "damage": 5,
        "hits_formula": {"type": "ceil_turn_divisor", "divisor": 2},
    }

    damage_curve = classifier._calculate_damage_curve(
        context,
        [transient],
        current_turn=1,
        look_ahead=2,
    )

    assert damage_curve == [40, 50]
    assert classifier._resolve_move_hits(maw_nom, context, target_turn=5) == 3
    assert FastCombatSimulator(None)._move_damage_value(transient_move, SimpleNamespace(player_hp=80), target_turn=3) == 50
    assert FastCombatSimulator(None)._move_hit_count(maw_nom, target_turn=5) == 3
