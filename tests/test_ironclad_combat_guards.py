from types import SimpleNamespace

import spirecomm.ai.heuristics.simulation as simulation
import spirecomm.ai.heuristics.combat_ending as combat_ending
import spirecomm.ai.heuristics.ironclad_combat as ironclad_combat
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.ai.heuristics.combat_ending import CombatEndingDetector
from spirecomm.ai.heuristics.simulation import FastCombatSimulator, HeuristicCombatPlanner, SimulationState
from spirecomm.communication.action import PlayCardAction
from spirecomm.data.loader import GameDataLoader, game_data_loader
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


def _green_louse_debuff(current_hp=13):
    return Monster(
        name="Louse",
        monster_id="FuzzyLouseDefensive",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.DEBUFF,
        half_dead=False,
        is_gone=False,
        move_id=4,
        move_adjusted_damage=0,
        move_hits=1,
    )


def _red_slaver(move_id=1, current_hp=48, intent=Intent.ATTACK_DEBUFF):
    return Monster(
        name="Slaver",
        monster_id="SlaverRed",
        max_hp=48,
        current_hp=current_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_adjusted_damage=8,
        move_hits=1,
    )


def _fungi_beast(current_hp=22):
    return Monster(
        name="Fungi Beast",
        monster_id="FungiBeast",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=6,
        move_hits=1,
    )


def _sentry(current_hp=39, move_id=1, intent=Intent.DEBUFF):
    return Monster(
        name="Sentry",
        monster_id="Sentry",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_adjusted_damage=0,
        move_hits=1,
    )


def _gremlin_nob(current_hp=82, move_adjusted_damage=14):
    monster = Monster(
        name="Gremlin Nob",
        monster_id="GremlinNob",
        max_hp=82,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=1,
    )
    monster.powers = [SimpleNamespace(name="Anger", amount=2)]
    return monster


def _lagavulin(
    current_hp=82,
    intent=Intent.ATTACK,
    move_id=0,
    move_adjusted_damage=18,
):
    return Monster(
        name="Lagavulin",
        monster_id="Lagavulin",
        max_hp=109,
        current_hp=current_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_adjusted_damage=move_adjusted_damage,
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


def _slime_boss(
    current_hp=56,
    max_hp=140,
    move_id=3,
    intent=Intent.UNKNOWN,
    move_adjusted_damage=0,
):
    return Monster(
        name="Slime Boss",
        monster_id="Slime_Boss",
        max_hp=max_hp,
        current_hp=current_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=1,
    )


def _acid_slime_l(current_hp=30, max_hp=65):
    return Monster(
        name="Acid Slime (L)",
        monster_id="Acid_Slime_L",
        max_hp=max_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=3,
        move_adjusted_damage=0,
        move_hits=1,
    )


def _hexaghost(current_hp=250):
    return Monster(
        name="Hexaghost",
        monster_id="Hexaghost",
        max_hp=250,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )


def _guardian(current_hp=240, mode_shift=0, thorns=0):
    monster = Monster(
        name="The Guardian",
        monster_id="TheGuardian",
        max_hp=240,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=4,
        move_adjusted_damage=20,
        move_hits=1,
    )
    powers = []
    if mode_shift:
        powers.append(SimpleNamespace(power_name="Mode Shift", amount=mode_shift))
    if thorns:
        powers.append(SimpleNamespace(power_name="Sharp Hide", amount=thorns))
    monster.powers = powers
    return monster


def _champ_transition(current_hp=206):
    return Monster(
        name="The Champ",
        monster_id="Champ",
        max_hp=420,
        current_hp=current_hp,
        block=0,
        intent=Intent.BUFF,
        half_dead=False,
        is_gone=False,
        move_id=7,
        move_adjusted_damage=0,
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


def test_simulation_reads_power_name_field_from_player_powers():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Rage", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.player_block == 3


def test_upgraded_rage_card_id_sets_attack_block_trigger():
    rage_plus = _card(
        "Rage+",
        "Rage+",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([rage_plus, strike], energy=1, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        rage_plus,
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

    assert state.rage_block_per_attack == 5
    assert result.player_block == 5


def test_simulation_tracks_chosen_hex_power_from_player_powers():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Hex", amount=-1)]

    state = SimulationState(context)

    assert state.player_hex == 1


def test_hex_adds_dazed_pollution_for_non_attack_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "defend": {"name": "Defend", "description": "Gain 5 Block."},
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    defend = _card(
        "Defend",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike", "Strike", cost=1)
    context = _combat_context([defend, strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Hex", amount=1)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    skill_result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )
    attack_result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert skill_result.dazed_cards_added == 1
    assert skill_result.status_cards_added == 1
    assert attack_result.dazed_cards_added == 0
    assert attack_result.status_cards_added == 0


def test_hex_status_pollution_is_scored_as_a_cost(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "defend": {"name": "Defend", "description": "Gain 5 Block."},
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    defend = _card(
        "Defend",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    no_hex_context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=100)])
    no_hex_initial = SimulationState(no_hex_context)
    no_hex_result = simulator.simulate_card_play(
        no_hex_initial,
        defend,
        target=None,
        target_index=None,
        context=no_hex_context,
    )
    no_hex_score = simulator.calculate_outcome_score(
        no_hex_initial,
        no_hex_result,
        context=no_hex_context,
    )

    hex_context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=100)])
    hex_context.game.player.powers = [SimpleNamespace(power_name="Hex", amount=1)]
    hex_initial = SimulationState(hex_context)
    hex_result = simulator.simulate_card_play(
        hex_initial,
        defend,
        target=None,
        target_index=None,
        context=hex_context,
    )
    hex_score = simulator.calculate_outcome_score(
        hex_initial,
        hex_result,
        context=hex_context,
    )

    assert hex_score < no_hex_score


def test_outcome_aoe_bonus_treats_counted_upgraded_cleave_as_cleave():
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    counted_cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=False, upgrades=1)
    context = _combat_context(
        [cleave, counted_cleave],
        energy=1,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)
    final_state = initial_state.clone()

    canonical_score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        context=context,
        sequence=[PlayCardAction(card=cleave)],
    )
    counted_score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        context=context,
        sequence=[PlayCardAction(card=counted_cleave)],
    )

    assert counted_score == canonical_score


def test_fungi_beast_death_applies_vulnerable_to_player():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_fungi_beast(current_hp=6), _louse(current_hp=50)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters_killed == 1
    assert result.player_vulnerable == 2
    assert result.player_vulnerable_added == 2


