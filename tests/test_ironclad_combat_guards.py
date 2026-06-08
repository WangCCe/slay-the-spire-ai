from types import SimpleNamespace

import spirecomm.ai.heuristics.simulation as simulation
import spirecomm.ai.heuristics.combat_ending as combat_ending
import spirecomm.ai.heuristics.ironclad_combat as ironclad_combat
import spirecomm.data.loader as data_loader_module
from spirecomm.ai.heuristics.enhanced_monster_database import EnhancedMonsterDatabase
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


def test_ironclad_plan_turn_accepts_string_player_hp_pct_in_opening_log():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.player_hp_pct = "0.5"
    planner = IroncladCombatPlanner()
    planner.combat_ending_detector.can_kill_all = lambda _context: False
    planner.timing_classifier.classify_turn = lambda _context: SimpleNamespace(
        turn_timing=SimpleNamespace(value="safe"),
        current_damage=0,
        future_damage_curve=[],
        safe_windows=[],
    )
    planner.balance_strategy.get_balance_weights = lambda *_args: SimpleNamespace(
        damage_weight=1.0,
        block_weight=1.0,
        kill_bonus=0.0,
    )
    planner._get_adaptive_parameters = lambda *_args: (1, 1)
    planner._beam_search_turn = lambda *_args: []

    assert planner.plan_turn(context) == []


def test_heuristic_plan_turn_accepts_string_energy_available():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    context = _combat_context([strike], energy="4", monsters=[_louse(current_hp=50)])
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    planner._simple_plan = lambda _context: []

    assert planner.plan_turn(context) == []
    assert planner.max_depth >= 1


def test_heuristic_plan_turn_accepts_string_act():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    context = _combat_context([strike], energy=3, monsters=[_louse(current_hp=50)])
    context.act = "1"
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    planner._simple_plan = lambda _context: []

    assert planner.plan_turn(context) == []
    assert planner.beam_width >= 1


def test_heuristic_plan_turn_rejects_nonfinite_energy_and_act():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    context = _combat_context([strike], energy=float("inf"), monsters=[_louse(current_hp=50)])
    context.act = float("inf")
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    planner._simple_plan = lambda _context: []

    assert planner.plan_turn(context) == []
    assert planner.beam_width == simulation.BEAM_WIDTH_ACT1
    assert planner.max_depth == 1


def test_heuristic_incoming_damage_rejects_nonfinite_move_hits():
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    monster = _louse(current_hp=50)
    monster.move_hits = float("inf")
    context = _combat_context([], energy=0, monsters=[monster])
    context.game.monsters = [monster]

    assert planner._get_incoming_damage(context) == 7


def test_heuristic_unknown_intent_fallback_rejects_nonfinite_act():
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    monster = Monster(
        name="Unknown Beast",
        monster_id="UnknownBeast",
        max_hp=30,
        current_hp=30,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=None,
        move_hits=1,
    )
    context = _combat_context([], energy=0, monsters=[monster])
    context.game.monsters = [monster]
    context.act = float("inf")

    assert planner._get_incoming_damage(context) == 5


def test_heuristic_get_confidence_accepts_string_energy_available():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    string_strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    enum_context = _combat_context([strike], energy=3, monsters=[_louse(current_hp=50)])
    enum_confidence = planner.get_confidence(enum_context)

    string_context = _combat_context([string_strike], energy="3", monsters=[_louse(current_hp=50)])
    string_confidence = planner.get_confidence(string_context)

    assert string_confidence == enum_confidence


def test_ironclad_get_confidence_accepts_string_player_hp_pct():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    string_strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    planner = IroncladCombatPlanner()
    planner.combat_ending_detector.can_kill_all = lambda _context: False

    enum_context = _combat_context([strike], energy=3, monsters=[_louse(current_hp=50)])
    enum_context.player_hp_pct = 0.8
    enum_confidence = planner.get_confidence(enum_context)

    string_context = _combat_context([string_strike], energy=3, monsters=[_louse(current_hp=50)])
    string_context.player_hp_pct = "0.8"
    string_confidence = planner.get_confidence(string_context)

    assert string_confidence == enum_confidence


def test_ironclad_get_confidence_accepts_string_energy_available():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    string_strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    planner = IroncladCombatPlanner()
    planner.combat_ending_detector.can_kill_all = lambda _context: False

    enum_context = _combat_context([strike], energy=3, monsters=[_louse(current_hp=50)])
    enum_confidence = planner.get_confidence(enum_context)

    string_context = _combat_context([string_strike], energy="3", monsters=[_louse(current_hp=50)])
    string_confidence = planner.get_confidence(string_context)

    assert string_confidence == enum_confidence


def test_ironclad_get_confidence_accepts_string_act():
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    string_strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        is_playable=True,
    )
    planner = IroncladCombatPlanner()
    planner.combat_ending_detector.can_kill_all = lambda _context: False

    enum_context = _combat_context([strike], energy=3, monsters=[_louse(current_hp=50)])
    enum_context.act = 1
    enum_confidence = planner.get_confidence(enum_context)

    string_context = _combat_context([string_strike], energy=3, monsters=[_louse(current_hp=50)])
    string_context.act = "1"
    string_confidence = planner.get_confidence(string_context)

    assert string_confidence == enum_confidence


def test_ironclad_card_priority_accepts_string_incoming_damage_for_defense():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    string_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    planner = IroncladCombatPlanner()

    enum_context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=50)])
    enum_context.incoming_damage = 70
    enum_score = planner._get_card_priority(defend, enum_context)

    string_context = _combat_context([string_defend], energy=1, monsters=[_louse(current_hp=50)])
    string_context.incoming_damage = "70"
    string_score = planner._get_card_priority(string_defend, string_context)

    assert string_score == enum_score


def test_ironclad_card_priority_accepts_string_turn_for_power_cards():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    string_demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    planner = IroncladCombatPlanner()

    enum_context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=50)])
    enum_context.turn = 2
    enum_score = planner._get_card_priority(demon_form, enum_context)

    string_context = _combat_context([string_demon_form], energy=3, monsters=[_louse(current_hp=50)])
    string_context.turn = "2"
    string_score = planner._get_card_priority(string_demon_form, string_context)

    assert string_score == enum_score


def test_ironclad_card_priority_rejects_nonfinite_incoming_damage_for_defense():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    baseline_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    planner = IroncladCombatPlanner()

    baseline_context = _combat_context([baseline_defend], energy=1, monsters=[_louse(current_hp=50)])
    baseline_context.incoming_damage = 0
    baseline_score = planner._get_card_priority(baseline_defend, baseline_context)

    nonfinite_context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=50)])
    nonfinite_context.incoming_damage = float("inf")
    nonfinite_score = planner._get_card_priority(defend, nonfinite_context)

    assert nonfinite_score == baseline_score


def test_ironclad_card_priority_rejects_nonfinite_turn_for_power_cards():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    baseline_demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    planner = IroncladCombatPlanner()

    baseline_context = _combat_context([baseline_demon_form], energy=3, monsters=[_louse(current_hp=50)])
    baseline_context.turn = 1
    baseline_score = planner._get_card_priority(baseline_demon_form, baseline_context)

    nonfinite_context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=50)])
    nonfinite_context.turn = float("inf")
    nonfinite_score = planner._get_card_priority(demon_form, nonfinite_context)

    assert nonfinite_score == baseline_score


def test_ironclad_context_ascension_level_rejects_nonfinite_game_value():
    context = SimpleNamespace(game=SimpleNamespace(ascension_level=float("inf")))

    assert IroncladCombatPlanner._context_ascension_level(context) == 0


def test_ironclad_get_confidence_rejects_nonfinite_numeric_context():
    strike = _card("Strike_R", "Strike", cost=1)
    baseline_strike = _card("Strike_R", "Strike", cost=1)
    planner = IroncladCombatPlanner()
    planner.combat_ending_detector.can_kill_all = lambda _context: False

    baseline_context = _combat_context([baseline_strike], energy=0, monsters=[_louse(current_hp=50)])
    baseline_context.player_hp_pct = 0
    baseline_context.act = 0
    baseline_confidence = planner.get_confidence(baseline_context)

    nonfinite_context = _combat_context([strike], energy=float("inf"), monsters=[_louse(current_hp=50)])
    nonfinite_context.player_hp_pct = float("inf")
    nonfinite_context.act = float("inf")
    nonfinite_confidence = planner.get_confidence(nonfinite_context)

    assert nonfinite_confidence == baseline_confidence


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


def _cultist_ritual(current_hp=50, ritual=0, intent=Intent.BUFF, move_id=0):
    monster = Monster(
        name="Cultist",
        monster_id="Cultist",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_adjusted_damage=6 if intent == Intent.ATTACK else 0,
        move_hits=1,
    )
    monster.powers = []
    if ritual:
        monster.powers.append(SimpleNamespace(power_name="Ritual", amount=ritual))
    return monster


def _chosen_hex(current_hp=99):
    return Monster(
        name="Chosen",
        monster_id="Chosen",
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


def _snecko_confused(current_hp=120):
    return Monster(
        name="Snecko",
        monster_id="Snecko",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.DEBUFF,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=0,
        move_hits=1,
    )


def _time_eater_head_slam(current_hp=456, damage=26):
    return Monster(
        name="Time Eater",
        monster_id="TimeEater",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK_DEBUFF,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=damage,
        move_hits=1,
    )


def _time_eater_haste(current_hp=200, max_hp=456):
    return Monster(
        name="Time Eater",
        monster_id="TimeEater",
        max_hp=max_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.BUFF,
        half_dead=False,
        is_gone=False,
        move_id=3,
        move_adjusted_damage=0,
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


def _mad_gremlin(current_hp=22, move_adjusted_damage=4):
    monster = Monster(
        name="Mad Gremlin",
        monster_id="GremlinWarrior",
        max_hp=22,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_base_damage=4,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=1,
    )
    monster.powers = [SimpleNamespace(name="Angry", amount=1)]
    return monster


def _byrd(current_hp=30, flight=3):
    monster = Monster(
        name="Byrd",
        monster_id="Byrd",
        max_hp=30,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=12,
        move_hits=1,
    )
    monster.powers = [SimpleNamespace(power_name="Flight", amount=flight)]
    return monster


def _nemesis(current_hp=185, intangible=0):
    monster = Monster(
        name="Nemesis",
        monster_id="Nemesis",
        max_hp=185,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=2,
        move_adjusted_damage=45,
        move_hits=1,
    )
    monster.powers = []
    if intangible:
        monster.powers.append(SimpleNamespace(power_name="Intangible", amount=intangible))
    return monster


def _giant_head(current_hp=500, slow=0):
    monster = Monster(
        name="Giant Head",
        monster_id="GiantHead",
        max_hp=500,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=13,
        move_hits=1,
    )
    monster.powers = [SimpleNamespace(power_name="Slow", amount=slow)]
    return monster


def _darkling(current_hp=48):
    return Monster(
        name="Darkling",
        monster_id="Darkling",
        max_hp=48,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=9,
        move_hits=1,
    )


def _collector_spawn(current_hp=260):
    return Monster(
        name="The Collector",
        monster_id="TheCollector",
        max_hp=current_hp,
        current_hp=current_hp,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=-1,
        move_hits=1,
    )


def _orb_walker(current_hp=96, move_id=0, move_adjusted_damage=10):
    return Monster(
        name="Orb Walker",
        monster_id="OrbWalker",
        max_hp=96,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_base_damage=move_adjusted_damage,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=1,
    )


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


def _exploder_explode(current_hp=30):
    return Monster(
        name="Exploder",
        monster_id="Exploder",
        max_hp=30,
        current_hp=current_hp,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )


def _transient_attack(current_hp=999, move_adjusted_damage=50):
    monster = Monster(
        name="Transient",
        monster_id="Transient",
        max_hp=999,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=1,
    )
    monster.move_base_damage = move_adjusted_damage
    return monster


def _spire_growth_constrict(current_hp=180):
    return Monster(
        name="Spire Growth",
        monster_id="SpireGrowth",
        max_hp=180,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK_DEBUFF,
        half_dead=False,
        is_gone=False,
        move_id=2,
        move_adjusted_damage=10,
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


def _bronze_automaton(current_hp=260):
    return Monster(
        name="Automaton",
        monster_id="BronzeAutomaton",
        max_hp=300,
        current_hp=current_hp,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=14,
        move_hits=1,
    )


def _bronze_orb(current_hp=52, intent=Intent.DEBUFF, move_id=0, move_adjusted_damage=0):
    return Monster(
        name="Orb",
        monster_id="BronzeOrb",
        max_hp=52,
        current_hp=current_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        move_id=move_id,
        move_adjusted_damage=move_adjusted_damage,
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


def test_simulation_duplication_power_defend_applies_block_twice():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend.block = 5
    context = _combat_context([defend], energy=3, monsters=[_louse(current_hp=50)])
    context.game.player.powers = [
        SimpleNamespace(power_id="DuplicationPower", power_name="Duplication", amount=1)
    ]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 2
    assert result.player_block == 10


def test_simulation_panache_triggers_aoe_on_fifth_card_play():
    anger = _card("Anger", "Anger", cost=0)
    anger.damage = 6
    first = _louse(current_hp=20)
    second = _louse(current_hp=15)
    context = _combat_context([anger], energy=0, monsters=[first, second])
    context.game.player.powers = [
        SimpleNamespace(power_id="Panache", power_name="Panache", amount=1)
    ]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        anger,
        target=first,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 26
    assert result.monsters[0]["hp"] == 4
    assert result.monsters[1]["hp"] == 5
    assert result.panache_counter == 5


def test_blue_candle_curse_play_loses_one_hp_without_spending_block():
    parasite = _card(
        "Parasite",
        "Parasite",
        card_type=CardType.CURSE,
        cost=0,
        has_target=False,
    )
    context = _combat_context([parasite], energy=2, monsters=[_louse(current_hp=50)])
    context.game.relics = [
        SimpleNamespace(relic_id="Blue Candle", name="Blue Candle"),
    ]
    context.game.current_hp = 80
    context.player_hp = 80
    context.game.player.block = 8

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        parasite,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_hp == 79
    assert result.player_block == 8
    assert result.player_energy == 2


def test_bandage_up_heals_and_caps_at_max_hp_in_fast_simulation():
    bandage_up = _card(
        "Bandage Up",
        "Bandage Up",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    context = _combat_context([bandage_up], energy=0, monsters=[_louse(current_hp=50)])
    context.game.current_hp = 78
    context.player_hp = 78
    context.game.max_hp = 80

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bandage_up,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_hp == 80


def test_bandage_up_plus_heals_six_in_fast_simulation():
    bandage_up_plus = _card(
        "Bandage Up",
        "Bandage Up+",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context(
        [bandage_up_plus],
        energy=0,
        monsters=[_louse(current_hp=50)],
    )
    context.game.current_hp = 45
    context.player_hp = 45
    context.game.max_hp = 80

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bandage_up_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_hp == 51


def test_simulate_card_play_applies_string_attack_type_damage():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    strike.damage = 6
    target = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[target])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_spent == 1
    assert result.total_damage_dealt == 6


def test_simulate_card_play_accepts_string_damage_attribute():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = "6"
    target = _louse(current_hp=20)
    context = _combat_context([strike], energy=1, monsters=[target])
    context.strength = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_spent == 1
    assert result.total_damage_dealt == 8


def test_simulate_card_play_combines_player_weak_and_target_vulnerable_before_rounding():
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.damage = 5
    target = _louse(current_hp=20)
    context = _combat_context([dropkick], energy=1, monsters=[target])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.vulnerable_stacks[0] = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        dropkick,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 5


def test_simulate_card_play_applies_paper_phrog_vulnerable_multiplier():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    target = _louse(current_hp=20)
    context = _combat_context([strike], energy=1, monsters=[target])
    context.vulnerable_stacks[0] = 1
    context.game.relics = [SimpleNamespace(relic_id="Paper Phrog", name="Paper Phrog")]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 10


def test_simulate_card_play_applies_pen_nib_before_target_vulnerable():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    target = _louse(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[target])
    context.vulnerable_stacks[0] = 1
    context.game.relics = [SimpleNamespace(relic_id="Pen Nib", name="Pen Nib", counter=9)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 18
    assert result.pen_nib_counter == 0


def test_simulate_card_play_nunchaku_counter_nine_refunds_energy():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    target = _louse(current_hp=20)
    context = _combat_context([strike], energy=1, monsters=[target])
    context.game.relics = [SimpleNamespace(relic_id="Nunchaku", name="Nunchaku", counter=9)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 6
    assert result.player_energy == 1
    assert result.energy_gained == 1
    assert result.nunchaku_counter == 0


def test_fallback_attack_estimate_combines_player_weak_and_target_vulnerable_before_rounding():
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.damage = 5
    target = _louse(current_hp=20)
    context = _combat_context([dropkick], energy=1, monsters=[target])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.vulnerable_stacks[0] = 1

    damage = HeuristicCombatPlanner()._estimate_attack_damage_without_simulation(
        dropkick,
        context,
        target=target,
    )

    assert damage == 5


def test_fallback_attack_estimate_applies_paper_phrog_vulnerable_multiplier():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    target = _louse(current_hp=20)
    context = _combat_context([strike], energy=1, monsters=[target])
    context.vulnerable_stacks[0] = 1
    context.game.relics = [SimpleNamespace(relic_id="Paper Phrog", name="Paper Phrog")]

    damage = HeuristicCombatPlanner()._estimate_attack_damage_without_simulation(
        strike,
        context,
        target=target,
    )

    assert damage == 10


def test_fallback_attack_estimate_applies_pen_nib_before_player_weak():
    blood_for_blood = _card("Blood for Blood", "Blood for Blood+", cost=1, upgrades=1)
    blood_for_blood.damage = 22
    target = _louse(current_hp=60)
    context = _combat_context([blood_for_blood], energy=1, monsters=[target])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.game.relics = [SimpleNamespace(relic_id="Pen Nib", name="Pen Nib", counter=9)]
    state = SimulationState(context)

    damage = HeuristicCombatPlanner()._estimate_attack_damage_without_simulation(
        blood_for_blood,
        context,
        state=state,
        target=target,
    )

    assert damage == 33
    assert state.pen_nib_counter == 9


def test_ironclad_fallback_attack_estimate_counts_upgraded_static_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "headbutt": {
            "name": "Headbutt",
            "type": "ATTACK",
            "cost": 1,
            "description": "Deal 9 damage. Put a card from your discard pile on top of your draw pile.",
        },
    }
    loader._wiki_data = {
        "headbutt": {
            "name": "Headbutt",
            "text": "Deal [9|12] damage.\nPut a card from your discard pile on top of your draw pile.",
        },
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    headbutt_plus = _card("Headbutt", "Headbutt+", cost=1, upgrades=1)
    context = _combat_context([headbutt_plus], energy=1, monsters=[_louse(current_hp=50)])
    planner = IroncladCombatPlanner()

    assert planner._estimate_attack_damage_without_simulation(headbutt_plus, context) == 12
    assert planner._is_big_attack_followup(headbutt_plus, context) is True


def test_ironclad_fallback_attack_estimate_reduces_upgraded_damage_while_weak(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "headbutt": {
            "name": "Headbutt",
            "type": "ATTACK",
            "cost": 1,
            "description": "Deal 9 damage. Put a card from your discard pile on top of your draw pile.",
        },
    }
    loader._wiki_data = {
        "headbutt": {
            "name": "Headbutt",
            "text": "Deal [9|12] damage.\nPut a card from your discard pile on top of your draw pile.",
        },
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    headbutt_plus = _card("Headbutt", "Headbutt+", cost=1, upgrades=1)
    context = _combat_context([headbutt_plus], energy=1, monsters=[_louse(current_hp=50)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    planner = IroncladCombatPlanner()

    assert planner._estimate_attack_damage_without_simulation(headbutt_plus, context) == 9
    assert planner._is_big_attack_followup(headbutt_plus, context) is False


def test_ironclad_fallback_attack_estimate_applies_weak_per_hit(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "pummel": {
            "name": "Pummel",
            "type": "ATTACK",
            "cost": 1,
            "description": "Deal 2 damage 4 times.",
        },
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    pummel = _card("Pummel", "Pummel", cost=1)
    pummel.damage = 2
    context = _combat_context([pummel], energy=1, monsters=[_louse(current_hp=50)])
    context.strength = 1
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]

    assert IroncladCombatPlanner()._estimate_attack_damage_without_simulation(
        pummel,
        context,
    ) == 8


def test_simulation_state_coerces_string_monster_hp_and_block():
    target = _louse(current_hp="20")
    target.max_hp = "50"
    target.block = "3"
    context = _combat_context([], energy=0, monsters=[target])

    state = SimulationState(context)

    assert state.monsters[0]["hp"] == 20
    assert state.monsters[0]["max_hp"] == 50
    assert state.monsters[0]["block"] == 3


def test_simulation_state_rejects_nonfinite_monster_current_hp_as_unknown():
    target = _louse(current_hp=20)
    target.current_hp = float("inf")
    target.max_hp = 50
    context = _combat_context([], energy=0, monsters=[target])

    state = SimulationState(context)

    assert state.monsters[0]["hp"] == 50
    assert state.monsters[0]["max_hp"] == 50


def test_simulation_state_coerces_string_monster_move_adjusted_damage():
    target = _louse(current_hp=20)
    target.move_adjusted_damage = "12"
    context = _combat_context([], energy=0, monsters=[target])

    state = SimulationState(context)

    assert state.monsters[0]["move_adjusted_damage"] == 12


def test_simulation_state_coerces_string_monster_base_damage_and_hits():
    target = _louse(current_hp=20)
    target.move_base_damage = "7"
    target.move_hits = "2"
    context = _combat_context([], energy=0, monsters=[target])

    state = SimulationState(context)

    assert state.monsters[0]["move_base_damage"] == 7
    assert state.monsters[0]["move_hits"] == 2


def test_simulation_state_coerces_string_monster_stacks_and_strength():
    target = _louse(current_hp=20)
    target.strength = "-1"
    context = _combat_context([], energy=0, monsters=[target])
    context.vulnerable_stacks[0] = "2"
    context.weak_stacks[0] = "1"
    context.frail_stacks[0] = "3"
    context.thorns_stacks[0] = "4"

    state = SimulationState(context)

    assert state.monsters[0]["vulnerable"] == 2
    assert state.monsters[0]["weak"] == 1
    assert state.monsters[0]["frail"] == 3
    assert state.monsters[0]["thorns"] == 4
    assert state.monsters[0]["strength"] == -1


def test_simulation_state_coerces_string_player_hp_and_block():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.current_hp = "31"
    context.game.max_hp = "80"
    context.game.player.block = "5"

    state = SimulationState(context)

    assert state.player_hp == 31
    assert state.player_max_hp == 80
    assert state.player_block == 5
    assert state.turn_block() == 5


def test_simulation_state_prefers_context_player_block_field():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.player_block = "18"
    context.game.player.block = 0

    state = SimulationState(context)

    assert state.player_block == 18
    assert state.turn_block() == 18


def test_simulation_state_orichalcum_counts_as_end_turn_block_when_empty():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.relics = [SimpleNamespace(name="Orichalcum")]
    context.relics = context.game.relics
    context.has_orichalcum = True

    state = SimulationState(context)

    assert state.player_block == 0
    assert state.turn_block() == 6


def test_simulation_state_orichalcum_does_not_stack_with_existing_block():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.player.block = 4
    context.game.relics = [SimpleNamespace(name="Orichalcum")]
    context.relics = context.game.relics
    context.has_orichalcum = True

    state = SimulationState(context)

    assert state.player_block == 4
    assert state.turn_block() == 4


def test_simulation_state_coerces_string_player_energy_and_strength():
    context = _combat_context([], energy="3", monsters=[_louse(current_hp=20)])
    context.strength = "-2"

    state = SimulationState(context)

    assert state.player_energy == 3
    assert state.player_strength == -2


def test_simulation_state_rejects_nonfinite_numeric_context_values():
    target = _louse(current_hp=20)
    target.block = float("inf")
    target.move_adjusted_damage = float("inf")
    target.move_base_damage = float("inf")
    target.move_hits = float("inf")
    target.strength = float("inf")
    context = _combat_context([], energy=float("inf"), monsters=[target])
    context.game.current_hp = float("inf")
    context.game.max_hp = float("inf")
    context.game.player.block = float("inf")
    context.strength = float("inf")
    context.vulnerable_stacks[0] = float("inf")
    context.weak_stacks[0] = float("inf")
    context.frail_stacks[0] = float("inf")
    context.thorns_stacks[0] = float("inf")

    state = SimulationState(context)

    assert state.player_hp == 0
    assert state.player_max_hp == 0
    assert state.player_block == 0
    assert state.player_energy == 0
    assert state.player_strength == 0
    assert state.monsters[0]["block"] == 0
    assert state.monsters[0]["move_adjusted_damage"] == 0
    assert state.monsters[0]["move_base_damage"] == 0
    assert state.monsters[0]["move_hits"] == 0
    assert state.monsters[0]["strength"] == 0
    assert state.monsters[0]["vulnerable"] == 0
    assert state.monsters[0]["weak"] == 0
    assert state.monsters[0]["frail"] == 0
    assert state.monsters[0]["thorns"] == 0


def test_simulate_card_play_accepts_name_only_upgraded_attack_from_data(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "type": "ATTACK",
            "cost": 1,
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        upgrades=1,
        has_target=True,
        is_playable=True,
    )
    target = _louse(current_hp=20)
    context = _combat_context([strike], energy=1, monsters=[target])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_spent == 1
    assert result.total_damage_dealt == 9


def test_simulate_card_play_accepts_name_only_block_skill():
    defend = SimpleNamespace(
        name="Defend",
        type=CardType.SKILL,
        cost=1,
        cost_for_turn=1,
        block=5,
        upgrades=0,
        has_target=False,
        is_playable=True,
    )
    context = _combat_context([defend], energy=1, monsters=[_louse()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_spent == 1
    assert result.player_block == 5


def test_simulate_card_play_accepts_string_block_attribute():
    defend = SimpleNamespace(
        name="Defend",
        type=CardType.SKILL,
        cost=1,
        cost_for_turn=1,
        block="5",
        upgrades=0,
        has_target=False,
        is_playable=True,
    )
    context = _combat_context([defend], energy=1, monsters=[_louse()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 0
    assert result.energy_spent == 1
    assert result.player_block == 5


def test_cultist_ritual_turn_handles_string_attack_intents():
    context = _combat_context(
        [],
        energy=0,
        monsters=[
            _cultist_ritual(),
            _cultist_ritual(),
            _cultist_ritual(),
        ],
    )
    context.monsters_alive[0].intent = "Intent.BUFF"
    context.monsters_alive[1].intent = "Intent.ATTACK"
    context.monsters_alive[2].intent = "Attack/Buff"
    planner = IroncladCombatPlanner()

    assert planner._is_cultist_ritual_turn(context) is True

    context.monsters_alive = context.monsters_alive[1:]

    assert planner._is_cultist_ritual_turn(context) is False


def test_lagavulin_hibernating_handles_string_defend_intent():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_lagavulin(intent="Intent.DEFEND")],
    )

    assert IroncladCombatPlanner()._is_lagavulin_hibernating(context) is True


def test_ironclad_planner_draw_card_detection_uses_display_name():
    pommel = _card("Pommel_Strike", "Pommel Strike", cost=1)

    assert IroncladCombatPlanner()._is_draw_card(pommel) is True


def test_ironclad_planner_defensive_card_detection_uses_display_name():
    shrug = _card(
        "Shrug_It_Off",
        "Shrug It Off",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )

    assert IroncladCombatPlanner()._is_defensive_card(shrug) is True


def test_ironclad_card_log_format_accepts_name_only_card():
    pommel = SimpleNamespace(name="Pommel Strike", upgrades=1)

    assert ironclad_combat._format_card_for_log(pommel) == "Pommel Strike(Pommel Strike,u1)"


def test_stack_block_uses_discard_pile_size(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "stack": {
            "name": "Stack",
            "description": "Gain Block equal to the number of cards in your discard pile.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    stack = _card("Stack", "Stack+", card_type=CardType.SKILL, cost=1, has_target=False, upgrades=1)
    context = _combat_context([stack], energy=1, monsters=[_louse(current_hp=100)])
    context.game.discard_pile = [
        _card("Strike_R", "Strike"),
        _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False),
        _card("Bash", "Bash"),
        _card("Anger", "Anger"),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        stack,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 7


def test_genetic_algorithm_block_uses_misc_growth(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "genetic algorithm": {
            "name": "Genetic Algorithm",
            "description": "Gain 1 Block. Permanently increase this card's Block by 2. Exhaust.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    genetic_algorithm = _card(
        "Genetic Algorithm",
        "Genetic Algorithm",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    genetic_algorithm.misc = 8
    context = _combat_context(
        [genetic_algorithm],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        genetic_algorithm,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 9


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


def test_rage_power_block_is_not_reduced_by_frail():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [
        SimpleNamespace(power_name="Rage", amount=3),
        SimpleNamespace(power_name="Frail", amount=1),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.player_block == 3


def test_gremlin_nob_skill_reaction_ignores_zero_hp_stale_simulated_monsters():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1)
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob(current_hp=20)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.monsters[0]["strength"] == 0


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


def test_simulation_tracks_player_constricted_power():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Constricted", amount=7)]

    state = SimulationState(context)
    unconstricted_state = state.clone()
    unconstricted_state.player_constricted = 0

    assert state.player_constricted == 7
    assert state.state_key(context.playable_cards) != unconstricted_state.state_key(
        context.playable_cards
    )


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


def test_simulator_rejects_nonfinite_hex_counter():
    defend = _card(
        "Defend",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=100)])
    state = SimulationState(context)
    state.player_hex = float("inf")

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.dazed_cards_added == 0
    assert result.status_cards_added == 0
    assert result.hex_non_attack_triggers == 0
    assert result.player_hex == 0


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


def test_fungi_beast_death_effect_uses_live_monster_id(monkeypatch):
    class CanonicalOnlyDeathEffectLoader:
        def __init__(self):
            self.data_names = []

        def get_enhanced_monster_data(self, monster_name):
            self.data_names.append(monster_name)
            if monster_name == "Fungi Beast":
                return {
                    "special_mechanics": {
                        "death_effect": {
                            "type": "apply_vulnerable",
                            "amount": 2,
                        }
                    }
                }
            return None

    monster_loader = CanonicalOnlyDeathEffectLoader()
    monkeypatch.setattr(simulation, "game_data_loader", monster_loader)
    fungi_beast = _fungi_beast(current_hp=6)
    fungi_beast.name = "FungiBeast"
    context = _combat_context([], energy=0, monsters=[fungi_beast])
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._apply_monster_death_effects(
        state,
        state.monsters[0],
    )

    assert state.player_vulnerable == 2
    assert state.player_vulnerable_added == 2
    assert monster_loader.data_names == ["Fungi Beast"]


def test_fungi_beast_death_vulnerable_consumes_player_artifact():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_fungi_beast(current_hp=6), _louse(current_hp=50)],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters_killed == 1
    assert result.player_vulnerable == 0
    assert result.player_vulnerable_added == 0
    assert result.player_artifact == 0


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


def test_curl_up_gains_block_after_first_nonlethal_attack_damage():
    louse = _louse(current_hp=20)
    louse.powers = [SimpleNamespace(power_name="Curl Up", amount=5)]
    context = _combat_context([], energy=0, monsters=[louse])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(state, state.monsters[0], 6)
    assert state.monsters[0]["hp"] == 14
    assert state.monsters[0]["block"] == 5

    simulator._deal_damage_to_monster(state, state.monsters[0], 6)

    assert state.monsters[0]["hp"] == 13
    assert state.monsters[0]["block"] == 0


def test_malleable_gains_increasing_block_after_each_nonlethal_attack_damage():
    snake_plant = Monster(
        name="Snake Plant",
        monster_id="SnakePlant",
        max_hp=50,
        current_hp=50,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=21,
        move_hits=3,
    )
    snake_plant.powers = [SimpleNamespace(power_name="Malleable", amount=3)]
    context = _combat_context([], energy=0, monsters=[snake_plant])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(state, state.monsters[0], 6)
    assert state.monsters[0]["hp"] == 44
    assert state.monsters[0]["block"] == 3
    assert state.monsters[0]["malleable_block"] == 4

    simulator._deal_damage_to_monster(state, state.monsters[0], 6)

    assert state.monsters[0]["hp"] == 41
    assert state.monsters[0]["block"] == 4
    assert state.monsters[0]["malleable_block"] == 5


def test_multihit_attack_malleable_block_does_not_absorb_later_hits(monkeypatch):
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
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    target = Monster(
        name="Snake Plant",
        monster_id="SnakePlant",
        max_hp=79,
        current_hp=76,
        block=0,
        intent=Intent.STRONG_DEBUFF,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    target.powers = [SimpleNamespace(power_name="Malleable", amount=3)]
    context = _combat_context([twin_strike], energy=1, monsters=[target])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        twin_strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 10
    assert result.monsters[0]["hp"] == 66
    assert result.monsters[0]["block"] == 7
    assert result.monsters[0]["malleable_block"] == 5


def test_multihit_attack_curl_up_block_does_not_absorb_later_hits(monkeypatch):
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
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    target = _louse(current_hp=12)
    target.powers = [SimpleNamespace(power_name="Curl Up", amount=4)]
    context = _combat_context([twin_strike], energy=1, monsters=[target])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        twin_strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 10
    assert result.monsters[0]["hp"] == 2
    assert result.monsters[0]["block"] == 4
    assert result.monsters[0]["curl_up_used"] is True
    assert result.monsters[0]["curl_up_block"] == 0


def test_whirlwind_malleable_block_does_not_absorb_later_energy_hits():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    target = Monster(
        name="Snake Plant",
        monster_id="SnakePlant",
        max_hp=79,
        current_hp=79,
        block=0,
        intent=Intent.STRONG_DEBUFF,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    target.powers = [SimpleNamespace(power_name="Malleable", amount=3)]
    context = _combat_context([whirlwind], energy=2, monsters=[target])
    context.strength = 1

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        whirlwind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 12
    assert result.monsters[0]["hp"] == 67
    assert result.monsters[0]["block"] == 7
    assert result.monsters[0]["malleable_block"] == 5


def test_simulator_rejects_nonfinite_malleable_block_counter():
    snake_plant = Monster(
        name="Snake Plant",
        monster_id="SnakePlant",
        max_hp=50,
        current_hp=50,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=21,
        move_hits=3,
    )
    snake_plant.powers = [SimpleNamespace(power_name="Malleable", amount=3)]
    context = _combat_context([], energy=0, monsters=[snake_plant])
    state = SimulationState(context)
    state.monsters[0]["malleable_block"] = float("inf")

    FastCombatSimulator(SynergyCardEvaluator())._deal_damage_to_monster(
        state,
        state.monsters[0],
        6,
    )

    assert state.monsters[0]["hp"] == 44
    assert state.monsters[0]["block"] == 0
    assert state.monsters[0]["malleable_block"] == 0


def test_byrd_flight_halves_attack_damage_and_counts_down():
    context = _combat_context([], energy=0, monsters=[_byrd(flight=3)])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(state, state.monsters[0], 7)

    assert state.monsters[0]["hp"] == 27
    assert state.monsters[0]["flight_stacks"] == 2
    assert simulator._estimate_incoming_damage(state.monsters) == 12


def test_byrd_flight_knockdown_stuns_current_attack():
    context = _combat_context([], energy=0, monsters=[_byrd(flight=1)])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(state, state.monsters[0], 8)

    assert state.monsters[0]["hp"] == 26
    assert state.monsters[0]["flight_stacks"] == 0
    assert state.monsters[0]["intent"] == Intent.STUN
    assert simulator._estimate_incoming_damage(state.monsters) == 0


def test_simulator_rejects_nonfinite_flight_counter():
    context = _combat_context([], energy=0, monsters=[_byrd(flight=3)])
    state = SimulationState(context)
    state.monsters[0]["flight_stacks"] = float("inf")

    FastCombatSimulator(SynergyCardEvaluator())._deal_damage_to_monster(
        state,
        state.monsters[0],
        8,
    )

    assert state.monsters[0]["hp"] == 22
    assert state.monsters[0]["flight_stacks"] == 0


def test_monster_intangible_caps_attack_damage_to_one():
    context = _combat_context([], energy=0, monsters=[_nemesis(intangible=1)])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(state, state.monsters[0], 40)

    assert state.monsters[0]["hp"] == 184
    assert state.total_damage_dealt == 1


def test_simulator_rejects_nonfinite_intangible_counter():
    context = _combat_context([], energy=0, monsters=[_nemesis(intangible=1)])
    state = SimulationState(context)
    state.monsters[0]["intangible"] = float("inf")

    FastCombatSimulator(SynergyCardEvaluator())._deal_damage_to_monster(
        state,
        state.monsters[0],
        40,
    )

    assert state.monsters[0]["hp"] == 145
    assert state.monsters[0]["intangible"] == 0
    assert state.total_damage_dealt == 40


def test_monster_intangible_caps_non_attack_damage_to_one():
    context = _combat_context([], energy=0, monsters=[_nemesis(intangible=1)])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(
        state,
        state.monsters[0],
        40,
        trigger_thorns=False,
    )

    assert state.monsters[0]["hp"] == 184
    assert state.total_damage_dealt == 1


def test_giant_head_slow_increments_on_each_card_and_boosts_attack_damage():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    carnage = _card("Carnage", "Carnage", cost=2)
    carnage.damage = 20
    giant_head = _giant_head()
    context = _combat_context([defend, carnage], energy=3, monsters=[giant_head])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    after_defend = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        context=context,
    )
    result = simulator.simulate_card_play(
        after_defend,
        carnage,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert after_defend.monsters[0]["slow_stacks"] == 1
    assert result.monsters[0]["slow_stacks"] == 2
    assert result.monsters[0]["hp"] == 476
    assert result.total_damage_dealt == 24


def test_simulator_rejects_nonfinite_slow_counter():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_giant_head()])
    state = SimulationState(context)
    state.monsters[0]["slow_stacks"] = float("inf")

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["slow_stacks"] == 1
    assert result.monsters[0]["hp"] == 494


def test_state_key_distinguishes_giant_head_slow_stacks():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_giant_head()])
    base_state = SimulationState(context)
    slow_state = base_state.clone()
    slow_state.monsters[0]["slow_stacks"] = 1

    assert base_state.state_key(context.playable_cards) != slow_state.state_key(
        context.playable_cards
    )


def test_darkling_life_link_first_defeat_becomes_half_dead():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_darkling(current_hp=6), _darkling(current_hp=20)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["hp"] == 0
    assert result.monsters[0]["half_dead"] is True
    assert result.monsters[0]["is_gone"] is False
    assert result.monsters_killed == 0


def test_darkling_life_link_group_clears_when_final_darkling_defeated():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_darkling(current_hp=6), _darkling(current_hp=6)],
    )
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["half_dead"] = True

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[1],
        target_index=1,
        context=context,
    )

    assert all(monster["is_gone"] for monster in result.monsters)
    assert all(monster["half_dead"] is False for monster in result.monsters)
    assert result.monsters_killed == 2


def test_half_dead_monsters_are_not_live_attack_or_damage_targets():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    context = _combat_context([strike], energy=1, monsters=[_darkling(current_hp=20)])
    state = SimulationState(context)
    state.monsters[0]["half_dead"] = True

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["hp"] == 20
    assert result.total_damage_dealt == 0


def test_state_key_distinguishes_half_dead_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_darkling(current_hp=20)])
    base_state = SimulationState(context)
    half_dead_state = base_state.clone()
    half_dead_state.monsters[0]["half_dead"] = True

    assert base_state.state_key(context.playable_cards) != half_dead_state.state_key(
        context.playable_cards
    )


def test_incoming_damage_ignores_half_dead_monsters():
    context = _combat_context([], energy=0, monsters=[_darkling(current_hp=20)])
    state = SimulationState(context)
    state.monsters[0]["half_dead"] = True

    assert FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        state.monsters
    ) == 0


def test_safe_timing_bonus_ignores_half_dead_monster_hp():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_darkling(current_hp=40), _darkling(current_hp=6)],
    )
    state = SimulationState(context)
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["is_gone"] = False
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator.set_timing_context(
        SimpleNamespace(turn_timing=SimpleNamespace(value="SAFE"))
    )

    assert simulator._calculate_timing_bonus(state) == 3.0


def test_project_end_turn_revives_buffing_half_dead_darkling():
    context = _combat_context([], energy=0, monsters=[_darkling(current_hp=1)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["max_hp"] = 50
    state.monsters[0]["is_gone"] = True
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["intent"] = Intent.BUFF
    state.monsters[0]["move_base_damage"] = 0
    state.monsters[0]["move_adjusted_damage"] = 0
    state.monsters[0]["move_hits"] = 0

    simulator = FastCombatSimulator(SynergyCardEvaluator())
    projected = simulator.project_end_turn_effects(state)

    assert projected.monsters[0]["hp"] == 25
    assert projected.monsters[0]["is_gone"] is False
    assert projected.monsters[0]["half_dead"] is False
    assert simulator._is_live_monster_state(projected.monsters[0]) is True


def test_project_end_turn_revives_simulated_half_dead_darkling_without_gone_flag():
    context = _combat_context([], energy=0, monsters=[_darkling(current_hp=1)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["intent"] = Intent.BUFF

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(
        state
    )

    assert projected.monsters[0]["hp"] == 24
    assert projected.monsters[0]["is_gone"] is False
    assert projected.monsters[0]["half_dead"] is False


def test_project_end_turn_keeps_non_buff_half_dead_darkling_waiting():
    context = _combat_context([], energy=0, monsters=[_darkling(current_hp=1)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = True
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["intent"] = Intent.ATTACK

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(
        state
    )

    assert projected.monsters[0]["hp"] == 0
    assert projected.monsters[0]["is_gone"] is True
    assert projected.monsters[0]["half_dead"] is True


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


def test_enemy_status_lookahead_accepts_string_context_turn(monkeypatch):
    class FakeLoader:
        def predict_monster_moves(self, _monster_name, turn, _hp_percent, **_kwargs):
            return [
                {
                    "turn": int(turn) + 1,
                    "move": {
                        "intent": "ATTACK_DEBUFF",
                        "dazed_count": 2,
                    },
                }
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: {"intent": "BUFF"}

    int_context = _combat_context([], energy=0, monsters=[_sentry(move_id=1)])
    int_context.turn = 1
    int_status = simulator.simulate_enemy_status_lookahead(
        SimulationState(int_context),
        int_context,
        look_ahead=2,
    )

    string_context = _combat_context([], energy=0, monsters=[_sentry(move_id=1)])
    string_context.turn = "1"
    string_status = simulator.simulate_enemy_status_lookahead(
        SimulationState(string_context),
        string_context,
        look_ahead=2,
    )

    assert int_status["dazed"] == 2
    assert string_status == int_status


def test_enemy_status_card_extraction_uses_count_and_added_aliases_without_effect_text():
    counts = FastCombatSimulator(SynergyCardEvaluator())._extract_move_status_cards(
        {
            "dazed_count": 1,
            "burn_added": 2,
            "slimed_count": 3,
            "wound_added": 4,
            "void_cards_added": 5,
            "effect": "",
        }
    )

    assert counts["dazed"] == 1
    assert counts["burn"] == 2
    assert counts["slimed"] == 3
    assert counts["wound"] == 4
    assert counts["void"] == 5
    assert counts["total"] == 15


def test_enemy_status_lookahead_applies_ascension_status_card_modifiers():
    context = _combat_context([], energy=0, monsters=[_sentry(move_id=1)])
    context.ascension_level = 18
    context.game.ascension_level = 18
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    status = simulator.simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["dazed"] == 3
    assert status["total"] == 3


def test_enemy_status_lookahead_counts_chosen_hex_as_future_dazed_risk():
    context = _combat_context([], energy=0, monsters=[_chosen_hex()])

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["hex"] == 1
    assert status["dazed"] == 1
    assert status["total"] == 1


def test_enemy_status_lookahead_player_artifact_blocks_predicted_hex():
    context = _combat_context([], energy=0, monsters=[_chosen_hex()])
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["hex"] == 0
    assert status["dazed"] == 0
    assert status["total"] == 0


def test_enemy_status_lookahead_counts_entangled_as_future_control_risk():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_red_slaver(move_id=2, intent=Intent.DEBUFF)],
    )

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["entangled"] == 1
    assert status["total"] == 1


def test_enemy_status_lookahead_player_artifact_blocks_predicted_entangled():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_red_slaver(move_id=2, intent=Intent.DEBUFF)],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["entangled"] == 0
    assert status["total"] == 0


def test_enemy_status_lookahead_counts_confused_as_future_control_risk():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_snecko_confused()],
    )

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["confused"] == 1
    assert status["total"] == 1


def test_enemy_status_lookahead_player_artifact_blocks_predicted_confused():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_snecko_confused()],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["confused"] == 0
    assert status["total"] == 0


def test_time_eater_wiki_data_matches_vanilla_moves():
    database = EnhancedMonsterDatabase()

    time_eater = database.get_monster_data("Time Eater")
    moves_by_name = {move["name"]: move for move in time_eater["moves"]}

    assert time_eater["hp_ranges"]["normal"] == {"min": 456, "max": 456}
    assert time_eater["hp_ranges"]["ascension_9+"] == {"min": 480, "max": 480}
    assert set(moves_by_name) == {"Reverberate", "Head Slam", "Ripple", "Haste"}

    head_slam = moves_by_name["Head Slam"]
    assert head_slam["intent"] == "ATTACK_DEBUFF"
    assert head_slam["damage"] == 26
    assert head_slam["draw_reduction"] == 1
    assert head_slam["ascension_modifiers"]["4+"]["damage"] == 32
    assert head_slam["ascension_modifiers"]["19+"]["slimed_added"] == 2

    ripple = moves_by_name["Ripple"]
    assert ripple["block_gain"] == 20
    assert ripple["weak_applied"] == 1
    assert ripple["vulnerable_applied"] == 1
    assert ripple["ascension_modifiers"]["19+"]["frail_applied"] == 1


def test_enemy_status_lookahead_counts_time_eater_draw_reduction():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_time_eater_head_slam()],
    )

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["draw_reduction"] == 1
    assert status["total"] == 1


def test_enemy_status_lookahead_counts_time_eater_a19_slimed():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_time_eater_head_slam(current_hp=480, damage=32)],
    )
    context.ascension_level = 19
    context.game.ascension_level = 19

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["draw_reduction"] == 1
    assert status["slimed"] == 2
    assert status["total"] == 3


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


def test_gremlin_nob_skill_strength_fallback_uses_ascension_modifier():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    nob = _gremlin_nob()
    nob.powers = []
    context = _combat_context([defend], energy=1, monsters=[nob])
    context.ascension_level = 18
    context.game.ascension_level = 18
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        context=context,
    )

    assert result.monsters[0]["strength"] == 3
    assert simulator._estimate_incoming_damage(result.monsters) == 17


