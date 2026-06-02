from types import SimpleNamespace
import json
from pathlib import Path
import re

import spirecomm.ai.heuristics.ironclad_combat as ironclad_combat
import spirecomm.ai.heuristics.simulation as simulation
import spirecomm.data.loader as data_loader
from spirecomm.data.loader import GameDataLoader
from spirecomm.ai.heuristics.card_costs import whirlwind_damage
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.simulation import (
    FastCombatSimulator,
    HeuristicCombatPlanner,
    SimulationState,
)
from spirecomm.ai.heuristics.timing.models import MonsterTimingHints, TurnTiming
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


def test_timing_classifier_prediction_passes_live_enemy_context(monkeypatch):
    class FakeLoader:
        def __init__(self):
            self.calls = []

        def get_monster_timing_hints(self, _monster_name):
            return {}

        def predict_monster_moves(
            self,
            monster_name,
            current_turn,
            hp_percent,
            ascension_level=0,
            other_enemy_count=None,
            other_enemy_names=None,
            same_monster_index=None,
        ):
            self.calls.append(
                {
                    "monster_name": monster_name,
                    "current_turn": current_turn,
                    "hp_percent": hp_percent,
                    "ascension_level": ascension_level,
                    "other_enemy_count": other_enemy_count,
                    "other_enemy_names": other_enemy_names,
                    "same_monster_index": same_monster_index,
                }
            )
            return [{"move": {"intent": "BUFF"}, "confidence": 1.0}]

    loader = FakeLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", loader)
    leader = SimpleNamespace(
        name="Gremlin Leader",
        current_hp=145,
        max_hp=145,
        intent="BUFF",
        move_adjusted_damage=0,
    )
    minion = SimpleNamespace(
        name="Mad Gremlin",
        current_hp=20,
        max_hp=20,
        intent="ATTACK",
        move_adjusted_damage=4,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[leader, minion], ascension_level=18),
        ascension_level=18,
    )

    TurnTimingClassifier()._analyze_monster_timing(context, [leader, minion], 1)

    assert loader.calls[0] == {
        "monster_name": "Gremlin Leader",
        "current_turn": 1,
        "hp_percent": 1.0,
        "ascension_level": 18,
        "other_enemy_count": 1,
        "other_enemy_names": ["Mad Gremlin"],
        "same_monster_index": 0,
    }


def test_timing_classifier_coerces_numeric_string_monster_hp_for_predictions(monkeypatch):
    class FakeLoader:
        def __init__(self):
            self.calls = []

        def get_monster_timing_hints(self, _monster_name):
            return {}

        def predict_monster_moves(
            self,
            monster_name,
            current_turn,
            hp_percent,
            ascension_level=0,
            other_enemy_count=None,
            other_enemy_names=None,
            same_monster_index=None,
        ):
            self.calls.append(
                {
                    "monster_name": monster_name,
                    "current_turn": current_turn,
                    "hp_percent": hp_percent,
                }
            )
            return [{"move": {"intent": "ATTACK"}, "confidence": 1.0}]

    loader = FakeLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", loader)
    monster = SimpleNamespace(
        name="Jaw Worm",
        current_hp="45",
        max_hp="90",
        intent="ATTACK",
        move_adjusted_damage="5",
        move_hits="2",
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster], ascension_level=0),
        ascension_level=0,
    )

    analysis = TurnTimingClassifier()._analyze_monster_timing(context, [monster], 1)

    assert loader.calls[0]["hp_percent"] == 0.5
    assert analysis["current_damage"] == 10


def test_damage_curve_fallback_prediction_keeps_live_enemy_context(monkeypatch):
    class FakeLoader:
        def __init__(self):
            self.calls = []

        def predict_monster_moves(
            self,
            monster_name,
            current_turn,
            hp_percent,
            ascension_level=0,
            other_enemy_count=None,
            other_enemy_names=None,
            same_monster_index=None,
        ):
            self.calls.append(
                {
                    "monster_name": monster_name,
                    "current_turn": current_turn,
                    "hp_percent": hp_percent,
                    "ascension_level": ascension_level,
                    "other_enemy_count": other_enemy_count,
                    "other_enemy_names": other_enemy_names,
                    "same_monster_index": same_monster_index,
                }
            )
            return [
                {
                    "turn": current_turn,
                    "move": {"name": "Wait", "intent": "BUFF"},
                    "confidence": 1.0,
                }
            ]

    loader = FakeLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", loader)
    leader = SimpleNamespace(
        name="Gremlin Leader",
        current_hp=145,
        max_hp=145,
        intent="BUFF",
        move_adjusted_damage=0,
        strength=0,
    )
    minion_a = SimpleNamespace(
        name="Mad Gremlin",
        current_hp=20,
        max_hp=20,
        intent="ATTACK",
        move_adjusted_damage=4,
        strength=0,
    )
    minion_b = SimpleNamespace(
        name="Fat Gremlin",
        current_hp=20,
        max_hp=20,
        intent="ATTACK",
        move_adjusted_damage=4,
        strength=0,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[leader, minion_a, minion_b], ascension_level=18),
        ascension_level=18,
    )

    TurnTimingClassifier()._calculate_damage_curve(
        context,
        [leader, minion_a, minion_b],
        current_turn=1,
        look_ahead=1,
    )

    assert next(
        call
        for call in loader.calls
        if call["monster_name"] == "Gremlin Leader"
        and call["current_turn"] == 2
    ) == {
        "monster_name": "Gremlin Leader",
        "current_turn": 2,
        "hp_percent": 1.0,
        "ascension_level": 18,
        "other_enemy_count": 2,
        "other_enemy_names": ["Mad Gremlin", "Fat Gremlin"],
        "same_monster_index": 0,
    }


def test_spike_imminent_fallback_prediction_keeps_live_enemy_context(monkeypatch):
    class FakeLoader:
        def predict_monster_moves(
            self,
            _monster_name,
            current_turn,
            _hp_percent,
            ascension_level=0,
            other_enemy_count=None,
            other_enemy_names=None,
            same_monster_index=None,
        ):
            if current_turn == 2 and other_enemy_count == 2:
                return [
                    {
                        "turn": 2,
                        "move": {
                            "name": "Contextual Slam",
                            "intent": "ATTACK",
                            "damage": 20,
                            "hits": 1,
                        },
                        "confidence": 1.0,
                    }
                ]
            return [
                {
                    "turn": current_turn,
                    "move": {"name": "Wait", "intent": "BUFF"},
                    "confidence": 1.0,
                }
            ]

    monkeypatch.setattr(data_loader, "game_data_loader", FakeLoader())
    leader = SimpleNamespace(
        name="Gremlin Leader",
        current_hp=145,
        max_hp=145,
        intent="BUFF",
        move_adjusted_damage=0,
        strength=0,
    )
    minion_a = SimpleNamespace(
        name="Mad Gremlin",
        current_hp=20,
        max_hp=20,
        intent="BUFF",
        move_adjusted_damage=0,
        strength=0,
    )
    minion_b = SimpleNamespace(
        name="Fat Gremlin",
        current_hp=20,
        max_hp=20,
        intent="BUFF",
        move_adjusted_damage=0,
        strength=0,
    )
    context = SimpleNamespace(
        turn=1,
        monsters_alive=[leader, minion_a, minion_b],
        game=SimpleNamespace(monsters=[leader, minion_a, minion_b], ascension_level=0),
        ascension_level=0,
    )

    assert TurnTimingClassifier()._spike_imminent(context) is True


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


def _patch_malformed_aoe_upgrade_loader(monkeypatch, card_name, description, wiki_text):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        card_name.lower(): {
            "name": card_name,
            "description": description,
        }
    }
    loader._wiki_data = {
        card_name.lower(): {
            "name": card_name,
            "text": wiki_text,
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)


def _two_monster_skill_state():
    return SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "half_dead": False,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "artifact": 0,
            },
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "half_dead": False,
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


def test_malformed_blind_upgrade_suffix_keeps_base_card_single_target(monkeypatch):
    _patch_malformed_aoe_upgrade_loader(
        monkeypatch,
        "Blind",
        "Apply 2 Weak.",
        "Apply 2 #Weak| to ALL enemies].",
    )
    blind = Card(
        card_id="Blind",
        name="Blind",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=0,
    )
    state = _two_monster_skill_state()

    FastCombatSimulator(None)._apply_skill(state, blind, target_index=1)

    assert state.monsters[0]["weak"] == 0
    assert state.monsters[1]["weak"] == 2


def test_malformed_trip_upgrade_suffix_applies_aoe_only_when_upgraded(monkeypatch):
    _patch_malformed_aoe_upgrade_loader(
        monkeypatch,
        "Trip",
        "Apply 2 Vulnerable.",
        "Apply 2 #Vulnerable| to ALL enemies].",
    )
    trip_plus = Card(
        card_id="Trip",
        name="Trip+",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=0,
        upgrades=1,
    )
    state = _two_monster_skill_state()

    FastCombatSimulator(None)._apply_skill(state, trip_plus, target_index=1)

    assert state.monsters[0]["vulnerable"] == 2
    assert state.monsters[1]["vulnerable"] == 2