def test_fungi_beast_death_vulnerable_applies_to_same_turn_incoming_damage():
    strike = _card("Strike_R", "Strike", cost=1)
    remaining_attacker = _louse(current_hp=50)
    remaining_attacker.move_adjusted_damage = 10
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_fungi_beast(current_hp=6), remaining_attacker],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)

    result = simulator.simulate_card_play(
        initial_state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert simulator._estimate_incoming_damage(
        result.monsters,
        result.player_vulnerable_added,
    ) == 15


def test_fungi_beast_death_vulnerable_can_make_same_turn_attack_lethal():
    strike = _card("Strike_R", "Strike", cost=1)
    remaining_attacker = _louse(current_hp=50)
    remaining_attacker.move_adjusted_damage = 10
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_fungi_beast(current_hp=6), remaining_attacker],
    )
    context.game.current_hp = 14
    context.player_hp = 14
    context.player_hp_pct = 14 / 80
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)

    result = simulator.simulate_card_play(
        initial_state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    score = simulator.calculate_outcome_score(
        initial_state,
        result,
        context=context,
    )

    assert score == float("-inf")


def test_enemy_status_lookahead_counts_sentry_bolt_dazed_cards():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_sentry(move_id=1), _sentry(move_id=1)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    status = simulator.simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["dazed"] == 4
    assert status["total"] == 4


def test_enemy_status_lookahead_ignores_zero_hp_stale_simulated_monsters():
    context = _combat_context([], energy=0, monsters=[_sentry(move_id=1)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert status["dazed"] == 0
    assert status["total"] == 0


def test_enemy_status_pollution_penalizes_outcome_score():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 1
    simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    initial_state = SimulationState(context)
    final_state = initial_state.clone()

    simulator.simulate_enemy_status_lookahead = lambda *_args, **_kwargs: {
        "total": 2,
        "dazed": 2,
        "burn": 0,
        "slimed": 0,
        "wound": 0,
    }
    polluted_score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        context=context,
    )

    simulator.simulate_enemy_status_lookahead = lambda *_args, **_kwargs: {
        "total": 0,
        "dazed": 0,
        "burn": 0,
        "slimed": 0,
        "wound": 0,
    }
    clean_score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        context=context,
    )

    assert polluted_score < clean_score


def test_gremlin_nob_gains_strength_when_skill_is_simulated():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)

    result = simulator.simulate_card_play(initial_state, defend, context=context)

    assert result.monsters[0]["strength"] == 2
    assert simulator._estimate_incoming_damage(result.monsters) == 16


def test_state_key_distinguishes_monster_strength_changes():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    initial_state = SimulationState(context)
    stronger_state = initial_state.clone()
    stronger_state.monsters[0]["strength"] = 2

    assert initial_state.state_key(context.playable_cards) != stronger_state.state_key(
        context.playable_cards
    )


def test_enemy_lookahead_applies_strength_gain_to_future_attacks(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, turn, _hp_percent):
            move = (
                {"move": {"intent": "BUFF", "strength_gain": 3}}
                if turn == 1
                else {"move": {"intent": "ATTACK", "damage": 6, "hits": 1}}
            )
            return [move]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(9 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_live_champ_transition_buff_resolves_to_anger_despite_live_move_id():
    context = _combat_context([], energy=0, monsters=[_champ_transition()])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    move = simulator._current_monster_move(state.monsters[0])

    assert move["name"] == "Anger"
    assert move["strength_gain"] == 6


def test_champ_transition_buff_uses_multi_turn_lookahead():
    cards = [
        _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False),
        _card("Shrug It Off", "Shrug It Off", card_type=CardType.SKILL, cost=1, has_target=False),
        _card("Second Wind", "Second Wind", card_type=CardType.SKILL, cost=1, has_target=False),
    ]
    context = _combat_context(cards, energy=1, monsters=[_champ_transition()])
    context.turn = 8
    context.game.current_hp = 50
    context.player_hp = 50
    context.player_hp_pct = 50 / 80
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    depth = simulator._get_enemy_lookahead_depth(state, context)
    future_damage = simulator.simulate_enemy_lookahead(
        state,
        context,
        look_ahead=depth,
    )

    assert depth == 2
    assert future_damage >= int(32 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_awakened_lagavulin_attack_is_not_marked_hibernating():
    context = _combat_context([], energy=0, monsters=[_lagavulin()])
    context.turn = 6
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._handle_hibernation(state, state.monsters[0])

    assert not state.monsters[0].get("is_hibernating", False)
    assert state.monsters[0].get("is_awakened", False)


def test_slime_boss_goop_spray_counts_slimed_status_from_effect_text():
    context = _combat_context(
        [],
        energy=0,
        monsters=[
            _slime_boss(
                current_hp=140,
                move_id=0,
                intent=Intent.DEBUFF,
            )
        ],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    status = simulator.simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["slimed"] == 3
    assert status["total"] == 3


def test_feel_no_pain_grants_block_for_exhaust_events(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "true grit": {
            "name": "True Grit",
            "description": "Gain 7 Block.\nExhaust 1 card at random.",
        }
    }
    loader._wiki_data = {
        "true grit": {
            "name": "True Grit",
            "text": "Gain [7|9] #Block.\n#Exhaust 1 card at random.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    true_grit = _card("True Grit", "True Grit", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([true_grit], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        true_grit,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert result.player_block == 10


def test_dark_embrace_draws_for_exhaust_events(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "true grit": {
            "name": "True Grit",
            "description": "Gain 7 Block.\nExhaust 1 card at random.",
        }
    }
    loader._wiki_data = {
        "true grit": {
            "name": "True Grit",
            "text": "Gain [7|9] #Block.\n#Exhaust 1 card at random.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    true_grit = _card("True Grit", "True Grit", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([true_grit], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Dark Embrace", amount=1)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        true_grit,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert result.cards_drawn == 1


def test_metallicize_tracks_end_turn_block_without_body_slam_block(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "metallicize": {
            "name": "Metallicize",
            "description": "At the end of your turn, gain 3 Block.",
        },
        "body slam": {
            "name": "Body Slam",
            "description": "Deal damage equal to your current Block.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    metallicize = _card("Metallicize", "Metallicize", card_type=CardType.POWER, cost=1, has_target=False)
    body_slam = _card("Body Slam", "Body Slam", cost=1)
    context = _combat_context([metallicize, body_slam], energy=2, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        metallicize,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        body_slam,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert state.player_block == 0
    assert state.end_turn_block == 3
    assert result.total_damage_dealt == 0


def test_rupture_gains_strength_once_when_card_loses_hp(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bloodletting": {
            "name": "Bloodletting",
            "description": "Lose 3 HP.\nGain 2 Energy.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    bloodletting = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    context = _combat_context([bloodletting], energy=0, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Rupture", amount=1)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        bloodletting,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_hp == context.game.current_hp - 3
    assert result.player_strength == 1


def test_combust_projects_end_turn_damage_without_immediate_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "combust": {
            "name": "Combust",
            "description": "At the end of your turn, lose 1 HP and deal 5 damage to ALL enemies.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    combust = _card("Combust", "Combust", card_type=CardType.POWER, cost=1, has_target=False)
    context = _combat_context(
        [combust],
        energy=1,
        monsters=[_louse(current_hp=5), _louse(current_hp=5)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        combust,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.total_damage_dealt == 0
    assert state.monsters_killed == 0

    projected = simulator.project_end_turn_effects(state)

    assert projected.player_hp == context.game.current_hp - 1
    assert projected.total_damage_dealt == 10
    assert projected.monsters_killed == 2


def test_end_turn_aoe_ignores_zero_hp_stale_simulated_monsters():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=5), _louse(current_hp=5)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False
    state.end_turn_aoe_damage = 5

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(state)

    assert projected.total_damage_dealt == 5
    assert projected.monsters_killed == 1
    assert projected.monsters[1]["is_gone"] is True


def test_combust_end_turn_hp_loss_triggers_rupture(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "combust": {
            "name": "Combust",
            "description": "At the end of your turn, lose 1 HP and deal 5 damage to ALL enemies.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    combust = _card("Combust", "Combust", card_type=CardType.POWER, cost=1, has_target=False)
    context = _combat_context([combust], energy=1, monsters=[_louse(current_hp=20)])
    context.game.player.powers = [SimpleNamespace(power_name="Rupture", amount=1)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        combust,
        target=None,
        target_index=None,
        context=context,
    )
    projected = simulator.project_end_turn_effects(state)

    assert projected.player_hp == context.game.current_hp - 1
    assert projected.player_strength == 1


def test_outcome_score_counts_combust_end_turn_lethal(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "combust": {
            "name": "Combust",
            "description": "At the end of your turn, lose 1 HP and deal 5 damage to ALL enemies.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    combust = _card("Combust", "Combust", card_type=CardType.POWER, cost=1, has_target=False)
    context = _combat_context([combust], energy=1, monsters=[_louse(current_hp=5)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)
    final_state = simulator.simulate_card_play(
        initial_state,
        combust,
        target=None,
        target_index=None,
        context=context,
    )

    score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        context=context,
        sequence=[PlayCardAction(card=combust)],
    )

    assert score >= simulation.KILL_BONUS


def test_slime_boss_split_materializes_large_slimes_with_inherited_hp():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_slime_boss(current_hp=56)])
    state = SimulationState(context)

    split_state = FastCombatSimulator(SynergyCardEvaluator())._materialize_pending_death_splits(state)

    alive = [monster for monster in split_state.monsters if not monster["is_gone"]]
    assert [monster["name"] for monster in alive] == ["Acid Slime (L)", "Spike Slime (L)"]
    assert [monster["hp"] for monster in alive] == [56, 56]
    assert [monster["max_hp"] for monster in alive] == [56, 56]


def test_ironclad_detects_slime_boss_without_elite_marker():
    context = _combat_context([], energy=0, monsters=[_slime_boss(current_hp=80)])

    assert IroncladCombatPlanner()._detect_elite_type(context) == ironclad_combat.EliteType.SLIME_BOSS


def test_slime_boss_strategy_treats_counted_upgraded_cleave_as_aoe():
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.damage = 8
    counted_cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=False, upgrades=1)
    counted_cleave.damage = 8
    context = _combat_context(
        [cleave, counted_cleave],
        energy=1,
        monsters=[_slime_boss(current_hp=80)],
    )
    planner = IroncladCombatPlanner()

    canonical_score = planner._apply_slime_boss_strategy(
        [PlayCardAction(card=cleave)],
        context,
        0.0,
    )
    counted_score = planner._apply_slime_boss_strategy(
        [PlayCardAction(card=counted_cleave)],
        context,
        0.0,
    )

    assert counted_score == canonical_score


def test_end_turn_projection_materializes_due_slime_boss_split():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_slime_boss(current_hp=56)])
    state = SimulationState(context)

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(state)

    alive = [monster for monster in projected.monsters if not monster["is_gone"]]
    assert [monster["name"] for monster in alive] == ["Acid Slime (L)", "Spike Slime (L)"]
    assert [monster["hp"] for monster in alive] == [56, 56]


def test_large_slime_split_materializes_medium_slime_names_and_threat():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_acid_slime_l(current_hp=30)])
    state = SimulationState(context)

    split_state = FastCombatSimulator(SynergyCardEvaluator())._materialize_pending_death_splits(state)

    alive = [monster for monster in split_state.monsters if not monster["is_gone"]]
    assert [monster["name"] for monster in alive] == ["Acid Slime (M)", "Acid Slime (M)"]
    assert [monster["hp"] for monster in alive] == [30, 30]
    assert all(monster["move_base_damage"] >= 10 for monster in alive)


def test_outcome_score_penalizes_shallow_slime_boss_split():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_slime_boss(current_hp=80)])
    context.turn = 3
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)
    above_split_state = initial_state.clone()
    above_split_state.monsters[0]["hp"] = 71
    above_split_state.total_damage_dealt = 9
    shallow_split_state = initial_state.clone()
    shallow_split_state.monsters[0]["hp"] = 69
    shallow_split_state.total_damage_dealt = 11

    above_split_score = simulator.calculate_outcome_score(
        initial_state,
        above_split_state,
        context=context,
    )
    shallow_split_score = simulator.calculate_outcome_score(
        initial_state,
        shallow_split_state,
        context=context,
    )

    assert shallow_split_score < above_split_score


def test_enemy_lookahead_delays_slime_boss_split_child_threat_until_after_split_turn():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_slime_boss(current_hp=56)])
    context.turn = 4

    simulator = FastCombatSimulator(SynergyCardEvaluator())

    immediate_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    delayed_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert immediate_damage == 0
    assert delayed_damage > 0


def test_enemy_lookahead_handles_monster_damage_ranges():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.turn = 1

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 7


def test_enemy_lookahead_ignores_zero_hp_stale_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert future_damage == 0


def test_enemy_lookahead_applies_negative_monster_strength():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    state.monsters[0]["strength"] = -2

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert future_damage == 5


def test_enemy_weak_reduces_current_incoming_damage_per_hit():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    state = SimulationState(context)
    state.monsters[0]["weak"] = 1

    incoming_damage = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        state.monsters
    )

    assert incoming_damage == 5


def test_enemy_lookahead_applies_monster_weak_per_hit():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    state.monsters[0]["weak"] = 1

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert future_damage == 5


def test_enemy_lookahead_decrements_monster_weak_between_turns():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    state.monsters[0]["weak"] = 1

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        state,
        context,
        look_ahead=2,
    )

    assert future_damage == 10