def test_mad_gremlin_angry_does_not_trigger_on_skill_cards():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_mad_gremlin()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        defend,
        context=context,
    )

    assert result.monsters[0]["strength"] == 0
    assert simulator._estimate_incoming_damage(result.monsters) == 4


def test_mad_gremlin_angry_gains_strength_after_nonlethal_attack_damage():
    context = _combat_context([], energy=0, monsters=[_mad_gremlin()])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._deal_damage_to_monster(state, state.monsters[0], 6)

    assert state.monsters[0]["hp"] == 16
    assert state.monsters[0]["strength"] == 1
    assert state.monsters[0]["move_adjusted_damage"] == 5


def test_gremlin_nob_skill_strength_updates_current_attack_after_disarm():
    disarm = _card("Disarm", "Disarm", card_type=CardType.SKILL, cost=1, has_target=True)
    context = _combat_context([disarm], energy=1, monsters=[_gremlin_nob(move_adjusted_damage=14)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        disarm,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["strength"] == 0
    assert result.monsters[0]["move_adjusted_damage"] == 14


def test_gremlin_nob_skill_strength_recomputes_weak_adjusted_attack_damage():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    nob = _gremlin_nob(move_adjusted_damage=6)
    nob.move_base_damage = 8
    context = _combat_context([defend], energy=1, monsters=[nob])
    context.weak_stacks[0] = 1

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        defend,
        context=context,
    )

    assert result.monsters[0]["strength"] == 2
    assert result.monsters[0]["move_adjusted_damage"] == 7
    assert FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        result.monsters
    ) == 7


def test_simulation_state_rejects_nonfinite_skill_reactive_strength_amount():
    nob = _gremlin_nob()
    nob.powers[0].amount = float("inf")
    context = _combat_context([], energy=0, monsters=[nob])

    state = SimulationState(context)

    assert state.monsters[0]["skill_strength_gain"] == 0


def test_simulator_rejects_nonfinite_skill_reactive_strength_counter():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    state = SimulationState(context)
    state.monsters[0]["skill_strength_gain"] = float("inf")

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        defend,
        context=context,
    )

    assert result.monsters[0]["skill_strength_gain"] == 0
    assert result.monsters[0]["strength"] == 0


def test_state_key_distinguishes_monster_strength_changes():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    initial_state = SimulationState(context)
    stronger_state = initial_state.clone()
    stronger_state.monsters[0]["strength"] = 2

    assert initial_state.state_key(context.playable_cards) != stronger_state.state_key(
        context.playable_cards
    )


def test_simulation_state_tracks_orb_walker_end_turn_strength_gain():
    context = _combat_context([], energy=0, monsters=[_orb_walker()])
    normal_state = SimulationState(context)

    context.ascension_level = 17
    context.game.ascension_level = 17
    asc17_state = SimulationState(context)

    assert normal_state.monsters[0]["end_turn_strength_gain"] == 3
    assert asc17_state.monsters[0]["end_turn_strength_gain"] == 5


def test_simulation_state_orb_walker_strength_gain_rejects_nonfinite_ascension():
    context = _combat_context([], energy=0, monsters=[_orb_walker()])
    context.ascension_level = float("inf")
    context.game.ascension_level = float("inf")

    state = SimulationState(context)

    assert state.monsters[0]["end_turn_strength_gain"] == 3


def test_simulation_state_orb_walker_strength_gain_rejects_nonfinite_data(monkeypatch):
    class NonfiniteOrbWalkerLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return {
                "special_mechanics": {
                    "type": "strength_up",
                    "strength_gain": float("inf"),
                }
            }

    monkeypatch.setattr(simulation, "game_data_loader", NonfiniteOrbWalkerLoader())
    context = _combat_context([], energy=0, monsters=[_orb_walker()])

    state = SimulationState(context)

    assert state.monsters[0]["end_turn_strength_gain"] == 0


def test_enemy_lookahead_applies_orb_walker_strength_up_to_future_attacks():
    context = _combat_context([], energy=0, monsters=[_orb_walker()])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    def predicted_attack(_monster_name, _current_turn, step, _hp_percent):
        if step == 1:
            return {"intent": "ATTACK", "damage": 15, "hits": 1}
        return None

    simulator._predicted_monster_move_for_step = predicted_attack

    damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert damage == 24


def test_simulation_state_tracks_live_monster_ritual_strength_gain():
    context = _combat_context([], energy=0, monsters=[_cultist_ritual(ritual=3)])
    state = SimulationState(context)
    no_ritual_state = state.clone()
    no_ritual_state.monsters[0]["end_turn_strength_gain"] = 0

    assert state.monsters[0]["end_turn_strength_gain"] == 3
    assert state.state_key(context.playable_cards) != no_ritual_state.state_key(
        context.playable_cards
    )


def test_simulation_state_rejects_nonfinite_ritual_power_amount():
    cultist = _cultist_ritual(ritual=3)
    cultist.powers[0].amount = float("inf")
    context = _combat_context([], energy=0, monsters=[cultist])

    state = SimulationState(context)

    assert state.monsters[0]["end_turn_strength_gain"] == 0


def test_enemy_lookahead_applies_live_cultist_ritual_to_future_attacks():
    context = _combat_context(
        [],
        energy=0,
        monsters=[
            _cultist_ritual(
                ritual=3,
                intent=Intent.ATTACK,
                move_id=1,
            )
        ],
    )
    context.turn = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    def predicted_attack(_monster_name, _current_turn, step, _hp_percent):
        if step == 1:
            return {"intent": "ATTACK", "damage": 6, "hits": 1}
        return None

    simulator._predicted_monster_move_for_step = predicted_attack

    damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert damage == 13


def test_state_key_distinguishes_internal_monster_damage_refresh_state():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    base_state = SimulationState(context)
    refreshed_state = base_state.clone()

    refreshed_state.monsters[0]["_simulated_move_adjusted_source"] = 18
    refreshed_state.monsters[0]["_simulated_strength_delta"] = -4
    refreshed_state.monsters[0]["_simulated_temporary_strength_delta"] = -4

    simulator = FastCombatSimulator(SynergyCardEvaluator())
    base_projected = base_state.clone()
    refreshed_projected = refreshed_state.clone()
    simulator._decrement_monster_turn_debuffs(base_projected)
    simulator._decrement_monster_turn_debuffs(refreshed_projected)

    assert base_projected.monsters[0]["move_adjusted_damage"] == 14
    assert refreshed_projected.monsters[0]["move_adjusted_damage"] == 18

    assert base_state.state_key(context.playable_cards) != refreshed_state.state_key(
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


def test_enemy_lookahead_applies_all_enemies_strength_gain_to_future_attacks():
    leader = Monster(
        name="Gremlin Leader",
        monster_id="Gremlin_Leader",
        max_hp=145,
        current_hp=145,
        block=0,
        intent=Intent.BUFF,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=0,
        move_hits=1,
    )
    minion = Monster(
        name="Mad Gremlin",
        monster_id="GremlinFat",
        max_hp=25,
        current_hp=25,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    context = _combat_context([], energy=0, monsters=[leader, minion])
    context.turn = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda monster: (
        {
            "name": "Encourage",
            "intent": "BUFF",
            "strength_gain": 3,
            "effect": "All enemies gain 3 Strength. All minions gain 6 Block.",
        }
        if monster["name"] == "Gremlin Leader"
        else None
    )
    simulator._predicted_monster_move_for_step = lambda monster_name, _turn, step, _hp: (
        {"name": "Scratch", "intent": "ATTACK", "damage": 6, "hits": 1}
        if monster_name == "Mad Gremlin" and step == 1
        else None
    )

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(9 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_prediction_passes_other_enemy_count_to_loader(monkeypatch):
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
        ):
            self.calls.append(
                {
                    "monster_name": monster_name,
                    "current_turn": current_turn,
                    "hp_percent": hp_percent,
                    "ascension_level": ascension_level,
                    "other_enemy_count": other_enemy_count,
                }
            )
            return []

    loader = FakeLoader()
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    leader = Monster(
        name="Gremlin Leader",
        monster_id="Gremlin_Leader",
        max_hp=145,
        current_hp=145,
        block=0,
        intent=Intent.BUFF,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=0,
        move_hits=1,
    )
    minion = Monster(
        name="Mad Gremlin",
        monster_id="GremlinFat",
        max_hp=25,
        current_hp=25,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    context = _combat_context([], energy=0, monsters=[leader, minion])
    context.game.monsters = [leader, minion]
    context.ascension_level = 18
    context.game.ascension_level = 18

    FastCombatSimulator(SynergyCardEvaluator())._predict_monster_moves(
        "Gremlin Leader",
        current_turn=1,
        hp_percent=1.0,
        context=context,
    )

    assert loader.calls == [
        {
            "monster_name": "Gremlin Leader",
            "current_turn": 1,
            "hp_percent": 1.0,
            "ascension_level": 18,
            "other_enemy_count": 1,
        }
    ]


def test_enemy_prediction_passes_other_enemy_names_to_loader(monkeypatch):
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
        ):
            self.calls.append(
                {
                    "monster_name": monster_name,
                    "current_turn": current_turn,
                    "hp_percent": hp_percent,
                    "ascension_level": ascension_level,
                    "other_enemy_count": other_enemy_count,
                    "other_enemy_names": other_enemy_names,
                }
            )
            return []

    loader = FakeLoader()
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    collector = Monster(
        name="The Collector",
        monster_id="TheCollector",
        max_hp=282,
        current_hp=282,
        block=0,
        intent=Intent.UNKNOWN,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=0,
        move_hits=1,
    )
    torch_head = Monster(
        name="Torch Head",
        monster_id="TorchHead",
        max_hp=40,
        current_hp=40,
        block=0,
        intent=Intent.ATTACK,
        half_dead=False,
        is_gone=False,
        move_id=0,
        move_adjusted_damage=7,
        move_hits=1,
    )
    context = _combat_context([], energy=0, monsters=[collector, torch_head])
    context.game.monsters = [collector, torch_head]

    FastCombatSimulator(SynergyCardEvaluator())._predict_monster_moves(
        "The Collector",
        current_turn=2,
        hp_percent=1.0,
        context=context,
    )

    assert loader.calls == [
        {
            "monster_name": "The Collector",
            "current_turn": 2,
            "hp_percent": 1.0,
            "ascension_level": 0,
            "other_enemy_count": 1,
            "other_enemy_names": ["Torch Head"],
        }
    ]


def test_enemy_prediction_includes_same_name_other_enemies(monkeypatch):
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
        ):
            self.calls.append(
                {
                    "monster_name": monster_name,
                    "other_enemy_count": other_enemy_count,
                    "other_enemy_names": other_enemy_names,
                }
            )
            return []

    loader = FakeLoader()
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    context = _combat_context(
        [],
        energy=0,
        monsters=[_sentry(current_hp=40), _sentry(current_hp=40)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._prediction_monsters = context.monsters_alive
    simulator._prediction_monster = context.monsters_alive[0]

    simulator._predict_monster_moves(
        "Sentry",
        current_turn=1,
        hp_percent=1.0,
        context=context,
    )

    assert loader.calls == [
        {
            "monster_name": "Sentry",
            "other_enemy_count": 1,
            "other_enemy_names": ["Sentry"],
        }
    ]


def test_enemy_prediction_passes_same_monster_index_to_loader(monkeypatch):
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
                    "same_monster_index": same_monster_index,
                }
            )
            return []

    loader = FakeLoader()
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    context = _combat_context(
        [],
        energy=0,
        monsters=[_sentry(current_hp=40), _sentry(current_hp=40)],
    )
    context.turn = 1

    FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert sorted({
        call["same_monster_index"]
        for call in loader.calls
        if call["monster_name"] == "Sentry" and call["current_turn"] == 1
        and call["same_monster_index"] is not None
    }) == [0, 1]


def test_enemy_lookahead_depth_prediction_passes_same_monster_index_to_loader(monkeypatch):
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
                    "same_monster_index": same_monster_index,
                }
            )
            if same_monster_index != 1:
                return [
                    {"move": {"name": "Bolt", "intent": "DEBUFF"}},
                    {"move": {"name": "Bolt", "intent": "DEBUFF"}},
                ]
            return [
                {"move": {"name": "Bolt", "intent": "DEBUFF"}},
                {"move": {"name": "Beam", "intent": "ATTACK", "damage": 10, "hits": 1}},
            ]

    loader = FakeLoader()
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    context = _combat_context(
        [],
        energy=0,
        monsters=[_sentry(current_hp=40), _sentry(current_hp=40)],
    )
    context.turn = 1

    needs_lookahead = FastCombatSimulator(SynergyCardEvaluator())._needs_multi_turn_enemy_lookahead(
        SimulationState(context),
        context,
    )

    assert needs_lookahead is True
    assert sorted({
        call["same_monster_index"]
        for call in loader.calls
        if call["monster_name"] == "Sentry" and call["current_turn"] == 1
        and call["same_monster_index"] is not None
    }) == [0, 1]


