from types import SimpleNamespace

import spirecomm.ai.heuristics.simulation as simulation
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.ai.heuristics.combat_ending import CombatEndingDetector
from spirecomm.ai.heuristics.simulation import FastCombatSimulator, SimulationState
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