def test_hexaghost_divider_uses_player_hp_formula_in_lookahead():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_hexaghost()])
    context.turn = 2
    context.game.current_hp = 53
    context.player_hp = 53
    context.player_hp_pct = 53 / 80

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 30


def test_enemy_lookahead_applies_player_vulnerable_per_hit():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_hexaghost()])
    context.turn = 2
    context.game.current_hp = 53
    context.player_hp = 53
    context.player_hp_pct = 53 / 80
    state = SimulationState(context)
    state.player_vulnerable = 1

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert future_damage == 42


def test_big_attack_pattern_handles_monster_damage_ranges():
    assert game_data_loader.get_monster_big_attack_pattern("Louse") == []


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


def test_armaments_upgrade_keeps_same_block_amount(monkeypatch):
    armaments = _card(
        "Armaments",
        "Armaments+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([armaments], energy=3)
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "armaments": {
            "name": "Armaments",
            "description": "Gain 5 Block. Upgrade a card in your hand for the rest of combat.",
        }
    }
    loader._wiki_data = {
        "armaments": {
            "name": "Armaments",
            "text": "Gain 5 #Block.\nUpgrade [1|ALL] cards in your hand for the rest of combat.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        armaments,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 5


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


def test_incoming_damage_estimate_ignores_zero_hp_stale_monsters():
    incoming = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        [
            {
                "name": "Cultist",
                "monster_id": "Cultist",
                "move_id": 1,
                "hp": 0,
                "is_gone": False,
                "intent": "Intent.ATTACK",
                "move_adjusted_damage": 12,
                "move_hits": 1,
                "strength": 0,
                "weak": 0,
            }
        ]
    )

    assert incoming == 0


def test_incoming_damage_estimate_clamps_negative_live_move_damage_to_zero():
    incoming = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        [
            {
                "name": "Spike Slime (M)",
                "monster_id": "SpikeSlime_M",
                "move_id": 2,
                "current_hp": 25,
                "is_gone": False,
                "intent": "Intent.ATTACK",
                "move_adjusted_damage": -3,
                "move_hits": 2,
                "strength": 0,
                "weak": 0,
            }
        ]
    )

    assert incoming == 0