class _BaseOnlyBlockLoader:
    def __init__(self, descriptions):
        self.descriptions = descriptions
        self._wiki_data = {}

    def get_card_data(self, card_name):
        description = self.descriptions.get(card_name)
        if description is None:
            return None
        return {"name": card_name, "description": description}

    def _parse_card_block(self, card_data):
        match = re.search(r"gain (\d+) block", card_data.get("description", "").lower())
        if not match:
            return None
        return int(match.group(1))


def _simple_skill_state():
    return SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "half_dead": False,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "artifact": 0,
            }
        ],
        player_block=0,
        player_frail=0,
        player_dexterity=0,
        player_energy=0,
        player_strength=0,
        player_artifact=0,
        player_temp_strength=0,
        energy_gained=0,
        exhaust_events=0,
        cards_drawn=0,
        draw_blocked=False,
        status_cards_added=0,
        dazed_cards_added=0,
        rage_block_per_attack=0,
        damage_instances=0,
        total_damage_dealt=0,
        monsters_killed=0,
    )


def _upgraded_block_skill(name, cost=1):
    return Card(
        card_id=name,
        name=name,
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=False,
        cost=cost,
        upgrades=1,
    )


def test_upgraded_block_skills_use_fallback_bonus_without_wiki(monkeypatch):
    monkeypatch.setattr(
        simulation,
        "game_data_loader",
        _BaseOnlyBlockLoader(
            {
                "Finesse": "Gain 2 Block. Draw 1 card.",
                "Ghostly Armor": "Gain 10 Block. Exhaust.",
                "Good Instincts": "Gain 6 Block.",
                "Panic Button": "Gain 30 Block. You cannot gain Block from cards for 2 turns.",
                "Power Through": "Add 2 Wounds to your hand. Gain 15 Block.",
                "Safety": "Gain 12 Block.",
                "Sentinel": "Gain 5 Block.",
                "Shrug It Off": "Gain 8 Block. Draw 1 card.",
                "True Grit": "Gain 7 Block. Exhaust a random card in your hand.",
            }
        ),
    )
    cases = [
        ("Finesse", 0, 4),
        ("Ghostly Armor", 1, 13),
        ("Good Instincts", 0, 9),
        ("Panic Button", 0, 40),
        ("Power Through", 1, 20),
        ("Safety", 1, 16),
        ("Sentinel", 1, 8),
        ("Shrug It Off", 1, 11),
        ("True Grit", 1, 9),
    ]

    simulator = FastCombatSimulator(None)
    context = SimpleNamespace(energy_available=3)
    for card_name, cost, expected_block in cases:
        state = _simple_skill_state()

        simulator._apply_skill(
            state,
            _upgraded_block_skill(card_name, cost=cost),
            context=context,
        )

        assert state.player_block == expected_block, card_name


def test_skill_simulation_applies_temporary_targeted_strength_loss(monkeypatch):
    card = Card(
        card_id="Dark Shackles",
        name="Dark Shackles",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=0,
    )
    card_data = {
        "name": "Dark Shackles",
        "description": "Enemy loses 9 Strength this turn.\nExhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Dark Shackles" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "intent": Intent.ATTACK,
                "move_adjusted_damage": 12,
                "strength": 0,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
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

    assert state.monsters[0]["move_adjusted_damage"] == 3
    assert state.monsters[0]["strength"] == 0


def test_temporary_strength_loss_reduces_base_damage_intent(monkeypatch):
    card = Card(
        card_id="Dark Shackles",
        name="Dark Shackles",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=0,
    )
    card_data = {
        "name": "Dark Shackles",
        "description": "Enemy loses 9 Strength this turn.\nExhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Dark Shackles" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "intent": Intent.ATTACK,
                "move_base_damage": 12,
                "move_adjusted_damage": 12,
                "strength": 0,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
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

    assert state.monsters[0]["move_adjusted_damage"] == 3
    assert state.monsters[0]["strength"] == 0


def test_enemy_lookahead_expires_temporary_strength_loss_after_current_turn(monkeypatch):
    card = Card(
        card_id="Dark Shackles",
        name="Dark Shackles",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=0,
    )
    card_data = {
        "name": "Dark Shackles",
        "description": "Enemy loses 9 Strength this turn.\nExhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Dark Shackles" else None,
    )
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
        move_base_damage=12,
        move_adjusted_damage=12,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            relics=[],
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
        playable_cards=[card],
        incoming_damage=12,
        player_hp=80,
        player_hp_pct=1.0,
    )
    simulator = FastCombatSimulator(None)
    state = simulation.SimulationState(context)
    result = simulator.simulate_card_play(state, card, context=context, target_index=0)
    move = {"name": "Slash", "intent": "ATTACK", "damage": 12, "hits": 1}
    simulator._current_monster_move = lambda _monster: move
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: move

    future_damage = simulator.simulate_enemy_lookahead(result, context, look_ahead=2)

    assert result.monsters[0]["move_adjusted_damage"] == 3
    assert future_damage == 12


def test_skill_simulation_applies_temporary_aoe_strength_loss(monkeypatch):
    card = Card(
        card_id="Piercing Wail",
        name="Piercing Wail",
        card_type=CardType.SKILL,
        rarity=CardRarity.COMMON,
        has_target=False,
        cost=1,
    )
    card_data = {
        "name": "Piercing Wail",
        "description": "ALL enemies lose 6 Strength this turn.\nExhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Piercing Wail" else None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "intent": Intent.ATTACK,
                "move_adjusted_damage": 8,
                "strength": 0,
                "vulnerable": 0,
                "weak": 0,
                "frail": 0,
                "artifact": 0,
            },
            {
                "hp": 30,
                "block": 0,
                "is_gone": False,
                "intent": Intent.ATTACK,
                "move_adjusted_damage": 12,
                "strength": 0,
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

    FastCombatSimulator(None)._apply_skill(state, card)

    assert [monster["move_adjusted_damage"] for monster in state.monsters] == [2, 6]
    assert [monster["strength"] for monster in state.monsters] == [0, 0]


def test_simulate_card_play_spends_all_energy_on_reinforced_body_block(monkeypatch):
    card_data = {
        "name": "Reinforced Body",
        "description": "Gain 7 Block X times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Reinforced Body" else None,
    )
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
        move_hits=1,
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
        energy_available=3,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    for card_name, upgrades, expected_block in (
        ("Reinforced Body", 0, 21),
        ("Reinforced Body+", 1, 27),
    ):
        state = simulation.SimulationState(context)
        card = Card(
            card_id="Reinforced Body",
            name=card_name,
            card_type=CardType.SKILL,
            rarity=CardRarity.UNCOMMON,
            upgrades=upgrades,
            has_target=False,
            cost=-1,
            cost_for_turn=-1,
        )

        result = FastCombatSimulator(None).simulate_card_play(
            state,
            card,
            context=context,
        )

        assert result.player_block == expected_block
        assert result.player_energy == 0


def test_simulate_card_play_applies_chemical_x_to_reinforced_body(monkeypatch):
    card_data = {
        "name": "Reinforced Body",
        "description": "Gain 7 Block X times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Reinforced Body" else None,
    )
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
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            relics=[SimpleNamespace(relic_id="Chemical X", name="Chemical X")],
        ),
        act=1,
        turn=1,
        energy_available=3,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    state = simulation.SimulationState(context)
    card = Card(
        card_id="Reinforced Body",
        name="Reinforced Body",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        upgrades=0,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    result = FastCombatSimulator(None).simulate_card_play(
        state,
        card,
        context=context,
    )

    assert result.player_block == 35
    assert result.player_energy == 0
    assert result.energy_spent == 3


def test_x_block_estimate_applies_chemical_x_without_playing_card():
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
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
            relics=[SimpleNamespace(relic_id="Chemical X", name="Chemical X")],
        ),
        act=1,
        turn=1,
        energy_available=3,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    state = simulation.SimulationState(context)
    card = Card(
        card_id="Reinforced Body",
        name="Reinforced Body",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        upgrades=0,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    assert FastCombatSimulator(None)._calculate_x_block(card, state, context) == 35


def test_x_damage_estimate_applies_chemical_x_without_playing_card():
    context = SimpleNamespace(
        game=SimpleNamespace(
            relics=[SimpleNamespace(relic_id="Chemical X", name="Chemical X")],
        )
    )
    state = SimpleNamespace(
        player_block=0,
        player_energy=3,
        player_strength=0,
    )
    card = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        upgrades=0,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    assert FastCombatSimulator(None)._calculate_x_damage(card, state, context) == 25


def test_x_damage_estimate_applies_strength_to_each_whirlwind_hit():
    context = SimpleNamespace(game=SimpleNamespace(relics=[]))
    state = SimpleNamespace(
        player_block=0,
        player_energy=3,
        player_strength=2,
    )
    card = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        upgrades=0,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    assert FastCombatSimulator(None)._calculate_x_damage(card, state, context) == 21


def test_whirlwind_damage_treats_none_upgrades_as_base_card():
    card = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        upgrades=None,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    assert whirlwind_damage(card, energy_spent=3, strength=2) == 21


def test_x_card_helpers_treat_none_upgrades_as_base_card():
    context = SimpleNamespace(
        game=SimpleNamespace(
            relics=[],
            discard_pile=[
                SimpleNamespace(card_id="Strike_R"),
                SimpleNamespace(card_id="Defend_R"),
                SimpleNamespace(card_id="Bash"),
            ],
        )
    )
    state = SimpleNamespace(
        player_block=0,
        player_energy=3,
        player_strength=0,
    )
    simulator = FastCombatSimulator(None)

    whirlwind = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        upgrades=None,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )
    reinforced_body = Card(
        card_id="Reinforced Body",
        name="Reinforced Body",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        upgrades=None,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )
    stack = Card(
        card_id="Stack",
        name="Stack",
        card_type=CardType.SKILL,
        rarity=CardRarity.COMMON,
        upgrades=None,
        has_target=False,
        cost=1,
    )

    assert simulator._calculate_x_damage(whirlwind, state, context) == 15
    assert simulator._calculate_x_block(reinforced_body, state, context) == 21
    assert simulator._calculate_x_block(stack, state, context) == 3


def test_x_hit_count_estimate_applies_chemical_x_without_playing_card():
    context = SimpleNamespace(
        game=SimpleNamespace(
            relics=[SimpleNamespace(relic_id="Chemical X", name="Chemical X")],
        )
    )
    state = SimpleNamespace(player_energy=3)
    card = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        upgrades=0,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    assert FastCombatSimulator(None)._get_attack_hit_count(card, state, context) == 5


def test_simulate_card_play_spends_x_energy_on_malaise_debuffs(monkeypatch):
    card_data = {
        "name": "Malaise",
        "description": "Enemy loses [X|X+1] Strength. Apply [X|X+1] Weak.\nExhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Malaise" else None,
    )
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
        move_adjusted_damage=12,
        move_hits=1,
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
        energy_available=3,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    for card_name, upgrades, expected_debuff in (
        ("Malaise", 0, 3),
        ("Malaise+", 1, 4),
    ):
        state = simulation.SimulationState(context)
        card = Card(
            card_id="Malaise",
            name=card_name,
            card_type=CardType.SKILL,
            rarity=CardRarity.RARE,
            upgrades=upgrades,
            has_target=True,
            cost=-1,
            cost_for_turn=-1,
        )

        result = FastCombatSimulator(None).simulate_card_play(
            state,
            card,
            target=monster,
            context=context,
        )

        assert result.monsters[0]["strength"] == -expected_debuff
        assert result.monsters[0]["weak"] == expected_debuff
        assert result.monsters[0]["move_adjusted_damage"] == int((12 - expected_debuff) * 0.75)
        assert result.player_energy == 0


def test_simulate_card_play_spends_x_energy_on_skewer_hits(monkeypatch):
    card_data = {
        "name": "Skewer",
        "description": "Deal [7|10] damage X times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Skewer" else None,
    )
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        max_hp=100,
        current_hp=100,
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
            current_hp=80,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            monsters=[monster],
        ),
        act=1,
        turn=1,
        energy_available=3,
        strength=2,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=[],
    )
    for card_name, upgrades, expected_damage in (
        ("Skewer", 0, 27),
        ("Skewer+", 1, 36),
    ):
        state = simulation.SimulationState(context)
        card = Card(
            card_id="Skewer",
            name=card_name,
            card_type=CardType.ATTACK,
            rarity=CardRarity.UNCOMMON,
            upgrades=upgrades,
            has_target=True,
            cost=-1,
            cost_for_turn=-1,
        )

        result = FastCombatSimulator(None).simulate_card_play(
            state,
            card,
            target=monster,
            context=context,
        )

        assert result.total_damage_dealt == expected_damage
        assert result.damage_instances == 3
        assert result.monsters[0]["hp"] == 100 - expected_damage
        assert result.player_energy == 0