def test_enemy_lookahead_ignores_negated_attack_intent(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, _turn, _hp_percent):
            return [
                {"move": {"intent": "NOT_ATTACK", "damage": 20, "hits": 1}}
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: None

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 0


def test_enemy_lookahead_counts_live_unknown_damage_move():
    context = _combat_context([], energy=0, monsters=[_exploder_explode()])
    context.turn = 3
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 30


def test_enemy_lookahead_counts_predicted_unknown_damage_move():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 3
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: None
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: {
        "name": "Explode",
        "intent": "UNKNOWN",
        "damage": 30,
        "hits": 1,
    }

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 30


def test_enemy_lookahead_counts_constrict_move_future_constricted_loss():
    context = _combat_context([], energy=0, monsters=[_spire_growth_constrict()])
    context.turn = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: {
        "name": "Constrict",
        "intent": "ATTACK_DEBUFF",
        "damage": 10,
        "constricted": 10,
    }
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: {
        "name": "No Damage Followup",
        "intent": "BUFF",
        "damage": 0,
    }

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == 10 + int(10 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_accepts_string_context_turn_for_current_attack():
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: {
        "intent": "ATTACK",
        "damage": 10,
        "hits": 1,
    }

    int_context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    int_context.turn = 1
    int_damage = simulator.simulate_enemy_lookahead(
        SimulationState(int_context),
        int_context,
        look_ahead=1,
    )

    string_context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    string_context.turn = "1"
    string_damage = simulator.simulate_enemy_lookahead(
        SimulationState(string_context),
        string_context,
        look_ahead=1,
    )

    assert string_damage == int_damage == 10


def test_transient_shifting_reduces_current_attack_after_attack_damage():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_transient_attack()])
    context.turn = 3
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 6
    assert result.monsters[0]["move_adjusted_damage"] == 44
    assert simulator._estimate_incoming_damage(result.monsters) == 44
    assert simulator.simulate_enemy_lookahead(result, context, look_ahead=1) == 44


def test_enemy_lookahead_applies_ascension_ritual_gain_to_future_attacks():
    context = _combat_context([], energy=0, monsters=[_cultist_ritual()])
    context.turn = 1
    context.ascension_level = 2
    context.game.ascension_level = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(10 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_applies_ascension_damage_modifiers(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, _turn, _hp_percent):
            return [
                {
                    "move": {
                        "intent": "ATTACK",
                        "damage": 8,
                        "hits": 1,
                        "ascension_modifiers": {"2+": {"damage": 12}},
                    }
                }
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    context.ascension_level = 2
    context.game.ascension_level = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 12


def test_enemy_lookahead_applies_ascension_damage_bonus_modifiers(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, _turn, _hp_percent):
            return [
                {
                    "move": {
                        "intent": "ATTACK",
                        "damage": 8,
                        "hits": 1,
                        "ascension_modifiers": {"2+": {"damage_bonus": 1}},
                    }
                }
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    context.ascension_level = 2
    context.game.ascension_level = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 9


def test_enemy_lookahead_applies_ascension_hit_modifiers(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, _turn, _hp_percent):
            return [
                {
                    "move": {
                        "intent": "ATTACK",
                        "damage": 5,
                        "hits": 1,
                        "ascension_modifiers": {"4+": {"hits": 2}},
                    }
                }
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    context.ascension_level = 4
    context.game.ascension_level = 4
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 10


def test_enemy_lookahead_applies_ascension_strength_gain_modifiers(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, turn, _hp_percent):
            move = (
                {
                    "move": {
                        "intent": "BUFF",
                        "strength_gain": 2,
                        "ascension_modifiers": {"2+": {"strength_gain": 4}},
                    }
                }
                if turn == 1
                else {"move": {"intent": "ATTACK", "damage": 6, "hits": 1}}
            )
            return [move]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    context.ascension_level = 2
    context.game.ascension_level = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(10 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_applies_ascension_debuff_modifiers(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, turn, _hp_percent):
            move = (
                {
                    "move": {
                        "intent": "DEBUFF",
                        "vulnerable_applied": 1,
                        "ascension_modifiers": {"17+": {"vulnerable_applied": 2}},
                    }
                }
                if turn == 1
                else {"move": {"intent": "ATTACK", "damage": 10, "hits": 1}}
            )
            return [move]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    context.ascension_level = 17
    context.game.ascension_level = 17
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(15 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_counts_random_debuff_as_conservative_single_risk(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, turn, _hp_percent):
            move = (
                {
                    "move": {
                        "intent": "DEBUFF",
                        "random_debuff": ["weak", "vulnerable", "frail"],
                        "debuff_count": 2,
                    }
                }
                if turn == 1
                else {"move": {"intent": "ATTACK", "damage": 10, "hits": 1}}
            )
            return [move]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(15 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_player_artifact_blocks_predicted_debuff(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def predict_monster_moves(self, _monster_name, turn, _hp_percent):
            move = (
                {"move": {"intent": "DEBUFF", "vulnerable_applied": 2}}
                if turn == 1
                else {"move": {"intent": "ATTACK", "damage": 10, "hits": 1}}
            )
            return [move]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    future_damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(10 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_applies_same_turn_vulnerable_before_later_attack():
    context = _combat_context(
        [],
        energy=0,
        monsters=[_green_louse_debuff(current_hp=20), _louse(current_hp=50)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    def current_move(monster):
        if monster["monster_id"] == "FuzzyLouseDefensive":
            return {"intent": "DEBUFF", "vulnerable_applied": 2}
        return {"intent": "ATTACK", "damage": 10, "hits": 1}

    simulator._current_monster_move = current_move

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert future_damage == 15


def test_live_champ_transition_buff_resolves_to_anger_despite_live_move_id():
    context = _combat_context([], energy=0, monsters=[_champ_transition()])
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    move = simulator._current_monster_move(state.monsters[0])

    assert move["name"] == "Anger"
    assert move["strength_gain"] == 6


def test_champ_anger_clears_weak_before_future_execute_damage():
    context = _combat_context([], energy=0, monsters=[_champ_transition()])
    context.turn = 8
    context.weak_stacks[0] = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: {
        "name": "Execute",
        "intent": "ATTACK",
        "damage": 10,
        "hits": 2,
    }

    future_damage = simulator.simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert future_damage == int(32 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_live_move_resolution_ignores_damage_matching_for_negated_attack_intent():
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    move = simulator._find_current_move_by_live_state(
        {
            "name": "Training Dummy",
            "hp": 20,
            "intent": "NOT_ATTACK",
            "move_adjusted_damage": 20,
            "move_hits": 1,
        },
        [
            {"name": "Preferred Feint", "intent": "NOT_ATTACK", "damage": 5, "hits": 1},
            {"name": "Stale Damage Feint", "intent": "NOT_ATTACK", "damage": 20, "hits": 1},
        ],
    )

    assert move["name"] == "Preferred Feint"


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


def test_time_eater_haste_uses_multi_turn_lookahead():
    cards = [
        _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False),
        _card("Shrug It Off", "Shrug It Off", card_type=CardType.SKILL, cost=1, has_target=False),
        _card("Second Wind", "Second Wind", card_type=CardType.SKILL, cost=1, has_target=False),
    ]
    context = _combat_context(cards, energy=1, monsters=[_time_eater_haste()])
    context.turn = 5
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    depth = simulator._get_enemy_lookahead_depth(state, context)
    future_damage = simulator.simulate_enemy_lookahead(
        state,
        context,
        look_ahead=depth,
    )

    assert depth == 2
    assert future_damage >= int(21 * simulation.LOOKAHEAD_DAMAGE_DISCOUNT)


def test_enemy_lookahead_depth_ignores_negated_future_attack_intent():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: None
    simulator._predict_monster_moves = lambda *_args, **_kwargs: [
        {"move": {"intent": "BUFF"}},
        {"move": {"intent": "NOT_ATTACK", "damage": 20, "hits": 1}},
    ]

    assert simulator._needs_multi_turn_enemy_lookahead(state, context) is False


def test_enemy_lookahead_depth_counts_future_unknown_damage_move():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: None
    simulator._predict_monster_moves = lambda *_args, **_kwargs: [
        {"move": {"intent": "BUFF"}},
        {"move": {"name": "Explode", "intent": "UNKNOWN", "damage": 30, "hits": 1}},
    ]

    assert simulator._needs_multi_turn_enemy_lookahead(state, context) is True


def test_enemy_lookahead_depth_accepts_string_context_turn(monkeypatch):
    class FakeLoader:
        def predict_monster_moves(self, _monster_name, current_turn, _hp_percent, **_kwargs):
            if current_turn != 1:
                return [{"move": {"intent": "BUFF"}}]
            return [
                {"move": {"intent": "BUFF"}},
                {"move": {"intent": "ATTACK", "damage": 8, "hits": 1}},
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=50)])
    context.turn = "1"
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: {"intent": "BUFF"}

    assert simulator._needs_multi_turn_enemy_lookahead(state, context) is True


def test_awakened_lagavulin_attack_is_not_marked_hibernating():
    context = _combat_context([], energy=0, monsters=[_lagavulin()])
    context.turn = 6
    state = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    simulator._handle_hibernation(state, state.monsters[0])

    assert not state.monsters[0].get("is_hibernating", False)
    assert state.monsters[0].get("is_awakened", False)


def test_lagavulin_negated_attack_intent_does_not_wake_hibernation(monkeypatch):
    monkeypatch.setattr(
        game_data_loader,
        "get_enhanced_monster_data",
        lambda _monster_name: {"special_mechanics": {"type": "hibernation"}},
    )
    monkeypatch.setattr(
        game_data_loader,
        "is_monster_hibernating",
        lambda _monster_name, _turn: True,
    )
    context = _combat_context(
        [],
        energy=0,
        monsters=[_lagavulin(intent="NOT_ATTACK", move_adjusted_damage=0)],
    )
    context.turn = 1
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._handle_hibernation(state, state.monsters[0])

    assert state.monsters[0].get("is_hibernating", False)
    assert not state.monsters[0].get("is_awakened", False)


def test_lagavulin_hibernation_accepts_string_state_turn(monkeypatch):
    monkeypatch.setattr(
        game_data_loader,
        "get_enhanced_monster_data",
        lambda _monster_name: {"special_mechanics": {"type": "hibernation"}},
    )
    monkeypatch.setattr(
        game_data_loader,
        "is_monster_hibernating",
        lambda _monster_name, turn: turn == 1,
    )
    context = _combat_context(
        [],
        energy=0,
        monsters=[_lagavulin(intent="NOT_ATTACK", move_adjusted_damage=0)],
    )
    context.turn = "1"
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._handle_hibernation(state, state.monsters[0])

    assert state.monsters[0].get("is_hibernating", False)
    assert not state.monsters[0].get("is_awakened", False)


def test_lagavulin_hibernation_handler_uses_live_monster_id(monkeypatch):
    class CanonicalOnlyHibernationLoader:
        def __init__(self):
            self.data_names = []
            self.hibernation_names = []

        def get_enhanced_monster_data(self, monster_name):
            self.data_names.append(monster_name)
            if monster_name == "Lagavulin":
                return {"special_mechanics": {"type": "hibernation"}}
            return None

        def is_monster_hibernating(self, monster_name, _turn):
            self.hibernation_names.append(monster_name)
            return monster_name == "Lagavulin"

    monster_loader = CanonicalOnlyHibernationLoader()
    monkeypatch.setattr(data_loader_module, "game_data_loader", monster_loader)
    lagavulin = _lagavulin(intent="NOT_ATTACK", move_adjusted_damage=0)
    lagavulin.name = ""
    context = _combat_context([], energy=0, monsters=[lagavulin])
    context.turn = 1
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._handle_hibernation(state, state.monsters[0])

    assert state.monsters[0].get("is_hibernating", False)
    assert not state.monsters[0].get("is_awakened", False)
    assert monster_loader.data_names == ["Lagavulin"]
    assert monster_loader.hibernation_names == ["Lagavulin"]


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


def test_enemy_status_lookahead_counts_void_cards():
    awakened_one = _awakened_one()
    awakened_one.intent = Intent.ATTACK_DEBUFF
    awakened_one.move_id = 5
    awakened_one.move_adjusted_damage = 18
    context = _combat_context([], energy=0, monsters=[awakened_one])

    status = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_status_lookahead(
        SimulationState(context),
        context,
        look_ahead=1,
    )

    assert status["void"] == 1
    assert status["total"] == 1


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
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([true_grit, strike], energy=1, monsters=[_louse(current_hp=100)])
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


def test_single_card_exhaust_skill_without_hand_card_has_no_exhaust_event(monkeypatch):
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

    assert result.exhaust_events == 0
    assert result.player_block == 7


def test_single_card_exhaust_skill_marks_exhausted_sentinel_unavailable(monkeypatch):
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
    sentinel = _card("Sentinel", "Sentinel", card_type=CardType.SKILL, cost=1, has_target=False)
    sentinel.uuid = "sentinel-card"
    context = _combat_context([true_grit, sentinel], energy=1, monsters=[_louse(current_hp=100)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        true_grit,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert "sentinel-card" in result.played_card_uuids
    assert result.energy_gained == 2
    assert result.player_energy == 2


def test_sequential_simulation_keeps_played_card_out_of_hand_exhaust(monkeypatch):
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
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike-card"
    true_grit = _card("True Grit", "True Grit", card_type=CardType.SKILL, cost=1, has_target=False)
    sentinel = _card("Sentinel", "Sentinel", card_type=CardType.SKILL, cost=1, has_target=False)
    sentinel.uuid = "sentinel-card"
    context = _combat_context(
        [strike, true_grit, sentinel],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        true_grit,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert "sentinel-card" in result.played_card_uuids
    assert result.energy_gained == 2
    assert result.player_energy == 2


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
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([true_grit, strike], energy=1, monsters=[_louse(current_hp=100)])
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


def test_played_feel_no_pain_stacks_with_existing_power(monkeypatch):
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
            "text": "Gain <R> <R>.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    feel_no_pain = _card(
        "Feel No Pain",
        "Feel No Pain",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
    )
    seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context([feel_no_pain, seeing_red], energy=2, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        feel_no_pain,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        seeing_red,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.feel_no_pain_block_per_exhaust == 6
    assert result.exhaust_events == 1
    assert result.player_block == 6


def test_played_dark_embrace_stacks_with_existing_power(monkeypatch):
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
            "text": "Gain <R> <R>.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    dark_embrace = _card(
        "Dark Embrace",
        "Dark Embrace",
        card_type=CardType.POWER,
        cost=2,
        has_target=False,
    )
    seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context([dark_embrace, seeing_red], energy=3, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Dark Embrace", amount=1)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        dark_embrace,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        state,
        seeing_red,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.dark_embrace_draw_per_exhaust == 2
    assert result.exhaust_events == 1
    assert result.cards_drawn == 2


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


def test_metallicize_end_turn_block_triggers_juggernaut(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "metallicize": {
            "name": "Metallicize",
            "description": "At the end of your turn, gain 3 Block.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    metallicize = _card("Metallicize", "Metallicize", card_type=CardType.POWER, cost=1, has_target=False)
    context = _combat_context([metallicize], energy=1, monsters=[_louse(current_hp=20)])
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        metallicize,
        target=None,
        target_index=None,
        context=context,
    )
    projected = simulator.project_end_turn_effects(state)

    assert state.player_block == 0
    assert state.end_turn_block == 3
    assert state.total_damage_dealt == 0
    assert projected.player_block == 3
    assert projected.end_turn_block == 0
    assert projected.total_damage_dealt == 5
    assert projected.monsters[0]["hp"] == 15


def test_existing_juggernaut_deals_damage_when_skill_gains_block():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend.block = 5
    context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=20)])
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 5
    assert result.total_damage_dealt == 5
    assert result.monsters[0]["hp"] == 15


def test_played_juggernaut_deals_damage_on_followup_block():
    juggernaut = _card(
        "Juggernaut",
        "Juggernaut",
        card_type=CardType.POWER,
        cost=2,
        has_target=False,
    )
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend.block = 5
    context = _combat_context([juggernaut, defend], energy=3, monsters=[_louse(current_hp=20)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        juggernaut,
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

    assert result.player_block == 5
    assert result.total_damage_dealt == 5
    assert result.monsters[0]["hp"] == 15


def test_feel_no_pain_block_triggers_juggernaut_per_exhaust_event(monkeypatch):
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
    context.game.player.powers = [
        SimpleNamespace(power_name="Feel No Pain", amount=3),
        SimpleNamespace(power_name="Juggernaut", amount=5),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        fiend_fire,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.exhaust_events == 3
    assert result.player_block == 9
    assert result.total_damage_dealt == 29
    assert result.damage_instances == 5


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


def test_project_end_turn_burn_uses_remaining_block():
    burn = _card("Burn", "Burn", card_type=CardType.STATUS, cost=0, has_target=False)
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.current_hp = 29
    context.player_hp = 29
    context.game.player.block = 11
    context.game.hand = [burn]

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(
        SimulationState(context)
    )

    assert projected.player_hp == 29
    assert projected.player_block == 9


def test_project_end_turn_burn_plus_deals_four_after_block():
    burn_plus = _card(
        "Burn",
        "Burn+",
        card_type=CardType.STATUS,
        cost=0,
        has_target=False,
        upgrades=1,
    )
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.current_hp = 14
    context.player_hp = 14
    context.game.player.block = 3
    context.game.hand = [burn_plus, burn_plus]

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(
        SimulationState(context)
    )

    assert projected.player_hp == 9
    assert projected.player_block == 0


def test_project_end_turn_decay_loses_hp_through_block():
    decay = _card("Decay", "Decay", card_type=CardType.CURSE, cost=0, has_target=False)
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.current_hp = 52
    context.player_hp = 52
    context.game.player.block = 10
    context.game.hand = [decay]

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(
        SimulationState(context)
    )

    assert projected.player_hp == 50
    assert projected.player_block == 10


def test_power_energy_gain_uses_name_only_card_data(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "energy surge": {
            "name": "Energy Surge",
            "description": "Gain 2 Energy.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    energy_surge = SimpleNamespace(
        name="Energy Surge",
        type=CardType.POWER,
        cost=0,
        cost_for_turn=0,
        has_target=False,
        is_playable=True,
        upgrades=0,
    )
    context = _combat_context([energy_surge], energy=0, monsters=[_louse(current_hp=20)])

    state = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        energy_surge,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.energy_gained == 2


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


def test_constricted_end_turn_hp_loss_does_not_trigger_rupture():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    context.game.player.powers = [
        SimpleNamespace(power_name="Constricted", amount=6),
        SimpleNamespace(power_name="Rupture", amount=1),
    ]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    projected = simulator.project_end_turn_effects(SimulationState(context))

    assert projected.player_hp == context.game.current_hp - 6
    assert projected.player_strength == 0
    assert projected.player_constricted == 6


def test_outcome_score_counts_constricted_end_turn_death():
    context = _combat_context([], energy=0, monsters=[_green_louse_debuff(current_hp=20)])
    context.game.current_hp = 5
    context.player_hp = 5
    context.player_hp_pct = 5 / context.game.max_hp
    context.game.player.powers = [SimpleNamespace(power_name="Constricted", amount=6)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)
    final_state = initial_state.clone()

    score = simulator.calculate_outcome_score(initial_state, final_state, context=context)

    assert score == float("-inf")


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


def test_simulation_death_split_handler_uses_live_monster_id(monkeypatch):
    class CanonicalOnlySplitLoader:
        def __init__(self):
            self.data_names = []

        def get_enhanced_monster_data(self, monster_name):
            self.data_names.append(monster_name)
            if monster_name == "Slime Boss":
                return {
                    "special_mechanics": {
                        "type": "death_split",
                        "split_conditions": {"hp_threshold": 50},
                        "splits_into": ["Acid Slime (L)", "Spike Slime (L)"],
                    }
                }
            return None

    monster_loader = CanonicalOnlySplitLoader()
    monkeypatch.setattr(simulation, "game_data_loader", monster_loader)
    slime_boss = _slime_boss(current_hp=56)
    slime_boss.name = "SlimeBoss"
    context = _combat_context([], energy=0, monsters=[slime_boss])
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._handle_death_split(state, state.monsters[0], 0)

    assert state.monsters[0]["split_pending"] is True
    assert monster_loader.data_names[0] == "Slime Boss"


def test_ironclad_detects_slime_boss_without_elite_marker():
    context = _combat_context([], energy=0, monsters=[_slime_boss(current_hp=80)])

    assert IroncladCombatPlanner()._detect_elite_type(context) == ironclad_combat.EliteType.SLIME_BOSS


def test_gremlin_nob_detection_accepts_live_monster_id():
    context = _combat_context([], energy=0, monsters=[_gremlin_nob()])
    planner = IroncladCombatPlanner()

    assert planner._has_gremlin_nob(context)
    assert planner._detect_elite_type(context) == ironclad_combat.EliteType.GREMLIN_NOB


def test_ironclad_low_scaling_check_uses_live_monster_id_for_summoners(monkeypatch):
    class CanonicalOnlyMonsterLoader:
        def __init__(self):
            self.summoner_names = []

        def is_monster_summoner(self, monster_name):
            self.summoner_names.append(monster_name)
            return monster_name == "Bronze Automaton"

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def get_monster_threat_profile(self, _monster_name):
            return {"scaling_threat": 0}

    monster_loader = CanonicalOnlyMonsterLoader()
    monkeypatch.setattr(ironclad_combat, "game_data_loader", monster_loader)
    context = _combat_context([], energy=0, monsters=[_bronze_automaton()])

    assert IroncladCombatPlanner()._is_low_scaling_encounter(context) is False
    assert monster_loader.summoner_names == ["Bronze Automaton"]


def test_ironclad_low_scaling_check_uses_live_monster_id_for_threat_profile(monkeypatch):
    class CanonicalOnlyMonsterLoader:
        def __init__(self):
            self.profile_names = []

        def is_monster_summoner(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def get_monster_threat_profile(self, monster_name):
            self.profile_names.append(monster_name)
            if monster_name == "Red Slaver":
                return {"scaling_threat": 5}
            return {"scaling_threat": 0}

    monster_loader = CanonicalOnlyMonsterLoader()
    monkeypatch.setattr(ironclad_combat, "game_data_loader", monster_loader)
    context = _combat_context([], energy=0, monsters=[_red_slaver()])

    assert IroncladCombatPlanner()._is_low_scaling_encounter(context) is False
    assert monster_loader.profile_names == ["Red Slaver"]


def test_lagavulin_strategy_accepts_string_turn_for_siphon_pressure():
    planner = IroncladCombatPlanner()

    int_context = _combat_context([], energy=0, monsters=[_lagavulin()])
    int_context.turn = 6
    int_initial = SimulationState(int_context)
    int_final = int_initial.clone()
    int_final.total_damage_dealt = 10
    int_score = planner._apply_lagavulin_strategy(
        [],
        int_initial,
        int_final,
        int_context,
        0.0,
    )

    string_context = _combat_context([], energy=0, monsters=[_lagavulin()])
    string_context.turn = "6"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_final.total_damage_dealt = 10
    string_score = planner._apply_lagavulin_strategy(
        [],
        string_initial,
        string_final,
        string_context,
        0.0,
    )

    assert string_score == int_score


def test_a20_elite_aggression_uses_context_ascension_level():
    context = _combat_context([], energy=0, monsters=[_gremlin_nob()])
    context.turn = 1
    context.ascension_level = 20
    context.game.ascension_level = 20
    initial_state = SimulationState(context)
    final_state = initial_state.clone()
    planner = IroncladCombatPlanner()

    score = planner._apply_elite_strategy_override(
        ironclad_combat.EliteType.GREMLIN_NOB,
        [],
        initial_state,
        final_state,
        context,
        0.0,
    )

    assert score == -50.0


def test_a20_elite_aggression_accepts_string_turn_for_early_penalty():
    planner = IroncladCombatPlanner()

    int_context = _combat_context([], energy=0, monsters=[_gremlin_nob()])
    int_context.turn = 1
    int_initial = SimulationState(int_context)
    int_final = int_initial.clone()
    int_score = planner._apply_a20_early_aggression(
        [],
        int_initial,
        int_final,
        int_context,
        0.0,
    )

    string_context = _combat_context([], energy=0, monsters=[_gremlin_nob()])
    string_context.turn = "1"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_score = planner._apply_a20_early_aggression(
        [],
        string_initial,
        string_final,
        string_context,
        0.0,
    )

    assert string_score == int_score == -50.0


def test_a20_elite_aggression_counts_killed_sentry_progress():
    killed_sentry = _sentry(current_hp=39)
    killed_sentry.current_hp = 0
    killed_sentry.is_gone = True
    alive_sentries = [_sentry(current_hp=39), _sentry(current_hp=39)]
    context = _combat_context([], energy=0, monsters=alive_sentries)
    context.turn = 3
    context.ascension_level = 20
    context.game.ascension_level = 20
    context.game.monsters = [killed_sentry] + alive_sentries
    initial_state = SimulationState(context)
    final_state = initial_state.clone()
    planner = IroncladCombatPlanner()

    score = planner._apply_a20_early_aggression(
        [],
        initial_state,
        final_state,
        context,
        0.0,
    )

    assert score == 0.0


def test_a20_elite_aggression_rejects_nonfinite_monster_hp_progress():
    unknown_hp_sentry = _sentry(current_hp=39)
    unknown_hp_sentry.current_hp = float("inf")
    context = _combat_context([], energy=0, monsters=[unknown_hp_sentry])
    context.turn = 3
    initial_state = SimpleNamespace(total_damage_dealt=0)
    final_state = SimpleNamespace(total_damage_dealt=0)
    planner = IroncladCombatPlanner()

    score = planner._apply_a20_early_aggression(
        [],
        initial_state,
        final_state,
        context,
        0.0,
    )

    assert score == -150.0


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


def test_slime_boss_strategy_uses_parsed_aoe_damage_without_damage_field(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_slime_boss(current_hp=80)],
    )

    score = IroncladCombatPlanner()._apply_slime_boss_strategy(
        [PlayCardAction(card=cleave)],
        context,
        0.0,
    )

    assert score == 12.0


def test_slime_boss_strategy_accepts_string_attack_type_for_parsed_aoe(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.type = "ATTACK"
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_slime_boss(current_hp=80)],
    )

    score = IroncladCombatPlanner()._apply_slime_boss_strategy(
        [PlayCardAction(card=cleave)],
        context,
        0.0,
    )

    assert score == 12.0


def test_slime_boss_strategy_accepts_string_hp_for_split_window_bonus():
    carnage = _card("Carnage", "Carnage", cost=2)
    carnage.damage = 20
    context = _combat_context(
        [carnage],
        energy=2,
        monsters=[_slime_boss(current_hp="70", max_hp="140")],
    )

    score = IroncladCombatPlanner()._apply_slime_boss_strategy(
        [PlayCardAction(card=carnage)],
        context,
        0.0,
    )

    assert score == 30.0


def test_sentries_damage_distribution_uses_parsed_damage_without_damage_field(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_louse(current_hp=40), _louse(current_hp=40), _louse(current_hp=40)],
    )

    distribution = IroncladCombatPlanner()._calculate_damage_distribution(
        [PlayCardAction(card=strike, target_monster=context.monsters_alive[1])],
        context,
    )

    assert distribution["highest_damage"] == 6
    assert distribution["total_damage"] == 6
    assert distribution["target_count"] == 1


def test_sentries_damage_distribution_uses_live_index_for_distinct_target_object(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_sentry(current_hp=40), _sentry(current_hp=40), _sentry(current_hp=40)],
    )
    context.vulnerable_stacks[1] = 1
    target = SimpleNamespace(
        name="Sentry",
        monster_id="Sentry",
        current_hp=40,
        block=0,
        monster_index=1,
    )

    distribution = IroncladCombatPlanner()._calculate_damage_distribution(
        [PlayCardAction(card=strike, target_monster=target)],
        context,
    )

    assert distribution["highest_damage"] == 9
    assert distribution["total_damage"] == 9
    assert distribution["target_count"] == 1


def test_end_turn_projection_materializes_due_slime_boss_split():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_slime_boss(current_hp=56)])
    state = SimulationState(context)

    projected = FastCombatSimulator(SynergyCardEvaluator()).project_end_turn_effects(state)

    alive = [monster for monster in projected.monsters if not monster["is_gone"]]
    assert [monster["name"] for monster in alive] == ["Acid Slime (L)", "Spike Slime (L)"]
    assert [monster["hp"] for monster in alive] == [56, 56]


def test_special_monster_preprocessing_ignores_zero_hp_stale_simulated_monsters():
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    context = _combat_context([defend], energy=1, monsters=[_slime_boss(current_hp=56)])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert not result.monsters[0].get("split_pending", False)


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


def test_enemy_lookahead_depth_counts_only_live_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    stale = _louse(current_hp=50)
    live = _louse(current_hp=50)
    context = _combat_context([strike], energy=1, monsters=[stale, live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    depth = FastCombatSimulator(SynergyCardEvaluator())._get_enemy_lookahead_depth(
        state,
        context,
        max_depth=2,
    )

    assert depth == 1


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


def test_enemy_lookahead_fallback_does_not_reapply_strength_to_adjusted_damage():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    state.monsters[0]["move_adjusted_damage"] = 9
    state.monsters[0]["move_base_damage"] = 7
    state.monsters[0]["strength"] = 2
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: None
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: None

    future_damage = simulator.simulate_enemy_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert future_damage == 9


def test_incoming_damage_estimate_does_not_reapply_weak_to_adjusted_damage():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    state = SimulationState(context)
    state.monsters[0]["weak"] = 1

    incoming_damage = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        state.monsters
    )

    assert incoming_damage == 7


def test_incoming_damage_estimate_applies_weak_to_base_damage_fallback():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    state = SimulationState(context)
    state.monsters[0]["move_adjusted_damage"] = None
    state.monsters[0]["move_base_damage"] = 7
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


def test_enemy_lookahead_fallback_does_not_reapply_weak_to_adjusted_damage():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=50)])
    context.turn = 1
    state = SimulationState(context)
    state.monsters[0]["weak"] = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    simulator._current_monster_move = lambda *_args, **_kwargs: None
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: None

    future_damage = simulator.simulate_enemy_lookahead(
        state,
        context,
        look_ahead=1,
    )

    assert future_damage == 7


def test_enemy_lookahead_fallback_refreshes_damage_when_weak_expires():
    strike = _card("Strike_R", "Strike", cost=1)
    monster = _louse(current_hp=50)
    monster.move_base_damage = 10
    monster.move_adjusted_damage = 7
    context = _combat_context([strike], energy=1, monsters=[monster])
    context.turn = 1
    state = SimulationState(context)
    state.monsters[0]["weak"] = 1
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    current_move = {"name": "Bite", "intent": "ATTACK", "damage": 10, "hits": 1}
    simulator._current_monster_move = lambda *_args, **_kwargs: current_move
    simulator._predicted_monster_move_for_step = lambda *_args, **_kwargs: None

    future_damage = simulator.simulate_enemy_lookahead(
        state,
        context,
        look_ahead=2,
    )

    assert future_damage == 15


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


def test_big_attack_pattern_ignores_high_damage_non_attack_moves():
    database = EnhancedMonsterDatabase()
    database._data["Training Dummy"] = {
        "moves": [
            {"name": "Feint", "intent": "NOT_ATTACK", "damage": 99},
            {"name": "Harden", "intent": "BUFF", "damage": 50},
            {"name": "Heavy Strike", "intent": "ATTACK", "damage": 21},
        ],
        "pattern": {},
    }

    big_attacks = database.get_big_attack_pattern("Training Dummy")

    assert [attack["move"] for attack in big_attacks] == ["Heavy Strike"]


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


def test_simulator_resolves_distinct_target_object_by_live_monster_id(monkeypatch):
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
    second = _red_slaver(current_hp=40)
    context = _combat_context([strike], energy=1, monsters=[first, second])
    target = SimpleNamespace(name="Red Slaver", monster_id="SlaverRed", current_hp=40)

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        context=context,
    )

    assert result.monsters[0]["hp"] == 40
    assert result.monsters[1]["hp"] == 34


def test_simulator_resolves_distinct_target_object_by_live_monster_index(monkeypatch):
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
    target = SimpleNamespace(
        name="Louse",
        monster_id="FuzzyLouseNormal",
        current_hp=40,
        monster_index=1,
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        context=context,
    )

    assert result.monsters[0]["hp"] == 40
    assert result.monsters[1]["hp"] == 34


def test_simulator_prefers_target_monster_over_stale_target_index(monkeypatch):
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
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_sentry(current_hp=40), _sentry(current_hp=40)],
    )
    context.vulnerable_stacks[1] = 1
    target = SimpleNamespace(
        name="Sentry",
        monster_id="Sentry",
        current_hp=40,
        monster_index=1,
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=target,
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["hp"] == 40
    assert result.monsters[1]["hp"] == 31


def test_incoming_damage_estimate_multiplies_monster_hits():
    monster = _louse(current_hp=40)
    monster.move_adjusted_damage = 6
    monster.move_hits = 3
    context = _combat_context([], energy=3, monsters=[monster])
    state = SimulationState(context)

    incoming = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(state.monsters)

    assert incoming == 18


def test_incoming_damage_estimate_does_not_reapply_strength_to_adjusted_damage():
    monster = _louse(current_hp=40)
    monster.move_adjusted_damage = 9
    monster.strength = 2
    context = _combat_context([], energy=3, monsters=[monster])
    state = SimulationState(context)

    incoming = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(state.monsters)

    assert incoming == 9


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


def test_incoming_damage_estimate_ignores_negated_attack_intent_string():
    incoming = FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        [
            {
                "name": "Cultist",
                "monster_id": "Cultist",
                "move_id": 1,
                "current_hp": 48,
                "is_gone": False,
                "intent": "NOT_ATTACK",
                "move_adjusted_damage": 12,
                "move_hits": 1,
                "strength": 0,
                "weak": 0,
            }
        ]
    )

    assert incoming == 0


def test_strongest_known_attack_damage_ignores_negated_attack_intent(monkeypatch):
    class FakeLoader:
        def get_monster_moves(self, _monster_name):
            return [
                {"name": "Feint", "intent": "NOT_ATTACK", "damage": 99, "hits": 1},
                {"name": "Harden", "intent": "BUFF", "damage": 50, "hits": 1},
                {"name": "Strike", "intent": "ATTACK", "damage": 7, "hits": 2},
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())

    damage = FastCombatSimulator(SynergyCardEvaluator())._strongest_known_attack_damage(
        "Training Dummy"
    )

    assert damage == 14


def test_incoming_damage_estimate_keeps_explicit_zero_adjusted_damage():
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    explicit_zero = simulator._estimate_incoming_damage(
        [
            {
                "name": "Jaw Worm",
                "monster_id": "JawWorm",
                "move_id": 1,
                "current_hp": 40,
                "is_gone": False,
                "intent": "Intent.ATTACK",
                "move_adjusted_damage": 0,
                "move_base_damage": 11,
                "move_hits": 1,
                "strength": 0,
                "weak": 0,
            }
        ]
    )
    missing_adjusted = simulator._estimate_incoming_damage(
        [
            {
                "name": "Jaw Worm",
                "monster_id": "JawWorm",
                "move_id": 1,
                "current_hp": 40,
                "is_gone": False,
                "intent": "Intent.ATTACK",
                "move_adjusted_damage": None,
                "move_base_damage": 11,
                "move_hits": 1,
                "strength": 0,
                "weak": 0,
            }
        ]
    )

    assert explicit_zero == 0
    assert missing_adjusted == 11


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


def test_single_target_selection_ignores_half_dead_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    waiting_darkling = _darkling(current_hp=20)
    live_darkling = _darkling(current_hp=40)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[waiting_darkling, live_darkling],
    )
    state = SimulationState(context)
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["is_gone"] = False

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card(
        strike,
        context,
        state,
    )

    assert target is live_darkling
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


def test_reaper_target_selection_accepts_string_strength_for_aoe():
    reaper = _card(
        "Reaper",
        "Reaper",
        card_type=CardType.ATTACK,
        cost=2,
        has_target=False,
    )
    context = _combat_context(
        [reaper],
        energy=2,
        monsters=[_louse(current_hp=40), _louse(current_hp=40)],
    )
    context.strength = "3"

    try:
        target, target_idx = IroncladCombatPlanner()._choose_target_for_card(
            reaper,
            context,
            SimulationState(context),
        )
    except TypeError:
        target, target_idx = "type-error", "type-error"

    assert target is None
    assert target_idx is None


def test_standard_targeting_uses_parsed_damage_for_plain_card_lethals(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    strike = _card("Strike_R", "Strike", cost=1)
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[high_threat, killable])
    monkeypatch.setattr(
        ironclad_combat,
        "evaluate_monster_threat",
        lambda monster, _context: 100 if monster is high_threat else 1,
    )
    state = SimulationState(context)

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card(
        strike,
        context,
        state,
    )

    assert target is killable
    assert target_idx == 1


def test_ironclad_targeting_treats_string_attack_as_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[high_threat, killable])
    monkeypatch.setattr(
        ironclad_combat,
        "evaluate_monster_threat",
        lambda monster, _context: 100 if monster is high_threat else 1,
    )

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card(
        strike,
        context,
        SimulationState(context),
    )

    assert target is killable
    assert target_idx == 1


def test_ironclad_single_target_attack_accepts_string_attack_type():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"

    assert IroncladCombatPlanner()._is_single_target_attack(strike, target_idx=0) is True


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


def test_v2_single_target_selection_ignores_half_dead_simulated_monsters():
    strike = _card("Strike_R", "Strike", cost=1)
    waiting_darkling = _darkling(current_hp=20)
    live_darkling = _darkling(current_hp=40)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[waiting_darkling, live_darkling],
    )
    context.compute_threat_v2 = lambda monster: 1
    state = SimulationState(context)
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["is_gone"] = False

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        state,
    )

    assert target is live_darkling
    assert target_idx == 1