def test_single_target_selection_ignores_zero_hp_stale_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    stale = _louse(current_hp=40)
    live = _louse(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[stale, live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card(
        strike,
        context,
        state,
    )

    assert target is live
    assert target_idx == 1


def test_primary_target_selection_clears_zero_hp_stale_simulated_monster():
    strike = _card("Strike_R", "Strike", cost=1)
    stale = _louse(current_hp=40)
    live = _louse(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[stale, live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False
    state.primary_target = 0

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card(
        strike,
        context,
        state,
    )

    assert target is live
    assert target_idx == 1
    assert state.primary_target is None


def test_v2_single_target_selection_ignores_zero_hp_stale_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    stale = _louse(current_hp=40)
    live = _louse(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[stale, live])
    context.compute_threat_v2 = lambda monster: 1
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        state,
    )

    assert target is live
    assert target_idx == 1


def test_aoe_decision_ignores_zero_hp_stale_simulated_monsters():
    stale = _louse(current_hp=40)
    first_live = _louse(current_hp=40)
    second_live = _louse(current_hp=40)
    context = _combat_context([], monsters=[stale, first_live, second_live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    assert not IroncladCombatPlanner()._should_use_aoe("Cleave", context, state)


def test_rank_targets_ignores_zero_hp_stale_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    stale = _louse(current_hp=40)
    live = _louse(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[stale, live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    ranked = IroncladCombatPlanner()._rank_targets(strike, context, state)

    assert ranked == [(live, 1, ranked[0][2])]


def test_outcome_score_counts_zero_hp_stale_monsters_as_killed():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=7)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)
    final_state = initial_state.clone()
    final_state.monsters[0]["hp"] = 0
    final_state.monsters[0]["is_gone"] = False

    score = simulator.calculate_outcome_score(initial_state, final_state)

    assert score >= simulation.KILL_BONUS + simulation.ALL_LETHAL_BONUS


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


def test_thunderclap_applies_vulnerable_to_all_enemies(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "thunderclap": {
            "name": "Thunderclap",
            "description": "Deal 4 damage and apply 1 Vulnerable to ALL enemies.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    thunderclap = _card("Thunderclap", "Thunderclap", cost=1, has_target=False)
    context = _combat_context(
        [thunderclap],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )
    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        thunderclap,
        target=None,
        target_index=None,
        context=context,
    )

    assert [monster["vulnerable"] for monster in result.monsters] == [1, 1]


def test_simulator_known_aoe_fallback_uses_base_name_for_upgraded_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=False, upgrades=1)
    cleave.damage = 8
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        cleave,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 16
    assert [monster["hp"] for monster in result.monsters] == [22, 22]


def test_pommel_strike_tracks_attack_card_draw(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "pommel strike": {
            "name": "Pommel Strike",
            "description": "Deal 9 damage.\nDraw 1 card.",
        },
    }
    loader._wiki_data = {
        "pommel strike": {
            "name": "Pommel Strike",
            "text": "Deal [9|10] damage.\nDraw [1|2] cards.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    simulator = FastCombatSimulator(SynergyCardEvaluator())
    pommel = _card("Pommel Strike", "Pommel Strike", cost=1)
    context = _combat_context([pommel], energy=1, monsters=[_louse(current_hp=30)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        pommel,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.cards_drawn == 1

    pommel_plus = _card("Pommel Strike", "Pommel Strike+", cost=1, upgrades=1)
    context = _combat_context([pommel_plus], energy=1, monsters=[_louse(current_hp=30)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        pommel_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.cards_drawn == 2


def test_warcry_plus_tracks_upgraded_draw_card_plural_text(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "warcry": {
            "name": "Warcry",
            "description": (
                "Draw 1 card.\n"
                "Put a card from your hand onto the top of your draw pile.\n"
                "Exhaust."
            ),
        },
    }
    loader._wiki_data = {
        "warcry": {
            "name": "Warcry",
            "text": (
                "Draw [1|2] [card|cards].\n"
                "Put a card from your hand onto the top of your draw pile.\n"
                "#Exhaust."
            ),
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    warcry_plus = _card(
        "Warcry",
        "Warcry+",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([warcry_plus], energy=0, monsters=[_louse(current_hp=30)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        warcry_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.cards_drawn == 2
    assert result.exhaust_events == 1


def test_battle_trance_blocks_later_card_draw_this_turn(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "battle trance": {
            "name": "Battle Trance",
            "description": "Draw 3 cards.\nYou cannot draw additional cards this turn.",
        },
        "pommel strike": {
            "name": "Pommel Strike",
            "description": "Deal 9 damage.\nDraw 1 card.",
        },
    }
    loader._wiki_data = {
        "battle trance": {
            "name": "Battle Trance",
            "text": "Draw [3|4] cards.\nYou cannot draw additional cards this turn.",
        },
        "pommel strike": {
            "name": "Pommel Strike",
            "text": "Deal [9|10] damage.\nDraw [1|2] cards.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    battle_trance = _card(
        "Battle Trance",
        "Battle Trance",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    pommel = _card("Pommel Strike", "Pommel Strike", cost=1)
    context = _combat_context(
        [battle_trance, pommel],
        energy=1,
        monsters=[_louse(current_hp=30)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        battle_trance,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        pommel,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert state.cards_drawn == 3
    assert result.cards_drawn == 3

    battle_trance_plus = _card(
        "Battle Trance+1",
        "Battle Trance+1",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [battle_trance_plus, pommel],
        energy=1,
        monsters=[_louse(current_hp=30)],
    )

    state = simulator.simulate_card_play(
        SimulationState(context),
        battle_trance_plus,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        pommel,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert state.cards_drawn == 4
    assert result.cards_drawn == 4


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

    counted_entrench = _card(
        "Entrench+1",
        "Entrench+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([counted_entrench], energy=1, monsters=[_louse(current_hp=100)])
    initial_state = SimulationState(context)
    initial_state.player_block = 12

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        initial_state,
        counted_entrench,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 24


def test_counted_upgraded_block_skill_uses_upgrade_block_value(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "power through": {
            "name": "Power Through",
            "description": "Gain 15 Block.\nAdd 2 Wounds into your hand.",
        }
    }
    loader._wiki_data = {
        "power through": {
            "name": "Power Through",
            "text": "Gain [15|20] #Block.\nAdd 2 #Wounds into your hand.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    power_through = _card(
        "Power Through+1",
        "Power Through+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([power_through], energy=1, monsters=[_louse(current_hp=100)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        power_through,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 20


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

    counted_second_wind = _card(
        "Second Wind+1",
        "Second Wind+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [counted_second_wind, defend, power_through, strike],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        counted_second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 14
    assert result.exhaust_events == 2


def test_second_wind_marks_exhausted_cards_unavailable_for_later_search():
    second_wind = _card(
        "Second Wind",
        "Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    battle_trance = _card(
        "Battle Trance",
        "Battle Trance",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    iron_wave = _card("Iron Wave", "Iron Wave", cost=1)
    second_wind.uuid = "second-wind"
    defend.uuid = "defend"
    battle_trance.uuid = "battle-trance"
    iron_wave.uuid = "iron-wave"
    context = _combat_context(
        [second_wind, defend, battle_trance, iron_wave],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    context.game.hand = [second_wind, defend, battle_trance, iron_wave]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    remaining_cards = simulator._unplayed_hand_cards(result, context, exclude_card=second_wind)
    assert [card.uuid for card in remaining_cards] == ["iron-wave"]
    assert {"defend", "battle-trance"}.issubset(result.played_card_uuids)


def test_state_key_treats_uuid_marked_cards_as_unavailable():
    strike = _card("Strike_R", "Strike", cost=1)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    strike.uuid = "strike-uuid"
    defend.uuid = "defend-uuid"
    context = _combat_context([strike, defend], energy=2, monsters=[_louse(current_hp=100)])
    state = SimulationState(context)
    baseline_key = state.state_key(context.playable_cards)

    state.played_card_uuids.add("strike-uuid")

    played_key = state.state_key(context.playable_cards)
    assert played_key != baseline_key
    assert played_key[2] == ("Defend_R",)


def test_second_wind_exhausting_sentinel_grants_energy():
    second_wind = _card(
        "Second Wind",
        "Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    sentinel = _card(
        "Sentinel",
        "Sentinel",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([second_wind, sentinel, defend], energy=1, monsters=[_louse(current_hp=100)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 2
    assert result.player_energy == 2
    assert result.energy_gained == 2


def test_second_wind_exhausting_counted_upgraded_sentinel_grants_energy():
    second_wind = _card(
        "Second Wind",
        "Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    sentinel = _card(
        "Sentinel+1",
        "Sentinel+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([second_wind, sentinel, defend], energy=1, monsters=[_louse(current_hp=100)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 2
    assert result.player_energy == 3
    assert result.energy_gained == 3


def test_playing_sentinel_does_not_trigger_exhaust_synergy(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "sentinel": {
            "name": "Sentinel",
            "description": "Gain 5 Block. If this card is Exhausted, gain [R] [R].",
        }
    }
    loader._wiki_data = {
        "sentinel": {
            "name": "Sentinel",
            "text": "Gain [5|8] #Block. If this card is #Exhausted, gain [R] [R].",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    sentinel = _card("Sentinel", "Sentinel", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([sentinel], energy=1, monsters=[_louse(current_hp=50)])
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        sentinel,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 0
    assert result.player_block == 5


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


def test_reaper_healing_caps_overkill_damage(monkeypatch):
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
        monsters=[_louse(current_hp=1), _louse(current_hp=1)],
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

    assert result.total_damage_dealt == 2
    assert result.player_hp == 22


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

    counted_heavy_blade_plus = _card("Heavy Blade+1", "Heavy Blade+1", cost=2, upgrades=1)
    context = _combat_context([counted_heavy_blade_plus], energy=2, monsters=[_louse(current_hp=100)])
    context.strength = 3
    result = simulator.simulate_card_play(
        SimulationState(context),
        counted_heavy_blade_plus,
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


def test_fiend_fire_counts_unplayable_hand_cards(monkeypatch):
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

    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    strike = _card("Strike_R", "Strike", cost=1)
    dazed = _card("Dazed", "Dazed", card_type=CardType.STATUS, cost=-2, has_target=False)
    context = _combat_context([fiend_fire, strike], energy=2, monsters=[_louse(current_hp=100)])
    context.game.hand = [fiend_fire, strike, dazed]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        fiend_fire,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 14
    assert result.damage_instances == 2
    assert result.exhaust_events == 3


def test_exhausting_attack_cards_trigger_feel_no_pain(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "reaper": {
            "name": "Reaper",
            "description": "Deal 4 damage to ALL enemies. Heal HP equal to unblocked damage.\nExhaust.",
        },
    }
    loader._wiki_data = {
        "reaper": {
            "name": "Reaper",
            "text": "Deal [4|5] damage to ALL enemies. Heal HP equal to unblocked damage.\n#Exhaust.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    reaper = _card("Reaper", "Reaper", cost=2, has_target=False)
    context = _combat_context([reaper], energy=2, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        reaper,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert result.player_block == 3


def test_fiend_fire_exhausts_hand_and_self_for_feel_no_pain(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust.",
        },
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "#Exhaust your hand.\nDeal [7|10] damage for each card #Exhausted.\n#Exhaust.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    strike = _card("Strike_R", "Strike", cost=1)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([fiend_fire, strike, defend], energy=2, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        fiend_fire,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.exhaust_events == 3
    assert result.player_block == 9


def test_fiend_fire_marks_exhausted_hand_cards_unavailable_for_later_search(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust.",
        },
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "#Exhaust your hand.\nDeal [7|10] damage for each card #Exhausted.\n#Exhaust.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    strike = _card("Strike_R", "Strike", cost=1)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    fiend_fire.uuid = "fiend-fire"
    strike.uuid = "strike"
    defend.uuid = "defend"
    context = _combat_context([fiend_fire, strike, defend], energy=3, monsters=[_louse(current_hp=100)])
    context.game.hand = [fiend_fire, strike, defend]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        fiend_fire,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    remaining_cards = simulator._unplayed_hand_cards(result, context, exclude_card=fiend_fire)
    assert remaining_cards == []
    assert {"strike", "defend"}.issubset(result.played_card_uuids)


def test_sever_soul_exhausts_non_attacks_for_feel_no_pain(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "sever soul": {
            "name": "Sever Soul",
            "description": "Exhaust all non-Attack cards in your hand.\nDeal 16 damage.",
        },
    }
    loader._wiki_data = {
        "sever soul": {
            "name": "Sever Soul",
            "text": "#Exhaust all non-Attack cards in your hand.\nDeal [16|22] damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    sever_soul = _card("Sever Soul", "Sever Soul", cost=2)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [sever_soul, defend, flex, strike],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        sever_soul,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.exhaust_events == 2
    assert result.player_block == 6


def test_sever_soul_marks_exhausted_non_attacks_unavailable_for_later_search(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "sever soul": {
            "name": "Sever Soul",
            "description": "Exhaust all non-Attack cards in your hand.\nDeal 16 damage.",
        },
    }
    loader._wiki_data = {
        "sever soul": {
            "name": "Sever Soul",
            "text": "#Exhaust all non-Attack cards in your hand.\nDeal [16|22] damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    sever_soul = _card("Sever Soul", "Sever Soul", cost=2)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1)
    sever_soul.uuid = "sever-soul"
    defend.uuid = "defend"
    flex.uuid = "flex"
    strike.uuid = "strike"
    context = _combat_context(
        [sever_soul, defend, flex, strike],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    context.game.hand = [sever_soul, defend, flex, strike]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        sever_soul,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    remaining_cards = simulator._unplayed_hand_cards(result, context, exclude_card=sever_soul)
    assert [card.uuid for card in remaining_cards] == ["strike"]
    assert {"defend", "flex"}.issubset(result.played_card_uuids)


def test_second_wind_counts_unplayable_non_attack_cards():
    second_wind = _card("Second Wind", "Second Wind", card_type=CardType.SKILL, cost=1, has_target=False)
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    wound = _card("Wound", "Wound", card_type=CardType.STATUS, cost=-2, has_target=False)
    context = _combat_context([second_wind, defend], energy=1, monsters=[_louse(current_hp=100)])
    context.game.hand = [second_wind, defend, wound]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 10
    assert result.exhaust_events == 2


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


def test_monster_weak_does_not_reduce_player_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.weak_stacks[0] = 2

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 6


def test_player_weak_reduces_player_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 4


def test_player_weak_applies_before_target_vulnerable(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"dropkick": {"name": "Dropkick", "description": "Deal 5 damage."}}
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    context = _combat_context([dropkick], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.vulnerable_stacks[0] = 1

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        dropkick,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 4


def test_ironclad_target_pruning_counts_upgraded_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bash": {
            "name": "Bash",
            "description": "Deal 8 damage. Apply 2 Vulnerable.",
        }
    }
    loader._wiki_data = {
        "bash": {
            "name": "Bash",
            "text": "Deal [8|10] damage.\nApply [2|3] Vulnerable.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    bash_plus = _card("Bash", "Bash+", cost=2, upgrades=1)
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=10)
    context = _combat_context([bash_plus], energy=2, monsters=[high_threat, killable])
    state = SimulationState(context)
    ranked_targets = [(high_threat, 0, 100.0), (killable, 1, 1.0)]

    pruned = IroncladCombatPlanner()._prune_targets(
        bash_plus,
        ranked_targets,
        context,
        state,
    )

    assert [idx for _, idx, _ in pruned] == [1]


def test_ironclad_target_pruning_counts_multi_hit_attack_damage(monkeypatch):
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
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=10)
    context = _combat_context([twin_strike], energy=1, monsters=[high_threat, killable])
    state = SimulationState(context)
    ranked_targets = [(high_threat, 0, 100.0), (killable, 1, 1.0)]

    pruned = IroncladCombatPlanner()._prune_targets(
        twin_strike,
        ranked_targets,
        context,
        state,
    )

    assert [idx for _, idx, _ in pruned] == [1]


def test_shockwave_plus_uses_upgraded_stacks_for_all_debuffs(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "shockwave": {
            "name": "Shockwave",
            "description": "Apply 3 Weak, Vulnerable, and Strength Down to ALL enemies. Exhaust.",
        }
    }
    loader._wiki_data = {
        "shockwave": {
            "name": "Shockwave",
            "text": "Apply [3|5] #Weak, #Vulnerable, and #Strength Down to ALL enemies.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    shockwave_plus = _card(
        "Shockwave",
        "Shockwave+",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [shockwave_plus],
        energy=2,
        monsters=[_louse(current_hp=100), _louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        shockwave_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert [monster["weak"] for monster in result.monsters] == [5, 5]
    assert [monster["vulnerable"] for monster in result.monsters] == [5, 5]
    assert [monster["strength"] for monster in result.monsters] == [-5, -5]
    assert [monster["move_adjusted_damage"] for monster in result.monsters] == [2, 2]

    counted_shockwave = _card(
        "Shockwave+1",
        "Shockwave+1",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [counted_shockwave],
        energy=2,
        monsters=[_louse(current_hp=100), _louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        counted_shockwave,
        target=None,
        target_index=None,
        context=context,
    )

    assert [monster["weak"] for monster in result.monsters] == [5, 5]
    assert [monster["vulnerable"] for monster in result.monsters] == [5, 5]
    assert [monster["strength"] for monster in result.monsters] == [-5, -5]
    assert [monster["move_adjusted_damage"] for monster in result.monsters] == [2, 2]


def test_artifact_blocks_attack_debuff_and_is_consumed(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bash": {
            "name": "Bash",
            "description": "Deal 8 damage.\nApply 2 Vulnerable.",
        }
    }
    loader._wiki_data = {
        "bash": {
            "name": "Bash",
            "text": "Deal [8|10] damage.\nApply [2|3] #Vulnerable.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    bash = _card("Bash", "Bash", cost=2)
    context = _combat_context([bash], energy=2, monsters=[_louse(current_hp=50)])
    context.monsters_alive[0].powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bash,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.monsters[0]["vulnerable"] == 0
    assert result.monsters[0].get("artifact", 0) == 0


def test_artifact_blocks_disarm_strength_down():
    disarm = _card("Disarm", "Disarm", card_type=CardType.SKILL, cost=1)
    context = _combat_context([disarm], energy=1, monsters=[_louse(current_hp=50)])
    context.monsters_alive[0].strength = 5
    context.monsters_alive[0].move_adjusted_damage = 10
    context.monsters_alive[0].powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        disarm,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["strength"] == 5
    assert result.monsters[0]["move_adjusted_damage"] == 10
    assert result.monsters[0].get("artifact", 0) == 0


def test_artifact_blocks_first_debuff_in_card_text_order(monkeypatch):
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
    uppercut = _card("Uppercut", "Uppercut", cost=2)
    context = _combat_context([uppercut], energy=2, monsters=[_louse(current_hp=50)])
    context.monsters_alive[0].powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        uppercut,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["weak"] == 0
    assert result.monsters[0]["vulnerable"] == 1
    assert result.monsters[0].get("artifact", 0) == 0


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

    counted_inflame_plus = _card(
        "Inflame+1",
        "Inflame+1",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([counted_inflame_plus, strike], energy=2, monsters=[_louse(current_hp=100)])
    state = simulator.simulate_card_play(
        SimulationState(context),
        counted_inflame_plus,
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


def test_berserk_applies_self_vulnerable_without_immediate_energy_gain():
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    berserk = _card(
        "Berserk",
        "Berserk",
        card_type=CardType.POWER,
        cost=0,
        has_target=False,
    )
    context = _combat_context([berserk], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        berserk,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_vulnerable == 2
    assert result.player_vulnerable_added == 2
    assert result.player_energy == 1
    assert result.energy_gained == 1

    counted_berserk = _card(
        "Berserk+1",
        "Berserk+1",
        card_type=CardType.POWER,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([counted_berserk], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        counted_berserk,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_vulnerable == 1
    assert result.player_vulnerable_added == 1
    assert result.player_energy == 1
    assert result.energy_gained == 1


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

    counted_flex_plus = _card(
        "Flex+1",
        "Flex+1",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([counted_flex_plus, strike], energy=1, monsters=[_louse(current_hp=100)])
    state = simulator.simulate_card_play(
        SimulationState(context),
        counted_flex_plus,
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

    assert result.total_damage_dealt == 10

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


def test_spot_weakness_ignores_zero_hp_stale_attacking_target():
    spot_weakness = _card(
        "Spot Weakness",
        "Spot Weakness",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    context = _combat_context([spot_weakness], energy=1, monsters=[_louse(current_hp=20)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        spot_weakness,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.player_strength == 0


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

    counted_bloodletting = _card(
        "Bloodletting+1",
        "Bloodletting+1",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([counted_bloodletting], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        counted_bloodletting,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 4
    assert result.energy_gained == 3
    assert result.player_hp == 77

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

    counted_seeing_red = _card(
        "Seeing Red+1",
        "Seeing Red+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([counted_seeing_red], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        counted_seeing_red,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 2
    assert result.energy_gained == 2


def test_wiki_escaped_newline_exhaust_triggers_feel_no_pain(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "seeing red": {
            "name": "Seeing Red",
            "description": "Gain [R] [R].\nExhaust.",
        }
    }
    loader._wiki_data = {
        "seeing red": {
            "name": "Seeing Red",
            "text": "Gain <R> <R>.\\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    seeing_red = _card("Seeing Red", "Seeing Red", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([seeing_red], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        seeing_red,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert result.player_block == 3


def test_limit_break_upgrade_removes_self_exhaust_for_synergies(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "limit break": {
            "name": "Limit Break",
            "description": "Double your Strength.\nExhaust.",
        }
    }
    loader._wiki_data = {
        "limit break": {
            "name": "Limit Break",
            "text": "Double your #Strength. [\\n#Exhaust.|",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    base_limit_break = _card(
        "Limit Break",
        "Limit Break",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context([base_limit_break], energy=1, monsters=[_louse(current_hp=100)])
    context.strength = 2
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]
    result = simulator.simulate_card_play(
        SimulationState(context),
        base_limit_break,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert result.player_block == 3

    upgraded_limit_break = _card(
        "Limit Break",
        "Limit Break+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([upgraded_limit_break], energy=1, monsters=[_louse(current_hp=100)])
    context.strength = 2
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]
    result = simulator.simulate_card_play(
        SimulationState(context),
        upgraded_limit_break,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 0
    assert result.player_block == 0


def test_energy_gain_plain_text_is_not_double_counted(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bloodletting": {
            "name": "Bloodletting",
            "description": "Lose 3 HP.\nGain 2 Energy.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    bloodletting = _card("Bloodletting", "Bloodletting", card_type=CardType.SKILL, cost=0, has_target=False)
    context = _combat_context([bloodletting], energy=0, monsters=[_louse(current_hp=100)])
    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bloodletting,
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

    counted_disarm = _card(
        "Disarm+1",
        "Disarm+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
        upgrades=1,
    )
    monster = _louse(current_hp=100)
    monster.move_adjusted_damage = 12
    context = _combat_context([counted_disarm], energy=1, monsters=[monster])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        counted_disarm,
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

    counted_double_tap = _card(
        "Double Tap+1",
        "Double Tap+1",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [counted_double_tap, strike, strike],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    state = simulator.simulate_card_play(
        SimulationState(context),
        counted_double_tap,
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


def test_corruption_makes_followup_skills_cost_zero(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "defend": {
            "name": "Defend",
            "description": "Gain 5 Block.",
        }
    }
    loader._wiki_data = {
        "defend": {
            "name": "Defend",
            "text": "Gain [5|8] #Block.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    corruption = _card(
        "Corruption",
        "Corruption",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    defend = _card("Defend", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([corruption, defend], energy=3, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        corruption,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_saved == 1
    assert result.player_block == 5
    assert result.exhaust_events == 1

    context = _combat_context([defend], energy=0, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Corruption", amount=1)]
    result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_saved == 1
    assert result.player_block == 5
    assert result.exhaust_events == 1


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


def test_fast_score_aoe_multiplier_ignores_zero_hp_stale_simulated_monsters(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        }
    }
    loader._wiki_data = {
        "cleave": {
            "name": "Cleave",
            "text": "Deal [8|11] damage to ALL enemies.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    stale = _louse(current_hp=30)
    live = _louse(current_hp=30)
    context = _combat_context([cleave], energy=1, monsters=[stale, live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    score = HeuristicCombatPlanner().fast_score_action(cleave, state, context)

    assert score == simulation.FASTSCORE_ATTACK_BONUS + 8 * simulation.FASTSCORE_DAMAGE_MULTIPLIER


def test_lethal_targeting_treats_carnage_as_single_target():
    carnage = _card("Carnage", "Carnage", cost=2)
    context = _combat_context([carnage], energy=2, monsters=[_louse(current_hp=20), _louse(current_hp=20)])

    assert CombatEndingDetector()._can_target_all_monsters(context, affordable_damage=40) is False


def test_lethal_detector_treats_counted_upgraded_cleave_as_aoe(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        }
    }
    loader._wiki_data = {
        "cleave": {
            "name": "Cleave",
            "text": "Deal [8|11] damage to ALL enemies.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=False, upgrades=1)
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=5), _louse(current_hp=5)],
    )

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 11
    assert detector.can_kill_all(context) is True


def test_ironclad_targeting_treats_counted_upgraded_cleave_as_aoe():
    cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=False, upgrades=1)
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    context.compute_threat_v2 = lambda monster: 1
    state = SimulationState(context)
    planner = IroncladCombatPlanner()

    target, target_index = planner._choose_target_for_card(cleave, context, state)
    assert target is None
    assert target_index is None

    target, target_index = planner._choose_target_for_card_v2(cleave, context, state)
    assert target is None
    assert target_index is None


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


def test_beam_search_skips_zero_energy_whirlwind():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=0, monsters=[_louse(current_hp=50)])
    planner = IroncladCombatPlanner()

    assert planner._beam_search_turn(context, [whirlwind], 10, 4) == []


def test_beam_search_skips_zero_energy_whirlwind_in_multi_monster_fight():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context(
        [whirlwind],
        energy=0,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    planner = IroncladCombatPlanner()

    assert planner._beam_search_turn(context, [whirlwind], 10, 4) == []


def test_lethal_detector_counts_whirlwind_damage_without_negative_energy():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=50)])

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 15


def test_lethal_detector_allows_certain_kill_at_critical_hp():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=5)])
    context.game.current_hp = 6
    context.player_hp = 6
    context.player_hp_pct = 6 / 80

    assert CombatEndingDetector().can_kill_all(context) is True


def test_lethal_sequence_uses_multiple_attacks_on_one_monster():
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [strike_1, strike_2],
        energy=2,
        monsters=[_louse(current_hp=10)],
    )

    sequence = CombatEndingDetector().find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["strike-1", "strike-2"]


def test_lethal_detector_counts_vulnerable_damage_on_single_target():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike-vulnerable"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=8)])
    context.vulnerable_stacks[0] = 1

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["strike-vulnerable"]


def test_lethal_detector_applies_vulnerable_rounding_per_attack_hit(monkeypatch):
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
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    sword_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1)
    context = _combat_context([sword_boomerang], energy=1, monsters=[_louse(current_hp=100)])
    context.vulnerable_stacks[0] = 1

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 12


def test_lethal_detector_applies_vulnerable_rounding_per_whirlwind_hit():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=100)])
    context.vulnerable_stacks[0] = 1

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 21


def test_lethal_detector_applies_player_weak_before_target_vulnerable(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"dropkick": {"name": "Dropkick", "description": "Deal 5 damage."}}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    context = _combat_context([dropkick], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.vulnerable_stacks[0] = 1

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 4


def test_lethal_detector_counts_perfected_strike_deck_scaling(monkeypatch):
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
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    perfected_strike = _card("Perfected Strike", "Perfected Strike+", cost=2, upgrades=1)
    perfected_strike.uuid = "perfected-strike"
    context = _combat_context(
        [perfected_strike],
        energy=2,
        monsters=[_louse(current_hp=16)],
    )
    context.game.deck = [
        _card("Strike_R", "Strike"),
        _card("Strike_R", "Strike"),
        _card("Twin Strike", "Twin Strike"),
        _card("Perfected Strike", "Perfected Strike"),
    ]

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 18
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["perfected-strike"]


def test_lethal_detector_counts_repeated_searing_blow_upgrades(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "searing blow": {
            "name": "Searing Blow",
            "description": "Deal 12 damage. Can be Upgraded any number of times.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    searing_blow = _card("Searing Blow", "Searing Blow+2", cost=2, upgrades=2)
    context = _combat_context([searing_blow], energy=2, monsters=[_louse(current_hp=100)])

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 21


def test_lethal_detector_counts_multi_hit_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "twin strike": {
            "name": "Twin Strike",
            "description": "Deal 5 damage twice.",
        },
        "sword boomerang": {
            "name": "Sword Boomerang",
            "description": "Deal 3 damage to a random enemy 3 times.",
        },
    }
    loader._wiki_data = {
        "twin strike": {
            "name": "Twin Strike",
            "text": "Deal [5|7] damage twice.",
        },
        "sword boomerang": {
            "name": "Sword Boomerang",
            "text": "Deal 3 damage to a random enemy [3|4] times.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    sword_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1)
    context = _combat_context(
        [twin_strike, sword_boomerang],
        energy=2,
        monsters=[_louse(current_hp=17)],
    )

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 19


def test_lethal_detector_counts_fiend_fire_exhausted_hand_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Deal 7 damage. Exhaust your hand.",
        }
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "Deal [7|10] damage. Exhaust your hand.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    fiend_fire.uuid = "fiend-fire"
    other_cards = [
        _card("Second Wind", "Second Wind", card_type=CardType.SKILL, cost=0),
        _card("Strike_R", "Strike", cost=1),
        _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1),
        _card("Pommel Strike", "Pommel Strike", cost=1),
    ]
    cards = [fiend_fire, *other_cards]
    context = _combat_context(cards, energy=2, monsters=[_louse(current_hp=36)])
    context.strength = 3
    context.game.hand = cards

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 40
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["fiend-fire"]


def test_lethal_detector_counts_upgraded_static_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bash": {
            "name": "Bash",
            "description": "Deal 8 damage. Apply 2 Vulnerable.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "bash": {
            "name": "Bash",
            "text": "Deal [8|10] damage.\nApply [2|3] Vulnerable.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bash = _card("Bash", "Bash+", cost=2, upgrades=1)
    bash.uuid = "bash-plus"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([bash, strike], energy=3, monsters=[_louse(current_hp=14)])

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["bash-plus", "strike"]


def test_lethal_detector_counts_heavy_blade_strength_multiplier(monkeypatch):
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
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    heavy_blade = _card("Heavy Blade", "Heavy Blade+", cost=2, upgrades=1)
    context = _combat_context(
        [heavy_blade],
        energy=2,
        monsters=[_louse(current_hp=26)],
    )
    context.strength = 3

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 29
    assert detector.can_kill_all(context) is True


def test_thorns_deals_full_stack_damage_per_attack_hit():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.thorns_stacks = {0: 3}

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.player_hp == 77


def test_thorns_triggers_on_killing_attack_hit():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=1)])
    context.thorns_stacks = {0: 3}

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters_killed == 1
    assert result.player_hp == 77


def test_guardian_mode_shift_power_is_tracked_in_simulation_state():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_guardian(mode_shift=12)],
    )

    state = SimulationState(context)

    assert state.monsters[0]["mode_shift"] == 12


def test_guardian_mode_shift_adds_block_and_sharp_hide_after_threshold():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_guardian(mode_shift=5)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["hp"] == 234
    assert result.monsters[0]["mode_shift"] == 0
    assert result.monsters[0]["block"] == 20
    assert result.monsters[0]["thorns"] == 3
    assert result.player_hp == 80


def test_guardian_sharp_hide_applies_to_attacks_after_mode_shift_trigger():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=2,
        monsters=[_guardian(mode_shift=5)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    first = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    first.player_energy = 1
    second = simulator.simulate_card_play(
        first,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert second.player_hp == 77
    assert second.monsters[0]["block"] == 14


def test_state_key_distinguishes_guardian_mode_shift_and_thorns():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_guardian(mode_shift=5)],
    )
    state = SimulationState(context)
    before_shift_key = state.state_key(context.playable_cards)

    state.monsters[0]["mode_shift"] = 0
    state.monsters[0]["thorns"] = 3

    assert state.state_key(context.playable_cards) != before_shift_key


def test_ironclad_sequence_aoe_bonus_treats_counted_upgraded_cleave_as_cleave():
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    counted_cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=False, upgrades=1)
    context = _combat_context(
        [cleave, counted_cleave],
        energy=1,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    initial_state = SimulationState(context)
    final_state = initial_state.clone()

    canonical_score = planner._score_sequence(
        [PlayCardAction(card=cleave)],
        initial_state,
        final_state,
        context,
    )
    counted_score = planner._score_sequence(
        [PlayCardAction(card=counted_cleave)],
        initial_state,
        final_state,
        context,
    )

    assert counted_score == canonical_score


def test_ironclad_sequence_strategic_bonus_treats_counted_upgraded_whirlwind_as_whirlwind():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    counted_whirlwind = _card(
        "Whirlwind+1",
        "Whirlwind+1",
        cost=-1,
        cost_for_turn=-1,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [whirlwind, counted_whirlwind],
        energy=3,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    initial_state = SimulationState(context)
    final_state = initial_state.clone()
    final_state.energy_spent = 3

    canonical_score = planner._score_sequence(
        [PlayCardAction(card=whirlwind)],
        initial_state,
        final_state,
        context,
    )
    counted_score = planner._score_sequence(
        [PlayCardAction(card=counted_whirlwind)],
        initial_state,
        final_state,
        context,
    )

    assert counted_score == canonical_score


def test_ironclad_sequence_bash_followup_bonus_ignores_upgraded_bash_as_big_attack():
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    bash.damage = 8
    counted_bash = _card("Bash+1", "Bash+1", cost=2, upgrades=1)
    counted_bash.uuid = "counted-bash"
    counted_bash.damage = 12
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    solo_context = _combat_context([bash], energy=2, monsters=[_louse(current_hp=100)])
    solo_initial = SimulationState(solo_context)
    solo_score = planner._score_sequence(
        [PlayCardAction(card=bash)],
        solo_initial,
        solo_initial.clone(),
        solo_context,
    )

    extra_bash_context = _combat_context(
        [bash, counted_bash],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    extra_bash_initial = SimulationState(extra_bash_context)
    extra_bash_score = planner._score_sequence(
        [PlayCardAction(card=bash)],
        extra_bash_initial,
        extra_bash_initial.clone(),
        extra_bash_context,
    )

    assert extra_bash_score == solo_score


def test_target_exploration_ignores_counted_upgraded_aoe_target_flag():
    counted_cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=True, upgrades=1)
    context = _combat_context(
        [counted_cleave],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    should_explore = IroncladCombatPlanner()._should_explore_targets(context, elapsed_time=0)

    assert should_explore is False


def test_beam_search_does_not_set_primary_target_for_counted_upgraded_aoe():
    counted_cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=True, upgrades=1)
    strike = _card("Strike_R", "Strike", cost=1, has_target=True)
    monsters = [_louse(current_hp=30), _louse(current_hp=30)]
    context = _combat_context([counted_cleave, strike], energy=2, monsters=monsters)
    planner = IroncladCombatPlanner()
    cleave_primary_targets = []

    def rank_targets(_card, _context, _state):
        return [(monsters[0], 0, 10), (monsters[1], 1, 9)]

    def simulate(state, _card, _target, _target_idx, context=None):
        return state.clone()

    def score(sequence, _initial_state, final_state, _context):
        if len(sequence) == 1 and sequence[0].card is counted_cleave:
            cleave_primary_targets.append(final_state.primary_target)
        return len(sequence)

    planner._rank_targets = rank_targets
    planner._prune_targets = lambda _card, ranked_targets, _context, _state: ranked_targets
    planner.simulator.simulate_card_play = simulate
    planner._score_sequence = score

    planner._beam_search_turn(context, [counted_cleave, strike], beam_width=10, max_depth=1)

    assert cleave_primary_targets
    assert all(primary_target is None for primary_target in cleave_primary_targets)


def test_ironclad_fallback_priority_treats_counted_upgraded_demon_form_as_demon_form():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    counted_demon_form = _card(
        "Demon Form+1",
        "Demon Form+1",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [demon_form, counted_demon_form],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    planner = IroncladCombatPlanner()

    canonical_priority = planner._get_card_priority(demon_form, context)
    counted_priority = planner._get_card_priority(counted_demon_form, context)

    assert counted_priority == canonical_priority


def test_ironclad_fallback_priority_values_bash_before_big_attacks():
    bash = _card("Bash+1", "Bash+1", cost=2, upgrades=1)
    carnage = _card("Carnage", "Carnage", cost=2)
    carnage.damage = 20
    context = _combat_context(
        [bash, carnage],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )

    assert IroncladCombatPlanner()._get_card_priority(bash, context) == 850


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


def test_live_red_slaver_id_resolves_scrape_not_blue_rake():
    context = _combat_context([], monsters=[_red_slaver()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    state = SimulationState(context)

    move = simulator._current_monster_move(state.monsters[0])
    debuffs = simulator._extract_move_debuffs(move)

    assert move["name"] == "Scrape"
    assert debuffs["vulnerable"] == 1
    assert debuffs["weak"] == 0


def test_live_green_louse_id_resolves_spit_web_despite_live_move_id():
    context = _combat_context([], monsters=[_green_louse_debuff()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    state = SimulationState(context)

    move = simulator._current_monster_move(state.monsters[0])
    debuffs = simulator._extract_move_debuffs(move)

    assert move["name"] == "Spit Web"
    assert debuffs["weak"] == 2


def test_live_spheric_guardian_defend_intent_overrides_mismatched_move_id():
    spheric_guardian = Monster(
        name="Spheric Guardian",
        monster_id="SphericGuardian",
        max_hp=20,
        current_hp=20,
        block=40,
        intent=Intent.DEFEND,
        half_dead=False,
        is_gone=False,
        move_id=2,
        move_adjusted_damage=0,
        move_hits=1,
    )
    context = _combat_context([], monsters=[spheric_guardian])
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    state = SimulationState(context)

    move = simulator._current_monster_move(state.monsters[0])
    damage = simulator.simulate_enemy_lookahead(state, context, look_ahead=1)

    assert move["name"] == "Activate"
    assert damage == 0
