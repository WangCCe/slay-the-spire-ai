from types import SimpleNamespace

import spirecomm.ai.heuristics.timing.timing_planner as timing_planner
from spirecomm.ai.heuristics.timing.models import BalanceWeights, TimingContext, TurnTiming
from spirecomm.ai.heuristics.timing.timing_planner import TimingAwareCombatPlanner
from spirecomm.data.loader import GameDataLoader
from spirecomm.spire.card import Card, CardRarity, CardType


def _card(card_id, name, card_type=CardType.ATTACK, cost=1, has_target=True):
    return Card(
        card_id=card_id,
        name=name,
        card_type=card_type,
        rarity=CardRarity.BASIC,
        cost=cost,
        has_target=has_target,
        is_playable=True,
    )


def _loader_with_basic_ironclad_cards():
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "strike": {
            "name": "Strike",
            "description": "Deal 6 damage.",
        },
        "defend": {
            "name": "Defend",
            "description": "Gain 5 Block.",
        },
        "cleave": {
            "name": "Cleave",
            "description": "Deal 8 damage to ALL enemies.",
        },
        "bash": {
            "name": "Bash",
            "description": "Deal 8 damage. Apply 2 Vulnerable.",
        },
        "whirlwind": {
            "name": "Whirlwind",
            "description": "Deal 5 damage to ALL enemies X times.",
        },
        "twin strike": {
            "name": "Twin Strike",
            "description": "Deal 5 damage 2 times.",
        },
        "sword boomerang": {
            "name": "Sword Boomerang",
            "description": "Deal 3 damage to a random enemy 3 times.",
        },
        "heavy blade": {
            "name": "Heavy Blade",
            "description": "Deal 14 damage. Strength affects Heavy Blade 3 times.",
        },
        "perfected strike": {
            "name": "Perfected Strike",
            "description": "Deal 6 damage. Deals 2 additional damage for ALL your cards containing \"Strike\".",
        },
    }
    return loader


