from types import SimpleNamespace

import spirecomm.ai.heuristics.simulation as simulation
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.ai.heuristics.combat_ending import CombatEndingDetector
from spirecomm.ai.heuristics.simulation import FastCombatSimulator, HeuristicCombatPlanner, SimulationState
from spirecomm.communication.action import PlayCardAction
from spirecomm.data.loader import GameDataLoader
from spirecomm.spire.card import Card, CardRarity, CardType
from spirecomm.spire.character import Intent, Monster


def _context_with_one_playable(card):
    monster = Monster(
        name="The Guardian",
        monster_id="TheGuardian",
        max_hp=240,
        current_hp=120,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=5,
        move_adjusted_damage=12,
        move_hits=1,
    )
    game = SimpleNamespace(
        current_hp=30,
        max_hp=80,
        player=SimpleNamespace(block=0, powers=[]),
    )
    return SimpleNamespace(
        game=game,
        game_id="test-negative-score",
        energy_available=1,
        strength=0,
        monsters_alive=[monster],
        vulnerable_stacks={0: 0},
        weak_stacks={0: 0},
        frail_stacks={0: 0},
        thorns_stacks={0: 3},
        playable_cards=[card],
        incoming_damage=12,
        turn=5,
        floor=16,
        act=1,
        player_hp=30,
        player_hp_pct=30 / 80,
    )