def test_simulate_card_play_spends_x_energy_on_whirlwind_aoe_hits(monkeypatch):
    card_data = {
        "name": "Whirlwind",
        "description": "Deal [5|8] damage to ALL enemies X times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Whirlwind" else None,
    )
    monsters = [
        SimpleNamespace(
            name=f"Cultist {index}",
            monster_id="Cultist",
            max_hp=50,
            current_hp=50,
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
        for index in range(2)
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            player=SimpleNamespace(
                block=0,
                powers=[SimpleNamespace(power_name="Weak", amount=1)],
            ),
            monsters=monsters,
        ),
        act=1,
        turn=1,
        energy_available=3,
        strength=0,
        monsters_alive=monsters,
        vulnerable_stacks={0: 0, 1: 0},
        weak_stacks={0: 0, 1: 0},
        frail_stacks={0: 0, 1: 0},
        thorns_stacks={0: 0, 1: 0},
        playable_cards=[],
    )
    state = simulation.SimulationState(context)
    card = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        upgrades=0,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
    )

    result = FastCombatSimulator(None).simulate_card_play(
        state,
        card,
        context=context,
    )

    assert result.total_damage_dealt == 18
    assert result.damage_instances == 6
    assert [monster["hp"] for monster in result.monsters] == [41, 41]
    assert result.player_energy == 0


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


def test_attack_simulation_bane_adds_extra_hit_only_against_poisoned_target(monkeypatch):
    card = Card(
        card_id="Bane",
        name="Bane",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
    )
    card_data = {
        "name": "Bane",
        "description": "Deal 7 damage. If the enemy has Poison, deal 7 damage again.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Bane" else None,
    )

    unpoisoned_state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
                "poison": 0,
            }
        ],
        player_strength=0,
        player_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
    )
    poisoned_state = SimpleNamespace(
        monsters=[
            {
                "hp": 40,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
                "poison": 1,
            }
        ],
        player_strength=0,
        player_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
    )

    simulator = FastCombatSimulator(None)
    simulator._apply_attack(
        unpoisoned_state,
        card,
        target=None,
        target_index=0,
        context=None,
    )
    simulator._apply_attack(
        poisoned_state,
        card,
        target=None,
        target_index=0,
        context=None,
    )

    assert unpoisoned_state.total_damage_dealt == 7
    assert unpoisoned_state.damage_instances == 1
    assert poisoned_state.total_damage_dealt == 14
    assert poisoned_state.damage_instances == 2


def test_attack_simulation_upgraded_bane_uses_upgraded_per_hit_damage(monkeypatch):
    card = Card(
        card_id="Bane",
        name="Bane+",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Bane",
        "description": "Deal 7 damage. If the enemy has Poison, deal 7 damage again.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Bane" else None,
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
                "poison": 1,
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

    assert state.total_damage_dealt == 20
    assert state.damage_instances == 2


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


def test_skill_simulation_applies_random_enemy_poison_to_only_live_monster(monkeypatch):
    card = Card(
        card_id="Bouncing Flask",
        name="Bouncing Flask",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=False,
        cost=2,
    )
    card_data = {
        "name": "Bouncing Flask",
        "description": "Apply 3 Poison to a random enemy 3 times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Bouncing Flask" else None,
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

    FastCombatSimulator(None)._apply_skill(state, card, target_index=None)

    assert state.monsters[0]["poison"] == 9


def test_skill_simulation_catalyst_doubles_existing_poison(monkeypatch):
    card = Card(
        card_id="Catalyst",
        name="Catalyst",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=1,
    )
    card_data = {
        "name": "Catalyst",
        "description": "Double an enemy's Poison. Exhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Catalyst" else None,
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
                "poison": 5,
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

    assert state.monsters[0]["poison"] == 10


def test_skill_simulation_upgraded_catalyst_triples_existing_poison(monkeypatch):
    card = Card(
        card_id="Catalyst",
        name="Catalyst+",
        card_type=CardType.SKILL,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    card_data = {
        "name": "Catalyst",
        "description": "Double an enemy's Poison. Exhaust.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Catalyst" else None,
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
                "poison": 5,
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

    assert state.monsters[0]["poison"] == 15


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


def test_target_estimation_accepts_numeric_string_monster_hp_and_block_for_lethal():
    card = SimpleNamespace(
        card_id="Strike_R",
        name="Strike",
        type="ATTACK",
        damage=8,
    )
    killable = SimpleNamespace(current_hp="6", block="2")
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


def test_fast_simulator_treats_none_upgrades_as_base_sword_boomerang_hits(monkeypatch):
    card = Card(
        card_id="Sword Boomerang",
        name="Sword Boomerang",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=False,
        cost=1,
        upgrades=None,
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

    assert state.damage_instances == 3
    assert state.total_damage_dealt == 9


def test_fast_simulator_treats_none_upgrades_as_base_heavy_blade_scaling(monkeypatch):
    card = Card(
        card_id="Heavy Blade",
        name="Heavy Blade",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=2,
        upgrades=None,
    )
    card_data = {
        "name": "Heavy Blade",
        "description": "Deal 14 damage. Strength affects Heavy Blade 3 times.",
    }
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: card_data if card_name == "Heavy Blade" else None,
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
        player_strength=2,
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

    assert state.total_damage_dealt == 20


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
        upgrades=None,
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


def test_aoe_parser_respects_malformed_upgrade_only_all_enemies_suffix():
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "trip": {
            "name": "Trip",
            "text": "Apply 2 #Vulnerable| to ALL enemies].",
        },
    }

    assert loader._is_card_aoe({"name": "Trip", "description": "Apply 2 Vulnerable."}) is False
    assert loader._is_card_aoe({"name": "Trip+1", "description": "Apply 2 Vulnerable."}) is True


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


def test_generic_prune_targets_falls_back_when_damage_parse_returns_none(monkeypatch):
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
    monster = SimpleNamespace(current_hp=20, block=0)
    context = SimpleNamespace(
        monsters_alive=[monster],
        player=SimpleNamespace(strength=0),
    )

    pruned = HeuristicCombatPlanner()._prune_targets(
        _unknown_attack(),
        [(monster, 10)],
        context,
    )

    assert pruned == [(monster, 10)]


def test_generic_find_best_target_falls_back_when_damage_parse_returns_none(monkeypatch):
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
    high_threat = SimpleNamespace(current_hp=20, block=0, threat=20)
    killable = SimpleNamespace(current_hp=6, block=0, threat=1)
    context = SimpleNamespace(
        monsters_alive=[high_threat, killable],
        player=SimpleNamespace(strength=0),
        compute_threat=lambda monster: monster.threat,
    )

    target = HeuristicCombatPlanner()._find_best_target(
        _unknown_attack(),
        context,
    )

    assert target is killable


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


def test_ironclad_fallback_damage_accepts_string_damage_attribute():
    card = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        has_target=True,
        cost=1,
        upgrades=0,
    )
    card.damage = "6"
    context = SimpleNamespace(strength=2)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(card, context)

    assert damage == 8


def test_ironclad_fallback_damage_applies_all_searing_blow_upgrades(monkeypatch):
    card = Card(
        card_id="Searing Blow",
        name="Searing Blow+2",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=2,
        upgrades=2,
    )
    card.damage = None

    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 12 damage. Can be Upgraded any number of times."}
        if card_name == "Searing Blow"
        else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 12,
    )
    context = SimpleNamespace(strength=0)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(card, context)

    assert damage == 21


def test_ironclad_fallback_damage_counts_whirlwind_x_energy(monkeypatch):
    card = Card(
        card_id="Whirlwind",
        name="Whirlwind",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=False,
        cost=-1,
        cost_for_turn=-1,
        upgrades=0,
    )
    card.damage = None

    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 5 damage to ALL enemies."} if card_name == "Whirlwind" else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 5,
    )
    context = SimpleNamespace(
        strength=0,
        energy_available=3,
        game=SimpleNamespace(relics=[]),
    )

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(card, context)

    assert damage == 15


def test_ironclad_fallback_damage_applies_heavy_blade_strength_multiplier(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 14 damage. Strength affects Heavy Blade 3 times."}
        if card_name == "Heavy Blade"
        else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 14,
    )

    heavy_blade = Card(
        card_id="Heavy Blade",
        name="Heavy Blade",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=2,
        upgrades=0,
    )
    heavy_blade.damage = None
    context = SimpleNamespace(strength=3)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        heavy_blade,
        context,
    )

    assert damage == 23

    heavy_blade_plus = Card(
        card_id="Heavy Blade",
        name="Heavy Blade+",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=2,
        upgrades=1,
    )
    heavy_blade_plus.damage = None

    upgraded_damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        heavy_blade_plus,
        context,
    )

    assert upgraded_damage == 29