def test_v2_targeting_treats_string_attack_as_attack(monkeypatch):
    class FakeMonsterLoader:
        def is_monster_summoner(self, _monster_name):
            return False

        def get_monster_minions(self, _monster_name):
            return []

        def is_monster_hibernating(self, _monster_name, _turn):
            return False

        def does_monster_have_death_split(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def is_monster_duo_boss(self, _monster_name):
            return False

    monkeypatch.setattr(ironclad_combat, "game_data_loader", FakeMonsterLoader())
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    vulnerable_high_threat = _louse(current_hp=40)
    non_vulnerable_low_threat = _louse(current_hp=40)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[vulnerable_high_threat, non_vulnerable_low_threat],
    )
    context.compute_threat_v2 = lambda monster: 100 if monster is vulnerable_high_threat else 1
    state = SimulationState(context)
    state.monsters[0]["vulnerable"] = 1

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        state,
    )

    assert target is non_vulnerable_low_threat
    assert target_idx == 1


def test_v2_targeting_accepts_string_turn_for_hibernation_filter(monkeypatch):
    class FakeMonsterLoader:
        def is_monster_summoner(self, _monster_name):
            return False

        def get_monster_minions(self, _monster_name):
            return []

        def is_monster_hibernating(self, monster_name, turn):
            return monster_name == "Lagavulin" and turn == 1

        def does_monster_have_death_split(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def is_monster_duo_boss(self, _monster_name):
            return False

    monkeypatch.setattr(ironclad_combat, "game_data_loader", FakeMonsterLoader())
    strike = _card("Strike_R", "Strike", cost=1)
    sleeping_lagavulin = _lagavulin(intent="NOT_ATTACK", move_adjusted_damage=0)
    awake_louse = _louse(current_hp=40)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[sleeping_lagavulin, awake_louse],
    )
    context.turn = "1"
    context.compute_threat_v2 = lambda monster: 100 if monster is sleeping_lagavulin else 1
    state = SimulationState(context)

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        state,
    )

    assert target is awake_louse
    assert target_idx == 1


def test_v2_split_targeting_uses_parsed_damage_for_plain_cards(monkeypatch):
    class FakeMonsterLoader:
        def is_monster_summoner(self, _monster_name):
            return False

        def get_monster_minions(self, _monster_name):
            return []

        def is_monster_hibernating(self, _monster_name, _turn):
            return False

        def does_monster_have_death_split(self, monster_name):
            return monster_name == "Acid Slime (L)"

        def get_enhanced_monster_data(self, monster_name):
            if monster_name == "Acid Slime (L)":
                return {
                    "special_mechanics": {
                        "split_conditions": {"hp_threshold": 50}
                    }
                }
            return None

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def is_monster_duo_boss(self, _monster_name):
            return False

    card_loader = GameDataLoader(auto_load=False)
    card_loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", FakeMonsterLoader())
    monkeypatch.setattr(simulation, "game_data_loader", card_loader)

    strike = _card("Strike_R", "Strike", cost=1)
    high_threat = _louse(current_hp=40)
    splitting = _acid_slime_l(current_hp=6, max_hp=65)
    context = _combat_context([strike], energy=1, monsters=[high_threat, splitting])
    context.compute_threat_v2 = lambda monster: 100 if monster is high_threat else 1
    state = SimulationState(context)

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        state,
    )

    assert target is splitting
    assert target_idx == 1


def test_v2_phase_change_targeting_accepts_string_hp_for_burst_window(monkeypatch):
    class FakeMonsterLoader:
        def is_monster_summoner(self, _monster_name):
            return False

        def get_monster_minions(self, _monster_name):
            return []

        def is_monster_hibernating(self, _monster_name, _turn):
            return False

        def does_monster_have_death_split(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, monster_name):
            return monster_name == "The Guardian"

        def get_monster_recommended_strategy(self, monster_name):
            if monster_name == "The Guardian":
                return {"primary": "burst_50_percent_window"}
            return None

        def is_monster_duo_boss(self, _monster_name):
            return False

    monkeypatch.setattr(ironclad_combat, "game_data_loader", FakeMonsterLoader())

    strike = _card("Strike_R", "Strike", cost=1)
    high_threat = _louse(current_hp=40)
    guardian = _guardian(current_hp="100")
    guardian.max_hp = "240"
    context = _combat_context([strike], energy=1, monsters=[high_threat, guardian])
    context.compute_threat_v2 = lambda monster: 100 if monster is high_threat else 1

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        SimulationState(context),
    )

    assert target is guardian
    assert target_idx == 1


def test_v2_summoner_targeting_matches_live_bronze_orbs_by_id(monkeypatch):
    class FakeMonsterLoader:
        def __init__(self):
            self.summoner_names = []

        def is_monster_summoner(self, monster_name):
            self.summoner_names.append(monster_name)
            return monster_name == "Bronze Automaton"

        def get_monster_minions(self, monster_name):
            if monster_name == "Bronze Automaton":
                return ["Bronze Orb"]
            return []

        def get_monster_recommended_strategy(self, monster_name):
            if monster_name == "Bronze Automaton":
                return {"primary": "kill_minions_first"}
            return None

        def is_monster_hibernating(self, _monster_name, _turn):
            return False

        def does_monster_have_death_split(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def is_monster_duo_boss(self, _monster_name):
            return False

    automaton = _bronze_automaton()
    first_orb = _bronze_orb()
    second_orb = _bronze_orb(current_hp=40, intent=Intent.ATTACK, move_id=1, move_adjusted_damage=8)
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[automaton, first_orb, second_orb])
    context.compute_threat_v2 = lambda monster: 100 if monster is automaton else 1
    state = SimulationState(context)
    monster_loader = FakeMonsterLoader()
    monkeypatch.setattr(ironclad_combat, "game_data_loader", monster_loader)

    target, target_idx = IroncladCombatPlanner()._choose_target_for_card_v2(
        strike,
        context,
        state,
    )

    assert target is first_orb
    assert target_idx == 1
    assert "Bronze Automaton" in monster_loader.summoner_names


def test_simulation_summoner_handler_uses_live_monster_id(monkeypatch):
    class CanonicalOnlySummonerLoader:
        def __init__(self):
            self.summoner_names = []
            self.minion_names = []

        def is_monster_summoner(self, monster_name):
            self.summoner_names.append(monster_name)
            return monster_name == "Bronze Automaton"

        def get_monster_minions(self, monster_name):
            self.minion_names.append(monster_name)
            if monster_name == "Bronze Automaton":
                return ["Bronze Orb"]
            return []

    monster_loader = CanonicalOnlySummonerLoader()
    monkeypatch.setattr(data_loader_module, "game_data_loader", monster_loader)
    context = _combat_context([], energy=0, monsters=[_bronze_automaton()])
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._handle_summoner(state, state.monsters[0])

    assert state.monsters[0]["is_summoner"] is True
    assert state.monsters[0]["minions"] == ["Bronze Orb"]
    assert monster_loader.summoner_names == ["Bronze Automaton"]
    assert monster_loader.minion_names == ["Bronze Automaton"]


def test_simulation_phase_change_handler_uses_live_monster_id(monkeypatch):
    class CanonicalOnlyPhaseLoader:
        def __init__(self):
            self.phase_names = []
            self.data_names = []

        def does_monster_have_phase_change(self, monster_name):
            self.phase_names.append(monster_name)
            return monster_name == "The Guardian"

        def get_enhanced_monster_data(self, monster_name):
            self.data_names.append(monster_name)
            if monster_name == "The Guardian":
                return {
                    "special_mechanics": {
                        "phases": [
                            {
                                "threshold_percent": 50,
                                "name": "Defensive Mode",
                                "burst_window": True,
                            }
                        ]
                    }
                }
            return None

    monster_loader = CanonicalOnlyPhaseLoader()
    monkeypatch.setattr(data_loader_module, "game_data_loader", monster_loader)
    guardian = _guardian(current_hp=100)
    guardian.name = "Guardian"
    context = _combat_context([], energy=0, monsters=[guardian])
    state = SimulationState(context)

    FastCombatSimulator(SynergyCardEvaluator())._handle_phase_change(state, state.monsters[0])

    assert state.monsters[0]["current_phase"] == "Defensive Mode"
    assert state.monsters[0]["phase_burst_window"] is True
    assert monster_loader.phase_names == ["The Guardian"]
    assert monster_loader.data_names == ["The Guardian"]


def test_aoe_decision_matches_live_bronze_orb_minions_by_id(monkeypatch):
    class FakeMonsterLoader:
        def __init__(self):
            self.summoner_names = []

        def is_monster_summoner(self, monster_name):
            self.summoner_names.append(monster_name)
            return monster_name == "Bronze Automaton"

        def get_monster_minions(self, monster_name):
            if monster_name == "Bronze Automaton":
                return ["Bronze Orb"]
            return []

        def does_monster_have_death_split(self, _monster_name):
            return False

        def is_monster_duo_boss(self, _monster_name):
            return False

    automaton = _bronze_automaton()
    first_orb = _bronze_orb()
    second_orb = _bronze_orb(current_hp=40, intent=Intent.ATTACK, move_id=1, move_adjusted_damage=8)
    context = _combat_context([], monsters=[automaton, first_orb, second_orb])
    state = SimulationState(context)
    monster_loader = FakeMonsterLoader()
    monkeypatch.setattr(ironclad_combat, "game_data_loader", monster_loader)

    assert IroncladCombatPlanner()._should_use_aoe("Cleave", context, state)
    assert "Bronze Automaton" in monster_loader.summoner_names


def test_aoe_decision_ignores_zero_hp_stale_simulated_monsters():
    stale = _louse(current_hp=40)
    first_live = _louse(current_hp=40)
    second_live = _louse(current_hp=40)
    context = _combat_context([], monsters=[stale, first_live, second_live])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    assert not IroncladCombatPlanner()._should_use_aoe("Cleave", context, state)


def test_aoe_decision_accepts_string_strength_for_reaper():
    context = _combat_context(
        [],
        monsters=[_louse(current_hp=40), _louse(current_hp=40)],
    )
    context.strength = "3"
    state = SimulationState(context)

    try:
        should_use_aoe = IroncladCombatPlanner()._should_use_aoe("Reaper", context, state)
    except TypeError:
        should_use_aoe = "type-error"

    assert should_use_aoe is True


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
    iron_wave = _card("Iron Wave", "Iron Wave", cost=1, upgrades=None)
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

    thunderclap = _card("Thunderclap", "Thunderclap", cost=1, has_target=False, upgrades=None)
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


def test_aoe_attack_does_not_count_zero_hp_stale_simulated_monster_hits(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=20), _louse(current_hp=20)],
    )
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        cleave,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.damage_instances == 1


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
    pommel = _card("Pommel Strike", "Pommel Strike", cost=1, upgrades=None)
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


def test_entrench_triggers_juggernaut_for_doubled_block():
    entrench = _card(
        "Entrench",
        "Entrench",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    context = _combat_context([entrench], energy=2, monsters=[_louse(current_hp=20)])
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]
    initial_state = SimulationState(context)
    initial_state.player_block = 6

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        initial_state,
        entrench,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 12
    assert result.total_damage_dealt == 5
    assert result.damage_instances == 1
    assert result.monsters[0]["hp"] == 15


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
    assert result.status_cards_added == 2
    assert result.dazed_cards_added == 0