def test_beam_search_can_end_turn_when_every_play_is_worse_than_empty():
    card = Card(
        card_id="Defend_R",
        name="Defend",
        card_type=CardType.SKILL,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    planner = IroncladCombatPlanner()

    def score(sequence, _initial_state, _final_state, _context):
        return 0 if not sequence else -10

    def simulate(state, _card, _target, _target_idx, context=None):
        new_state = state.clone()
        new_state.energy_spent += 1
        return new_state

    planner._score_sequence = score
    planner.simulator.simulate_card_play = simulate

    assert planner._beam_search_turn(_context_with_one_playable(card), [card], 10, 4) == []


def _louse(current_hp=50):
    return Monster(
        name="Louse",
        monster_id="FuzzyLouseNormal",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=3,
        move_adjusted_damage=7,
        move_hits=1,
    )


def _awakened_one(current_hp=300):
    return Monster(
        name="Awakened One",
        monster_id="AwakenedOne",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=18,
        move_hits=1,
    )


def _combat_context(cards, energy=3, monsters=None):
    monsters = monsters or [_louse(), _louse()]
    game = SimpleNamespace(
        current_hp=80,
        max_hp=80,
        player=SimpleNamespace(block=0, powers=[]),
    )
    return SimpleNamespace(
        game=game,
        game_id="test-x-cost",
        energy_available=energy,
        strength=0,
        monsters_alive=monsters,
        vulnerable_stacks={i: 0 for i, _ in enumerate(monsters)},
        weak_stacks={i: 0 for i, _ in enumerate(monsters)},
        frail_stacks={i: 0 for i, _ in enumerate(monsters)},
        thorns_stacks={i: 0 for i, _ in enumerate(monsters)},
        playable_cards=cards,
        incoming_damage=0,
        turn=2,
        floor=8,
        act=1,
        player_hp=80,
        player_hp_pct=1.0,
    )


def _card(
    card_id,
    name,
    card_type=CardType.ATTACK,
    cost=1,
    cost_for_turn=None,
    has_target=True,
    upgrades=0,
):
    return Card(
        card_id=card_id,
        name=name,
        card_type=card_type,
        rarity=CardRarity.UNCOMMON,
        upgrades=upgrades,
        cost=cost,
        cost_for_turn=cost_for_turn,
        has_target=has_target,
        is_playable=True,
    )


def test_x_cost_whirlwind_spends_current_energy_without_negative_simulation_state():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        whirlwind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_spent == 3
    assert result.total_damage_dealt == 30


def test_simulator_does_not_treat_upgraded_non_block_skills_as_block(monkeypatch):
    burning_pact = _card(
        "Burning Pact",
        "Burning Pact+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([burning_pact], energy=3)
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "burning pact": {
            "name": "Burning Pact",
            "description": "Exhaust 1 card. Draw 2 cards.",
        }
    }
    loader._wiki_data = {
        "burning pact": {
            "name": "Burning Pact",
            "text": "#Exhaust 1 card.\nDraw [2|3] cards.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        burning_pact,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 0


def test_bludgeon_damage_is_static_not_scaled_by_block(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bludgeon": {
            "name": "Bludgeon",
            "description": "Deal 32 damage.",
        }
    }
    loader._wiki_data = {
        "bludgeon": {
            "name": "Bludgeon",
            "text": "Deal [32|42] damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    bludgeon = _card("Bludgeon", "Bludgeon", cost=3)

    for block in (0, 200):
        context = _combat_context([bludgeon], energy=3, monsters=[_louse(current_hp=100)])
        state = SimulationState(context)
        state.player_block = block

        result = simulator.simulate_card_play(
            state,
            bludgeon,
            target=context.monsters_alive[0],
            target_index=0,
            context=context,
        )

        assert result.total_damage_dealt == 32


def test_upgraded_bludgeon_damage_is_42(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bludgeon": {
            "name": "Bludgeon",
            "description": "Deal 32 damage.",
        }
    }
    loader._wiki_data = {
        "bludgeon": {
            "name": "Bludgeon",
            "text": "Deal [32|42] damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    context = _combat_context([], energy=3, monsters=[_louse(current_hp=100)])
    bludgeon_plus = _card("Bludgeon", "Bludgeon+", cost=3, upgrades=1)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bludgeon_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 42


def test_reaper_damage_is_static_aoe_not_unknown_fallback(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "reaper": {
            "name": "Reaper",
            "description": "Deal 4 damage to ALL enemies. Heal HP equal to unblocked damage. Exhaust.",
        }
    }
    loader._wiki_data = {
        "reaper": {
            "name": "Reaper",
            "text": "Deal [4|5] damage to ALL enemies. Heal HP equal to unblocked damage.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    context = _combat_context([], energy=2, monsters=[_louse(current_hp=20), _louse(current_hp=20)])
    reaper = _card("Reaper", "Reaper", cost=2, has_target=False)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        reaper,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.damage_instances == 2


def test_upgraded_reaper_damage_is_5_per_enemy(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "reaper": {
            "name": "Reaper",
            "description": "Deal 4 damage to ALL enemies. Heal HP equal to unblocked damage. Exhaust.",
        }
    }
    loader._wiki_data = {
        "reaper": {
            "name": "Reaper",
            "text": "Deal [4|5] damage to ALL enemies. Heal HP equal to unblocked damage.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    context = _combat_context([], energy=2, monsters=[_louse(current_hp=20), _louse(current_hp=20)])
    reaper_plus = _card("Reaper", "Reaper+", cost=2, has_target=False, upgrades=1)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        reaper_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 10
    assert result.damage_instances == 2


def test_carnage_is_single_target_not_aoe(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "carnage": {
            "name": "Carnage",
            "description": "Ethereal. Deal 20 damage.",
        }
    }
    loader._wiki_data = {
        "carnage": {
            "name": "Carnage",
            "text": "#Ethereal.\nDeal [20|28] damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    monsters = [_louse(current_hp=30), _louse(current_hp=30)]
    context = _combat_context([], energy=2, monsters=monsters)
    carnage = _card("Carnage", "Carnage", cost=2)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        carnage,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 20
    assert result.damage_instances == 1


def test_twin_strike_hits_twice_with_upgrade_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "twin strike": {
            "name": "Twin Strike",
            "description": "Deal 5 damage twice.",
        }
    }
    loader._wiki_data = {
        "twin strike": {
            "name": "Twin Strike",
            "text": "Deal [5|7] damage twice.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    context = _combat_context([twin_strike], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        twin_strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 10
    assert result.damage_instances == 2

    twin_strike_plus = _card("Twin Strike", "Twin Strike+", cost=1, upgrades=1)
    context = _combat_context([twin_strike_plus], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        twin_strike_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 14
    assert result.damage_instances == 2


def test_pummel_uses_hit_count_upgrade_not_hit_count_as_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "pummel": {
            "name": "Pummel",
            "description": "Deal 2 damage 4 times. Exhaust.",
        }
    }
    loader._wiki_data = {
        "pummel": {
            "name": "Pummel",
            "text": "Deal 2 damage [4|5] times.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    pummel = _card("Pummel", "Pummel", cost=1)
    context = _combat_context([pummel], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        pummel,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.damage_instances == 4

    pummel_plus = _card("Pummel", "Pummel+", cost=1, upgrades=1)
    context = _combat_context([pummel_plus], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        pummel_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 10
    assert result.damage_instances == 5


def test_upgraded_single_hit_attacks_use_exported_damage_bonus(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "anger": {"name": "Anger", "description": "Deal 6 damage."},
        "dropkick": {"name": "Dropkick", "description": "Deal 5 damage."},
        "reckless charge": {"name": "Reckless Charge", "description": "Deal 7 damage."},
    }
    loader._wiki_data = {
        "anger": {"name": "Anger", "text": "Deal [6|8] damage.\nAdd a copy of this card into your discard pile."},
        "dropkick": {"name": "Dropkick", "text": "Deal [5|8] damage.\nIf the enemy has #Vulnerable,\ngain <R> and\ndraw 1 card."},
        "reckless charge": {"name": "Reckless Charge", "text": "Deal [7|10] damage.\nShuffle a *Dazed into your draw pile."},
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    for card_name, expected_damage in (
        ("Anger", 8),
        ("Dropkick", 8),
        ("Reckless Charge", 10),
    ):
        card = _card(card_name, f"{card_name}+", cost=1, upgrades=1)
        context = _combat_context([card], energy=1, monsters=[_louse(current_hp=100)])

        result = simulator.simulate_card_play(
            SimulationState(context),
            card,
            target=context.monsters_alive[0],
            target_index=0,
            context=context,
        )

        assert result.total_damage_dealt == expected_damage
        assert result.damage_instances == 1


def test_heavy_blade_uses_strength_multiplier_and_static_base_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "heavy blade": {
            "name": "Heavy Blade",
            "description": "Deal 14 damage. Strength affects Heavy Blade 3 times.",
        }
    }
    loader._wiki_data = {
        "heavy blade": {
            "name": "Heavy Blade",
            "text": "Deal 14 damage.\nStrength affects Heavy Blade [3|5] times.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    heavy_blade = _card("Heavy Blade", "Heavy Blade", cost=2)
    context = _combat_context([heavy_blade], energy=2, monsters=[_louse(current_hp=100)])
    context.strength = 3
    result = simulator.simulate_card_play(
        SimulationState(context),
        heavy_blade,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 23

    heavy_blade_plus = _card("Heavy Blade", "Heavy Blade+", cost=2, upgrades=1)
    context = _combat_context([heavy_blade_plus], energy=2, monsters=[_louse(current_hp=100)])
    context.strength = 3
    result = simulator.simulate_card_play(
        SimulationState(context),
        heavy_blade_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 29


def test_fiend_fire_hits_once_per_other_unplayed_card_with_upgrade_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust.",
        }
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "#Exhaust your hand.\nDeal [7|10] damage for each card #Exhausted.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    strike = _card("Strike_R", "Strike", cost=1)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    context = _combat_context([fiend_fire, strike, defend], energy=2, monsters=[_louse(current_hp=100)])
    context.strength = 2
    result = simulator.simulate_card_play(
        SimulationState(context),
        fiend_fire,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 18
    assert result.damage_instances == 2

    fiend_fire_plus = _card("Fiend Fire", "Fiend Fire+", cost=2, upgrades=1)
    context = _combat_context([fiend_fire_plus, strike, defend], energy=2, monsters=[_louse(current_hp=100)])
    context.strength = 2
    result = simulator.simulate_card_play(
        SimulationState(context),
        fiend_fire_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 24
    assert result.damage_instances == 2


def test_uppercut_applies_weak_and_vulnerable_with_upgrade_stacks(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "uppercut": {
            "name": "Uppercut",
            "description": "Deal 13 damage.\nApply 1 Weak.\nApply 1 Vulnerable.",
        }
    }
    loader._wiki_data = {
        "uppercut": {
            "name": "Uppercut",
            "text": "Deal 13 damage.\nApply [1|2] #Weak.\nApply [1|2] #Vulnerable.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    uppercut = _card("Uppercut", "Uppercut", cost=2)
    context = _combat_context([uppercut], energy=2, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        uppercut,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["weak"] == 1
    assert result.monsters[0]["vulnerable"] == 1

    uppercut_plus = _card("Uppercut", "Uppercut+", cost=2, upgrades=1)
    context = _combat_context([uppercut_plus], energy=2, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        uppercut_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["weak"] == 2
    assert result.monsters[0]["vulnerable"] == 2


def test_perfected_strike_counts_strike_cards_in_deck(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "perfected strike": {
            "name": "Perfected Strike",
            "description": "Deal 6 damage. Deals 2 additional damage for ALL your cards containing \"Strike\".",
        }
    }
    loader._wiki_data = {
        "perfected strike": {
            "name": "Perfected Strike",
            "text": "Deal 6 damage.\nDeals [2|3] additional damage for ALL your cards containing \"Strike\".",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    perfected_strike = _card("Perfected Strike", "Perfected Strike", cost=2)
    context = _combat_context([perfected_strike], energy=2, monsters=[_louse(current_hp=100)])
    context.game.deck = [
        _card("Strike_R", "Strike"),
        _card("Strike_R", "Strike"),
        _card("Twin Strike", "Twin Strike"),
        _card("Perfected Strike", "Perfected Strike"),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        perfected_strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 14

    perfected_strike_plus = _card("Perfected Strike", "Perfected Strike+", cost=2, upgrades=1)
    context = _combat_context([perfected_strike_plus], energy=2, monsters=[_louse(current_hp=100)])
    context.game.deck = [
        _card("Strike_R", "Strike"),
        _card("Strike_R", "Strike"),
        _card("Twin Strike", "Twin Strike"),
        _card("Perfected Strike", "Perfected Strike"),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        perfected_strike_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 18


def test_fast_score_does_not_apply_aoe_multiplier_to_carnage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "carnage": {
            "name": "Carnage",
            "description": "Ethereal. Deal 20 damage.",
        }
    }
    loader._wiki_data = {
        "carnage": {
            "name": "Carnage",
            "text": "#Ethereal.\nDeal [20|28] damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    carnage = _card("Carnage", "Carnage", cost=2)
    context = _combat_context([carnage], energy=2, monsters=[_louse(current_hp=30), _louse(current_hp=30)])

    score = HeuristicCombatPlanner().fast_score_action(
        carnage,
        SimulationState(context),
        context,
    )

    assert score == simulation.FASTSCORE_ATTACK_BONUS + 20 * simulation.FASTSCORE_DAMAGE_MULTIPLIER


def test_lethal_targeting_treats_carnage_as_single_target():
    carnage = _card("Carnage", "Carnage", cost=2)
    context = _combat_context([carnage], energy=2, monsters=[_louse(current_hp=20), _louse(current_hp=20)])

    assert CombatEndingDetector()._can_target_all_monsters(context, affordable_damage=40) is False


def test_beam_search_does_not_play_more_cards_after_x_cost_whirlwind_spends_all_energy():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1, cost_for_turn=1)
    context = _combat_context([whirlwind, strike], energy=3)
    planner = IroncladCombatPlanner()

    def prefer_long_sequences(sequence, _initial_state, _final_state, _context):
        return len(sequence)

    planner._score_sequence = prefer_long_sequences
    sequence = planner._beam_search_turn(context, [whirlwind, strike], 10, 4)
    card_ids = [action.card.card_id for action in sequence]

    assert "Whirlwind" in card_ids
    assert card_ids[-1] == "Whirlwind"


def test_lethal_detector_counts_whirlwind_damage_without_negative_energy():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=50)])

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 15


def test_awakened_one_penalizes_slow_power_setup_in_beam_score():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    context = _combat_context([demon_form], energy=3, monsters=[_awakened_one()])
    context.game_id = "test-awakened-one-power"
    context.incoming_damage = 18
    context.turn = 3
    context.floor = 50
    context.act = 3
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    initial_state = SimulationState(context)
    power_state = initial_state.clone()
    power_state.energy_spent = 3

    empty_score = planner._score_sequence([], initial_state, initial_state, context)
    power_score = planner._score_sequence(
        [PlayCardAction(card=demon_form)],
        initial_state,
        power_state,
        context,
    )

    assert power_score < empty_score