def test_ironclad_fallback_damage_treats_none_upgrades_as_base_heavy_blade(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 14 damage. Strength affects Heavy Blade 3 times."}
        if card_name == "Heavy Blade"
        else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 14,
    )

    heavy_blade = Card(
        card_id="Heavy Blade",
        name="Heavy Blade",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=2,
        upgrades=None,
    )
    heavy_blade.damage = None
    context = SimpleNamespace(strength=3)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        heavy_blade,
        context,
    )

    assert damage == 23


def test_ironclad_fallback_damage_counts_twin_strike_hits(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 5 damage twice."} if card_name == "Twin Strike" else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 5,
    )
    twin_strike = Card(
        card_id="Twin Strike",
        name="Twin Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        upgrades=0,
    )
    twin_strike.damage = None
    context = SimpleNamespace(strength=1)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        twin_strike,
        context,
    )

    assert damage == 12


def test_ironclad_fallback_damage_counts_pummel_hits(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 2 damage 4 times."} if card_name == "Pummel" else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 2,
    )
    pummel = Card(
        card_id="Pummel",
        name="Pummel",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=1,
        upgrades=0,
    )
    pummel.damage = None
    context = SimpleNamespace(strength=1)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        pummel,
        context,
    )

    assert damage == 12

    pummel_plus = Card(
        card_id="Pummel",
        name="Pummel+",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=1,
        upgrades=1,
    )
    pummel_plus.damage = None

    upgraded_damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        pummel_plus,
        context,
    )

    assert upgraded_damage == 15


def test_ironclad_fallback_damage_clamps_negative_strength_per_hit(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 2 damage 4 times."} if card_name == "Pummel" else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 2,
    )
    pummel = Card(
        card_id="Pummel",
        name="Pummel",
        card_type=CardType.ATTACK,
        rarity=CardRarity.UNCOMMON,
        has_target=True,
        cost=1,
        upgrades=0,
    )
    pummel.damage = None
    context = SimpleNamespace(strength=-5)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        pummel,
        context,
    )

    assert damage == 0


def test_ironclad_fallback_damage_counts_sword_boomerang_hits(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal 3 damage to a random enemy 3 times."}
        if card_name == "Sword Boomerang"
        else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 3,
    )
    sword_boomerang = Card(
        card_id="Sword Boomerang",
        name="Sword Boomerang",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=False,
        cost=1,
        upgrades=0,
    )
    sword_boomerang.damage = None
    context = SimpleNamespace(strength=1)

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        sword_boomerang,
        context,
    )

    assert damage == 12

    sword_boomerang_plus = Card(
        card_id="Sword Boomerang",
        name="Sword Boomerang+",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=False,
        cost=1,
        upgrades=1,
    )
    sword_boomerang_plus.damage = None

    upgraded_damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        sword_boomerang_plus,
        context,
    )

    assert upgraded_damage == 16


def test_ironclad_fallback_damage_counts_fiend_fire_exhausted_cards(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust."}
        if card_name == "Fiend Fire"
        else None,
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: 7,
    )
    fiend_fire = Card(
        card_id="Fiend Fire",
        name="Fiend Fire",
        card_type=CardType.ATTACK,
        rarity=CardRarity.RARE,
        has_target=True,
        cost=2,
        uuid="fiend-fire",
    )
    fiend_fire.damage = None
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        has_target=True,
        cost=1,
        uuid="strike",
    )
    dazed = Card(
        card_id="Dazed",
        name="Dazed",
        card_type=CardType.STATUS,
        rarity=CardRarity.SPECIAL,
        has_target=False,
        cost=-2,
        uuid="dazed",
    )
    context = SimpleNamespace(
        strength=1,
        game=SimpleNamespace(hand=[fiend_fire, strike, dazed]),
        playable_cards=[fiend_fire, strike],
    )

    damage = IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        fiend_fire,
        context,
    )

    assert damage == 16


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


def test_bronze_automaton_summoner_burst_counts_as_summoner():
    database = EnhancedMonsterDatabase()

    assert database.is_summoner("Bronze Automaton") is True


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


def test_safe_window_detection_clamps_negative_monster_strength_per_hit(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {"move": {"name": "Clipped Bite", "intent": "ATTACK", "damage": 3, "hits": 2}}
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=-5)

    windows = classifier._detect_safe_windows(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert len(windows) == 1
    assert windows[0].expected_damage == 0


def test_safe_window_detection_treats_negated_attack_intent_as_safe(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {"move": {"name": "Feint", "intent": "NOT_ATTACK", "damage": 20, "hits": 1}}
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
    assert windows[0].monsters_safe == ["Unknown"]


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


def test_attack_strength_prediction_accepts_numeric_string_current_strength(monkeypatch):
    class NoEnhancedDataLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

    monkeypatch.setattr(data_loader, "game_data_loader", NoEnhancedDataLoader())
    classifier = TurnTimingClassifier()
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength="2")
    predictions = [
        {
            "turn": 2,
            "move": {
                "name": "Grow",
                "intent": "BUFF",
                "strength_gain": 3,
            },
        },
    ]

    assert classifier._predict_attack_strength(
        monster,
        predictions,
        current_turn=2,
        target_turn=3,
        context=SimpleNamespace(game=SimpleNamespace(ascension_level=0)),
    ) == 5


def test_damage_curve_uses_live_monster_id_for_predicted_moves(monkeypatch):
    class CanonicalOnlyPredictionLoader:
        def __init__(self):
            self.names = []

        def predict_monster_moves(self, monster_name, _current_turn, _hp_percent):
            self.names.append(monster_name)
            if monster_name != "Red Slaver":
                return []
            return [
                {
                    "turn": 2,
                    "move": {
                        "name": "Stab",
                        "intent": "ATTACK",
                        "damage": 10,
                        "hits": 1,
                    },
                }
            ]

    prediction_loader = CanonicalOnlyPredictionLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", prediction_loader)
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    live_slaver = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        current_hp=30,
        max_hp=60,
        strength=0,
    )

    damage_curve = classifier._calculate_damage_curve(
        context,
        [live_slaver],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [10]
    assert prediction_loader.names == ["Red Slaver"]


def test_safe_window_detection_uses_live_monster_id_for_predicted_damage(monkeypatch):
    class CanonicalOnlyPredictionLoader:
        def __init__(self):
            self.names = []

        def predict_monster_moves(self, monster_name, _current_turn, _hp_percent):
            self.names.append(monster_name)
            if monster_name != "Red Slaver":
                return []
            return [
                {
                    "turn": 1,
                    "move": {
                        "name": "Stab",
                        "intent": "ATTACK",
                        "damage": 12,
                        "hits": 1,
                    },
                }
            ]

    prediction_loader = CanonicalOnlyPredictionLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", prediction_loader)
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    live_slaver = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        current_hp=30,
        max_hp=60,
        strength=0,
    )

    windows = classifier._detect_safe_windows(
        context,
        [live_slaver],
        current_turn=1,
        look_ahead=1,
    )

    assert windows == []
    assert prediction_loader.names == ["Red Slaver"]


