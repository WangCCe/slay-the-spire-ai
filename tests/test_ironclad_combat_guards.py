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


def test_simulator_resolves_target_object_when_target_index_is_omitted(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike_r": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    loader._wiki_data = {
        "strike": {
            "name": "Strike",
            "text": "Deal [6|9] damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    first = _louse(current_hp=40)
    second = _louse(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[first, second])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=first,
        context=context,
    )

    assert result.monsters[0]["hp"] == 34
    assert result.monsters[1]["hp"] == 40


def test_incoming_damage_estimate_multiplies_monster_hits():
    monster = _louse(current_hp=40)
    monster.move_adjusted_damage = 6
    monster.move_hits = 3
    context = _combat_context([], energy=3, monsters=[monster])
    state = SimulationState(context)

    incoming = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(state.monsters)

    assert incoming == 18


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


def test_iron_wave_deals_damage_and_gains_block(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "iron wave": {
            "name": "Iron Wave",
            "description": "Gain 5 Block.\nDeal 5 damage.",
        }
    }
    loader._wiki_data = {
        "iron wave": {
            "name": "Iron Wave",
            "text": "Gain [5|7] #Block.\nDeal [5|7] damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    iron_wave = _card("Iron Wave", "Iron Wave", cost=1)
    context = _combat_context([iron_wave], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        iron_wave,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 5
    assert result.player_block == 5

    iron_wave_plus = _card("Iron Wave", "Iron Wave+", cost=1, upgrades=1)
    context = _combat_context([iron_wave_plus], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        iron_wave_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 7
    assert result.player_block == 7


def test_entrench_doubles_current_block():
    entrench = _card(
        "Entrench",
        "Entrench",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    context = _combat_context([entrench], energy=2, monsters=[_louse(current_hp=100)])
    initial_state = SimulationState(context)
    initial_state.player_block = 12

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        initial_state,
        entrench,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 24


def test_second_wind_gains_block_for_each_non_attack_card_exhausted():
    second_wind = _card(
        "Second Wind",
        "Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    power_through = _card(
        "Power Through",
        "Power Through",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [second_wind, defend, power_through, strike],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 10
    assert result.exhaust_events == 2

    second_wind_plus = _card(
        "Second Wind",
        "Second Wind+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [second_wind_plus, defend, power_through, strike],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 14
    assert result.exhaust_events == 2


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


def test_reaper_heals_for_unblocked_damage(monkeypatch):
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
    reaper = _card("Reaper", "Reaper", cost=2, has_target=False)
    context = _combat_context(
        [reaper],
        energy=2,
        monsters=[_louse(current_hp=20), _louse(current_hp=20)],
    )
    context.game.current_hp = 20
    context.player_hp = 20

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        reaper,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.player_hp == 28


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


def test_sword_boomerang_hits_random_enemy_three_or_four_times_without_target(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "sword boomerang": {
            "name": "Sword Boomerang",
            "description": "Deal 3 damage to a random enemy 3 times.",
        }
    }
    loader._wiki_data = {
        "sword boomerang": {
            "name": "Sword Boomerang",
            "text": "Deal 3 damage to a random enemy [3|4] times.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    sword_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1, has_target=False)
    context = _combat_context([sword_boomerang], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        sword_boomerang,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 9
    assert result.damage_instances == 3

    sword_boomerang_plus = _card(
        "Sword Boomerang",
        "Sword Boomerang+",
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([sword_boomerang_plus], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        sword_boomerang_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 12
    assert result.damage_instances == 4


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


def test_dropkick_refunds_energy_and_draws_against_vulnerable_enemy(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage.\nIf the enemy has Vulnerable,\ngain [R] and\ndraw 1 card.",
        }
    }
    loader._wiki_data = {
        "dropkick": {
            "name": "Dropkick",
            "text": "Deal [5|8] damage.\nIf the enemy has #Vulnerable,\ngain [R] and\ndraw 1 card.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    context = _combat_context([dropkick], energy=1, monsters=[_louse(current_hp=100)])
    context.vulnerable_stacks[0] = 1

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        dropkick,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 7
    assert result.player_energy == 1
    assert result.energy_gained == 1
    assert result.cards_drawn == 1


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


def test_inflame_uses_real_strength_amount_before_attacks():
    inflame = _card(
        "Inflame",
        "Inflame",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([inflame, strike], energy=2, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        inflame,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 8

    inflame_plus = _card(
        "Inflame",
        "Inflame+",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([inflame_plus, strike], energy=2, monsters=[_louse(current_hp=100)])
    state = simulator.simulate_card_play(
        SimulationState(context),
        inflame_plus,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 9


def test_strength_skill_cards_affect_followup_attacks():
    strike = _card("Strike_R", "Strike", cost=1)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    context = _combat_context([flex, strike], energy=1, monsters=[_louse(current_hp=100)])
    state = simulator.simulate_card_play(
        SimulationState(context),
        flex,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 8

    spot_weakness = _card(
        "Spot Weakness",
        "Spot Weakness",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    context = _combat_context([spot_weakness, strike], energy=2, monsters=[_louse(current_hp=100)])
    state = simulator.simulate_card_play(
        SimulationState(context),
        spot_weakness,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 9

    limit_break = _card(
        "Limit Break",
        "Limit Break",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context([limit_break, strike], energy=2, monsters=[_louse(current_hp=100)])
    context.strength = 3
    state = simulator.simulate_card_play(
        SimulationState(context),
        limit_break,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 12


def test_energy_gain_skills_add_usable_energy(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bloodletting": {
            "name": "Bloodletting",
            "description": "Lose 3 HP.\nGain [R] [R].",
        },
        "offering": {
            "name": "Offering",
            "description": "Lose 6 HP.\nGain [R] [R].\nDraw 3 cards.\nExhaust.",
        },
        "seeing red": {
            "name": "Seeing Red",
            "description": "Gain [R] [R].\nExhaust.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    bloodletting = _card("Bloodletting", "Bloodletting", card_type=CardType.SKILL, cost=0, has_target=False)
    context = _combat_context([bloodletting], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        bloodletting,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 3
    assert result.energy_gained == 2
    assert result.player_hp == 77

    bloodletting_plus = _card(
        "Bloodletting",
        "Bloodletting+",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([bloodletting_plus], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        bloodletting_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 4
    assert result.energy_gained == 3

    offering = _card("Offering", "Offering", card_type=CardType.SKILL, cost=0, has_target=False)
    context = _combat_context([offering], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        offering,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 3
    assert result.energy_gained == 2
    assert result.cards_drawn == 3
    assert result.player_hp == 74

    seeing_red = _card("Seeing Red", "Seeing Red", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([seeing_red], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        seeing_red,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 2
    assert result.energy_gained == 2


def test_disarm_reduces_enemy_strength_and_current_attack_damage():
    disarm = _card(
        "Disarm",
        "Disarm",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    monster = _louse(current_hp=100)
    monster.move_adjusted_damage = 12
    context = _combat_context([disarm], energy=1, monsters=[monster])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        disarm,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["strength"] == -2
    assert result.monsters[0]["move_adjusted_damage"] == 10

    disarm_plus = _card(
        "Disarm",
        "Disarm+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
        upgrades=1,
    )
    monster = _louse(current_hp=100)
    monster.move_adjusted_damage = 12
    context = _combat_context([disarm_plus], energy=1, monsters=[monster])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        disarm_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["strength"] == -3
    assert result.monsters[0]["move_adjusted_damage"] == 9


def test_double_tap_repeats_next_attack_once_or_twice():
    double_tap = _card(
        "Double Tap",
        "Double Tap",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([double_tap, strike], energy=2, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        double_tap,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 12
    assert result.attacks_played == 2

    double_tap_plus = _card(
        "Double Tap",
        "Double Tap+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [double_tap_plus, strike, strike],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    state = simulator.simulate_card_play(
        SimulationState(context),
        double_tap_plus,
        target=None,
        target_index=None,
        context=context,
    )
    state = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 24
    assert result.attacks_played == 4


def test_demon_form_does_not_add_strength_on_the_turn_it_is_played():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([demon_form, strike], energy=4, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        demon_form,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 6


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