def test_timing_lethal_check_uses_parsed_damage_for_plain_cards(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = _card("Strike_R", "Strike")
    strike_a.uuid = "strike-a"
    strike_b = _card("Strike_R", "Strike")
    strike_b.uuid = "strike-b"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike_a, strike_b],
        monsters_alive=[SimpleNamespace(current_hp=12, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_ignores_unaffordable_parsed_damage(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = _card("Strike_R", "Strike")
    strike_a.uuid = "strike-a"
    strike_b = _card("Strike_R", "Strike")
    strike_b.uuid = "strike-b"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike_a, strike_b],
        monsters_alive=[SimpleNamespace(current_hp=12, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert not TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_accounts_for_single_target_overkill(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = _card("Strike_R", "Strike")
    strike_a.uuid = "strike-a"
    strike_b = _card("Strike_R", "Strike")
    strike_b.uuid = "strike-b"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike_a, strike_b],
        monsters_alive=[
            SimpleNamespace(current_hp=10, block=0),
            SimpleNamespace(current_hp=2, block=0),
        ],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert not TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_applies_aoe_damage_to_each_monster(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    cleave = _card("Cleave", "Cleave", has_target=False)
    cleave.uuid = "cleave"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[cleave],
        monsters_alive=[
            SimpleNamespace(current_hp=8, block=0),
            SimpleNamespace(current_hp=8, block=0),
        ],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_chooses_lethal_subset_over_hand_order(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike, bash],
        monsters_alive=[SimpleNamespace(current_hp=8, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_whirlwind_x_energy_damage(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, has_target=False)
    whirlwind.cost_for_turn = -1
    whirlwind.uuid = "whirlwind"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=3,
        playable_cards=[whirlwind],
        monsters_alive=[
            SimpleNamespace(current_hp=15, block=0),
            SimpleNamespace(current_hp=15, block=0),
        ],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_multi_hit_attack_damage(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    twin_strike = _card("Twin Strike", "Twin Strike", cost=1)
    twin_strike.uuid = "twin-strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[twin_strike],
        monsters_alive=[SimpleNamespace(current_hp=10, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_random_hit_attack_damage_against_single_monster(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    sword_boomerang = _card(
        "Sword Boomerang",
        "Sword Boomerang",
        cost=1,
        has_target=False,
    )
    sword_boomerang.uuid = "sword-boomerang"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[sword_boomerang],
        monsters_alive=[SimpleNamespace(current_hp=9, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_applies_heavy_blade_strength_multiplier(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    heavy_blade = _card("Heavy Blade", "Heavy Blade+", cost=2)
    heavy_blade.upgrades = 1
    heavy_blade.uuid = "heavy-blade"
    context = SimpleNamespace(
        turn=1,
        strength=3,
        energy_available=2,
        playable_cards=[heavy_blade],
        monsters_alive=[SimpleNamespace(current_hp=29, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_perfected_strike_deck_scaling(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    perfected_strike = _card("Perfected Strike", "Perfected Strike+", cost=2)
    perfected_strike.upgrades = 1
    perfected_strike.uuid = "perfected-strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[perfected_strike],
        monsters_alive=[SimpleNamespace(current_hp=18, block=0)],
        game=SimpleNamespace(
            deck=[
                _card("Strike_R", "Strike"),
                _card("Strike_R", "Strike"),
                _card("Twin Strike", "Twin Strike"),
                _card("Perfected Strike", "Perfected Strike"),
            ],
        ),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_sequence_does_not_target_aoe_cards(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    cleave = _card("Cleave", "Cleave", has_target=False)
    cleave.uuid = "cleave"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[cleave],
        monsters_alive=[
            SimpleNamespace(current_hp=8, block=0, monster_index=0),
            SimpleNamespace(current_hp=8, block=0, monster_index=1),
        ],
    )

    actions = TimingAwareCombatPlanner()._generate_lethal_sequence(context)

    assert len(actions) == 1
    assert actions[0].card is cleave
    assert actions[0].target_monster is None


def test_timing_lethal_sequence_targets_multiple_single_target_monsters(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = _card("Strike_R", "Strike")
    strike_a.uuid = "strike-a"
    strike_b = _card("Strike_R", "Strike")
    strike_b.uuid = "strike-b"
    first_monster = SimpleNamespace(current_hp=6, block=0, monster_index=0)
    second_monster = SimpleNamespace(current_hp=6, block=0, monster_index=1)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike_a, strike_b],
        monsters_alive=[first_monster, second_monster],
    )

    actions = TimingAwareCombatPlanner()._generate_lethal_sequence(context)

    assert [action.card for action in actions] == [strike_a, strike_b]
    assert [action.target_monster for action in actions] == [first_monster, second_monster]


def test_timing_lethal_sequence_uses_lethal_subset_not_highest_damage_greedy(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    strike_a = _card("Strike_R", "Strike", cost=1)
    strike_a.uuid = "strike-a"
    strike_b = _card("Strike_R", "Strike", cost=1)
    strike_b.uuid = "strike-b"
    monster = SimpleNamespace(current_hp=12, block=0, monster_index=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[bash, strike_a, strike_b],
        monsters_alive=[monster],
    )

    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(
        context,
        TimingContext(
            turn_timing=TurnTiming.SAFE,
            current_damage=0,
            balance_weights=BalanceWeights.safe_turn_weights(),
        ),
    )
    actions = planner._generate_lethal_sequence(context)

    assert [action.card for action in actions] == [strike_a, strike_b]
    assert [action.target_monster for action in actions] == [monster, monster]


def test_timing_fallback_scores_parsed_damage_and_block_for_plain_cards(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False)
    defend.uuid = "defend"
    strike = _card("Strike_R", "Strike")
    strike.uuid = "strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[defend, strike],
        monsters_alive=[SimpleNamespace(current_hp=30, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is strike


def test_timing_fallback_does_not_target_no_target_cards(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False)
    defend.uuid = "defend"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[defend],
        monsters_alive=[SimpleNamespace(current_hp=30, block=0, monster_index=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.THREAT_SPIKE,
        current_damage=12,
        balance_weights=BalanceWeights.threat_spike_weights(),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is defend
    assert actions[0].target_monster is None