def test_classify_turn_uses_live_monster_id_for_timing_hints(monkeypatch):
    class CanonicalOnlyTimingLoader:
        def __init__(self):
            self.hint_names = []

        def get_monster_timing_hints(self, monster_name):
            self.hint_names.append(monster_name)
            if monster_name == "Red Slaver":
                return {"always_classify_as": "SAFE"}
            return None

        def predict_monster_moves(self, _monster_name, _current_turn, _hp_percent):
            return []

    timing_loader = CanonicalOnlyTimingLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", timing_loader)
    classifier = TurnTimingClassifier()
    live_slaver = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        intent="ATTACK",
        move_adjusted_damage=0,
        move_hits=1,
        current_hp=30,
        max_hp=60,
        strength=0,
    )
    context = SimpleNamespace(turn=1, monsters_alive=[live_slaver])

    timing_context = classifier.classify_turn(context)

    assert timing_context.turn_timing == TurnTiming.SAFE
    assert timing_loader.hint_names == ["Red Slaver"]


def test_spike_imminent_uses_live_monster_id_for_predicted_moves(monkeypatch):
    class CanonicalOnlyPredictionLoader:
        def __init__(self):
            self.names = []

        def predict_monster_moves(self, monster_name, _current_turn, _hp_percent):
            self.names.append(monster_name)
            if monster_name != "Red Slaver":
                return []
            return [
                {
                    "turn": 2,
                    "move": {
                        "name": "Heavy Stab",
                        "intent": "ATTACK",
                        "damage": 20,
                        "hits": 1,
                    },
                }
            ]

    prediction_loader = CanonicalOnlyPredictionLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", prediction_loader)
    classifier = TurnTimingClassifier()
    live_slaver = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        current_hp=30,
        max_hp=60,
        strength=0,
    )
    context = SimpleNamespace(turn=1, monsters_alive=[live_slaver], game=SimpleNamespace(ascension_level=0))

    assert classifier._spike_imminent(context) is True
    assert prediction_loader.names == ["Red Slaver"]


def test_classify_turn_accepts_string_turn_for_imminent_spike(monkeypatch):
    class FutureSpikeLoader:
        def get_monster_timing_hints(self, _monster_name):
            return {}

        def predict_monster_moves(self, _monster_name, current_turn, _hp_percent):
            if current_turn != 1:
                return []
            return [
                {
                    "turn": 2,
                    "move": {
                        "name": "Heavy Stab",
                        "intent": "ATTACK",
                        "damage": 20,
                        "hits": 1,
                    },
                }
            ]

    monkeypatch.setattr(data_loader, "game_data_loader", FutureSpikeLoader())
    classifier = TurnTimingClassifier()
    monster = SimpleNamespace(
        name="Red Slaver",
        monster_id="SlaverRed",
        intent="ATTACK",
        move_adjusted_damage=5,
        move_hits=1,
        current_hp=45,
        max_hp=60,
        strength=0,
    )
    context = SimpleNamespace(
        turn="1",
        monsters_alive=[monster],
        game=SimpleNamespace(ascension_level=0),
    )

    timing_context = classifier.classify_turn(context)

    assert timing_context.turn_timing == TurnTiming.PREPARATION
    assert timing_context.future_damage_curve[0] == 20
    assert timing_context.current_turn_offset() == 1


def test_classify_turn_ignores_nonfinite_monster_hp_for_timing_hints(monkeypatch):
    class TimingHintLoader:
        def __init__(self):
            self.hint_names = []

        def get_monster_timing_hints(self, monster_name):
            self.hint_names.append(monster_name)
            if monster_name == "Red Slaver":
                return {"always_classify_as": "SAFE"}
            return None

        def predict_monster_moves(self, _monster_name, _current_turn, _hp_percent):
            return []

    timing_loader = TimingHintLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", timing_loader)
    classifier = TurnTimingClassifier()
    monster = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        intent="ATTACK",
        move_adjusted_damage=0,
        move_hits=1,
        current_hp=float("inf"),
        max_hp=60,
        strength=0,
    )
    context = SimpleNamespace(turn=1, monsters_alive=[monster])

    timing_context = classifier.classify_turn(context)

    assert timing_context.turn_timing == TurnTiming.SAFE
    assert timing_loader.hint_names == ["Red Slaver"]


def test_damage_curve_ignores_nonfinite_predicted_strength_gain(monkeypatch):
    class FutureAttackLoader:
        def get_monster_timing_hints(self, _monster_name):
            return {}

        def predict_monster_moves(self, _monster_name, current_turn, _hp_percent):
            if current_turn != 1:
                return []
            return [
                {
                    "turn": 1,
                    "move": {
                        "name": "Corrupt Grow",
                        "intent": "BUFF",
                        "strength_gain": float("inf"),
                    },
                },
                {
                    "turn": 2,
                    "move": {
                        "name": "Heavy Stab",
                        "intent": "ATTACK",
                        "damage": 10,
                        "hits": 1,
                    },
                },
            ]

    monkeypatch.setattr(data_loader, "game_data_loader", FutureAttackLoader())
    classifier = TurnTimingClassifier()
    monster = SimpleNamespace(
        name="Red Slaver",
        monster_id="SlaverRed",
        current_hp=45,
        max_hp=60,
        strength=0,
    )
    context = SimpleNamespace(
        turn=1,
        monsters_alive=[monster],
        game=SimpleNamespace(ascension_level=0),
    )

    damage_curve = classifier._calculate_damage_curve(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [10]


def test_combat_mode_hibernation_accepts_string_context_turn(monkeypatch):
    class HibernationOnlyLoader:
        def is_monster_summoner(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def is_monster_hibernating(self, _monster_name, turn):
            return turn == 1

        def does_monster_have_death_split(self, _monster_name):
            return False

        def is_monster_duo_boss(self, _monster_name):
            return False

        def get_monster_threat_profile(self, _monster_name):
            return {}

        def get_monster_type(self, _monster_name):
            return "normal"

    monkeypatch.setattr(simulation, "game_data_loader", HibernationOnlyLoader())
    context = SimpleNamespace(
        turn="1",
        monsters_alive=[
            SimpleNamespace(
                name="Sleeper",
                monster_id="Sleeper",
                current_hp=40,
                max_hp=40,
            )
        ],
    )

    assert (
        simulation.select_combat_mode_with_monster_data(context)
        == simulation.CombatMode.SEMI_AGGRESSIVE
    )


def test_future_strength_prediction_uses_live_id_for_louse_grow(monkeypatch):
    class CanonicalOnlyLoader:
        def get_enhanced_monster_data(self, monster_name):
            if monster_name != "Red Louse":
                return None
            return {
                "moves": [
                    {
                        "name": "Grow",
                        "strength_gain": 3,
                        "ascension_modifiers": {"17+": {"strength_gain": 4}},
                    }
                ],
                "special_mechanics": {"type": "curl_up"},
            }

    monkeypatch.setattr(data_loader, "game_data_loader", CanonicalOnlyLoader())
    classifier = TurnTimingClassifier()
    live_louse = SimpleNamespace(name="Louse", monster_id="FuzzyLouseNormal", strength=0)

    predicted_strength = classifier._predict_future_strength(
        live_louse,
        current_turn=1,
        target_turn=2,
        current_strength=0,
        ascension_level=17,
    )

    assert predicted_strength == 4


def test_future_strength_prediction_counts_grow_on_non_scaler_special_mechanics(monkeypatch):
    class FungiLoader:
        def get_enhanced_monster_data(self, monster_name):
            if monster_name != "Fungi Beast":
                return None
            return {
                "moves": [
                    {
                        "name": "Bite",
                        "damage": 6,
                    },
                    {
                        "name": "Grow",
                        "strength_gain": 3,
                        "ascension_modifiers": {"17+": {"strength_gain": 5}},
                    },
                ],
                "special_mechanics": {"type": "death_effect"},
            }

    monkeypatch.setattr(data_loader, "game_data_loader", FungiLoader())
    classifier = TurnTimingClassifier()
    fungi_beast = SimpleNamespace(name="Fungi Beast", monster_id="FungiBeast", strength=0)

    predicted_strength = classifier._predict_future_strength(
        fungi_beast,
        current_turn=1,
        target_turn=2,
        current_strength=0,
        ascension_level=17,
    )

    assert predicted_strength == 5


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


def test_spike_imminent_ignores_negated_attack_intent(monkeypatch):
    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        lambda *_args, **_kwargs: [
            {
                "turn": 2,
                "move": {"name": "Feint", "intent": "NOT_ATTACK", "damage": 30, "hits": 1},
            }
        ],
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp=80, ascension_level=0),
        turn=1,
        monsters_alive=[SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=0)],
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