def test_power_through_wounds_are_available_to_followup_second_wind(monkeypatch):
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
        "Power Through",
        "Power Through",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    second_wind = _card(
        "Second Wind",
        "Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context(
        [power_through, second_wind],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    after_power_through = simulator.simulate_card_play(
        SimulationState(context),
        power_through,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        after_power_through,
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 25
    assert result.exhaust_events == 2
    assert result.status_cards_added == 0


def test_power_through_wounds_are_available_to_followup_fiend_fire(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust.",
        },
        "power through": {
            "name": "Power Through",
            "description": "Gain 15 Block.\nAdd 2 Wounds into your hand.",
        },
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "#Exhaust your hand.\nDeal [7|10] damage for each card #Exhausted.\n#Exhaust.",
        },
        "power through": {
            "name": "Power Through",
            "text": "Gain [15|20] #Block.\nAdd 2 #Wounds into your hand.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    power_through = _card(
        "Power Through",
        "Power Through",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    context = _combat_context(
        [power_through, fiend_fire],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    after_power_through = simulator.simulate_card_play(
        SimulationState(context),
        power_through,
        target=None,
        target_index=None,
        context=context,
    )
    result = simulator.simulate_card_play(
        after_power_through,
        fiend_fire,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 14
    assert result.damage_instances == 2
    assert result.exhaust_events == 3
    assert result.status_cards_added == 0


def test_block_skill_ignores_stale_zero_block_attribute(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "defend": {
            "name": "Defend",
            "description": "Gain 5 Block.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend.block = 0
    context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=100)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        defend,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 5


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


def test_second_wind_keeps_string_attack_cards():
    second_wind = _card(
        "Second Wind",
        "Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    context = _combat_context(
        [second_wind, defend, strike],
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

    assert result.player_block == 5
    assert result.exhaust_events == 1


def test_second_wind_applies_card_block_modifiers_per_exhausted_card():
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
    context = _combat_context(
        [second_wind, defend, power_through],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.game.player.powers = [
        SimpleNamespace(power_name="Dexterity", amount=2),
        SimpleNamespace(power_name="Frail", amount=1),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 10
    assert result.exhaust_events == 2


def test_second_wind_block_triggers_juggernaut_per_exhausted_card():
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
        monsters=[_louse(current_hp=30)],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        second_wind,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 10
    assert result.exhaust_events == 2
    assert result.total_damage_dealt == 10
    assert result.damage_instances == 2
    assert result.monsters[0]["hp"] == 20


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
    assert [card_key[0] for card_key in played_key[2]] == ["Defend_R"]


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
        upgrades=None,
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


def _patch_feed_loader(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "feed": {
            "name": "Feed",
            "description": "Deal 10 damage. If this kills a non-minion enemy, gain 3 Max HP. Exhaust.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)


def test_feed_kill_increases_max_hp_and_current_hp(monkeypatch):
    _patch_feed_loader(monkeypatch)

    feed = _card("Feed", "Feed", cost=1, upgrades=None)
    context = _combat_context([feed], energy=1, monsters=[_louse(current_hp=8)])
    context.game.current_hp = 30
    context.player_hp = 30

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        feed,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.monsters[0]["is_gone"] is True
    assert result.player_max_hp == 83
    assert result.player_hp == 33


def test_upgraded_feed_uses_12_damage_and_4_max_hp(monkeypatch):
    _patch_feed_loader(monkeypatch)

    feed_plus = _card("Feed", "Feed+", cost=1, upgrades=1)
    context = _combat_context([feed_plus], energy=1, monsters=[_louse(current_hp=12)])
    context.game.current_hp = 30
    context.player_hp = 30

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        feed_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 12
    assert result.monsters[0]["is_gone"] is True
    assert result.player_max_hp == 84
    assert result.player_hp == 34


def _patch_reward_attack_loader(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "hand of greed": {
            "name": "Hand of Greed",
            "description": "Deal 20 damage. If Fatal, gain 20 Gold.",
        },
        "lesson learned": {
            "name": "Lesson Learned",
            "description": (
                "Deal 10 damage. If Fatal, Upgrade a random card in your deck. "
                "Exhaust."
            ),
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)


def test_upgraded_hand_of_greed_uses_25_damage(monkeypatch):
    _patch_reward_attack_loader(monkeypatch)

    hand_of_greed_plus = _card("Hand of Greed", "Hand of Greed+", cost=2, upgrades=1)
    context = _combat_context(
        [hand_of_greed_plus],
        energy=2,
        monsters=[_louse(current_hp=40)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        hand_of_greed_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 25


def test_upgraded_lesson_learned_uses_13_damage(monkeypatch):
    _patch_reward_attack_loader(monkeypatch)

    lesson_learned_plus = _card("Lesson Learned", "Lesson Learned+", cost=2, upgrades=1)
    context = _combat_context(
        [lesson_learned_plus],
        energy=2,
        monsters=[_louse(current_hp=40)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        lesson_learned_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 13


def _patch_simple_colorless_attack_loader(monkeypatch, module=simulation):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "flash of steel": {
            "name": "Flash of Steel",
            "description": "Deal 3 damage. Draw 1 card.",
        },
        "swift strike": {
            "name": "Swift Strike",
            "description": "Deal 7 damage.",
        },
        "dramatic entrance": {
            "name": "Dramatic Entrance",
            "description": "Innate. Deal 8 damage to ALL enemies. Exhaust.",
        },
        "shiv": {
            "name": "Shiv",
            "description": "Deal 4 damage. Exhaust.",
        },
        "smite": {
            "name": "Smite",
            "description": "Retain. Deal 12 damage. Exhaust.",
        },
        "through violence": {
            "name": "Through Violence",
            "description": "Retain. Deal 20 damage. Exhaust.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(module, "game_data_loader", loader)


def test_upgraded_flash_of_steel_uses_6_damage(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch)

    flash_plus = _card("Flash of Steel", "Flash of Steel+", cost=0, upgrades=1)
    context = _combat_context([flash_plus], energy=0, monsters=[_louse(current_hp=20)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        flash_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 6


def test_upgraded_swift_strike_uses_10_damage(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch)

    swift_plus = _card("Swift Strike", "Swift Strike+", cost=0, upgrades=1)
    context = _combat_context([swift_plus], energy=0, monsters=[_louse(current_hp=20)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        swift_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 10


def test_upgraded_dramatic_entrance_uses_12_aoe_damage(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch)

    dramatic_plus = _card(
        "Dramatic Entrance",
        "Dramatic Entrance+",
        cost=0,
        upgrades=1,
        has_target=False,
    )
    context = _combat_context(
        [dramatic_plus],
        energy=0,
        monsters=[_louse(current_hp=20), _louse(current_hp=20)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        dramatic_plus,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 24


def test_upgraded_shiv_uses_6_damage(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch)

    shiv_plus = _card("Shiv", "Shiv+", cost=0, upgrades=1)
    context = _combat_context([shiv_plus], energy=0, monsters=[_louse(current_hp=20)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        shiv_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 6


def test_upgraded_smite_uses_16_damage(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch)

    smite_plus = _card("Smite", "Smite+", cost=1, upgrades=1)
    context = _combat_context([smite_plus], energy=1, monsters=[_louse(current_hp=30)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        smite_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 16


def test_upgraded_through_violence_uses_30_damage(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch)

    through_violence_plus = _card(
        "Through Violence",
        "Through Violence+",
        cost=0,
        upgrades=1,
    )
    context = _combat_context(
        [through_violence_plus],
        energy=0,
        monsters=[_louse(current_hp=40)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        through_violence_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 30


def _patch_bite_loader(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bite": {
            "name": "Bite",
            "description": "Deal 7 damage. Heal 2 HP.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)


def test_bite_heals_fixed_amount(monkeypatch):
    _patch_bite_loader(monkeypatch)

    bite = _card("Bite", "Bite", cost=1, upgrades=None)
    context = _combat_context([bite], energy=1, monsters=[_louse(current_hp=20)])
    context.game.current_hp = 20
    context.player_hp = 20

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bite,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 7
    assert result.player_hp == 22


def test_upgraded_bite_uses_8_damage_and_heals_3(monkeypatch):
    _patch_bite_loader(monkeypatch)

    bite_plus = _card("Bite", "Bite+", cost=1, upgrades=1)
    context = _combat_context([bite_plus], energy=1, monsters=[_louse(current_hp=20)])
    context.game.current_hp = 20
    context.player_hp = 20

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bite_plus,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 8
    assert result.player_hp == 23


def test_feed_does_not_gain_max_hp_from_minion(monkeypatch):
    _patch_feed_loader(monkeypatch)

    feed = _card("Feed", "Feed", cost=1)
    minion = _louse(current_hp=8)
    minion.powers = [SimpleNamespace(power_name="Minion", amount=0)]
    context = _combat_context([feed], energy=1, monsters=[minion])
    context.game.current_hp = 30
    context.player_hp = 30

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        feed,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["is_gone"] is True
    assert result.player_max_hp == 80
    assert result.player_hp == 30


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


def test_random_target_attack_ignores_zero_hp_stale_simulated_monsters(monkeypatch):
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
    sword_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1, has_target=False)
    context = _combat_context(
        [sword_boomerang],
        energy=1,
        monsters=[_louse(current_hp=20), _louse(current_hp=20)],
    )
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        sword_boomerang,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.total_damage_dealt == 9
    assert result.monsters[1]["hp"] == 11


def test_attack_damage_clamps_negative_player_strength_before_block():
    strike = _card("Strike_R", "Strike", cost=1)
    monster = _louse(current_hp=20)
    monster.block = 5
    context = _combat_context([strike], energy=1, monsters=[monster])
    context.strength = -10

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["block"] == 5
    assert result.monsters[0]["hp"] == 20
    assert result.total_damage_dealt == 0


def test_melter_removes_block_before_dealing_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "melter": {
            "name": "Melter",
            "description": "Remove all Block from the enemy. Deal 10 damage.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    melter = _card("Melter", "Melter", cost=1)
    monster = _louse(current_hp=20)
    monster.block = 12
    context = _combat_context([melter], energy=1, monsters=[monster])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        melter,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["block"] == 0
    assert result.monsters[0]["hp"] == 10
    assert result.total_damage_dealt == 10


def test_deal_damage_to_monster_ignores_negative_damage():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=20)])
    state = SimulationState(context)
    state.monsters[0]["block"] = 5

    FastCombatSimulator(SynergyCardEvaluator())._deal_damage_to_monster(
        state,
        state.monsters[0],
        -4,
    )

    assert state.monsters[0]["block"] == 5
    assert state.monsters[0]["hp"] == 20
    assert state.total_damage_dealt == 0


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


def test_reckless_charge_tracks_dazed_pollution(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "reckless charge": {
            "name": "Reckless Charge",
            "description": "Deal 7 damage.\nShuffle a Dazed into your draw pile.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    reckless_charge = _card("Reckless Charge", "Reckless Charge", cost=1)
    context = _combat_context([reckless_charge], energy=1, monsters=[_louse(current_hp=100)])

    result = simulator.simulate_card_play(
        SimulationState(context),
        reckless_charge,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.status_cards_added == 1
    assert result.dazed_cards_added == 1


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


def test_sever_soul_keeps_string_attack_cards(monkeypatch):
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
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    context = _combat_context(
        [sever_soul, defend, strike],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        sever_soul,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.exhaust_events == 1


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
    assert result.monsters[0]["move_adjusted_damage"] == 5

    already_weak_context = _combat_context(
        [uppercut],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    already_weak_context.weak_stacks[0] = 1
    already_weak_context.monsters_alive[0].move_adjusted_damage = 5
    result = simulator.simulate_card_play(
        SimulationState(already_weak_context),
        uppercut,
        target=already_weak_context.monsters_alive[0],
        target_index=0,
        context=already_weak_context,
    )

    assert result.monsters[0]["weak"] == 2
    assert result.monsters[0]["move_adjusted_damage"] == 5

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


def test_effect_text_lookup_handles_counted_upgrade_suffixes(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._wiki_data = {
        "uppercut": {
            "name": "Uppercut",
            "text": "Deal 13 damage.\nApply [1|2] #Weak.\nApply [1|2] #Vulnerable.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    text = FastCombatSimulator(SynergyCardEvaluator())._get_card_effect_text(
        "Uppercut+1",
        {"description": "Deal 13 damage.\nApply 1 Weak.\nApply 1 Vulnerable."},
    )

    assert "[1|2] #weak" in text


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


def test_player_weak_and_target_vulnerable_combine_before_rounding(monkeypatch):
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

    assert result.total_damage_dealt == 5


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


def test_ironclad_target_pruning_treats_string_attack_as_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[high_threat, killable])
    state = SimulationState(context)
    ranked_targets = [(high_threat, 0, 100.0), (killable, 1, 1.0)]

    pruned = IroncladCombatPlanner()._prune_targets(
        strike,
        ranked_targets,
        context,
        state,
    )

    assert [idx for _, idx, _ in pruned] == [1]


def test_ironclad_target_pruning_ignores_half_dead_for_cleanup_phase(monkeypatch):
    strike = _card("Strike_R", "Strike", cost=1)
    waiting_darkling = _darkling(current_hp=40)
    high_threat_low_hp = _darkling(current_hp=7)
    lowest_hp = _darkling(current_hp=5)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[waiting_darkling, high_threat_low_hp, lowest_hp],
    )
    state = SimulationState(context)
    state.monsters[0]["half_dead"] = True
    state.monsters[0]["is_gone"] = False
    ranked_targets = [
        (high_threat_low_hp, 1, 100.0),
        (lowest_hp, 2, 1.0),
    ]

    planner = IroncladCombatPlanner()
    monkeypatch.setattr(
        planner,
        "_estimate_attack_damage_to_target",
        lambda _card, _context, _state, _target_idx: 1,
    )

    pruned = planner._prune_targets(
        strike,
        ranked_targets,
        context,
        state,
    )

    assert [idx for _, idx, _ in pruned] == [2]


def test_heuristic_target_pruning_treats_string_attack_as_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[high_threat, killable])
    state = SimulationState(context)

    pruned = HeuristicCombatPlanner()._prune_targets(
        strike,
        [(high_threat, 100.0), (killable, 1.0)],
        context,
        state,
    )

    assert pruned == [(killable, 1.0)]


def test_heuristic_best_target_treats_string_attack_as_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    high_threat = _louse(current_hp=40)
    killable = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[high_threat, killable])
    context.compute_threat = lambda monster: 100 if monster is high_threat else 1

    target = HeuristicCombatPlanner()._find_best_target(
        strike,
        context,
        SimulationState(context),
    )

    assert target is killable


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
    assert [monster["move_adjusted_damage"] for monster in result.monsters] == [1, 1]

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
    assert [monster["move_adjusted_damage"] for monster in result.monsters] == [1, 1]


def test_shockwave_ignores_zero_hp_stale_simulated_monsters(monkeypatch):
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
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    context = _combat_context(
        [shockwave],
        energy=2,
        monsters=[_louse(current_hp=20), _louse(current_hp=20)],
    )
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        shockwave,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.monsters[0]["weak"] == 0
    assert result.monsters[0]["vulnerable"] == 0
    assert result.monsters[0]["strength"] == 0
    assert result.monsters[1]["weak"] == 3
    assert result.monsters[1]["vulnerable"] == 3
    assert result.monsters[1]["strength"] == -3


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


def test_dropkick_does_not_refund_against_zero_hp_stale_vulnerable_target(monkeypatch):
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
    context = _combat_context([dropkick], energy=1, monsters=[_louse(current_hp=20)])
    context.vulnerable_stacks[0] = 1
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        dropkick,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 0
    assert result.player_energy == 0
    assert result.energy_gained == 0
    assert result.cards_drawn == 0


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


def test_mind_blast_damage_uses_draw_pile_size(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "mind blast": {
            "name": "Mind Blast",
            "description": "Innate. Deal damage equal to the number of cards in your draw pile.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    mind_blast = _card("Mind Blast", "Mind Blast+", cost=1, upgrades=1)
    context = _combat_context([mind_blast], energy=1, monsters=[_louse(current_hp=100)])
    context.game.draw_pile = [
        _card("Strike_R", "Strike"),
        _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False),
        _card("Bash", "Bash"),
        _card("Anger", "Anger"),
    ]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        mind_blast,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 4


def test_havoc_plays_known_draw_pile_top_attack_against_single_monster():
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    bottom_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        has_target=False,
    )
    top_strike = _card("Strike_R", "Strike")
    top_strike.damage = 6
    context = _combat_context([havoc], energy=1, monsters=[_louse(current_hp=100)])
    context.game.draw_pile = [bottom_defend, top_strike]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        havoc,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 0
    assert result.total_damage_dealt == 6
    assert result.exhaust_events == 1


def test_havoc_plays_known_draw_pile_top_skill_block():
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    bottom_strike = _card("Strike_R", "Strike")
    top_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    top_defend.block = 5
    context = _combat_context([havoc], energy=0, monsters=[_louse(current_hp=100)])
    context.game.draw_pile = [bottom_strike, top_defend]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        havoc,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_block == 5
    assert result.exhaust_events == 1


def test_havoc_exhausted_top_card_triggers_feel_no_pain_block():
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    top_power = _card(
        "Berserk",
        "Berserk",
        card_type=CardType.POWER,
        cost=0,
        has_target=False,
    )
    context = _combat_context([havoc], energy=0, monsters=[_louse(current_hp=100)])
    context.game.draw_pile = [top_power]
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        havoc,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.exhaust_events == 1
    assert result.player_block == 3


def test_havoc_consumes_visible_top_card_for_later_simulated_havoc():
    first_havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    second_havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    bottom_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    bottom_defend.block = 5
    top_strike = _card("Strike_R", "Strike")
    top_strike.damage = 6
    context = _combat_context(
        [first_havoc, second_havoc],
        energy=0,
        monsters=[_louse(current_hp=100)],
    )
    context.game.draw_pile = [bottom_defend, top_strike]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    after_first = simulator.simulate_card_play(
        SimulationState(context),
        first_havoc,
        target=None,
        target_index=None,
        context=context,
    )
    after_second = simulator.simulate_card_play(
        after_first,
        second_havoc,
        target=None,
        target_index=None,
        context=context,
    )

    assert after_second.total_damage_dealt == 6
    assert after_second.player_block == 5
    assert after_second.exhaust_events == 2


def _patch_ritual_dagger_loader(monkeypatch, module):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "ritual dagger": {
            "name": "Ritual Dagger",
            "description": (
                "Deal 15 damage. If Fatal, permanently increase this card's "
                "damage by 3. Exhaust."
            ),
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(module, "game_data_loader", loader)


def test_ritual_dagger_damage_uses_misc_growth(monkeypatch):
    _patch_ritual_dagger_loader(monkeypatch, simulation)

    ritual_dagger = _card("Ritual Dagger", "Ritual Dagger", cost=1)
    ritual_dagger.misc = 9
    context = _combat_context([ritual_dagger], energy=1, monsters=[_louse(current_hp=50)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        ritual_dagger,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 24


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


def test_power_simulation_treats_none_upgrades_as_base_card():
    inflame = _card(
        "Inflame",
        "Inflame",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
    )
    inflame.upgrades = None
    context = _combat_context([inflame], energy=1, monsters=[_louse(current_hp=100)])

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        inflame,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_strength == 2


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
    assert result.energy_gained == 0

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
    assert result.energy_gained == 0


def test_berserk_self_vulnerable_consumes_player_artifact():
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    berserk = _card(
        "Berserk",
        "Berserk",
        card_type=CardType.POWER,
        cost=0,
        has_target=False,
    )
    context = _combat_context([berserk], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]

    result = simulator.simulate_card_play(
        SimulationState(context),
        berserk,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_vulnerable == 0
    assert result.player_vulnerable_added == 0
    assert result.player_artifact == 0
    assert result.player_energy == 1
    assert result.energy_gained == 0


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


def test_flex_strength_expires_at_end_of_turn_projection():
    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    context = _combat_context([flex], energy=0, monsters=[_louse(current_hp=100)])
    context.strength = 3
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        flex,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.player_strength == 5

    projected = simulator.project_end_turn_effects(state)

    assert projected.player_strength == 3


def test_flex_artifact_blocks_end_of_turn_strength_loss():
    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    context = _combat_context([flex], energy=0, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Artifact", amount=1)]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        flex,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.player_strength == 2
    assert state.player_artifact == 0

    projected = simulator.project_end_turn_effects(state)

    assert projected.player_strength == 2


def test_flex_treats_none_upgrades_as_base_strength_gain():
    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    flex.upgrades = None
    context = _combat_context([flex], energy=0, monsters=[_louse(current_hp=100)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        flex,
        target=None,
        target_index=None,
        context=context,
    )

    projected = simulator.project_end_turn_effects(state)

    assert state.player_strength == 2
    assert projected.player_strength == 0


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


def test_spot_weakness_ignores_negated_attack_intent_string():
    spot_weakness = _card(
        "Spot Weakness",
        "Spot Weakness",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    context = _combat_context([spot_weakness], energy=1, monsters=[_louse(current_hp=20)])
    state = SimulationState(context)
    state.monsters[0]["intent"] = "NOT_ATTACK"

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

    bloodletting_unknown_upgrade = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    bloodletting_unknown_upgrade.upgrades = None
    context = _combat_context([bloodletting_unknown_upgrade], energy=1, monsters=[_louse(current_hp=100)])
    result = simulator.simulate_card_play(
        SimulationState(context),
        bloodletting_unknown_upgrade,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 3
    assert result.energy_gained == 2
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


def test_tungsten_rod_reduces_fast_sim_bloodletting_hp_loss(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bloodletting": {
            "name": "Bloodletting",
            "description": "Lose 3 HP.\nGain [R] [R].",
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
    context = _combat_context([bloodletting], energy=1, monsters=[_louse(current_hp=100)])
    context.game.relics = [SimpleNamespace(name="Tungsten Rod", relic_id="TungstenRod")]

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        bloodletting,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.player_energy == 3
    assert result.energy_gained == 2
    assert result.player_hp == 78


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


def test_feel_no_pain_block_is_not_reduced_by_frail(monkeypatch):
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
    context.game.player.powers = [
        SimpleNamespace(power_name="Feel No Pain", amount=3),
        SimpleNamespace(power_name="Frail", amount=1),
    ]

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


def test_disarm_recomputes_weak_adjusted_attack_damage_from_base():
    disarm = _card(
        "Disarm",
        "Disarm",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    monster = _louse(current_hp=100)
    monster.move_base_damage = 10
    monster.move_adjusted_damage = 7
    context = _combat_context([disarm], energy=1, monsters=[monster])
    context.weak_stacks[0] = 1

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        SimulationState(context),
        disarm,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["strength"] == -2
    assert result.monsters[0]["move_adjusted_damage"] == 6
    assert FastCombatSimulator(SynergyCardEvaluator())._estimate_incoming_damage(
        result.monsters
    ) == 6


def test_disarm_ignores_zero_hp_stale_simulated_target():
    disarm = _card(
        "Disarm",
        "Disarm",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    monster = _louse(current_hp=20)
    monster.move_adjusted_damage = 12
    context = _combat_context([disarm], energy=1, monsters=[monster])
    state = SimulationState(context)
    state.monsters[0]["hp"] = 0
    state.monsters[0]["is_gone"] = False

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        disarm,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["strength"] == 0
    assert result.monsters[0]["move_adjusted_damage"] == 12


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


def test_ornamental_fan_adds_block_on_third_simulated_attack():
    first_strike = _card("Strike_R", "Strike", cost=1)
    first_strike.damage = 6
    sever_soul = _card("Sever Soul", "Sever Soul", cost=1)
    sever_soul.damage = 16
    anger = _card("Anger", "Anger", cost=0)
    anger.damage = 6
    context = _combat_context(
        [first_strike, sever_soul, anger],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    context.game.relics = [
        SimpleNamespace(relic_id="Ornamental Fan", name="Ornamental Fan")
    ]
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        first_strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    assert state.player_block == 0

    state = simulator.simulate_card_play(
        state,
        sever_soul,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )
    assert state.player_block == 0

    result = simulator.simulate_card_play(
        state,
        anger,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.attacks_played == 3
    assert result.player_block == 4


def test_double_tapped_rampage_uses_first_play_scaling(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "rampage": {
            "name": "Rampage",
            "description": "Deal 8 damage.\nIncrease this card's damage by 5 this combat.",
        }
    }
    loader._wiki_data = {
        "rampage": {
            "name": "Rampage",
            "text": "Deal 8 damage.\nIncrease this card's damage by [5|8] this combat.",
        }
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    double_tap = _card(
        "Double Tap",
        "Double Tap",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    rampage = _card("Rampage", "Rampage", cost=1, upgrades=None)
    context = _combat_context([double_tap, rampage], energy=2, monsters=[_louse(current_hp=100)])
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
        rampage,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.total_damage_dealt == 21
    assert result.attacks_played == 2


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


def test_planner_corruption_cost_handles_string_skill_type():
    defend = _card("Defend", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    defend.type = "SKILL"
    context = _combat_context([defend], energy=0, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Corruption", amount=1)]

    cost = HeuristicCombatPlanner._card_cost_for_state(defend, SimulationState(context))

    assert cost == 0


def test_ironclad_planner_corruption_cost_handles_string_skill_type():
    defend = _card("Defend", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    defend.type = "SKILL"
    context = _combat_context([defend], energy=0, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Corruption", amount=1)]

    cost = IroncladCombatPlanner._card_cost_for_state(defend, SimulationState(context))

    assert cost == 0


def test_ironclad_known_attack_damage_bonus_accepts_string_attack_type(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "iron wave": {
            "name": "Iron Wave",
            "description": "Gain 5 Block. Deal 5 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    iron_wave = _card("Iron Wave", "Iron Wave", cost=1)
    iron_wave.type = "ATTACK"

    assert IroncladCombatPlanner()._known_attack_damage_for_bonus(iron_wave) == 5


def test_ironclad_known_attack_damage_bonus_accepts_string_damage_attribute():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = "6"

    assert IroncladCombatPlanner()._known_attack_damage_for_bonus(strike) == 6


def test_ironclad_known_attack_damage_bonus_respects_player_weak():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]

    assert IroncladCombatPlanner()._known_attack_damage_for_bonus(strike, context) == 4


def test_ironclad_known_attack_damage_bonus_applies_pen_nib_before_weak():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.damage = 6
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.game.relics = [SimpleNamespace(relic_id="Pen Nib", name="Pen Nib", counter=9)]

    assert IroncladCombatPlanner()._known_attack_damage_for_bonus(strike, context) == 9


def test_ironclad_known_attack_damage_bonus_counts_strength_for_zero_damage_static_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "headbutt": {
            "name": "Headbutt",
            "description": "Deal 9 damage. Put a card from your discard pile on top of your draw pile.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    headbutt = _card("Headbutt", "Headbutt", cost=1)
    headbutt.damage = 0
    context = _combat_context([headbutt], energy=1, monsters=[_louse(current_hp=100)])
    context.strength = 2

    assert IroncladCombatPlanner()._known_attack_damage_for_bonus(headbutt, context) == 11


def test_ironclad_known_attack_damage_bonus_counts_whirlwind_x_energy_per_hit(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "whirlwind": {
            "name": "Whirlwind",
            "description": "Deal 5 damage to ALL enemies X times.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    whirlwind.damage = 0
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=100)])
    context.strength = 2
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]

    assert IroncladCombatPlanner()._known_attack_damage_for_bonus(whirlwind, context) == 15


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


def test_awakened_one_curiosity_gains_strength_when_power_is_played():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    awakened_one = _awakened_one()
    awakened_one.powers = [SimpleNamespace(power_name="Curiosity", amount=1)]
    context = _combat_context([demon_form], energy=3, monsters=[awakened_one])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        demon_form,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.monsters[0]["strength"] == 1
    assert result.monsters[0]["move_adjusted_damage"] == 19


def test_simulation_state_rejects_nonfinite_power_reactive_strength_amount():
    awakened_one = _awakened_one()
    awakened_one.powers = [SimpleNamespace(power_name="Curiosity", amount=float("inf"))]
    context = _combat_context([], energy=0, monsters=[awakened_one])

    state = SimulationState(context)

    assert state.monsters[0]["power_strength_gain"] == 0


def test_simulator_rejects_nonfinite_power_reactive_strength_counter():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    context = _combat_context([demon_form], energy=3, monsters=[_awakened_one()])
    state = SimulationState(context)
    state.monsters[0]["power_strength_gain"] = float("inf")

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        demon_form,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.monsters[0]["power_strength_gain"] == 0
    assert result.monsters[0]["strength"] == 0


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
    carnage.type = "ATTACK"
    context = _combat_context([carnage], energy=2, monsters=[_louse(current_hp=30), _louse(current_hp=30)])

    score = HeuristicCombatPlanner().fast_score_action(
        carnage,
        SimulationState(context),
        context,
    )

    assert score == simulation.FASTSCORE_ATTACK_BONUS + 20 * simulation.FASTSCORE_DAMAGE_MULTIPLIER


def test_fast_score_gives_setup_bonus_to_string_power_cards(monkeypatch):
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    demon_form.type = "POWER"
    context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=100)])
    context.turn = 1

    score = HeuristicCombatPlanner().fast_score_action(
        demon_form,
        SimulationState(context),
        context,
    )

    assert score == simulation.FASTSCORE_POWER_BONUS + simulation.FASTSCORE_POWER_EARLY_BONUS


def test_fast_score_power_bonus_accepts_string_turn(monkeypatch):
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=100)])
    context.turn = "1"

    score = HeuristicCombatPlanner().fast_score_action(
        demon_form,
        SimulationState(context),
        context,
    )

    assert score == simulation.FASTSCORE_POWER_BONUS + simulation.FASTSCORE_POWER_EARLY_BONUS


def test_fast_score_rage_counts_string_attack_cards(monkeypatch):
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    rage = _card("Rage", "Rage", card_type=CardType.SKILL, cost=0, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    context = _combat_context([rage, strike], energy=0, monsters=[_louse(current_hp=100)])

    score = HeuristicCombatPlanner().fast_score_action(
        rage,
        SimulationState(context),
        context,
    )

    assert score == 15 + (3 * 1.5) + simulation.FASTSCORE_ZERO_COST_BONUS


def test_fast_score_uses_upgraded_trip_aoe_text_for_setup_bonus(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "trip": {
            "name": "Trip",
            "description": "Apply 2 Vulnerable.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "trip": {
            "name": "Trip",
            "text": "Apply 2 #Vulnerable| to ALL enemies].",
        },
        "strike": {
            "name": "Strike",
            "text": "Deal [6|9] damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    strike = _card("Strike_R", "Strike")
    strike.type = "ATTACK"
    base_trip = _card("Trip", "Trip", card_type=CardType.SKILL, cost=0, has_target=True, upgrades=None)
    base_trip.type = "SKILL"
    upgraded_trip = _card("Trip", "Trip+", card_type=CardType.SKILL, cost=0, has_target=True, upgrades=1)
    upgraded_trip.type = "SKILL"
    base_context = _combat_context(
        [base_trip, strike],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )
    upgraded_context = _combat_context(
        [upgraded_trip, strike],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )
    planner = HeuristicCombatPlanner()

    base_score = planner.fast_score_action(base_trip, SimulationState(base_context), base_context)
    upgraded_score = planner.fast_score_action(upgraded_trip, SimulationState(upgraded_context), upgraded_context)

    assert upgraded_score == base_score + 4


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


def test_fast_score_aoe_multiplier_accepts_name_only_cleave(monkeypatch):
    monkeypatch.setattr(HeuristicCombatPlanner, "_calculate_x_block", lambda *_args, **_kwargs: 0, raising=False)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    name_only_cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=8,
        upgrades=0,
        has_target=False,
        is_playable=True,
    )
    context = _combat_context(
        [cleave, name_only_cleave],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )
    state = SimulationState(context)
    planner = HeuristicCombatPlanner()

    canonical_score = planner.fast_score_action(cleave, state, context)
    name_only_score = planner.fast_score_action(name_only_cleave, state, context)

    assert name_only_score == canonical_score


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

    assert detector._calculate_affordable_damage(context) == 22
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


def test_beam_search_uses_energy_gained_by_bloodletting_for_followup_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bloodletting": {
            "name": "Bloodletting",
            "description": "Lose 3 HP.\nGain 2 Energy.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    bloodletting = _card("Bloodletting", "Bloodletting", card_type=CardType.SKILL, cost=0, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1)
    bloodletting.uuid = "bloodletting"
    strike.uuid = "strike"
    context = _combat_context([bloodletting, strike], energy=0, monsters=[_louse(current_hp=100)])
    planner = IroncladCombatPlanner()

    def prefer_long_sequences(sequence, _initial_state, _final_state, _context):
        return len(sequence)

    planner._score_sequence = prefer_long_sequences

    sequence = planner._beam_search_turn(context, [bloodletting, strike], 10, 4)

    assert [action.card.card_id for action in sequence] == ["Bloodletting", "Strike_R"]


def test_beam_search_keeps_distinct_cards_when_uuid_is_missing():
    bash = _card("Bash", "Bash", cost=2)
    strike = _card("Strike_R", "Strike", cost=1)
    bash.uuid = None
    strike.uuid = None
    context = _combat_context([bash, strike], energy=3, monsters=[_louse(current_hp=100)])
    planner = IroncladCombatPlanner()

    def prefer_long_sequences(sequence, _initial_state, _final_state, _context):
        return len(sequence)

    planner._score_sequence = prefer_long_sequences

    sequence = planner._beam_search_turn(context, [bash, strike], 10, 4)

    assert [action.card.card_id for action in sequence] == ["Bash", "Strike_R"]


def test_beam_search_skips_zero_energy_whirlwind():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=0, monsters=[_louse(current_hp=50)])
    planner = IroncladCombatPlanner()

    assert planner._beam_search_turn(context, [whirlwind], 10, 4) == []


def test_zero_effect_x_attack_accepts_string_attack_type():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    whirlwind.type = "ATTACK"
    context = _combat_context([whirlwind], energy=0, monsters=[_louse(current_hp=50)])

    assert IroncladCombatPlanner._is_zero_effect_x_attack(whirlwind, 0, context) is True


def test_beam_search_skips_zero_energy_whirlwind_in_multi_monster_fight():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context(
        [whirlwind],
        energy=0,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    planner = IroncladCombatPlanner()

    assert planner._beam_search_turn(context, [whirlwind], 10, 4) == []


def test_beam_search_allows_zero_energy_whirlwind_with_chemical_x():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context(
        [whirlwind],
        energy=0,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    context.game.relics = [SimpleNamespace(relic_id="Chemical X", name="Chemical X")]
    planner = IroncladCombatPlanner()

    sequence = planner._beam_search_turn(context, [whirlwind], 10, 4)

    assert [action.card.card_id for action in sequence] == ["Whirlwind"]


def test_lethal_detector_counts_whirlwind_damage_without_negative_energy():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=50)])

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 15


def test_lethal_detector_affordable_damage_accepts_string_energy_available():
    int_context = _combat_context(
        [_card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)],
        energy=3,
        monsters=[_louse(current_hp=50)],
    )
    string_context = _combat_context(
        [_card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)],
        energy="3",
        monsters=[_louse(current_hp=50)],
    )
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(string_context) == detector._calculate_affordable_damage(int_context)


def test_lethal_detector_sequence_accepts_string_energy_available():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy="3", monsters=[_louse(current_hp=15)])
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.card_id for action in detector.find_lethal_sequence(context)] == ["Whirlwind"]


def test_lethal_detector_applies_chemical_x_to_whirlwind_damage():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=50)])
    context.game.relics = [SimpleNamespace(relic_id="Chemical X", name="Chemical X")]

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 25


def test_lethal_detector_applies_chemical_x_to_whirlwind_vulnerable_hits():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context([whirlwind], energy=3, monsters=[_louse(current_hp=100)])
    context.game.relics = [SimpleNamespace(relic_id="Chemical X", name="Chemical X")]
    context.vulnerable_stacks[0] = 1

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 35


def test_lethal_detector_allows_certain_kill_at_critical_hp():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=5)])
    context.game.current_hp = 6
    context.player_hp = 6
    context.player_hp_pct = 6 / 80

    assert CombatEndingDetector().can_kill_all(context) is True


def test_lethal_detector_accepts_numeric_string_player_hp_at_critical_hp():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=5)])
    context.game.current_hp = "6"
    context.player_hp = "6"
    context.player_hp_pct = "0.075"

    assert CombatEndingDetector().can_kill_all(context) is True


def test_lethal_detector_skip_defense_accepts_numeric_string_player_hp_pct():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=5)])
    context.game.current_hp = "80"
    context.player_hp = "80"
    context.player_hp_pct = "1.0"

    assert CombatEndingDetector().should_skip_defense(context) is True


def test_lethal_detector_skip_defense_prefers_game_hp_over_stale_context_pct():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=5)])
    context.game.current_hp = 6
    context.game.max_hp = 80
    context.player_hp = 80
    context.player_hp_pct = 1.0

    assert CombatEndingDetector().should_skip_defense(context) is False


def test_lethal_detector_allows_exact_single_target_kill(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=6)])
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 6
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["strike"]


def test_lethal_detector_accepts_numeric_string_monster_hp(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp="6")])
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 6
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["strike"]


def test_lethal_detector_counts_string_attack_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    strike.uuid = "strike"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=6)])
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 6
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["strike"]


def test_lethal_sequence_targets_name_only_single_target_attack_without_has_target(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        uuid="strike",
        is_playable=True,
    )
    target = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[target])
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["strike"]
    assert sequence[0].target_monster is target


def test_lethal_detector_proves_name_only_multi_target_attacks_without_has_target(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    strike_1 = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        uuid="strike-1",
        is_playable=True,
    )
    strike_2 = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        uuid="strike-2",
        is_playable=True,
    )
    first_target = _louse(current_hp=6)
    second_target = _louse(current_hp=6)
    context = _combat_context(
        [strike_1, strike_2],
        energy=2,
        monsters=[first_target, second_target],
    )
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["strike-1", "strike-2"]
    assert [action.target_monster for action in sequence] == [first_target, second_target]


def test_lethal_detector_counts_melter_block_removal(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "melter": {
            "name": "Melter",
            "description": "Remove all Block from the enemy. Deal 10 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    melter = _card("Melter", "Melter", cost=1)
    melter.uuid = "melter"
    monster = _louse(current_hp=10)
    monster.block = 12
    context = _combat_context([melter], energy=1, monsters=[monster])
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["melter"]


def test_lethal_detector_melter_accepts_numeric_string_monster_hp(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "melter": {
            "name": "Melter",
            "description": "Remove all Block from the enemy. Deal 10 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    melter = _card("Melter", "Melter", cost=1)
    melter.uuid = "melter"
    monster = _louse(current_hp="10")
    monster.block = 12
    context = _combat_context([melter], energy=1, monsters=[monster])
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["melter"]


def test_lethal_detector_counts_body_slam_current_block(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "body slam": {
            "name": "Body Slam",
            "description": "Deal damage equal to your current Block.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    body_slam = _card("Body Slam", "Body Slam", cost=1)
    body_slam.uuid = "body-slam"
    context = _combat_context([body_slam], energy=1, monsters=[_louse(current_hp=18)])
    context.game.player.block = 18
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 18
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["body-slam"]


def test_lethal_detector_counts_juggernaut_block_damage():
    defend = _card(
        "Defend_R",
        "Defend+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    defend.uuid = "defend"
    defend.block = 8
    context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=5)])
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 5
    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["defend"]
    assert sequence[0].target_monster is None


def test_lethal_detector_counts_juggernaut_after_blocking_attack():
    iron_wave = _card("Iron Wave", "Iron Wave", cost=1)
    iron_wave.uuid = "iron-wave"
    iron_wave.damage = 5
    iron_wave.block = 5
    monster = _louse(current_hp=10)
    context = _combat_context([iron_wave], energy=1, monsters=[monster])
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 10
    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["iron-wave"]
    assert sequence[0].target_monster is monster


def test_lethal_detector_keeps_juggernaut_random_targeting_conservative():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend.uuid = "defend"
    defend.block = 5
    context = _combat_context(
        [defend],
        energy=1,
        monsters=[_louse(current_hp=5), _louse(current_hp=5)],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Juggernaut", amount=5)]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 0
    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_counts_mind_blast_draw_pile_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "mind blast": {
            "name": "Mind Blast",
            "description": "Innate. Deal damage equal to the number of cards in your draw pile.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)

    mind_blast = _card("Mind Blast", "Mind Blast+", cost=1, upgrades=1)
    mind_blast.uuid = "mind-blast"
    context = _combat_context([mind_blast], energy=1, monsters=[_louse(current_hp=4)])
    context.game.draw_pile = [
        _card("Strike_R", "Strike"),
        _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False),
        _card("Bash", "Bash"),
        _card("Anger", "Anger"),
    ]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 4
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["mind-blast"]


def test_lethal_detector_counts_havoc_visible_top_attack_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    havoc.uuid = "havoc"
    top_strike = _card("Strike_R", "Strike", cost=1)
    top_strike.damage = 6
    context = _combat_context([havoc], energy=1, monsters=[_louse(current_hp=6)])
    context.game.draw_pile = [top_strike]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 6
    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["havoc"]
    assert sequence[0].target_monster is None


def test_lethal_detector_counts_havoc_visible_top_aoe_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    havoc.uuid = "havoc"
    top_cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    top_cleave.damage = 8
    context = _combat_context(
        [havoc],
        energy=1,
        monsters=[_louse(current_hp=8), _louse(current_hp=8)],
    )
    context.game.draw_pile = [top_cleave]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["havoc"]
    assert sequence[0].target_monster is None


def test_lethal_detector_counts_havoc_visible_top_energy_skill(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "seeing red": {
            "name": "Seeing Red",
            "description": "Gain [R] [R]. Exhaust.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    havoc.uuid = "havoc"
    first_strike = _card("Strike_R", "Strike", cost=1)
    first_strike.uuid = "first-strike"
    first_strike.damage = 6
    second_strike = _card("Strike_R", "Strike", cost=1)
    second_strike.uuid = "second-strike"
    second_strike.damage = 6
    top_seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context(
        [havoc, first_strike, second_strike],
        energy=1,
        monsters=[_louse(current_hp=12)],
    )
    context.game.draw_pile = [top_seeing_red]
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == [
        "havoc",
        "first-strike",
        "second-strike",
    ]
    assert sequence[0].target_monster is None


def test_lethal_detector_counts_havoc_top_exhaust_feel_no_pain_juggernaut(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "berserk": {
            "name": "Berserk",
            "description": "Gain 2 Vulnerable. At the start of your turn, gain [R].",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    havoc.uuid = "havoc"
    top_berserk = _card(
        "Berserk",
        "Berserk",
        card_type=CardType.POWER,
        cost=0,
        has_target=False,
    )
    context = _combat_context([havoc], energy=1, monsters=[_louse(current_hp=5)])
    context.game.draw_pile = [top_berserk]
    context.game.player.powers = [
        SimpleNamespace(power_name="Feel No Pain", amount=3),
        SimpleNamespace(power_name="Juggernaut", amount=5),
    ]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 5
    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["havoc"]
    assert sequence[0].target_monster is None


def test_lethal_detector_uses_dropkick_energy_refund_for_sequence(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([dropkick, strike], energy=1, monsters=[_louse(current_hp=16)])
    context.vulnerable_stacks[0] = 1
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "dropkick",
        "strike",
    ]


def test_lethal_detector_uses_nunchaku_energy_refund_for_sequence(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    first_strike = _card("Strike_R", "Strike", cost=1)
    first_strike.uuid = "first-strike"
    second_strike = _card("Strike_R", "Strike", cost=1)
    second_strike.uuid = "second-strike"
    context = _combat_context(
        [first_strike, second_strike],
        energy=1,
        monsters=[_louse(current_hp=12)],
    )
    context.game.relics = [SimpleNamespace(relic_id="Nunchaku", name="Nunchaku", counter=9)]
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 12
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "first-strike",
        "second-strike",
    ]


def test_lethal_detector_uses_dropkick_refund_before_other_target(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    vulnerable_target = _louse(current_hp=7)
    other_target = _louse(current_hp=6)
    context = _combat_context(
        [strike, dropkick],
        energy=1,
        monsters=[vulnerable_target, other_target],
    )
    context.vulnerable_stacks[0] = 1
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["dropkick", "strike"]
    assert sequence[0].target_monster is vulnerable_target
    assert sequence[1].target_monster is other_target


def test_lethal_aoe_cleanup_uses_dropkick_energy_refund(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "dropkick": {
            "name": "Dropkick",
            "text": "Deal [5|8] damage.\nIf the enemy has #Vulnerable,\ngain [R] and\ndraw 1 card.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.uuid = "cleave"
    dropkick = _card("Dropkick", "Dropkick+", cost=1, upgrades=1)
    dropkick.uuid = "dropkick"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    surviving_monster = _louse(current_hp=30)
    context = _combat_context(
        [cleave, dropkick, strike],
        energy=2,
        monsters=[surviving_monster, _louse(current_hp=8)],
    )
    context.vulnerable_stacks[0] = 1
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["cleave", "dropkick", "strike"]
    assert sequence[0].target_monster is None
    assert sequence[1].target_monster is surviving_monster
    assert sequence[2].target_monster is surviving_monster


def test_lethal_aoe_cleanup_tries_refund_line_before_greedy_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.uuid = "cleave"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    surviving_monster = _louse(current_hp=28)
    context = _combat_context(
        [cleave, dropkick, strike],
        energy=2,
        monsters=[surviving_monster, _louse(current_hp=8)],
    )
    context.vulnerable_stacks[0] = 1
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["cleave", "dropkick", "strike"]


def test_lethal_sequence_can_refund_before_aoe_cleanup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.uuid = "cleave"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    vulnerable_target = _louse(current_hp=15)
    other_target = _louse(current_hp=8)
    context = _combat_context(
        [cleave, dropkick],
        energy=1,
        monsters=[vulnerable_target, other_target],
    )
    context.vulnerable_stacks[0] = 1
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["dropkick", "cleave"]
    assert sequence[0].target_monster is vulnerable_target
    assert sequence[1].target_monster is None


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


def test_lethal_sequence_uses_single_aoe_card_for_multiple_monsters():
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, cost_for_turn=-1, has_target=False)
    context = _combat_context(
        [whirlwind],
        energy=3,
        monsters=[_louse(current_hp=6), _louse(current_hp=6)],
    )
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.card_id for action in sequence] == ["Whirlwind"]
    assert sequence[0].target_monster is None


def test_lethal_detector_counts_aoe_damage_against_each_monster(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=7), _louse(current_hp=7)],
    )
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is True
    assert [action.card.card_id for action in detector.find_lethal_sequence(context)] == ["Cleave"]


def test_lethal_detector_rejects_aoe_overkill_false_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=1), _louse(current_hp=12)],
    )
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_rejects_aoe_cleanup_through_malleable_block(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.uuid = "cleave"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    malleable_target = _louse(current_hp=14)
    malleable_target.powers = [SimpleNamespace(power_name="Malleable", amount=3)]
    context = _combat_context(
        [cleave, strike],
        energy=2,
        monsters=[malleable_target, _louse(current_hp=5)],
    )
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 22
    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_rejects_single_target_distribution_false_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 5 damage.",
        },
        "carnage": {
            "name": "Carnage",
            "description": "Deal 15 damage.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    carnage = _card("Carnage", "Carnage", cost=1)
    carnage.uuid = "carnage"
    context = _combat_context(
        [strike, carnage],
        energy=2,
        monsters=[_louse(current_hp=10), _louse(current_hp=10)],
    )
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_rejects_random_target_attack_false_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "sword boomerang": {
            "name": "Sword Boomerang",
            "description": "Deal 3 damage to a random enemy 3 times.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    first_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1, has_target=False)
    first_boomerang.uuid = "boomerang-1"
    second_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1, has_target=False)
    second_boomerang.uuid = "boomerang-2"
    context = _combat_context(
        [first_boomerang, second_boomerang],
        energy=2,
        monsters=[_louse(current_hp=16), _louse(current_hp=11)],
    )
    context.strength = 2
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 30
    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_sequence_does_not_target_single_monster_random_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "sword boomerang": {
            "name": "Sword Boomerang",
            "description": "Deal 3 damage to a random enemy 3 times.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    sword_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1, has_target=False)
    sword_boomerang.uuid = "sword-boomerang"
    context = _combat_context(
        [sword_boomerang],
        energy=1,
        monsters=[_louse(current_hp=9)],
    )
    detector = CombatEndingDetector()

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["sword-boomerang"]
    assert sequence[0].target_monster is None


def test_lethal_detector_uses_aoe_damage_before_single_target_cleanup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    strike = _card("Strike_R", "Strike", cost=1)
    surviving_monster = _louse(current_hp=12)
    context = _combat_context(
        [cleave, strike],
        energy=2,
        monsters=[_louse(current_hp=5), surviving_monster],
    )
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 22
    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.card_id for action in sequence] == ["Cleave", "Strike_R"]
    assert sequence[0].target_monster is None
    assert sequence[1].target_monster is surviving_monster


def test_lethal_sequence_does_not_target_random_attack_after_aoe_cleanup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "sword boomerang": {
            "name": "Sword Boomerang",
            "description": "Deal 3 damage to a random enemy 3 times.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    sword_boomerang = _card("Sword Boomerang", "Sword Boomerang", cost=1, has_target=False)
    context = _combat_context(
        [cleave, sword_boomerang],
        energy=2,
        monsters=[_louse(current_hp=5), _louse(current_hp=15)],
    )
    detector = CombatEndingDetector()

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.card_id for action in sequence] == ["Cleave", "Sword Boomerang"]
    assert sequence[0].target_monster is None
    assert sequence[1].target_monster is None


def test_lethal_detector_counts_vulnerable_damage_on_single_target():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike-vulnerable"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=8)])
    context.vulnerable_stacks[0] = 1

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["strike-vulnerable"]


def test_lethal_detector_accepts_string_vulnerable_stacks_on_single_target():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike-vulnerable"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=8)])
    context.vulnerable_stacks[0] = "1"

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


def test_lethal_detector_combines_player_weak_and_target_vulnerable_before_rounding(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"dropkick": {"name": "Dropkick", "description": "Deal 5 damage."}}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    context = _combat_context([dropkick], energy=1, monsters=[_louse(current_hp=100)])
    context.game.player.powers = [SimpleNamespace(power_name="Weak", amount=1)]
    context.vulnerable_stacks[0] = 1

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 5


def test_lethal_detector_applies_paper_phrog_vulnerable_multiplier(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=10)])
    context.vulnerable_stacks[0] = 1
    context.game.relics = [SimpleNamespace(relic_id="Paper Phrog", name="Paper Phrog")]

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 10
    assert detector.can_kill_all(context) is True


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


def test_lethal_detector_counts_ritual_dagger_misc_damage(monkeypatch):
    _patch_ritual_dagger_loader(monkeypatch, combat_ending)
    ritual_dagger = _card("Ritual Dagger", "Ritual Dagger", cost=1)
    ritual_dagger.misc = 9
    context = _combat_context(
        [ritual_dagger],
        energy=1,
        monsters=[_louse(current_hp=24)],
    )

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 24


def test_lethal_detector_counts_generated_attack_upgrades_without_wiki(monkeypatch):
    _patch_simple_colorless_attack_loader(monkeypatch, combat_ending)
    shiv_plus = _card("Shiv", "Shiv+", cost=0, upgrades=1)
    smite_plus = _card("Smite", "Smite+", cost=1, upgrades=1)
    through_violence_plus = _card(
        "Through Violence",
        "Through Violence+",
        cost=0,
        upgrades=1,
    )
    context = _combat_context(
        [shiv_plus, smite_plus, through_violence_plus],
        energy=1,
        monsters=[_louse(current_hp=60)],
    )

    assert CombatEndingDetector()._calculate_affordable_damage(context) == 52


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


def test_lethal_detector_accounts_for_malleable_block_between_attack_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "twin strike": {
            "name": "Twin Strike",
            "description": "Deal 5 damage twice.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "twin strike": {
            "name": "Twin Strike",
            "text": "Deal [5|7] damage twice.",
        },
        "strike": {
            "name": "Strike",
            "text": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    twin_strike.uuid = "twin-strike"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    target = _louse(current_hp=14)
    target.powers = [SimpleNamespace(power_name="Malleable", amount=3)]
    context = _combat_context([twin_strike, strike], energy=2, monsters=[target])
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_accounts_for_curl_up_block_between_attack_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "twin strike": {
            "name": "Twin Strike",
            "description": "Deal 5 damage twice.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "twin strike": {
            "name": "Twin Strike",
            "text": "Deal [5|7] damage twice.",
        },
        "strike": {
            "name": "Strike",
            "text": "Deal 6 damage.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    twin_strike.uuid = "twin-strike"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    target = _louse(current_hp=14)
    target.powers = [SimpleNamespace(power_name="Curl Up", amount=3)]
    context = _combat_context([twin_strike, strike], energy=2, monsters=[target])
    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 16
    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_counts_bane_second_hit_against_poisoned_target(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bane": {
            "name": "Bane",
            "description": "Deal 7 damage. If the enemy has Poison, deal 7 damage again.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bane = _card("Bane", "Bane", cost=1)
    bane.uuid = "bane"
    monster = _louse(current_hp=12)
    monster.powers = [SimpleNamespace(power_name="Poison", amount=1)]
    context = _combat_context([bane], energy=1, monsters=[monster])

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 14
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["bane"]


def test_lethal_detector_accepts_string_poison_power_amount_for_bane(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bane": {
            "name": "Bane",
            "description": "Deal 7 damage. If the enemy has Poison, deal 7 damage again.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bane = _card("Bane", "Bane", cost=1)
    bane.uuid = "bane"
    monster = _louse(current_hp=12)
    monster.powers = [SimpleNamespace(power_name="Poison", amount="1")]
    context = _combat_context([bane], energy=1, monsters=[monster])

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 14
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["bane"]


def test_lethal_detector_bane_poison_check_accepts_numeric_string_hp():
    dead_poisoned = _louse(current_hp="0")
    dead_poisoned.powers = [SimpleNamespace(power_name="Poison", amount=1)]
    live_poisoned = _louse(current_hp="12")
    live_poisoned.powers = [SimpleNamespace(power_name="Poison", amount=1)]
    context = _combat_context([], energy=0, monsters=[dead_poisoned, live_poisoned])

    assert CombatEndingDetector()._all_alive_targets_poisoned(context)


def test_lethal_detector_bane_poison_check_rejects_nonfinite_hp():
    invalid_hp = _louse(current_hp=float("inf"))
    invalid_hp.powers = []
    live_poisoned = _louse(current_hp=12)
    live_poisoned.powers = [SimpleNamespace(power_name="Poison", amount=1)]
    context = _combat_context([], energy=0, monsters=[invalid_hp, live_poisoned])

    assert CombatEndingDetector()._all_alive_targets_poisoned(context)


def test_lethal_detector_player_hp_rejects_nonfinite_values():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=12)])
    context.game.current_hp = float("inf")
    context.game.max_hp = float("inf")
    context.player_hp = float("inf")
    context.player_max_hp = float("inf")
    context.player_hp_pct = float("inf")
    detector = CombatEndingDetector()

    assert detector._context_player_hp(context) == 0
    assert detector._context_player_hp_pct(context) == 0.0


def test_lethal_detector_counts_bane_second_hit_only_for_poisoned_target(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bane": {
            "name": "Bane",
            "description": "Deal 7 damage. If the enemy has Poison, deal 7 damage again.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bane = _card("Bane", "Bane", cost=1)
    bane.uuid = "bane"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    poisoned_target = _louse(current_hp=14)
    poisoned_target.powers = [SimpleNamespace(power_name="Poison", amount=1)]
    other_target = _louse(current_hp=6)
    context = _combat_context(
        [bane, strike],
        energy=2,
        monsters=[poisoned_target, other_target],
    )
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True

    sequence = detector.find_lethal_sequence(context)

    assert [action.card.uuid for action in sequence] == ["bane", "strike"]
    assert [action.target_monster for action in sequence] == [
        poisoned_target,
        other_target,
    ]


def test_lethal_detector_counts_skewer_x_energy_hits(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "skewer": {
            "name": "Skewer",
            "description": "Deal 7 damage X times.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    skewer = _card("Skewer", "Skewer", cost=-1, cost_for_turn=-1)
    skewer.uuid = "skewer"
    context = _combat_context([skewer], energy=3, monsters=[_louse(current_hp=21)])

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 21
    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["skewer"]


def test_lethal_detector_uses_remaining_energy_for_skewer_sequence(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "skewer": {
            "name": "Skewer",
            "description": "Deal 7 damage X times.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    skewer = _card("Skewer", "Skewer", cost=-1, cost_for_turn=-1)
    skewer.uuid = "skewer"
    context = _combat_context(
        [strike, skewer],
        energy=3,
        monsters=[_louse(current_hp=27)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


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


def test_lethal_detector_rejects_fiend_fire_exhausted_hand_false_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Deal 7 damage. Exhaust your hand.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "Deal [7|10] damage. Exhaust your hand.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    fiend_fire.uuid = "fiend-fire"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1)
    defend.uuid = "defend"
    cards = [fiend_fire, strike, defend]
    context = _combat_context(cards, energy=3, monsters=[_louse(current_hp=20)])
    context.game.hand = cards
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_aoe_cleanup_rejects_fiend_fire_exhausted_hand_false_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Deal 7 damage. Exhaust your hand.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "Deal [7|10] damage. Exhaust your hand.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.uuid = "cleave"
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    fiend_fire.uuid = "fiend-fire"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1)
    defend.uuid = "defend"
    cards = [cleave, fiend_fire, strike, defend]
    context = _combat_context(
        cards,
        energy=3,
        monsters=[_louse(current_hp=29), _louse(current_hp=8)],
    )
    context.game.hand = cards
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_fallback_rejects_fiend_fire_exhausted_hand_false_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Deal 7 damage. Exhaust your hand.",
        },
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
    }
    loader._wiki_data = {
        "fiend fire": {
            "name": "Fiend Fire",
            "text": "Deal [7|10] damage. Exhaust your hand.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    fiend_fire.uuid = "fiend-fire"
    strikes = []
    for index in range(8):
        strike = _card("Strike_R", "Strike", cost=1)
        strike.uuid = f"strike-{index}"
        strikes.append(strike)
    cards = [fiend_fire, *strikes]
    context = _combat_context(cards, energy=3, monsters=[_louse(current_hp=62)])
    context.game.hand = cards
    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


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


def test_lethal_detector_applies_bash_vulnerable_before_followup(monkeypatch):
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
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([bash, strike], energy=3, monsters=[_louse(current_hp=17)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == ["bash", "strike"]


def test_lethal_detector_uses_shockwave_vulnerable_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "shockwave": {
            "name": "Shockwave",
            "description": "Apply 3 Weak, Vulnerable, and Strength Down to ALL enemies. Exhaust.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "shockwave": {
            "name": "Shockwave",
            "text": "Apply [3|5] #Weak, #Vulnerable, and #Strength Down to ALL enemies.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    shockwave.uuid = "shockwave"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([shockwave, strike], energy=3, monsters=[_louse(current_hp=9)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["shockwave", "strike"]
    assert sequence[0].target_monster is None


def test_lethal_detector_uses_upgraded_trip_vulnerable_before_followups(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "trip": {
            "name": "Trip",
            "description": "Apply 2 Vulnerable.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "trip": {
            "name": "Trip",
            "text": "Apply 2 #Vulnerable| to ALL enemies].",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    trip = _card(
        "Trip",
        "Trip+",
        card_type=CardType.SKILL,
        cost=0,
        has_target=True,
        upgrades=1,
    )
    trip.type = "SKILL"
    trip.uuid = "trip-plus"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [trip, strike_1, strike_2],
        energy=2,
        monsters=[_louse(current_hp=18)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == [
        "trip-plus",
        "strike-1",
        "strike-2",
    ]
    assert sequence[0].target_monster is None


def test_lethal_detector_targets_trip_vulnerable_before_followups(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "trip": {
            "name": "Trip",
            "description": "Apply 2 Vulnerable.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "trip": {
            "name": "Trip",
            "text": "Apply 2 #Vulnerable| to ALL enemies].",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    trip = _card(
        "Trip",
        "Trip",
        card_type=CardType.SKILL,
        cost=0,
        has_target=True,
    )
    trip.type = "SKILL"
    trip.uuid = "trip"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    target = _louse(current_hp=18)
    context = _combat_context(
        [trip, strike_1, strike_2],
        energy=2,
        monsters=[target],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == [
        "trip",
        "strike-1",
        "strike-2",
    ]
    assert sequence[0].target_monster is target


def test_lethal_detector_treats_active_corruption_shockwave_as_zero_cost(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "shockwave": {
            "name": "Shockwave",
            "description": "Apply 3 Weak, Vulnerable, and Strength Down to ALL enemies. Exhaust.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "shockwave": {
            "name": "Shockwave",
            "text": "Apply [3|5] #Weak, #Vulnerable, and #Strength Down to ALL enemies.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    shockwave.uuid = "shockwave"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([shockwave, strike], energy=1, monsters=[_louse(current_hp=9)])
    context.game.player.powers = [SimpleNamespace(power_name="Corruption", amount=1)]

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "shockwave",
        "strike",
    ]


def test_lethal_detector_counts_shockwave_strength_down_artifact_consumption(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "shockwave": {
            "name": "Shockwave",
            "description": "Apply 3 Weak, Vulnerable, and Strength Down to ALL enemies. Exhaust.",
        },
        "bash": {
            "name": "Bash",
            "description": "Deal 8 damage. Apply 2 Vulnerable.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "shockwave": {
            "name": "Shockwave",
            "text": "Apply [3|5] #Weak, #Vulnerable, and #Strength Down to ALL enemies.\n#Exhaust.",
        },
        "bash": {
            "name": "Bash",
            "text": "Deal [8|10] damage.\nApply [2|3] Vulnerable.",
        },
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    shockwave.uuid = "shockwave"
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    target = _louse(current_hp=17)
    target.powers = [SimpleNamespace(power_name="Artifact", amount=3)]
    context = _combat_context([shockwave, bash, strike], energy=5, monsters=[target])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "shockwave",
        "bash",
        "strike",
    ]


def test_lethal_detector_uses_new_bash_vulnerable_for_dropkick_refund(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "bash": {
            "name": "Bash",
            "description": "Deal 8 damage. Apply 2 Vulnerable.",
        },
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
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
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([bash, dropkick, strike], energy=3, monsters=[_louse(current_hp=24)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "bash",
        "dropkick",
        "strike",
    ]


def test_lethal_detector_consumes_artifact_before_uppercut_vulnerable(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "uppercut": {
            "name": "Uppercut",
            "description": "Deal 13 damage.\nApply 1 Weak.\nApply 1 Vulnerable.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "uppercut": {
            "name": "Uppercut",
            "text": "Deal 13 damage.\nApply [1|2] Weak.\nApply [1|2] Vulnerable.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    uppercut = _card("Uppercut", "Uppercut", cost=2)
    uppercut.uuid = "uppercut"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    target = _louse(current_hp=22)
    target.powers = [SimpleNamespace(power_name="Artifact", amount=1)]
    context = _combat_context([uppercut, strike], energy=3, monsters=[target])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "uppercut",
        "strike",
    ]


def test_lethal_detector_artifact_blocks_bash_vulnerable_followup(monkeypatch):
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
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    target = _louse(current_hp=17)
    target.powers = [SimpleNamespace(power_name="Artifact", amount=1)]
    context = _combat_context([bash, strike], energy=3, monsters=[target])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_uses_flex_strength_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    flex = _card("Flex", "Flex", card_type=CardType.SKILL, cost=0, has_target=False)
    flex.uuid = "flex"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([flex, strike], energy=1, monsters=[_louse(current_hp=8)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "flex",
        "strike",
    ]


def test_lethal_detector_uses_limit_break_strength_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    limit_break = _card(
        "Limit Break",
        "Limit Break",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    limit_break.uuid = "limit-break"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([limit_break, strike], energy=2, monsters=[_louse(current_hp=12)])
    context.strength = 3

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "limit-break",
        "strike",
    ]


def test_lethal_detector_uses_spot_weakness_strength_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    spot_weakness = _card(
        "Spot Weakness",
        "Spot Weakness",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    spot_weakness.uuid = "spot-weakness"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    target = _louse(current_hp=9)
    target.intent = Intent.ATTACK
    context = _combat_context([spot_weakness, strike], energy=2, monsters=[target])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == [
        "spot-weakness",
        "strike",
    ]
    assert sequence[0].target_monster is target


def test_lethal_detector_uses_inflame_strength_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    inflame = _card(
        "Inflame",
        "Inflame",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
    )
    inflame.uuid = "inflame"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([inflame, strike], energy=2, monsters=[_louse(current_hp=8)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "inflame",
        "strike",
    ]


def test_lethal_detector_treats_none_upgrades_as_base_strength_support(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    inflame = _card(
        "Inflame",
        "Inflame",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
    )
    inflame.upgrades = None
    inflame.uuid = "inflame"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([inflame, strike], energy=2, monsters=[_louse(current_hp=8)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "inflame",
        "strike",
    ]


def test_lethal_detector_does_not_use_demon_form_as_immediate_strength(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context([demon_form, strike], energy=4, monsters=[_louse(current_hp=8)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_uses_seeing_red_energy_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    seeing_red.uuid = "seeing-red"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [seeing_red, strike_1, strike_2],
        energy=1,
        monsters=[_louse(current_hp=12)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "seeing-red",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_treats_active_corruption_seeing_red_as_zero_cost(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    seeing_red.uuid = "seeing-red"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [seeing_red, strike_1, strike_2],
        energy=0,
        monsters=[_louse(current_hp=12)],
    )
    context.game.player.powers = [SimpleNamespace(power_name="Corruption", amount=1)]

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "seeing-red",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_uses_played_corruption_for_followup_skill_costs(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "shockwave": {
            "name": "Shockwave",
            "description": "Apply 3 Weak, Vulnerable, and Strength Down to ALL enemies. Exhaust.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "shockwave": {
            "name": "Shockwave",
            "text": "Apply [3|5] #Weak, #Vulnerable, and #Strength Down to ALL enemies.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    corruption = _card(
        "Corruption",
        "Corruption",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    corruption.uuid = "corruption"
    seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        cost_for_turn=3,
        has_target=False,
    )
    seeing_red.uuid = "seeing-red"
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    shockwave.uuid = "shockwave"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [corruption, seeing_red, shockwave, strike_1, strike_2],
        energy=3,
        monsters=[_louse(current_hp=18)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == [
        "corruption",
        "shockwave",
        "seeing-red",
        "strike-1",
        "strike-2",
    ]
    assert sequence[1].target_monster is None


def test_lethal_detector_uses_string_typed_corruption_support_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "shockwave": {
            "name": "Shockwave",
            "description": "Apply 3 Weak, Vulnerable, and Strength Down to ALL enemies. Exhaust.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "shockwave": {
            "name": "Shockwave",
            "text": "Apply [3|5] #Weak, #Vulnerable, and #Strength Down to ALL enemies.\n#Exhaust.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    corruption = _card(
        "Corruption",
        "Corruption",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    corruption.type = "POWER"
    corruption.uuid = "corruption"
    seeing_red = _card(
        "Seeing Red",
        "Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        cost_for_turn=3,
        has_target=False,
    )
    seeing_red.type = "SKILL"
    seeing_red.uuid = "seeing-red"
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    shockwave.type = "SKILL"
    shockwave.uuid = "shockwave"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [corruption, seeing_red, shockwave, strike_1, strike_2],
        energy=3,
        monsters=[_louse(current_hp=18)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == [
        "corruption",
        "shockwave",
        "seeing-red",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_uses_double_tap_for_next_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    double_tap = _card(
        "Double Tap",
        "Double Tap",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    double_tap.uuid = "double-tap"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([double_tap, strike], energy=2, monsters=[_louse(current_hp=12)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "double-tap",
        "strike",
    ]


def test_lethal_detector_uses_duplication_power_for_next_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=12)])
    context.game.player.powers = [
        SimpleNamespace(power_id="DuplicationPower", power_name="Duplication", amount=1)
    ]

    detector = CombatEndingDetector()

    assert detector._calculate_affordable_damage(context) == 12
    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["strike"]
    assert sequence[0].target_monster is context.monsters_alive[0]


def test_lethal_detector_counts_panache_trigger_from_any_card():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    defend.block = 0
    defend.uuid = "defend"
    context = _combat_context(
        [defend],
        energy=0,
        monsters=[_louse(current_hp=10), _louse(current_hp=10)],
    )
    context.game.player.powers = [
        SimpleNamespace(power_id="Panache", power_name="Panache", amount=1)
    ]

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    sequence = detector.find_lethal_sequence(context)
    assert [action.card.uuid for action in sequence] == ["defend"]
    assert sequence[0].target_monster is None


def test_lethal_detector_uses_rampage_scaling_between_double_tap_repeats(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "rampage": {
            "name": "Rampage",
            "description": "Deal 8 damage.\nIncrease this card's damage by 5 this combat.",
        }
    }
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    double_tap = _card(
        "Double Tap",
        "Double Tap",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    double_tap.uuid = "double-tap"
    rampage = _card("Rampage", "Rampage", cost=1)
    rampage.uuid = "rampage"
    context = _combat_context([double_tap, rampage], energy=2, monsters=[_louse(current_hp=21)])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "double-tap",
        "rampage",
    ]


def test_lethal_detector_uses_upgraded_double_tap_for_two_attacks(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    double_tap = _card(
        "Double Tap",
        "Double Tap+",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    double_tap.uuid = "double-tap-plus"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [double_tap, strike_1, strike_2],
        energy=3,
        monsters=[_louse(current_hp=24)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "double-tap-plus",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_uses_double_tapped_dropkick_net_energy(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "dropkick": {
            "name": "Dropkick",
            "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {
        "dropkick": {
            "name": "Dropkick",
            "text": "Deal [5|8] damage.\nIf the enemy has #Vulnerable,\ngain [R] and\ndraw 1 card.",
        }
    }
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    double_tap = _card(
        "Double Tap",
        "Double Tap",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    double_tap.uuid = "double-tap"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [double_tap, dropkick, strike_1, strike_2],
        energy=2,
        monsters=[_louse(current_hp=32)],
    )
    context.vulnerable_stacks[0] = 1

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "double-tap",
        "dropkick",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_uses_bloodletting_energy_before_followup(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bloodletting = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    bloodletting.uuid = "bloodletting"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [bloodletting, strike_1, strike_2],
        energy=0,
        monsters=[_louse(current_hp=12)],
    )

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "bloodletting",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_rejects_bloodletting_energy_when_hp_would_hit_zero(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bloodletting = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_2 = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [bloodletting, strike_1, strike_2],
        energy=0,
        monsters=[_louse(current_hp=12)],
    )
    context.game.current_hp = 3
    context.player_hp = 3
    context.player_hp_pct = 3 / 80

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_allows_bloodletting_energy_when_tungsten_rod_keeps_hp_positive(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    bloodletting = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    bloodletting.uuid = "bloodletting"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [bloodletting, strike_1, strike_2],
        energy=0,
        monsters=[_louse(current_hp=12)],
    )
    context.game.current_hp = 3
    context.player_hp = 3
    context.player_hp_pct = 3 / 80
    context.game.relics = [SimpleNamespace(name="Tungsten Rod", relic_id="TungstenRod")]

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "bloodletting",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_rejects_hp_cost_lethal_when_game_hp_is_stale_in_context(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    offering = _card(
        "Offering",
        "Offering",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_2 = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [offering, strike_1, strike_2],
        energy=0,
        monsters=[_louse(current_hp=12)],
    )
    context.game.current_hp = 3
    context.game.max_hp = 80
    context.player_hp = 80
    context.player_hp_pct = 1.0

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


def test_lethal_detector_uses_offering_energy_before_followup_when_hp_safe(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    offering = _card(
        "Offering",
        "Offering",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    offering.uuid = "offering"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    context = _combat_context(
        [offering, strike_1, strike_2],
        energy=0,
        monsters=[_louse(current_hp=12)],
    )
    context.game.current_hp = 7
    context.player_hp = 7
    context.player_hp_pct = 7 / 80

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is True
    assert [action.card.uuid for action in detector.find_lethal_sequence(context)] == [
        "offering",
        "strike-1",
        "strike-2",
    ]


def test_lethal_detector_requires_attacking_target_for_spot_weakness(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {"strike": {"name": "Strike", "description": "Deal 6 damage."}}
    loader._wiki_data = {}
    monkeypatch.setattr(combat_ending, "game_data_loader", loader)
    spot_weakness = _card(
        "Spot Weakness",
        "Spot Weakness",
        card_type=CardType.SKILL,
        cost=1,
        has_target=True,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    target = _louse(current_hp=9)
    target.intent = Intent.DEBUFF
    context = _combat_context([spot_weakness, strike], energy=2, monsters=[target])

    detector = CombatEndingDetector()

    assert detector.can_kill_all(context) is False
    assert detector.find_lethal_sequence(context) == []


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


def test_player_thorns_score_bypasses_monster_block():
    monster = _louse(current_hp=1)
    monster.block = 99
    context = _combat_context([], energy=0, monsters=[monster])
    context.game.player.powers = [SimpleNamespace(power_name="Thorns", amount=3)]
    state = SimulationState(context)

    reflected = FastCombatSimulator(SynergyCardEvaluator())._estimate_player_thorns_damage(state)

    assert reflected == 1


def test_flame_barrier_power_scores_as_current_attacker_reflection():
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=8)])
    context.game.player.powers = [SimpleNamespace(power_name="Flame Barrier", amount=6)]
    state = SimulationState(context)

    reflected = FastCombatSimulator(SynergyCardEvaluator())._estimate_player_thorns_damage(state)

    assert state.player_thorns == 6
    assert reflected == 6


def test_flame_barrier_card_adds_current_turn_reflection(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "flame barrier": {
            "name": "Flame Barrier",
            "description": "Gain 12 Block. Whenever you are attacked this turn, deal 4 damage to the attacker.",
        },
    }
    monkeypatch.setattr(simulation, "game_data_loader", loader)

    flame_barrier = _card(
        "Flame Barrier",
        "Flame Barrier",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    context = _combat_context([flame_barrier], energy=2, monsters=[_louse(current_hp=8)])
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    state = simulator.simulate_card_play(
        SimulationState(context),
        flame_barrier,
        target=None,
        target_index=None,
        context=context,
    )

    assert state.player_thorns == 4
    assert simulator._estimate_player_thorns_damage(state) == 4


def test_guardian_mode_shift_power_is_tracked_in_simulation_state():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_guardian(mode_shift=12)],
    )

    state = SimulationState(context)

    assert state.monsters[0]["mode_shift"] == 12


def test_guardian_zero_incoming_window_values_attack_over_block_draw():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    shrug = _card(
        "Shrug It Off",
        "Shrug It Off",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    shrug.uuid = "shrug"
    guardian = _guardian(current_hp=218)
    guardian.intent = Intent.STRONG_DEBUFF
    guardian.move_id = 7
    guardian.move_adjusted_damage = 0
    guardian.move_hits = 0
    context = _combat_context([shrug, strike], energy=1, monsters=[guardian])
    context.incoming_damage = 0
    context.turn = 3
    context.floor = 16
    context.act = 1
    context.player_hp = 57
    context.player_hp_pct = 57 / 80
    context.game.current_hp = 57
    context.game.max_hp = 80
    context.game.player.block = 0
    planner = IroncladCombatPlanner()
    initial_state = SimulationState(context)

    strike_state = planner.simulator.simulate_card_play(
        initial_state.clone(),
        strike,
        target=guardian,
        target_index=0,
        context=context,
    )
    shrug_state = planner.simulator.simulate_card_play(
        initial_state.clone(),
        shrug,
        target=None,
        target_index=None,
        context=context,
    )

    strike_score = planner._score_sequence(
        [PlayCardAction(card=strike, target_monster=guardian)],
        initial_state,
        strike_state,
        context,
    )
    shrug_score = planner._score_sequence(
        [PlayCardAction(card=shrug)],
        initial_state,
        shrug_state,
        context,
    )

    assert strike_score > shrug_score


def test_simulation_state_rejects_nonfinite_guardian_mode_shift_amount():
    guardian = _guardian(mode_shift=12)
    guardian.powers[0].amount = float("inf")
    context = _combat_context([], energy=0, monsters=[guardian])

    state = SimulationState(context)

    assert state.monsters[0]["mode_shift"] == 0


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


def test_guardian_mode_shift_cancels_current_attack_damage_after_threshold():
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_guardian(mode_shift=5)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    result = simulator.simulate_card_play(
        SimulationState(context),
        strike,
        target=context.monsters_alive[0],
        target_index=0,
        context=context,
    )

    assert result.monsters[0]["mode_shift"] == 0
    assert simulator._estimate_incoming_damage(result.monsters) == 0
    assert simulator.simulate_enemy_lookahead(result, context, look_ahead=1) == 0


def test_simulator_rejects_nonfinite_guardian_mode_shift_counter():
    context = _combat_context([], energy=0, monsters=[_guardian(mode_shift=5)])
    state = SimulationState(context)
    state.monsters[0]["mode_shift"] = float("inf")

    FastCombatSimulator(SynergyCardEvaluator())._deal_damage_to_monster(
        state,
        state.monsters[0],
        6,
    )

    assert state.monsters[0]["hp"] == 234
    assert state.monsters[0]["mode_shift"] == 0
    assert state.monsters[0]["block"] == 0
    assert state.monsters[0]["thorns"] == 0


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


def test_ironclad_sequence_aoe_bonus_accepts_name_only_cleave():
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    name_only_cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=8,
        upgrades=0,
        has_target=False,
        is_playable=True,
    )
    context = _combat_context(
        [cleave, name_only_cleave],
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
    name_only_score = planner._score_sequence(
        [PlayCardAction(card=name_only_cleave)],
        initial_state,
        final_state,
        context,
    )

    assert name_only_score == canonical_score


def test_simulator_outcome_aoe_bonus_accepts_name_only_cleave():
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    name_only_cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=8,
        upgrades=0,
        has_target=False,
        is_playable=True,
    )
    context = _combat_context(
        [cleave, name_only_cleave],
        energy=1,
        monsters=[_louse(current_hp=50), _louse(current_hp=50)],
    )
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    initial_state = SimulationState(context)
    final_state = initial_state.clone()

    canonical_score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        current_act=1,
        context=context,
        sequence=[PlayCardAction(card=cleave)],
    )
    name_only_score = simulator.calculate_outcome_score(
        initial_state,
        final_state,
        current_act=1,
        context=context,
        sequence=[PlayCardAction(card=name_only_cleave)],
    )

    assert name_only_score == canonical_score


def test_ironclad_sequence_strategic_bonus_values_counted_upgraded_whirlwind_damage():
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

    expected_upgrade_delta = (8 - 5) * 3 * len(context.monsters_alive) * 0.5
    assert counted_score - canonical_score == expected_upgrade_delta


def test_ironclad_sequence_score_accepts_string_power_type():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    string_demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    string_demon_form.type = "POWER"
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=100)])
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_final.energy_spent = 3
    enum_score = planner._score_sequence(
        [PlayCardAction(card=demon_form)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([string_demon_form], energy=3, monsters=[_louse(current_hp=100)])
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_final.energy_spent = 3
    string_score = planner._score_sequence(
        [PlayCardAction(card=string_demon_form)],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_turn_for_power_bonus():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    string_demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=100)])
    enum_context.turn = 2
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_final.energy_spent = 3
    enum_score = planner._score_sequence(
        [PlayCardAction(card=demon_form)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([string_demon_form], energy=3, monsters=[_louse(current_hp=100)])
    string_context.turn = "2"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_final.energy_spent = 3
    string_score = planner._score_sequence(
        [PlayCardAction(card=string_demon_form)],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_skill_type_against_gremlin_nob():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    string_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    string_defend.type = "SKILL"
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_final.energy_spent = 1
    enum_score = planner._score_sequence(
        [PlayCardAction(card=defend)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([string_defend], energy=1, monsters=[_gremlin_nob()])
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_final.energy_spent = 1
    string_score = planner._score_sequence(
        [PlayCardAction(card=string_defend)],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_player_hp_for_hp_cost_cards():
    bloodletting = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    string_bloodletting = _card(
        "Bloodletting",
        "Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([bloodletting], energy=1, monsters=[_louse(current_hp=100)])
    enum_context.player_hp = 80
    enum_context.player_hp_pct = 1.0
    enum_context.game.current_hp = 80
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_score = planner._score_sequence(
        [PlayCardAction(card=bloodletting)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([string_bloodletting], energy=1, monsters=[_louse(current_hp=100)])
    string_context.player_hp = "80"
    string_context.player_hp_pct = "1.0"
    string_context.game.current_hp = "80"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_score = planner._score_sequence(
        [PlayCardAction(card=string_bloodletting)],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_player_hp_pct_for_immolate():
    immolate = _card(
        "Immolate",
        "Immolate",
        card_type=CardType.ATTACK,
        cost=2,
    )
    string_immolate = _card(
        "Immolate",
        "Immolate",
        card_type=CardType.ATTACK,
        cost=2,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([immolate], energy=2, monsters=[_louse(current_hp=100)])
    enum_context.player_hp_pct = 0.2
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_score = planner._score_sequence(
        [PlayCardAction(card=immolate, target_monster=enum_context.monsters_alive[0])],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([string_immolate], energy=2, monsters=[_louse(current_hp=100)])
    string_context.player_hp_pct = "0.2"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_score = planner._score_sequence(
        [PlayCardAction(card=string_immolate, target_monster=string_context.monsters_alive[0])],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_strength_for_reaper_bonus():
    reaper = _card(
        "Reaper",
        "Reaper",
        card_type=CardType.ATTACK,
        cost=2,
        has_target=False,
    )
    string_reaper = _card(
        "Reaper",
        "Reaper",
        card_type=CardType.ATTACK,
        cost=2,
        has_target=False,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context(
        [reaper],
        energy=2,
        monsters=[_louse(current_hp=100), _louse(current_hp=100)],
    )
    enum_context.strength = 3
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_score = planner._score_sequence(
        [PlayCardAction(card=reaper)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context(
        [string_reaper],
        energy=2,
        monsters=[_louse(current_hp=100), _louse(current_hp=100)],
    )
    string_context.strength = "3"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    try:
        string_score = planner._score_sequence(
            [PlayCardAction(card=string_reaper)],
            string_initial,
            string_final,
            string_context,
        )
    except TypeError:
        string_score = "type-error"

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_deck_size_for_battle_trance_bonus():
    battle_trance = _card(
        "Battle Trance",
        "Battle Trance",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    string_battle_trance = _card(
        "Battle Trance",
        "Battle Trance",
        card_type=CardType.SKILL,
        cost=0,
        has_target=False,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context(
        [battle_trance],
        energy=0,
        monsters=[_louse(current_hp=100)],
    )
    enum_context.deck_size = 20
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_score = planner._score_sequence(
        [PlayCardAction(card=battle_trance)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context(
        [string_battle_trance],
        energy=0,
        monsters=[_louse(current_hp=100)],
    )
    string_context.deck_size = "20"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    try:
        string_score = planner._score_sequence(
            [PlayCardAction(card=string_battle_trance)],
            string_initial,
            string_final,
            string_context,
        )
    except TypeError:
        string_score = "type-error"

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_name_only_skill_against_gremlin_nob():
    defend = SimpleNamespace(
        name="Defend",
        type=CardType.SKILL,
        cost=1,
        cost_for_turn=1,
        block=5,
        upgrades=0,
        has_target=False,
        is_playable=True,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    context = _combat_context([defend], energy=1, monsters=[_gremlin_nob()])
    initial = SimulationState(context)
    final = initial.clone()
    final.player_block = 5
    final.energy_spent = 1

    score = planner._score_sequence(
        [PlayCardAction(card=defend)],
        initial,
        final,
        context,
    )

    assert score == -45.5


def test_ironclad_block_penalty_accepts_string_attack_type_against_gremlin_nob():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    string_strike = _card("Strike_R", "Strike", cost=1)
    string_strike.type = "ATTACK"
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([defend, strike], energy=1, monsters=[_gremlin_nob()])
    enum_context.incoming_damage = 14
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_final.player_block = 5
    enum_final.energy_spent = 1
    enum_score = planner._score_sequence(
        [PlayCardAction(card=defend)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([defend, string_strike], energy=1, monsters=[_gremlin_nob()])
    string_context.incoming_damage = 14
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_final.player_block = 5
    string_final.energy_spent = 1
    string_score = planner._score_sequence(
        [PlayCardAction(card=defend)],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_accepts_string_incoming_damage_for_block_value():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    string_defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    enum_context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=50)])
    enum_context.incoming_damage = 10
    enum_initial = SimulationState(enum_context)
    enum_final = enum_initial.clone()
    enum_final.player_block = 5
    enum_final.energy_spent = 1
    enum_score = planner._score_sequence(
        [PlayCardAction(card=defend)],
        enum_initial,
        enum_final,
        enum_context,
    )

    string_context = _combat_context([string_defend], energy=1, monsters=[_louse(current_hp=50)])
    string_context.incoming_damage = "10"
    string_initial = SimulationState(string_context)
    string_final = string_initial.clone()
    string_final.player_block = 5
    string_final.energy_spent = 1
    string_score = planner._score_sequence(
        [PlayCardAction(card=string_defend)],
        string_initial,
        string_final,
        string_context,
    )

    assert string_score == enum_score


def test_ironclad_sequence_score_hard_penalizes_current_turn_lethal_incoming():
    strike = _card("Strike_R", "Strike", cost=1)
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    context = _combat_context([strike], energy=1, monsters=[_hexaghost(current_hp=50)])
    context.game.current_hp = 7
    context.player_hp = 7
    context.player_hp_pct = 7 / 80
    context.incoming_damage = 18
    context.turn = 14
    context.floor = 16
    initial = SimulationState(context)
    reckless_final = initial.clone()
    reckless_final.total_damage_dealt = 12
    reckless_final.energy_spent = 1

    score = planner._score_sequence(
        [PlayCardAction(card=strike)],
        initial,
        reckless_final,
        context,
    )

    assert score < -500

    intangible_final = reckless_final.clone()
    intangible_final.player_intangible = 1
    intangible_score = planner._score_sequence(
        [PlayCardAction(card=strike)],
        initial,
        intangible_final,
        context,
    )

    assert intangible_score > -500


def test_armaments_bonus_does_not_count_itself_when_uuid_is_missing():
    armaments_with_uuid = _card(
        "Armaments",
        "Armaments",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=None,
    )
    strike_with_uuid = _card("Strike_R", "Strike", cost=1)
    armaments_with_uuid.uuid = "armaments"
    strike_with_uuid.uuid = "strike"

    armaments_without_uuid = _card(
        "Armaments",
        "Armaments",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
        upgrades=None,
    )
    strike_without_uuid = _card("Strike_R", "Strike", cost=1)
    armaments_without_uuid.uuid = None
    strike_without_uuid.uuid = None

    context_with_uuid = _combat_context(
        [armaments_with_uuid, strike_with_uuid],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    context_without_uuid = _combat_context(
        [armaments_without_uuid, strike_without_uuid],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0

    initial_with_uuid = SimulationState(context_with_uuid)
    initial_without_uuid = SimulationState(context_without_uuid)

    score_with_uuid = planner._score_sequence(
        [PlayCardAction(card=armaments_with_uuid)],
        initial_with_uuid,
        initial_with_uuid.clone(),
        context_with_uuid,
    )
    score_without_uuid = planner._score_sequence(
        [PlayCardAction(card=armaments_without_uuid)],
        initial_without_uuid,
        initial_without_uuid.clone(),
        context_without_uuid,
    )

    assert score_without_uuid == score_with_uuid


def test_armaments_counts_none_upgrades_as_upgradeable():
    armaments = _card(
        "Armaments",
        "Armaments",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1, upgrades=None)
    context = _combat_context(
        [armaments, strike],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )

    assert IroncladCombatPlanner()._count_upgradeable_cards(
        context,
        exclude_card=armaments,
    ) == 1


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


def test_ironclad_sequence_bash_followup_bonus_uses_parsed_big_attack(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "carnage": {
            "name": "Carnage",
            "description": "Ethereal. Deal 20 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    carnage = _card("Carnage", "Carnage", cost=2)
    carnage.uuid = "carnage"
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

    followup_context = _combat_context(
        [bash, carnage],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    followup_initial = SimulationState(followup_context)
    followup_score = planner._score_sequence(
        [PlayCardAction(card=bash)],
        followup_initial,
        followup_initial.clone(),
        followup_context,
    )

    assert followup_score - solo_score == 25


def test_ironclad_sequence_bash_followup_bonus_accepts_string_attack_type(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "carnage": {
            "name": "Carnage",
            "description": "Ethereal. Deal 20 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    carnage = _card("Carnage", "Carnage", cost=2)
    carnage.uuid = "carnage"
    carnage.type = "ATTACK"
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

    followup_context = _combat_context(
        [bash, carnage],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    followup_initial = SimulationState(followup_context)
    followup_score = planner._score_sequence(
        [PlayCardAction(card=bash)],
        followup_initial,
        followup_initial.clone(),
        followup_context,
    )

    assert followup_score - solo_score == 25


def test_ironclad_sequence_immolate_bonus_uses_parsed_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "immolate": {
            "name": "Immolate",
            "description": "Deal 21 damage to ALL enemies. Add a Burn into your discard pile.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    immolate = _card("Immolate", "Immolate", cost=2, has_target=False)
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    context = _combat_context(
        [immolate],
        energy=2,
        monsters=[_louse(current_hp=100), _louse(current_hp=100)],
    )
    initial = SimulationState(context)

    score = planner._score_sequence(
        [PlayCardAction(card=immolate)],
        initial,
        initial.clone(),
        context,
    )

    assert score == 72


def test_ironclad_sequence_iron_wave_hybrid_bonus_uses_parsed_damage(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "iron wave": {
            "name": "Iron Wave",
            "description": "Gain 5 Block. Deal 5 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    iron_wave = _card("Iron Wave", "Iron Wave", cost=1, upgrades=None)
    planner = IroncladCombatPlanner()
    planner.simulator._get_enemy_lookahead_depth = lambda *_args, **_kwargs: 0
    planner.simulator.simulate_enemy_lookahead = lambda *_args, **_kwargs: 0
    context = _combat_context([iron_wave], energy=1, monsters=[_louse(current_hp=100)])
    initial = SimulationState(context)

    score = planner._score_sequence(
        [PlayCardAction(card=iron_wave)],
        initial,
        initial.clone(),
        context,
    )

    assert score == 37.5


def test_target_exploration_ignores_counted_upgraded_aoe_target_flag():
    counted_cleave = _card("Cleave+1", "Cleave+1", cost=1, has_target=True, upgrades=1)
    context = _combat_context(
        [counted_cleave],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    should_explore = IroncladCombatPlanner()._should_explore_targets(context, elapsed_time=0)

    assert should_explore is False


def test_ironclad_beam_target_exploration_accepts_name_only_card():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        has_target=True,
        is_playable=True,
    )
    monsters = [_louse(current_hp=30), _louse(current_hp=30)]
    context = _combat_context([strike], energy=1, monsters=monsters)
    planner = IroncladCombatPlanner()

    planner._should_explore_targets = lambda _context, _elapsed_time: True
    planner.fast_score_action = lambda _card, _state, _context: 10
    planner._rank_targets = lambda _card, _context, _state: [
        (monsters[0], 0, 10),
        (monsters[1], 1, 9),
    ]
    planner._prune_targets = lambda _card, ranked_targets, _context, _state: ranked_targets
    planner._is_single_target_attack = lambda _card, _target_idx: True
    planner.simulator.simulate_card_play = lambda state, *_args, **_kwargs: state.clone()
    planner._score_sequence = lambda sequence, *_args: len(sequence)

    sequence = planner._beam_search_turn(context, [strike], beam_width=10, max_depth=1)

    assert sequence
    assert sequence[0].card is strike


def test_heuristic_beam_target_exploration_accepts_name_only_card():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        has_target=True,
        is_playable=True,
    )
    monsters = [_louse(current_hp=30), _louse(current_hp=30)]
    context = _combat_context([strike], energy=1, monsters=monsters)
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    planner._should_explore_targets = lambda _context, _elapsed_time: True
    planner._get_potion_actions = lambda _context, _state: []
    planner.fast_score_action = lambda _card, _state, _context: 10
    planner._rank_targets = lambda _card, _context, **_kwargs: [
        (monsters[0], 10),
        (monsters[1], 9),
    ]
    planner._prune_targets = lambda _card, ranked_targets, _context, **_kwargs: ranked_targets
    planner.simulator.simulate_card_play = lambda state, *_args, **_kwargs: state.clone()
    planner.simulator.calculate_outcome_score = lambda *_args, **_kwargs: 1
    planner.card_evaluator.evaluate_card = lambda _card, _context: 0

    sequence = planner._beam_search_plan(context)

    assert sequence
    assert sequence[0].card is strike


def test_heuristic_simple_plan_accepts_name_only_power_without_has_target():
    demon_form = SimpleNamespace(
        name="Demon Form",
        type=CardType.POWER,
        cost=3,
        cost_for_turn=3,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=100)])
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    planner.card_evaluator.get_best_card = lambda _cards, _context: demon_form

    sequence = planner._simple_plan(context)

    assert len(sequence) == 1
    assert sequence[0].card is demon_form
    assert getattr(sequence[0], "target_monster", None) is None


def test_heuristic_simple_plan_targets_name_only_single_target_attack_without_has_target():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        is_playable=True,
    )
    target = _louse(current_hp=30)
    context = _combat_context([strike], energy=1, monsters=[target])
    context.compute_threat = lambda _monster: 0
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())
    planner.card_evaluator.get_best_card = lambda _cards, _context: strike

    sequence = planner._simple_plan(context)

    assert len(sequence) == 1
    assert sequence[0].card is strike
    assert sequence[0].target_monster is target


def test_heuristic_target_exploration_infers_name_only_single_target_attack():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    assert HeuristicCombatPlanner(SynergyCardEvaluator())._should_explore_targets(context, 0) is True


def test_ironclad_target_exploration_infers_name_only_single_target_attack():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    assert IroncladCombatPlanner()._should_explore_targets(context, 0) is True


def test_heuristic_target_exploration_accepts_numeric_string_monster_hp():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_louse(current_hp="7"), _louse(current_hp="12")],
    )

    assert HeuristicCombatPlanner(SynergyCardEvaluator())._should_explore_targets(context, 0) is True


def test_ironclad_target_exploration_accepts_numeric_string_monster_hp():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        damage=6,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context(
        [strike],
        energy=1,
        monsters=[_louse(current_hp="7"), _louse(current_hp="12")],
    )

    assert IroncladCombatPlanner()._should_explore_targets(context, 0) is True


def test_heuristic_target_exploration_accepts_name_only_aoe_without_has_target():
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    assert HeuristicCombatPlanner(SynergyCardEvaluator())._should_explore_targets(context, 0) is False


def test_ironclad_target_exploration_accepts_name_only_aoe_without_has_target():
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        upgrades=0,
        is_playable=True,
    )
    context = _combat_context(
        [cleave],
        energy=1,
        monsters=[_louse(current_hp=30), _louse(current_hp=30)],
    )

    assert IroncladCombatPlanner()._should_explore_targets(context, 0) is False


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


def test_ironclad_fallback_priority_accepts_string_power_type():
    demon_form = _card(
        "Demon Form",
        "Demon Form",
        card_type=CardType.POWER,
        cost=3,
        has_target=False,
    )
    demon_form.type = "POWER"
    context = _combat_context([demon_form], energy=3, monsters=[_louse(current_hp=100)])
    context.turn = 2

    assert IroncladCombatPlanner()._get_card_priority(demon_form, context) == 1000


def test_ironclad_fallback_priority_accepts_string_attack_type():
    strike = _card("Strike_R", "Strike", cost=1)
    strike.type = "ATTACK"
    context = _combat_context([strike], energy=1, monsters=[_louse(current_hp=100)])
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    assert planner._get_card_priority(strike, context) == 700


def test_ironclad_fallback_priority_accepts_string_strength_for_reaper():
    reaper = _card(
        "Reaper",
        "Reaper",
        card_type=CardType.ATTACK,
        cost=2,
        has_target=False,
    )
    context = _combat_context(
        [reaper],
        energy=2,
        monsters=[_louse(current_hp=100), _louse(current_hp=100)],
    )
    context.strength = "5"
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    try:
        priority = planner._get_card_priority(reaper, context)
    except TypeError:
        priority = "type-error"

    assert priority == 900


def test_ironclad_fallback_priority_accepts_string_player_hp_for_aggressive_defense():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    context = _combat_context([defend], energy=1, monsters=[_louse(current_hp=100)])
    context.game.current_hp = "20"
    context.incoming_damage = 17
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "aggressive",
        "threat_level": 2,
    }

    assert planner._get_card_priority(defend, context) == 600


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


def test_ironclad_fallback_priority_values_bash_before_parsed_big_attacks(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "carnage": {
            "name": "Carnage",
            "description": "Ethereal. Deal 20 damage.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    bash = _card("Bash", "Bash", cost=2)
    carnage = _card("Carnage", "Carnage", cost=2)
    context = _combat_context(
        [bash, carnage],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )

    assert IroncladCombatPlanner()._get_card_priority(bash, context) == 850


def test_ironclad_fallback_priority_values_bash_before_body_slam_with_current_block(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "body slam": {
            "name": "Body Slam",
            "description": "Deal damage equal to your current Block.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    bash = _card("Bash", "Bash", cost=2)
    body_slam = _card("Body Slam", "Body Slam", cost=1)
    context = _combat_context(
        [bash, body_slam],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    context.game.player.block = 18

    assert IroncladCombatPlanner()._get_card_priority(bash, context) == 850


def test_ironclad_fallback_priority_accepts_string_player_block_for_body_slam(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "body slam": {
            "name": "Body Slam",
            "description": "Deal damage equal to your current Block.",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    body_slam = _card("Body Slam", "Body Slam", cost=1)
    context = _combat_context(
        [body_slam],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.game.player.block = "20"

    try:
        priority = IroncladCombatPlanner()._get_card_priority(body_slam, context)
    except TypeError:
        priority = "type-error"

    assert priority == 950


def test_ironclad_fallback_priority_accepts_string_player_block_for_iron_wave():
    iron_wave = _card(
        "Iron Wave",
        "Iron Wave",
        card_type=CardType.ATTACK,
        cost=1,
    )
    enum_context = _combat_context(
        [iron_wave],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    enum_context.incoming_damage = 12
    enum_context.game.player.block = 5

    string_context = _combat_context(
        [iron_wave],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    string_context.incoming_damage = 12
    string_context.game.player.block = "5"

    planner = IroncladCombatPlanner()
    try:
        string_priority = planner._get_card_priority(iron_wave, string_context)
    except TypeError:
        string_priority = "type-error"

    assert string_priority == planner._get_card_priority(iron_wave, enum_context)


def test_ironclad_fallback_prefers_havoc_visible_top_card_block():
    strike = _card("Strike_R", "Strike", cost=1)
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    top_power_through = _card(
        "Power Through",
        "Power Through",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    top_power_through.block = 15
    context = _combat_context(
        [strike, havoc],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.incoming_damage = 18
    context.game.draw_pile = [top_power_through]
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    sequence = planner._fallback_plan(context, [strike, havoc])

    assert len(sequence) == 1
    assert sequence[0].card is havoc


def test_ironclad_fallback_counts_self_exhaust_feel_no_pain_block():
    strike = _card("Strike_R", "Strike", cost=1)
    shockwave = _card(
        "Shockwave",
        "Shockwave",
        card_type=CardType.SKILL,
        cost=2,
        has_target=False,
    )
    shockwave.exhausts = True
    context = _combat_context(
        [strike, shockwave],
        energy=2,
        monsters=[_louse(current_hp=100)],
    )
    context.incoming_damage = 3
    context.game.player.powers = [SimpleNamespace(power_name="Feel No Pain", amount=3)]
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    sequence = planner._fallback_plan(context, [strike, shockwave])

    assert len(sequence) == 1
    assert sequence[0].card is shockwave


def test_ironclad_fallback_counts_orichalcum_before_prioritizing_defense():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [defend, strike],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.incoming_damage = 5
    context.game.relics = [SimpleNamespace(name="Orichalcum")]
    context.relics = context.game.relics
    context.has_orichalcum = True
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    sequence = planner._fallback_plan(context, [defend, strike])

    assert len(sequence) == 1
    assert sequence[0].card is strike


def test_ironclad_fallback_counts_ornamental_fan_attack_block():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [defend, strike],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.incoming_damage = 4
    context.game.relics = [SimpleNamespace(name="Ornamental Fan", counter=2)]
    context.relics = context.game.relics
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    sequence = planner._fallback_plan(context, [defend, strike])

    assert len(sequence) == 1
    assert sequence[0].card is strike


def test_ironclad_fallback_prioritizes_nunchaku_refund_attack_before_defense():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [defend, strike],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.incoming_damage = 5
    context.game.relics = [SimpleNamespace(name="Nunchaku", relic_id="Nunchaku", counter=9)]
    context.relics = context.game.relics
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    sequence = planner._fallback_plan(context, [defend, strike])

    assert len(sequence) == 1
    assert sequence[0].card is strike


def test_ironclad_fallback_counts_ornamental_fan_from_havoc_top_attack():
    defend = _card(
        "Defend_R",
        "Defend",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    defend.block = 3
    havoc = _card(
        "Havoc",
        "Havoc",
        card_type=CardType.SKILL,
        cost=1,
        has_target=False,
    )
    top_strike = _card("Strike_R", "Strike", cost=1)
    context = _combat_context(
        [defend, havoc],
        energy=1,
        monsters=[_louse(current_hp=100)],
    )
    context.incoming_damage = 4
    context.game.draw_pile = [top_strike]
    context.game.relics = [SimpleNamespace(name="Ornamental Fan", counter=2)]
    context.relics = context.game.relics
    planner = IroncladCombatPlanner()
    planner._get_monster_info = lambda _monster: {
        "recommended_strategy": "balanced",
        "threat_level": 2,
    }

    sequence = planner._fallback_plan(context, [defend, havoc])

    assert len(sequence) == 1
    assert sequence[0].card is havoc


def test_ironclad_fallback_priority_values_bash_before_perfected_strike_with_strike_deck(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "perfected strike": {
            "name": "Perfected Strike",
            "description": "Deal 6 damage. Deals 2 additional damage for ALL your cards containing \"Strike\".",
        }
    }
    monkeypatch.setattr(ironclad_combat, "game_data_loader", loader)

    bash = _card("Bash", "Bash", cost=2)
    perfected_strike = _card("Perfected Strike", "Perfected Strike", cost=2)
    context = _combat_context(
        [bash, perfected_strike],
        energy=3,
        monsters=[_louse(current_hp=100)],
    )
    context.game.deck = [
        _card("Strike_R", "Strike"),
        _card("Strike_R", "Strike"),
        _card("Twin Strike", "Twin Strike"),
        _card("Perfected Strike", "Perfected Strike"),
    ]

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


def test_shelled_parasite_attack_buff_heal_updates_future_lookahead_hp(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, _monster_name):
            return None

        def get_monster_moves(self, _monster_name):
            return [
                {
                    "name": "Suck",
                    "move_id": 1,
                    "intent": "ATTACK_BUFF",
                    "damage": 10,
                    "hits": 1,
                }
            ]

        def predict_monster_moves(self, _monster_name, current_turn, hp_percent, **_kwargs):
            if hp_percent < 0.5:
                move = {
                    "name": "Low HP Strike",
                    "intent": "ATTACK",
                    "damage": 20,
                    "hits": 1,
                }
            else:
                move = {
                    "name": "High HP Wait",
                    "intent": "BUFF",
                    "damage": 0,
                    "hits": 1,
                }
            return [{"turn": current_turn + 1, "move": move}]

    shelled_parasite = Monster(
        name="Shelled Parasite",
        monster_id="Shelled Parasite",
        max_hp=68,
        current_hp=33,
        block=0,
        intent=Intent.ATTACK_BUFF,
        half_dead=False,
        is_gone=False,
        move_id=1,
        move_adjusted_damage=10,
        move_hits=1,
    )
    context = _combat_context([], monsters=[shelled_parasite])
    context.turn = 6
    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())

    damage = FastCombatSimulator(SynergyCardEvaluator()).simulate_enemy_lookahead(
        SimulationState(context),
        context,
        look_ahead=2,
    )

    assert damage == 10


def test_live_buff_intent_does_not_resolve_to_debuff_move(monkeypatch):
    class FakeLoader:
        def get_monster_moves(self, _monster_name):
            return [
                {"name": "Actual Debuff", "move_id": 1, "intent": "DEBUFF"},
                {"name": "Actual Buff", "move_id": 2, "intent": "BUFF"},
            ]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    monster = {
        "name": "Intent Test",
        "monster_id": "IntentTest",
        "hp": 20,
        "max_hp": 20,
        "intent": Intent.BUFF,
        "move_id": 99,
        "move_adjusted_damage": 0,
        "move_hits": 1,
    }
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    move = simulator._current_monster_move(monster)

    assert move["name"] == "Actual Buff"


def test_prediction_formula_damage_rejects_nonfinite_values():
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    assert simulator._formula_damage_value(
        {
            "type": "linear_by_turn",
            "base": float("inf"),
            "per_turn": 3,
            "turn_offset": 0,
        },
        target_turn=2,
    ) == 6
    assert simulator._formula_damage_value(
        {
            "type": "linear_after_turn",
            "base": 5,
            "increment": 3,
            "first_turn": 1,
            "max_bonus": float("inf"),
        },
        target_turn=4,
    ) == 14


def test_prediction_formula_hits_rejects_nonfinite_values():
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    assert simulator._formula_hit_count(
        {
            "type": "ceil_turn_divisor",
            "divisor": float("inf"),
            "min_hits": float("inf"),
            "max_hits": float("inf"),
        },
        target_turn=float("inf"),
    ) == 1


def test_prediction_numeric_damage_rejects_nonfinite_values():
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    assert simulator._numeric_damage_value(float("inf")) == 0
    assert simulator._numeric_damage_value({"normal": float("inf"), "base": 7}) == 7
    assert simulator._numeric_damage_value({"max": float("inf"), "fallback": 5}) == 5


def test_prediction_move_hit_count_rejects_nonfinite_fallback():
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    assert simulator._move_hit_count({"hits": float("inf")}) == 1
    assert simulator._move_hit_count({"move_hits": "2"}) == 2


def test_prediction_ascension_modifiers_reject_nonfinite_values():
    simulator = FastCombatSimulator(SynergyCardEvaluator())
    context = _combat_context([], monsters=[_louse()])
    move = {
        "damage": 4,
        "ascension_modifiers": {"2+": {"damage_bonus": 5}},
    }

    context.game.ascension_level = float("inf")
    assert simulator._apply_ascension_move_value(move, context, "damage", 4) == 4

    context.game.ascension_level = 2
    move["ascension_modifiers"]["2+"] = {"damage_bonus": float("inf")}
    assert simulator._apply_ascension_move_value(move, context, "damage", 4) == 4

    move["ascension_modifiers"]["2+"] = {"damage": float("inf")}
    assert simulator._apply_ascension_move_value(move, context, "damage", 4) == 4


def test_prediction_death_split_data_rejects_nonfinite_values(monkeypatch):
    class FakeLoader:
        def get_enhanced_monster_data(self, monster_name):
            if monster_name == "Inf Count":
                return {
                    "name": monster_name,
                    "special_mechanics": {
                        "type": "death_split",
                        "split_count": float("inf"),
                    },
                }
            return {
                "name": monster_name,
                "special_mechanics": {
                    "type": "death_split",
                    "splits_into": ["Small Slime"],
                    "split_threshold_percent": float("inf"),
                },
            }

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    assert simulator._get_death_split_info({"name": "Inf Count", "hp": 10, "max_hp": 20}) is None
    assert simulator._get_death_split_info(
        {"name": "Inf Threshold", "hp": 10, "max_hp": 20}
    ) == (50.0, ["Small Slime"])


def test_prediction_strongest_known_attack_damage_rejects_nonfinite_hits(monkeypatch):
    class FakeLoader:
        def get_monster_moves(self, _monster_name):
            return [{"intent": "ATTACK", "damage": 7, "hits": float("inf")}]

    monkeypatch.setattr(simulation, "game_data_loader", FakeLoader())
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    assert simulator._strongest_known_attack_damage("Bad Hits") == 7


def test_potion_target_state_index_prefers_live_monster_id_over_same_name():
    state = SimpleNamespace(
        monsters=[
            {
                "name": "Slaver",
                "monster_id": "SlaverBlue",
                "hp": 30,
                "is_gone": False,
            },
            {
                "name": "Slaver",
                "monster_id": "SlaverRed",
                "hp": 30,
                "is_gone": False,
            },
        ]
    )
    target = SimpleNamespace(name="Slaver", monster_id="SlaverRed", current_hp=30)

    assert HeuristicCombatPlanner._state_monster_index_for_potion_target(state, target) == 1


def test_targeted_potions_are_skipped_without_live_targets():
    potion = SimpleNamespace(
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
        effect_value=20,
        target_type="monster",
    )
    context = _combat_context([], energy=0, monsters=[_louse(current_hp=30)])
    context.monsters_alive = []
    context.game.monsters = []
    context.game.room_type = "Monster"
    context.game.get_real_potions = lambda: [potion]
    state = SimulationState(context)
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    assert planner._get_potion_actions(context, state) == []


def test_potion_target_state_index_prefers_live_monster_index_for_identical_targets():
    state = SimpleNamespace(
        monsters=[
            {
                "name": "Fungi Beast",
                "monster_id": "FungiBeast",
                "hp": 30,
                "is_gone": False,
            },
            {
                "name": "Fungi Beast",
                "monster_id": "FungiBeast",
                "hp": 30,
                "is_gone": False,
            },
        ]
    )
    target = SimpleNamespace(
        name="Fungi Beast",
        monster_id="FungiBeast",
        current_hp=30,
        monster_index=1,
    )

    assert HeuristicCombatPlanner._state_monster_index_for_potion_target(state, target) == 1


def test_draw_potions_respect_no_draw_power():
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    for effect_type in ("draw", "draw_randomize_cost"):
        potion = SimpleNamespace(
            name="Draw Potion",
            effect_type=effect_type,
            effect_value=3,
            target_type="self",
        )
        context = _combat_context([], energy=0, monsters=[_louse(current_hp=100)])
        state = SimulationState(context)
        state.draw_blocked = True

        result = planner._simulate_potion_use(state, potion, target=None)

        assert result.cards_drawn == 0


def test_toy_ornithopter_heals_after_beam_potion_use():
    potion = SimpleNamespace(
        name="Energy Potion",
        can_use=True,
        requires_target=False,
        effect_type="energy",
        effect_value=2,
        target_type="self",
    )
    context = _combat_context([], energy=3, monsters=[_louse(current_hp=30)])
    context.game.current_hp = 48
    context.game.max_hp = 95
    context.player_hp = 48
    context.player_hp_pct = 48 / 95
    context.game.relics = [
        SimpleNamespace(name="Toy Ornithopter", relic_id="Toy Ornithopter", counter=-1)
    ]
    state = SimulationState(context)
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    result = planner._simulate_potion_use(state, potion, target=None)

    assert result.player_energy == 5
    assert result.player_hp == 53


def test_smoke_bomb_simulation_marks_combat_escaped_without_killing_monsters():
    potion = SimpleNamespace(
        name="Smoke Bomb",
        can_use=True,
        requires_target=False,
        effect_type="escape",
        effect_value=0,
        target_type="none",
    )
    context = _combat_context(
        [],
        energy=0,
        monsters=[_louse(current_hp=30), _louse(current_hp=40)],
    )
    context.game.monsters = context.monsters_alive
    context.game.room_type = "MonsterRoom"
    state = SimulationState(context)
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    result = planner._simulate_potion_use(state, potion, target=None)

    assert result.combat_escaped is True
    assert result.monsters_killed == 0
    assert [monster["is_gone"] for monster in result.monsters] == [False, False]


def test_smoke_bomb_escape_score_avoids_lethal_without_lethal_bonus():
    potion = SimpleNamespace(
        name="Smoke Bomb",
        can_use=True,
        requires_target=False,
        effect_type="escape",
        effect_value=0,
        target_type="none",
    )
    monster = _louse(current_hp=30)
    monster.move_adjusted_damage = 7
    monster.move_hits = 1
    context = _combat_context([], energy=0, monsters=[monster])
    context.game.current_hp = 5
    context.player_hp = 5
    context.player_hp_pct = 5 / 80
    context.game.monsters = context.monsters_alive
    context.game.room_type = "MonsterRoom"
    initial = SimulationState(context)
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    escaped = planner._simulate_potion_use(initial, potion, target=None)
    score = FastCombatSimulator(SynergyCardEvaluator()).calculate_outcome_score(
        initial,
        escaped,
        current_act=1,
        context=context,
    )

    assert score > 0
    assert score < simulation.ALL_LETHAL_BONUS
    assert escaped.monsters_killed == 0


def test_fairy_potion_prevents_lethal_in_outcome_score():
    potion = SimpleNamespace(
        name="Fairy in a Bottle",
        potion_id="FairyPotion",
        can_use=True,
        requires_target=False,
        effect_type="fairy",
        effect_value=0.3,
        target_type="self",
    )
    monster = _louse(current_hp=30)
    monster.move_adjusted_damage = 7
    monster.move_hits = 1
    context = _combat_context([], energy=0, monsters=[monster])
    context.game.current_hp = 5
    context.game.max_hp = 80
    context.player_hp = 5
    context.player_hp_pct = 5 / 80
    context.game.monsters = context.monsters_alive
    context.game.potions = [potion]
    context.game.get_real_potions = lambda: [potion]
    initial = SimulationState(context)

    score = FastCombatSimulator(SynergyCardEvaluator()).calculate_outcome_score(
        initial,
        initial,
        current_act=1,
        context=context,
    )

    assert score != float("-inf")


def test_looter_end_turn_escape_projection_removes_threat_without_kill_score():
    looter = Monster(
        name="Looter",
        monster_id="Looter",
        max_hp=45,
        current_hp=6,
        block=0,
        intent=Intent.ESCAPE,
        half_dead=False,
        is_gone=False,
        move_id=3,
        move_adjusted_damage=-1,
        move_hits=1,
    )
    context = _combat_context([], energy=0, monsters=[looter])
    context.game.monsters = context.monsters_alive
    initial = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    projected = simulator.project_end_turn_effects(initial)
    score = simulator.calculate_outcome_score(
        initial,
        initial,
        current_act=1,
        context=context,
    )

    assert projected.monsters[0]["is_gone"] is True
    assert projected.monsters[0]["hp"] == 6
    assert projected.monsters_killed == 0
    assert getattr(projected, "monsters_escaped", 0) == 1
    assert score < simulation.KILL_BONUS
    assert score < simulation.ALL_LETHAL_BONUS


def test_collector_spawn_end_turn_projection_adds_torch_heads_without_negative_damage_score():
    context = _combat_context([], energy=0, monsters=[_collector_spawn()])
    context.act = 2
    context.floor = 33
    context.ascension_level = 0
    context.game.ascension_level = 0
    context.game.monsters = context.monsters_alive
    initial = SimulationState(context)
    simulator = FastCombatSimulator(SynergyCardEvaluator())

    projected = simulator.project_end_turn_effects(initial)
    live_names = [
        monster["name"]
        for monster in projected.monsters
        if simulator._is_live_monster_state(monster)
    ]
    torch_heads = [
        monster
        for monster in projected.monsters
        if monster["name"] == "Torch Head"
    ]

    assert live_names.count("The Collector") == 1
    assert live_names.count("Torch Head") == 2
    assert all(38 <= monster["hp"] <= 40 for monster in torch_heads)
    score = simulator.calculate_outcome_score(
        initial,
        initial,
        current_act=2,
        weights={
            "KILL_BONUS": 0,
            "DAMAGE_WEIGHT": 1,
            "BLOCK_WEIGHT": 0,
            "ENERGY_EFFICIENCY_WEIGHT": 0,
            "W_DEATHRISK": 0,
        },
        context=context,
    )
    assert score == 0


def test_smoke_bomb_gets_high_priority_when_incoming_damage_is_lethal():
    potion = SimpleNamespace(
        name="Smoke Bomb",
        can_use=True,
        requires_target=False,
        effect_type="escape",
        effect_value=0,
        target_type="none",
    )
    monster = _louse(current_hp=30)
    monster.move_adjusted_damage = 7
    monster.move_hits = 1
    context = _combat_context([], energy=0, monsters=[monster])
    context.game.current_hp = 5
    context.player_hp = 5
    context.player_hp_pct = 5 / 80
    context.game.monsters = context.monsters_alive
    context.game.room_type = "MonsterRoom"
    state = SimulationState(context)
    planner = HeuristicCombatPlanner(SynergyCardEvaluator())

    assert planner._score_potion(potion, context, state) > 100


def test_draw_power_respects_no_draw_power():
    draw_power = _card(
        "Draw",
        "Draw",
        card_type=CardType.POWER,
        cost=1,
        has_target=False,
    )
    context = _combat_context([draw_power], energy=1, monsters=[_louse(current_hp=100)])
    state = SimulationState(context)
    state.draw_blocked = True

    result = FastCombatSimulator(SynergyCardEvaluator()).simulate_card_play(
        state,
        draw_power,
        target=None,
        target_index=None,
        context=context,
    )

    assert result.cards_drawn == 0
