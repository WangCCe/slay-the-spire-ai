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
        "bane": {
            "name": "Bane",
            "description": "Deal 7 damage. If the enemy has Poison, deal 7 damage again.",
        },
        "whirlwind": {
            "name": "Whirlwind",
            "description": "Deal 5 damage to ALL enemies X times.",
        },
        "skewer": {
            "name": "Skewer",
            "description": "Deal 7 damage X times.",
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
        "body slam": {
            "name": "Body Slam",
            "description": "Deal damage equal to your current Block.",
        },
        "fiend fire": {
            "name": "Fiend Fire",
            "description": "Exhaust your hand. Deal 7 damage for each card Exhausted. Exhaust.",
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


def test_timing_lethal_check_uses_remaining_energy_for_x_cost_aoe(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    whirlwind = _card("Whirlwind", "Whirlwind", cost=-1, has_target=False)
    whirlwind.cost_for_turn = -1
    whirlwind.uuid = "whirlwind"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=3,
        playable_cards=[strike, whirlwind],
        monsters_alive=[
            SimpleNamespace(current_hp=15, block=0),
            SimpleNamespace(current_hp=21, block=0),
        ],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    planner = TimingAwareCombatPlanner()

    assert not planner._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_skewer_x_energy_hits(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    skewer = _card("Skewer", "Skewer", cost=-1)
    skewer.cost_for_turn = -1
    skewer.uuid = "skewer"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=3,
        playable_cards=[skewer],
        monsters_alive=[SimpleNamespace(current_hp=21, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_bane_second_hit_against_poisoned_target(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    bane = _card("Bane", "Bane", cost=1)
    bane.uuid = "bane"
    poisoned_monster = SimpleNamespace(
        current_hp=14,
        block=0,
        powers=[SimpleNamespace(power_name="Poison", amount=1)],
    )
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[bane],
        monsters_alive=[poisoned_monster],
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


def test_timing_lethal_check_treats_none_upgrades_as_base_hit_count(monkeypatch):
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
    sword_boomerang.upgrades = None
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


def test_timing_lethal_check_rejects_random_hit_attack_against_multiple_monsters(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    first_boomerang = _card(
        "Sword Boomerang",
        "Sword Boomerang",
        cost=1,
        has_target=False,
    )
    first_boomerang.uuid = "boomerang-1"
    second_boomerang = _card(
        "Sword Boomerang",
        "Sword Boomerang",
        cost=1,
        has_target=False,
    )
    second_boomerang.uuid = "boomerang-2"
    context = SimpleNamespace(
        turn=1,
        strength=2,
        energy_available=2,
        playable_cards=[first_boomerang, second_boomerang],
        monsters_alive=[
            SimpleNamespace(current_hp=15, block=0, monster_index=0),
            SimpleNamespace(current_hp=15, block=0, monster_index=1),
        ],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert not planner._can_kill_all_this_turn(context, timing_ctx)
    assert planner._generate_lethal_sequence(context) == []


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


def test_timing_lethal_check_counts_body_slam_current_block(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    body_slam = _card("Body Slam", "Body Slam", cost=1)
    body_slam.uuid = "body-slam"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[body_slam],
        monsters_alive=[SimpleNamespace(current_hp=24, block=0)],
        game=SimpleNamespace(player=SimpleNamespace(block=24)),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_counts_fiend_fire_hand_damage(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    fiend_fire = _card("Fiend Fire", "Fiend Fire", cost=2)
    fiend_fire.uuid = "fiend-fire"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, cost=1, has_target=False)
    defend.uuid = "defend"
    dazed = _card("Dazed", "Dazed", card_type=CardType.STATUS, cost=-2, has_target=False)
    dazed.uuid = "dazed"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[fiend_fire],
        monsters_alive=[SimpleNamespace(current_hp=21, block=0)],
        game=SimpleNamespace(hand=[fiend_fire, strike, defend, dazed]),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_reduces_damage_while_player_is_weak(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike")
    strike.uuid = "weak-strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[SimpleNamespace(current_hp=6, block=0)],
        game=SimpleNamespace(
            player=SimpleNamespace(powers=[SimpleNamespace(power_name="Weak", amount=1)]),
        ),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert not TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_applies_single_target_vulnerable(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike")
    strike.uuid = "vulnerable-strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[SimpleNamespace(current_hp=9, block=0)],
        vulnerable_stacks={0: 1},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_uses_dropkick_energy_refund(monkeypatch):
    loader = _loader_with_basic_ironclad_cards()
    loader._cards["dropkick"] = {
        "name": "Dropkick",
        "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
    }
    monkeypatch.setattr(timing_planner, "game_data_loader", loader, raising=False)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    monster = SimpleNamespace(current_hp=16, block=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[dropkick, strike],
        monsters_alive=[monster],
        vulnerable_stacks={0: 1},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(context, timing_ctx)
    assert [action.card.uuid for action in planner._generate_lethal_sequence(context)] == [
        "dropkick",
        "strike",
    ]


def test_timing_lethal_sequence_reorders_dropkick_before_spending_refunded_energy(monkeypatch):
    loader = _loader_with_basic_ironclad_cards()
    loader._cards["dropkick"] = {
        "name": "Dropkick",
        "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
    }
    monkeypatch.setattr(timing_planner, "game_data_loader", loader, raising=False)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    monster = SimpleNamespace(current_hp=16, block=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike, dropkick],
        monsters_alive=[monster],
        vulnerable_stacks={0: 1},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(context, timing_ctx)
    assert [action.card.uuid for action in planner._generate_lethal_sequence(context)] == [
        "dropkick",
        "strike",
    ]


def test_timing_lethal_sequence_uses_dropkick_refund_on_one_vulnerable_target(monkeypatch):
    loader = _loader_with_basic_ironclad_cards()
    loader._cards["dropkick"] = {
        "name": "Dropkick",
        "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
    }
    monkeypatch.setattr(timing_planner, "game_data_loader", loader, raising=False)
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    vulnerable_target = SimpleNamespace(current_hp=7, block=0, monster_index=0)
    other_target = SimpleNamespace(current_hp=6, block=0, monster_index=1)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike, dropkick],
        monsters_alive=[vulnerable_target, other_target],
        vulnerable_stacks={0: 1, 1: 0},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(context, timing_ctx)

    actions = planner._generate_lethal_sequence(context)

    assert [action.card.uuid for action in actions] == ["dropkick", "strike"]
    assert [action.target_monster for action in actions] == [
        vulnerable_target,
        other_target,
    ]


def test_timing_lethal_sequence_combines_aoe_with_dropkick_refund(monkeypatch):
    loader = _loader_with_basic_ironclad_cards()
    loader._cards["dropkick"] = {
        "name": "Dropkick",
        "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
    }
    monkeypatch.setattr(timing_planner, "game_data_loader", loader, raising=False)
    cleave = _card("Cleave", "Cleave", cost=1, has_target=False)
    cleave.uuid = "cleave"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    dropkick.uuid = "dropkick"
    vulnerable_target = SimpleNamespace(current_hp=15, block=0, monster_index=0)
    other_target = SimpleNamespace(current_hp=14, block=0, monster_index=1)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike, cleave, dropkick],
        monsters_alive=[vulnerable_target, other_target],
        vulnerable_stacks={0: 1, 1: 0},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(context, timing_ctx)

    actions = planner._generate_lethal_sequence(context)

    assert [action.card.uuid for action in actions] == ["dropkick", "cleave", "strike"]
    assert [action.target_monster for action in actions] == [
        vulnerable_target,
        None,
        other_target,
    ]


def test_timing_lethal_check_requires_upfront_energy_for_dropkick_refund(monkeypatch):
    loader = _loader_with_basic_ironclad_cards()
    loader._cards["dropkick"] = {
        "name": "Dropkick",
        "description": "Deal 5 damage. If the enemy has Vulnerable, gain [R] and draw 1 card.",
    }
    monkeypatch.setattr(timing_planner, "game_data_loader", loader, raising=False)
    dropkick = _card("Dropkick", "Dropkick", cost=1)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=0,
        playable_cards=[dropkick],
        monsters_alive=[SimpleNamespace(current_hp=7, block=0)],
        vulnerable_stacks={0: 1},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert not planner._can_kill_all_this_turn(context, timing_ctx)
    assert planner._generate_lethal_sequence(context) == []


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


def test_timing_lethal_sequence_returns_empty_when_no_lethal_subset(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
    )

    assert TimingAwareCombatPlanner()._generate_lethal_sequence(context) == []


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


def test_timing_fallback_applies_dexterity_to_block_scores(monkeypatch):
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
        playable_cards=[strike, defend],
        monsters_alive=[SimpleNamespace(current_hp=30, block=0)],
        game=SimpleNamespace(
            player=SimpleNamespace(powers=[SimpleNamespace(power_name="Dexterity", amount=2)]),
        ),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.BALANCED,
        current_damage=0,
        balance_weights=BalanceWeights(damage_weight=1.0, block_weight=1.0),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is defend


def test_timing_block_estimate_treats_none_upgrades_as_base_card(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL, has_target=False)
    defend.upgrades = None

    block = TimingAwareCombatPlanner()._estimate_card_block(defend)

    assert block == 5


def test_timing_fallback_applies_frail_to_block_scores(monkeypatch):
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
        game=SimpleNamespace(
            player=SimpleNamespace(powers=[SimpleNamespace(power_name="Frail", amount=1)]),
        ),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.BALANCED,
        current_damage=0,
        balance_weights=BalanceWeights(damage_weight=0.7, block_weight=1.0),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is strike


def test_timing_fallback_reduces_attack_scores_while_player_is_weak(monkeypatch):
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
        playable_cards=[strike, defend],
        monsters_alive=[SimpleNamespace(current_hp=30, block=0)],
        game=SimpleNamespace(
            player=SimpleNamespace(powers=[SimpleNamespace(power_name="Weak", amount=1)]),
        ),
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.BALANCED,
        current_damage=0,
        balance_weights=BalanceWeights(damage_weight=1.0, block_weight=1.0),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is defend


def test_timing_fallback_boosts_attack_scores_against_vulnerable_targets(monkeypatch):
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
        vulnerable_stacks={0: 1},
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.BURST_WINDOW,
        current_damage=0,
        balance_weights=BalanceWeights(damage_weight=0.6, block_weight=1.0),
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