def test_enhanced_monster_database_rejects_blank_monster_names():
    database = EnhancedMonsterDatabase()

    assert database.get_monster_data("") is None
    assert database.get_moves("") == []
    assert database.predict_next_moves("", current_turn=1, monster_hp_percent=1.0) == []


def test_enhanced_monster_database_rejects_ambiguous_partial_names():
    database = EnhancedMonsterDatabase()

    assert database.get_monster_data("Slaver") is None
    assert database.get_moves("Slaver") == []
    assert database.get_monster_data("Louse") is None
    assert database.get_monster_data("Champ")["name"] == "The Champ"


def test_enhanced_monster_database_loads_gremlin_nob_live_moves():
    database = EnhancedMonsterDatabase()

    gremlin_nob = database.get_monster_data("Gremlin Nob")
    predictions = database.predict_next_moves(
        "GremlinNob",
        current_turn=1,
        monster_hp_percent=1.0,
    )

    assert gremlin_nob is not None
    assert [move["name"] for move in gremlin_nob["moves"]] == [
        "Bull Rush",
        "Skull Bash",
        "Bellow",
    ]
    bellow = database.get_move_by_id("GremlinNob", 3)
    assert database.get_move_by_id("GremlinNob", 2)["name"] == "Skull Bash"
    assert bellow["name"] == "Bellow"
    assert "strength_gain" not in bellow
    assert bellow["skill_strength_gain"] == 2
    assert predictions[0]["move"]["name"] == "Bellow"
    assert {prediction["move"]["name"] for prediction in predictions[1:]} == {
        "Bull Rush",
        "Skull Bash",
    }


def test_enhanced_monster_database_rejects_fictional_gremlin_giant():
    database = EnhancedMonsterDatabase()

    assert database.get_monster_data("Gremlin Giant") is None
    assert database.get_monster_data("Gremlin_Giant") is None
    assert database.get_moves("Gremlin Giant") == []
    assert database.predict_next_moves(
        "Gremlin Giant",
        current_turn=1,
        monster_hp_percent=1.0,
    ) == []


def test_enhanced_monster_database_loads_jaw_worm_opening_and_moves():
    database = EnhancedMonsterDatabase()

    jaw_worm = database.get_monster_data("Jaw Worm")
    opening = database.predict_next_moves("Jaw Worm", current_turn=1, monster_hp_percent=1.0)
    later = database.predict_next_moves("Jaw Worm", current_turn=2, monster_hp_percent=1.0)

    assert jaw_worm is not None
    assert [move["name"] for move in jaw_worm["moves"]] == ["Chomp", "Thrash", "Bellow"]
    assert opening[0]["move"]["name"] == "Chomp"
    assert {prediction["move"]["name"] for prediction in later[:2]} == {"Bellow", "Thrash"}


def test_enhanced_monster_database_safe_turn_accepts_enum_string_non_attack():
    database = EnhancedMonsterDatabase()
    database.get_timing_hints = lambda _monster_name: None
    database.predict_next_moves = lambda *_args, **_kwargs: [
        {"move": {"name": "Ritual", "intent": "Intent.BUFF"}}
    ]

    assert database.is_safe_turn("Cultist", current_turn=1, monster_hp_percent=1.0) is True


def test_enhanced_monster_database_safe_turn_hint_rejects_attack_buff_overlap():
    database = EnhancedMonsterDatabase()
    database.get_timing_hints = lambda _monster_name: {"safe_turn_indicators": ["BUFF"]}
    database.predict_next_moves = lambda *_args, **_kwargs: [
        {"move": {"name": "Attack Buff", "intent": "Intent.ATTACK_BUFF"}}
    ]

    assert database.is_safe_turn("Jaw Worm", current_turn=2, monster_hp_percent=1.0) is False


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


def test_damage_curve_ignores_negated_attack_intent(monkeypatch):
    def fake_predict_monster_moves(_monster_name, _current_turn, _hp_percent):
        return [
            {
                "turn": 2,
                "move": {
                    "name": "Feint",
                    "intent": "NOT_ATTACK",
                    "damage": 20,
                    "hits": 1,
                },
            }
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
        look_ahead=1,
    )

    assert damage_curve == [0]


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


def test_damage_curve_clamps_negative_monster_strength_per_hit(monkeypatch):
    def fake_predict_monster_moves(_monster_name, _current_turn, _hp_percent):
        return [
            {
                "move": {
                    "name": "Clipped Bite",
                    "intent": "ATTACK",
                    "damage": 3,
                    "hits": 2,
                }
            }
        ]

    monkeypatch.setattr(
        data_loader.game_data_loader,
        "predict_monster_moves",
        fake_predict_monster_moves,
    )
    classifier = TurnTimingClassifier()
    context = SimpleNamespace(game=SimpleNamespace(current_hp=80, ascension_level=0))
    monster = SimpleNamespace(name="Unknown", current_hp=20, max_hp=20, strength=-5)

    damage_curve = classifier._calculate_damage_curve(
        context,
        [monster],
        current_turn=1,
        look_ahead=1,
    )

    assert damage_curve == [0]


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


def test_safe_intent_detection_rejects_attack_buff_even_when_hint_matches_buff():
    classifier = TurnTimingClassifier()
    hints = MonsterTimingHints(safe_turn_indicators=["BUFF"])

    assert classifier._is_safe_intent("Intent.ATTACK_BUFF", "Intent.BUFF", hints) is False


def test_monster_timing_hints_do_not_mark_attack_buff_as_safe():
    hints = MonsterTimingHints(safe_turn_indicators=["BUFF"])

    assert hints.is_safe_turn("Intent.ATTACK_BUFF") is False
    assert hints.is_safe_turn("Intent.BUFF") is True


def test_monster_timing_hints_do_not_mark_negated_attack_as_spike():
    hints = MonsterTimingHints(spike_turn_indicators=["ATTACK"])

    assert hints.is_spike_turn("NOT_ATTACK") is False
    assert hints.is_spike_turn("Intent.ATTACK_DEBUFF") is True


def test_monster_timing_hints_do_not_mark_negated_composite_attack_as_spike():
    hints = MonsterTimingHints(spike_turn_indicators=["ATTACK_DEBUFF"])

    assert hints.is_spike_turn("NOT_ATTACK_DEBUFF") is False
    assert hints.is_spike_turn("Intent.ATTACK_DEBUFF") is True


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


def test_heuristic_incoming_damage_accepts_string_move_adjusted_damage():
    monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp=25,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=2,
        move_adjusted_damage="7",
        move_hits=2,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=1,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 14


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


def test_heuristic_incoming_damage_counts_known_unknown_damage_move():
    monster = SimpleNamespace(
        name="Exploder",
        monster_id="Exploder",
        current_hp=30,
        is_gone=False,
        half_dead=False,
        intent=Intent.UNKNOWN,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[monster]),
        act=3,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 30


def test_heuristic_incoming_damage_ignores_known_no_damage_unknown_moves():
    monsters = [
        SimpleNamespace(
            name="Slime Boss",
            monster_id="Slime_Boss",
            current_hp=99,
            max_hp=140,
            is_gone=False,
            half_dead=False,
            intent=Intent.UNKNOWN,
            move_id=1,
            move_adjusted_damage=0,
            move_hits=1,
        ),
        SimpleNamespace(
            name="Slime Boss",
            monster_id="Slime_Boss",
            current_hp=65,
            max_hp=140,
            is_gone=False,
            half_dead=False,
            intent=Intent.UNKNOWN,
            move_id=3,
            move_adjusted_damage=0,
            move_hits=1,
        ),
        SimpleNamespace(
            name="Acid Slime (L)",
            monster_id="Acid_Slime_L",
            current_hp=15,
            max_hp=65,
            is_gone=False,
            half_dead=False,
            intent=Intent.UNKNOWN,
            move_id=3,
            move_adjusted_damage=0,
            move_hits=1,
        ),
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=monsters),
        act=2,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 0


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


def test_heuristic_incoming_damage_accepts_numeric_string_monster_hp():
    stale_monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        current_hp="0",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=1,
        move_adjusted_damage=12,
        move_hits=1,
    )
    live_monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp="12",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=2,
        move_adjusted_damage=7,
        move_hits=2,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(monsters=[stale_monster, live_monster]),
        act=1,
    )

    assert HeuristicCombatPlanner()._get_incoming_damage(context) == 14


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


def test_damage_potion_score_accepts_numeric_string_monster_hp():
    stale_monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        current_hp="0",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=1,
        move_adjusted_damage=12,
        move_hits=1,
    )
    live_monster = SimpleNamespace(
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
        current_hp="12",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_id=2,
        move_adjusted_damage=7,
        move_hits=2,
    )
    potion = SimpleNamespace(effect_type="damage", effect_value=10)
    context = SimpleNamespace(
        game=SimpleNamespace(
            monsters=[stale_monster, live_monster],
            room_type="Monster",
        ),
        act=1,
        vulnerable_stacks={0: 0},
    )
    state = SimpleNamespace(player_hp=80, player_max_hp=80)

    assert HeuristicCombatPlanner()._score_potion(potion, context, state) == 20


def test_damage_potion_target_accepts_numeric_string_hp_for_lethal():
    killable = SimpleNamespace(name="Low HP Slime", current_hp="7")
    dangerous = SimpleNamespace(name="High HP Slime", current_hp="20")
    potion = SimpleNamespace(effect_type="damage", effect_value=10)
    context = SimpleNamespace(
        monsters_alive=[killable, dangerous],
        compute_threat=lambda monster: 100 if monster is dangerous else 1,
    )

    assert HeuristicCombatPlanner()._find_best_potion_target(potion, context) is killable


def test_debuff_potion_target_orders_numeric_string_hp_numerically():
    lower_hp = SimpleNamespace(name="Nine HP Slime", current_hp="9")
    higher_hp = SimpleNamespace(name="Twelve HP Slime", current_hp="12")
    potion = SimpleNamespace(effect_type="debuff_weak")
    context = SimpleNamespace(monsters_alive=[lower_hp, higher_hp])

    assert HeuristicCombatPlanner()._find_best_potion_target(potion, context) is higher_hp


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


def test_potion_actions_accept_missing_can_use_and_requires_target():
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        current_hp=15,
        is_gone=False,
        half_dead=False,
        intent=Intent.SLEEP,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    potion = SimpleNamespace(effect_type="damage", effect_value=20)
    context = SimpleNamespace(
        game=SimpleNamespace(
            monsters=[monster],
            get_real_potions=lambda: [potion],
            room_type="Monster",
        ),
        monsters_alive=[monster],
        act=1,
        vulnerable_stacks={0: 0},
    )
    state = SimpleNamespace(player_hp=80, player_max_hp=80)

    actions = HeuristicCombatPlanner()._get_potion_actions(context, state)

    assert actions == [(potion, None, 0, 100.0)]


def test_potion_actions_skip_name_only_empty_potion_slot():
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        current_hp=15,
        is_gone=False,
        half_dead=False,
        intent=Intent.SLEEP,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    empty_slot = SimpleNamespace(name="Potion Slot")
    context = SimpleNamespace(
        game=SimpleNamespace(
            monsters=[monster],
            get_real_potions=lambda: [empty_slot],
            room_type="Monster",
        ),
        monsters_alive=[monster],
        act=1,
        vulnerable_stacks={0: 0},
    )
    state = SimpleNamespace(player_hp=80, player_max_hp=80)

    actions = HeuristicCombatPlanner()._get_potion_actions(context, state)

    assert actions == []


def _potion_projection_context(potion, *, player_powers=None, cards=None, energy=0):
    cards = cards or []
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
    return SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=player_powers or []),
            hand=cards,
            monsters=[monster],
            room_type="Monster",
            get_real_potions=lambda: [potion],
        ),
        act=1,
        turn=1,
        floor=5,
        energy_available=energy,
        strength=0,
        player_hp_pct=0.5,
        incoming_damage=18,
        card_synergies={},
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 0},
        playable_cards=cards,
        compute_threat=lambda monster: 18,
    )


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


def test_beam_search_can_use_potion_missing_can_use_when_no_cards_are_playable():
    potion = SimpleNamespace(
        potion_id="FirePotion",
        name="Fire Potion",
        effect_type="damage",
        effect_value=20,
        target_type="monster",
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        max_hp=15,
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

    sequence = HeuristicCombatPlanner().plan_turn(context)

    assert len(sequence) == 1
    assert isinstance(sequence[0], PotionAction)
    assert sequence[0].potion is potion
    assert sequence[0].target_monster is monster


def test_beam_search_can_use_game_potions_without_get_real_potions_method():
    potion = SimpleNamespace(
        potion_id="FirePotion",
        name="Fire Potion",
        effect_type="damage",
        effect_value=20,
        target_type="monster",
        requires_target=True,
    )
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        max_hp=15,
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
            potions=[potion],
            room_type="Monster",
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

    sequence = HeuristicCombatPlanner().plan_turn(context)

    assert len(sequence) == 1
    assert isinstance(sequence[0], PotionAction)
    assert sequence[0].potion is potion
    assert sequence[0].target_monster is monster


def test_beam_search_cultist_potion_applies_ritual_at_end_of_turn_projection():
    potion = Potion(
        potion_id="CultistPotion",
        name="Cultist Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            projected = planner.simulator.project_end_turn_effects(final_state)
            observed.append(
                (
                    getattr(final_state, "player_ritual", 0),
                    final_state.player_strength,
                    projected.player_strength,
                )
            )
        return 0

    planner.simulator.calculate_outcome_score = score

    planner.plan_turn(context)

    assert observed == [(1, 0, 1)]


def test_state_key_and_clone_preserve_player_ritual():
    potion = Potion(
        potion_id="CultistPotion",
        name="Cultist Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    base_state = simulation.SimulationState(context)
    ritual_state = base_state.clone()
    ritual_state.player_ritual = 1

    assert ritual_state.clone().player_ritual == 1
    assert base_state.state_key([]) != ritual_state.state_key([])


def test_beam_search_regen_potion_heals_at_end_of_turn_projection():
    potion = Potion(
        potion_id="RegenPotion",
        name="Regen Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            projected = planner.simulator.project_end_turn_effects(final_state)
            observed.append(
                (
                    final_state.player_hp,
                    getattr(final_state, "player_regen", 0),
                    projected.player_hp,
                    getattr(projected, "player_regen", 0),
                )
            )
        return 0

    planner.simulator.calculate_outcome_score = score

    planner.plan_turn(context)

    assert observed == [(40, 5, 45, 4)]


def test_state_key_and_clone_preserve_player_regen():
    potion = Potion(
        potion_id="RegenPotion",
        name="Regen Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    base_state = simulation.SimulationState(context)
    regen_state = base_state.clone()
    regen_state.player_regen = 5

    assert regen_state.clone().player_regen == 5
    assert base_state.state_key([]) != regen_state.state_key([])


def test_state_key_distinguishes_player_max_hp_for_future_healing():
    potion = Potion(
        potion_id="RegenPotion",
        name="Regen Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    base_state = simulation.SimulationState(context)
    larger_max_hp_state = base_state.clone()
    larger_max_hp_state.player_max_hp += 5

    assert larger_max_hp_state.player_hp == base_state.player_hp
    assert base_state.state_key([]) != larger_max_hp_state.state_key([])


def test_state_key_distinguishes_monster_max_hp_for_phase_thresholds():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    context = _potion_projection_context(potion)
    base_state = simulation.SimulationState(context)
    lower_percent_state = base_state.clone()

    base_state.monsters[0]["hp"] = 40
    lower_percent_state.monsters[0]["hp"] = 40
    lower_percent_state.monsters[0]["max_hp"] = 80

    assert base_state.monsters[0]["hp"] == lower_percent_state.monsters[0]["hp"]
    assert base_state.state_key([]) != lower_percent_state.state_key([])


def test_state_key_distinguishes_live_monster_move_threat():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    context = _potion_projection_context(potion)
    base_state = simulation.SimulationState(context)
    stronger_move_state = base_state.clone()
    multi_hit_state = base_state.clone()

    stronger_move_state.monsters[0]["move_adjusted_damage"] = (
        base_state.monsters[0]["move_adjusted_damage"] + 6
    )
    multi_hit_state.monsters[0]["move_hits"] = base_state.monsters[0]["move_hits"] + 1

    assert base_state.state_key([]) != stronger_move_state.state_key([])
    assert base_state.state_key([]) != multi_hit_state.state_key([])


def test_state_key_handles_mixed_type_monster_move_ids():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    context = _potion_projection_context(potion)
    state = simulation.SimulationState(context)
    second_monster = state.monsters[0].copy()

    state.monsters[0]["move_id"] = 1
    second_monster["move_id"] = "2"
    state.monsters.append(second_monster)

    assert len(state.state_key([])[1]) == 2


def test_state_key_handles_missing_or_numeric_monster_identity_fields():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    context = _potion_projection_context(potion)
    state = simulation.SimulationState(context)
    second_monster = state.monsters[0].copy()
    third_monster = state.monsters[0].copy()

    state.monsters[0]["move_id"] = 1
    second_monster["move_id"] = 1
    third_monster["move_id"] = 1
    state.monsters[0]["monster_id"] = None
    second_monster["monster_id"] = 7
    third_monster["monster_id"] = "Lagavulin"
    state.monsters[0]["name"] = None
    second_monster["name"] = 7
    third_monster["name"] = "Lagavulin"
    state.monsters.extend([second_monster, third_monster])

    assert len(state.state_key([])[1]) == 3


def test_state_key_handles_mixed_type_hand_card_key_fields():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    context = _potion_projection_context(potion)
    state = simulation.SimulationState(context)
    playable_cards = [
        SimpleNamespace(
            card_id=None,
            name="Flex",
            upgrades=0,
            cost=0,
            cost_for_turn=0,
        ),
        SimpleNamespace(
            card_id=7,
            name="Strike",
            upgrades=0,
            cost=1,
            cost_for_turn=1,
        ),
        SimpleNamespace(
            card_id="SameCard",
            name="Same Card",
            upgrades=None,
            cost=None,
            cost_for_turn=None,
        ),
        SimpleNamespace(
            card_id="SameCard",
            name="Same Card",
            upgrades=1,
            cost="1",
            cost_for_turn="1",
        ),
    ]

    assert len(state.state_key(playable_cards)[2]) == 4


def test_state_key_distinguishes_engine_events_used_for_scoring():
    potion = Potion(
        potion_id="SwiftPotion",
        name="Swift Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    base_state = simulation.SimulationState(context)
    event_state = base_state.clone()

    event_state.exhaust_events += 1
    event_state.cards_drawn += 2
    event_state.energy_gained += 1
    event_state.energy_saved += 1

    assert (
        FastCombatSimulator(None).calculate_outcome_score(base_state, event_state)
        > FastCombatSimulator(None).calculate_outcome_score(base_state, base_state)
    )
    assert base_state.state_key([]) != event_state.state_key([])


def test_state_key_distinguishes_remaining_duplicate_card_costs():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    cheap_strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        cost_for_turn=0,
        uuid="cheap-strike",
    )
    expensive_strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        cost_for_turn=2,
        uuid="expensive-strike",
    )
    context = _potion_projection_context(
        potion,
        cards=[cheap_strike, expensive_strike],
        energy=1,
    )
    cheap_played_state = simulation.SimulationState(context)
    expensive_played_state = cheap_played_state.clone()

    cheap_played_state.played_card_uuids.add(id(cheap_strike))
    expensive_played_state.played_card_uuids.add(id(expensive_strike))

    def remaining_costs(state):
        return [
            HeuristicCombatPlanner._card_cost_for_state(card, state)
            for card in context.playable_cards
            if id(card) not in state.played_card_uuids
        ]

    assert remaining_costs(cheap_played_state) == [2]
    assert remaining_costs(expensive_played_state) == [0]
    assert cheap_played_state.state_key(context.playable_cards) != (
        expensive_played_state.state_key(context.playable_cards)
    )


def test_simulation_state_includes_existing_plated_armor_end_turn_block():
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    context = _potion_projection_context(
        potion,
        player_powers=[
            SimpleNamespace(power_name="Metallicize", amount=3),
            SimpleNamespace(power_name="Plated Armor", amount=4),
        ],
    )

    state = simulation.SimulationState(context)

    assert state.end_turn_block == 7
    assert state.turn_block() == 7


def test_simulation_state_clone_preserves_future_state_fields():
    potion = Potion(
        potion_id="CultistPotion",
        name="Cultist Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    state = simulation.SimulationState(context)
    state.future_state_counter = 7

    cloned = state.clone()

    assert cloned.future_state_counter == 7

    cloned.monsters[0]["hp"] = 1
    assert state.monsters[0]["hp"] == 100

    cloned.played_card_uuids.add("generated")
    assert "generated" not in state.played_card_uuids


def test_beam_search_flex_potion_strength_expires_at_end_of_turn_projection():
    potion = Potion(
        potion_id="FlexPotion",
        name="Flex Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            projected = planner.simulator.project_end_turn_effects(final_state)
            observed.append((final_state.player_strength, projected.player_strength))
        return 0

    planner.simulator.calculate_outcome_score = score

    planner.plan_turn(context)

    assert observed == [(5, 0)]


def test_beam_search_flex_potion_artifact_blocks_strength_loss():
    potion = Potion(
        potion_id="FlexPotion",
        name="Flex Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(
        potion,
        player_powers=[SimpleNamespace(power_name="Artifact", amount=1)],
    )
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            projected = planner.simulator.project_end_turn_effects(final_state)
            observed.append(
                (
                    final_state.player_strength,
                    final_state.player_artifact,
                    projected.player_strength,
                )
            )
        return 0

    planner.simulator.calculate_outcome_score = score

    planner.plan_turn(context)

    assert observed == [(5, 0, 5)]


def test_beam_search_speed_potion_dexterity_expires_at_end_of_turn_projection():
    potion = Potion(
        potion_id="SpeedPotion",
        name="Speed Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    context = _potion_projection_context(potion)
    planner = HeuristicCombatPlanner()
    observed = []

    def score(_initial_state, final_state, _act, _weights, _context, sequence):
        if sequence and isinstance(sequence[-1], PotionAction):
            projected = planner.simulator.project_end_turn_effects(final_state)
            observed.append((final_state.player_dexterity, projected.player_dexterity))
        return 0

    planner.simulator.calculate_outcome_score = score

    planner.plan_turn(context)

    assert observed == [(5, 0)]


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


def test_beam_search_keeps_depth_local_candidates_for_future_payoffs():
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
            card_id=card_id,
            name=card_id,
            cost=1,
            cost_for_turn=1,
            has_target=False,
        )
        for card_id in ("BaitA", "SetupB", "ComboC", "PayoffD")
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
    planner = HeuristicCombatPlanner(beam_width=2)
    planner.fast_score_action = lambda _card, _state, _context: 1
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0

    def simulate_card_play(state, card, _target, context=None):
        new_state = state.clone()
        new_state.player_energy -= card.cost_for_turn
        return new_state

    def score(_initial_state, _final_state, _act, _weights, _context, sequence):
        ids = tuple(action.card.card_id for action in sequence)
        if ids == ("BaitA",):
            return 100
        if ids == ("SetupB",):
            return 90
        if len(ids) == 2 and ids[0] == "BaitA":
            return 85
        if ids == ("SetupB", "ComboC"):
            return 89
        if ids == ("SetupB", "ComboC", "PayoffD"):
            return 200
        return 1

    planner.simulator.simulate_card_play = simulate_card_play
    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert [action.card.card_id for action in sequence] == [
        "SetupB",
        "ComboC",
        "PayoffD",
    ]


def test_beam_search_keeps_best_scoring_sequence_across_depths():
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
            card_id=card_id,
            name=card_id,
            cost=1,
            cost_for_turn=1,
            has_target=False,
        )
        for card_id in ("BaitA", "LowB", "LowC")
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
    planner = HeuristicCombatPlanner(beam_width=2)
    planner.fast_score_action = lambda _card, _state, _context: 1
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0

    def simulate_card_play(state, card, _target, context=None):
        new_state = state.clone()
        new_state.player_energy -= card.cost_for_turn
        return new_state

    def score(_initial_state, _final_state, _act, _weights, _context, sequence):
        ids = tuple(action.card.card_id for action in sequence)
        if ids == ("BaitA",):
            return 100
        return 1

    planner.simulator.simulate_card_play = simulate_card_play
    planner.simulator.calculate_outcome_score = score

    sequence = planner.plan_turn(context)

    assert [action.card.card_id for action in sequence] == ["BaitA"]


def test_beam_search_retargets_after_simulated_monster_death(monkeypatch):
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    monsters = [
        SimpleNamespace(
            name="Louse",
            monster_id="LouseA",
            monster_index=0,
            max_hp=6,
            current_hp=6,
            block=0,
            intent=Intent.ATTACK,
            half_dead=False,
            is_gone=False,
            move_id=1,
            move_adjusted_damage=5,
            move_hits=1,
            strength=0,
            powers=[],
        ),
        SimpleNamespace(
            name="Louse",
            monster_id="LouseB",
            monster_index=1,
            max_hp=6,
            current_hp=6,
            block=0,
            intent=Intent.ATTACK,
            half_dead=False,
            is_gone=False,
            move_id=1,
            move_adjusted_damage=5,
            move_hits=1,
            strength=0,
            powers=[],
        ),
    ]
    strikes = [
        Card(
            card_id="Strike_R",
            name="Strike",
            card_type=CardType.ATTACK,
            rarity=CardRarity.COMMON,
            has_target=True,
            cost=1,
            cost_for_turn=1,
        )
        for _ in range(2)
    ]
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[], strength=0),
            monsters=monsters,
            room_type="Monster",
            get_real_potions=lambda: [],
        ),
        player=SimpleNamespace(strength=0),
        act=1,
        turn=1,
        floor=5,
        energy_available=2,
        strength=0,
        player_hp=40,
        player_hp_pct=0.5,
        monsters_alive=monsters,
        vulnerable_stacks={0: 0, 1: 0},
        weak_stacks={0: 0, 1: 0},
        frail_stacks={0: 0, 1: 0},
        thorns_stacks={0: 0, 1: 0},
        playable_cards=strikes,
        compute_threat=lambda _monster: 1,
    )
    planner = HeuristicCombatPlanner(beam_width=4, max_depth=2)
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0

    sequence = planner._beam_search_plan(context)

    assert [action.target_monster for action in sequence] == monsters


def test_find_best_target_ignores_simulated_dead_target_for_threat_fallback(monkeypatch):
    loader = data_loader.GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    dead_high_threat = SimpleNamespace(
        name="Louse",
        monster_id="DeadThreat",
        max_hp=30,
        current_hp=30,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=20,
        move_hits=1,
        strength=0,
        powers=[],
    )
    live_low_threat = SimpleNamespace(
        name="Louse",
        monster_id="LiveThreat",
        max_hp=30,
        current_hp=30,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=5,
        move_hits=1,
        strength=0,
        powers=[],
    )
    context = SimpleNamespace(
        game=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            player=SimpleNamespace(block=0, powers=[]),
            get_real_potions=lambda: [],
        ),
        player=SimpleNamespace(strength=0),
        energy_available=1,
        strength=0,
        monsters_alive=[dead_high_threat, live_low_threat],
        vulnerable_stacks={0: 0, 1: 0},
        weak_stacks={0: 0, 1: 0},
        frail_stacks={0: 0, 1: 0},
        thorns_stacks={0: 0, 1: 0},
        playable_cards=[],
        compute_threat=lambda monster: 100 if monster is dead_high_threat else 1,
    )
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = True
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
        cost_for_turn=1,
    )

    target = HeuristicCombatPlanner()._find_best_target(strike, context, state=state)

    assert target is live_low_threat


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
