from types import SimpleNamespace

import spirecomm.ai.heuristics.timing.timing_planner as timing_planner
from spirecomm.ai.heuristics.timing.models import (
    BalanceWeights,
    MonsterTimingHints,
    TimingContext,
    TurnTiming,
)
from spirecomm.ai.heuristics.timing.timing_planner import TimingAwareCombatPlanner
from spirecomm.data.loader import GameDataLoader
from spirecomm.spire.card import Card, CardRarity, CardType
from spirecomm.spire.character import Intent


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


def test_monster_timing_hints_accept_enum_intents():
    hints = MonsterTimingHints(
        safe_turn_indicators=["DEFEND"],
        spike_turn_indicators=["ATTACK_DEBUFF"],
    )

    assert hints.is_safe_turn(Intent.DEFEND) is True
    assert hints.is_safe_turn(Intent.ATTACK) is False
    assert hints.is_spike_turn(Intent.ATTACK_DEBUFF) is True


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


def test_timing_lethal_check_accepts_string_turn_for_dynamic_card_damage(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    turn_strike = _card("Turn_Strike", "Turn Strike")
    turn_strike.damage = 0

    def damage_for(turn, _strength):
        if not isinstance(turn, int):
            raise TypeError("turn must be int")
        return 12

    turn_strike.damage_for = damage_for
    context = SimpleNamespace(
        turn="1",
        strength=0,
        energy_available=1,
        playable_cards=[turn_strike],
        monsters_alive=[SimpleNamespace(current_hp=12, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_damage_estimate_rejects_nonfinite_strength():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        damage=6,
        cost=1,
        cost_for_turn=1,
        is_playable=True,
    )
    context = SimpleNamespace(turn=1, strength=float("inf"))

    assert TimingAwareCombatPlanner()._estimate_card_damage(strike, context) == 6


def test_timing_lethal_check_accepts_numeric_string_monster_hp_and_block(monkeypatch):
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
        monsters_alive=[SimpleNamespace(current_hp="10", block="2")],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    assert TimingAwareCombatPlanner()._can_kill_all_this_turn(context, timing_ctx)


def test_timing_lethal_check_accepts_string_attack_type(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = _card("Strike_R", "Strike")
    strike_a.uuid = "strike-a"
    strike_a.type = "ATTACK"
    strike_b = _card("Strike_R", "Strike")
    strike_b.uuid = "strike-b"
    strike_b.type = "ATTACK"
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


def test_timing_lethal_check_infers_name_only_single_target_attacks_without_has_target(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        uuid="strike-a",
        is_playable=True,
    )
    strike_b = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        uuid="strike-b",
        is_playable=True,
    )
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[strike_a, strike_b],
        monsters_alive=[
            SimpleNamespace(current_hp=6, block=0),
            SimpleNamespace(current_hp=6, block=0),
        ],
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


def test_timing_poisoned_target_check_accepts_numeric_string_hp():
    dead_poisoned = SimpleNamespace(
        current_hp="0",
        powers=[SimpleNamespace(power_name="Poison", amount=1)],
    )
    live_poisoned = SimpleNamespace(
        current_hp="12",
        powers=[SimpleNamespace(power_name="Poison", amount=1)],
    )
    context = SimpleNamespace(monsters_alive=[dead_poisoned, live_poisoned])

    assert TimingAwareCombatPlanner()._all_alive_targets_poisoned(context)


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


def test_timing_lethal_check_accepts_numeric_string_strength(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    heavy_blade = _card("Heavy Blade", "Heavy Blade+", cost=2)
    heavy_blade.upgrades = 1
    heavy_blade.uuid = "heavy-blade"
    context = SimpleNamespace(
        turn=1,
        strength="3",
        energy_available=3,
        playable_cards=[strike, heavy_blade],
        monsters_alive=[SimpleNamespace(current_hp=37, block=0)],
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


def test_timing_damage_estimate_counts_mind_blast_draw_pile():
    loader = _loader_with_basic_ironclad_cards()
    loader._cards["mind blast"] = {
        "name": "Mind Blast",
        "description": "Innate. Deal damage equal to the number of cards in your draw pile.",
    }
    mind_blast = _card("Mind Blast", "Mind Blast+", cost=1)
    mind_blast.damage = 0
    context = SimpleNamespace(
        turn=1,
        strength=2,
        energy_available=1,
        game=SimpleNamespace(draw_pile=[object() for _ in range(9)]),
    )

    damage = TimingAwareCombatPlanner(data_loader=loader)._estimate_card_damage(
        mind_blast,
        context,
    )

    assert damage == 11


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


def test_timing_lethal_check_combines_player_weak_and_target_vulnerable_before_rounding():
    dropkick = SimpleNamespace(
        name="Dropkick",
        type=CardType.ATTACK,
        damage=5,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        is_playable=True,
        uuid="weak-vulnerable-dropkick",
    )
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[dropkick],
        monsters_alive=[SimpleNamespace(current_hp=5, block=0)],
        vulnerable_stacks={0: 1},
        game=SimpleNamespace(
            player=SimpleNamespace(powers=[SimpleNamespace(power_name="Weak", amount=1)]),
        ),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._card_damage_against_monster(
        dropkick,
        context,
        context.monsters_alive,
        0,
        1,
    ) == 5
    assert planner._apply_attack_status_modifiers(
        dropkick,
        context,
        5,
        1,
        context.monsters_alive,
    ) == 5


def test_timing_lethal_check_applies_paper_phrog_vulnerable_multiplier(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = _card("Strike_R", "Strike")
    strike.uuid = "paper-phrog-strike"
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[SimpleNamespace(current_hp=10, block=0)],
        vulnerable_stacks={0: 1},
        game=SimpleNamespace(
            relics=[SimpleNamespace(relic_id="Paper Phrog", name="Paper Phrog")],
        ),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._card_damage_against_monster(
        strike,
        context,
        context.monsters_alive,
        0,
        1,
    ) == 10
    assert planner._apply_attack_status_modifiers(
        strike,
        context,
        6,
        1,
        context.monsters_alive,
    ) == 10


def test_timing_damage_estimate_applies_pen_nib_before_player_weak():
    strike = _card("Strike_R", "Strike")
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[SimpleNamespace(current_hp=9, block=0)],
        player=SimpleNamespace(powers=[SimpleNamespace(name="Weak", amount=1)]),
        game=SimpleNamespace(
            relics=[SimpleNamespace(relic_id="Pen Nib", name="Pen Nib", counter=9)],
        ),
    )
    planner = TimingAwareCombatPlanner(data_loader=_loader_with_basic_ironclad_cards())

    assert planner._card_damage_against_monster(
        strike,
        context,
        context.monsters_alive,
        0,
        1,
    ) == 9


def test_timing_lethal_sequence_uses_bash_vulnerable_before_followup(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    bash = _card("Bash", "Bash", cost=2)
    bash.uuid = "bash"
    strike = _card("Strike_R", "Strike", cost=1)
    strike.uuid = "strike"
    monster = SimpleNamespace(current_hp=17, block=0, monster_index=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=3,
        playable_cards=[bash, strike],
        monsters_alive=[monster],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(context, timing_ctx)
    actions = planner._generate_lethal_sequence(context)
    assert [action.card.uuid for action in actions] == ["bash", "strike"]
    assert [action.target_monster for action in actions] == [monster, monster]


def test_timing_lethal_sequence_uses_planner_loader_for_setup_cards(monkeypatch):
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "practice debuff": {
            "name": "Practice Debuff",
            "description": "Apply 2 Vulnerable.",
        },
        "strike": {"name": "Strike", "description": "Deal 6 damage."},
    }
    loader._wiki_data = {}
    monkeypatch.setattr(timing_planner, "game_data_loader", loader, raising=False)
    setup = _card(
        "Practice Debuff",
        "Practice Debuff",
        card_type=CardType.SKILL,
        cost=0,
        has_target=True,
    )
    setup.uuid = "setup"
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    monster = SimpleNamespace(current_hp=18, block=0, monster_index=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=2,
        playable_cards=[setup, strike_1, strike_2],
        monsters_alive=[monster],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner()

    assert planner._can_kill_all_this_turn(context, timing_ctx)
    actions = planner._generate_lethal_sequence(context)
    assert [action.card.uuid for action in actions] == [
        "setup",
        "strike-1",
        "strike-2",
    ]
    assert [action.target_monster for action in actions] == [monster, monster, monster]


def test_timing_planner_accepts_explicit_card_data_loader():
    loader = GameDataLoader(auto_load=False)
    loader._cards = {
        "practice strike": {
            "name": "Practice Strike",
            "description": "Deal 11 damage.",
        },
    }
    loader._wiki_data = {}
    strike = _card("Practice Strike", "Practice Strike", cost=1)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[SimpleNamespace(current_hp=11, block=0)],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )
    planner = TimingAwareCombatPlanner(data_loader=loader)

    assert planner._can_kill_all_this_turn(context, timing_ctx)


def test_timing_planner_cache_invalidates_when_same_turn_state_changes():
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=BalanceWeights.safe_turn_weights(),
    )

    class StaticClassifier:
        def classify_turn(self, _context):
            return timing_ctx

    class EchoPlanner:
        def __init__(self):
            self.calls = []

        def set_timing_context(self, timing_context):
            self.timing_context = timing_context

        def plan_turn(self, context):
            card_ids = tuple(card.uuid for card in context.playable_cards)
            self.calls.append(card_ids)
            return [card_ids[0]]

    first_card = _card("Defend_R", "Defend", card_type=CardType.SKILL)
    first_card.uuid = "first-defend"
    second_card = _card("Second Wind", "Second Wind", card_type=CardType.SKILL)
    second_card.uuid = "second-wind"
    first_context = SimpleNamespace(
        turn=1,
        energy_available=1,
        playable_cards=[first_card],
        monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
    )
    second_context = SimpleNamespace(
        turn=1,
        energy_available=1,
        playable_cards=[second_card],
        monsters_alive=[SimpleNamespace(current_hp=35, block=0, monster_index=0)],
    )
    base_planner = EchoPlanner()
    planner = TimingAwareCombatPlanner(
        base_planner=base_planner,
        classifier=StaticClassifier(),
    )

    assert planner.plan_with_timing(first_context) == ["first-defend"]
    assert planner.plan_with_timing(second_context) == ["second-wind"]
    assert base_planner.calls == [("first-defend",), ("second-wind",)]


def test_timing_planner_cache_invalidates_when_player_hp_changes():
    class StaticClassifier:
        def classify_turn(self, _context):
            return TimingContext(
                turn_timing=TurnTiming.SAFE,
                current_damage=0,
                balance_weights=BalanceWeights.safe_turn_weights(),
            )

    class HpSensitiveStrategy:
        def __init__(self):
            self.calls = []

        def get_balance_weights(self, timing, context, received_timing_ctx):
            self.calls.append((timing, context.player.current_hp, received_timing_ctx))
            return BalanceWeights(
                damage_weight=1.0,
                block_weight=1.0,
                kill_bonus=10.0,
                lethal_detection=True,
                block_threshold=99 if context.player.current_hp <= 10 else 0,
                opportunistic_attack=True,
            )

    class ThresholdPlanner:
        def __init__(self):
            self.calls = []

        def set_timing_context(self, timing_context):
            self.timing_context = timing_context

        def plan_turn(self, context):
            self.calls.append(context.player.current_hp)
            return [self.timing_context.balance_weights.block_threshold]

    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL)
    defend.uuid = "same-defend"

    def context_for_hp(current_hp):
        return SimpleNamespace(
            turn=1,
            energy_available=1,
            player=SimpleNamespace(current_hp=current_hp, max_hp=80),
            playable_cards=[defend],
            monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
        )

    base_planner = ThresholdPlanner()
    strategy = HpSensitiveStrategy()
    planner = TimingAwareCombatPlanner(
        base_planner=base_planner,
        classifier=StaticClassifier(),
        strategy=strategy,
    )

    assert planner.plan_with_timing(context_for_hp(60)) == [0]
    assert planner.plan_with_timing(context_for_hp(10)) == [99]
    assert base_planner.calls == [60, 10]
    assert [call[1] for call in strategy.calls] == [60, 10]


def test_timing_planner_cache_invalidates_when_game_hp_changes_with_stale_context_hp():
    class StaticClassifier:
        def classify_turn(self, _context):
            return TimingContext(
                turn_timing=TurnTiming.SAFE,
                current_damage=0,
                balance_weights=BalanceWeights.safe_turn_weights(),
            )

    class GameHpSensitiveStrategy:
        def get_balance_weights(self, _timing, context, _received_timing_ctx):
            return BalanceWeights(
                damage_weight=1.0,
                block_weight=1.0,
                kill_bonus=10.0,
                lethal_detection=True,
                block_threshold=99 if context.game.current_hp <= 10 else 0,
                opportunistic_attack=True,
            )

    class ThresholdPlanner:
        def __init__(self):
            self.calls = []

        def set_timing_context(self, timing_context):
            self.timing_context = timing_context

        def plan_turn(self, context):
            self.calls.append(context.game.current_hp)
            return [self.timing_context.balance_weights.block_threshold]

    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL)
    defend.uuid = "same-defend"

    def context_for_game_hp(current_hp):
        return SimpleNamespace(
            turn=1,
            energy_available=1,
            game=SimpleNamespace(
                current_hp=current_hp,
                max_hp=80,
                player=SimpleNamespace(block=0, powers=[]),
            ),
            player_hp=80,
            player_max_hp=80,
            playable_cards=[defend],
            monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
        )

    base_planner = ThresholdPlanner()
    planner = TimingAwareCombatPlanner(
        base_planner=base_planner,
        classifier=StaticClassifier(),
        strategy=GameHpSensitiveStrategy(),
    )

    assert planner.plan_with_timing(context_for_game_hp(60)) == [0]
    assert planner.plan_with_timing(context_for_game_hp(10)) == [99]
    assert base_planner.calls == [60, 10]


def test_timing_planner_cache_invalidates_when_player_block_status_changes():
    class StaticClassifier:
        def classify_turn(self, _context):
            return TimingContext(
                turn_timing=TurnTiming.SAFE,
                current_damage=0,
                balance_weights=BalanceWeights.safe_turn_weights(),
            )

    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL)
    defend.uuid = "same-defend"
    defend.block = 5

    class BlockEstimatingPlanner:
        def __init__(self, timing_planner):
            self.timing_planner = timing_planner
            self.calls = []

        def set_timing_context(self, timing_context):
            self.timing_context = timing_context

        def plan_turn(self, context):
            block = self.timing_planner._estimate_card_block(defend, context)
            self.calls.append(block)
            return [block]

    def context_for_powers(powers):
        return SimpleNamespace(
            turn=1,
            energy_available=1,
            game=SimpleNamespace(player=SimpleNamespace(block=0, powers=powers)),
            playable_cards=[defend],
            monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
        )

    planner = TimingAwareCombatPlanner(classifier=StaticClassifier())
    base_planner = BlockEstimatingPlanner(planner)
    planner.base_planner = base_planner

    assert planner.plan_with_timing(context_for_powers([])) == [5]
    assert planner.plan_with_timing(
        context_for_powers([SimpleNamespace(power_name="Dexterity", amount=2)])
    ) == [7]
    assert base_planner.calls == [5, 7]


def test_timing_planner_cache_invalidates_when_pen_nib_counter_changes():
    class StaticClassifier:
        def classify_turn(self, _context):
            return TimingContext(
                turn_timing=TurnTiming.SAFE,
                current_damage=0,
                balance_weights=BalanceWeights.safe_turn_weights(),
            )

    strike = _card("Strike_R", "Strike")
    strike.uuid = "same-strike"

    class DamageEstimatingPlanner:
        def __init__(self, timing_planner):
            self.timing_planner = timing_planner
            self.calls = []

        def set_timing_context(self, timing_context):
            self.timing_context = timing_context

        def plan_turn(self, context):
            damage = self.timing_planner._estimate_card_damage(strike, context)
            self.calls.append(damage)
            return [damage]

    def context_for_pen_nib(counter):
        return SimpleNamespace(
            turn=1,
            strength=0,
            energy_available=1,
            game=SimpleNamespace(
                player=SimpleNamespace(block=0, powers=[]),
                relics=[
                    SimpleNamespace(
                        relic_id="Pen Nib",
                        name="Pen Nib",
                        counter=counter,
                    )
                ],
            ),
            playable_cards=[strike],
            monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
        )

    planner = TimingAwareCombatPlanner(
        classifier=StaticClassifier(),
        data_loader=_loader_with_basic_ironclad_cards(),
    )
    base_planner = DamageEstimatingPlanner(planner)
    planner.base_planner = base_planner

    assert planner.plan_with_timing(context_for_pen_nib(0)) == [6]
    assert planner.plan_with_timing(context_for_pen_nib(9)) == [12]
    assert base_planner.calls == [6, 12]


def test_timing_planner_applies_injected_balance_strategy():
    classifier_weights = BalanceWeights(
        damage_weight=1.0,
        block_weight=1.0,
        kill_bonus=10.0,
        lethal_detection=True,
        block_threshold=0,
        opportunistic_attack=True,
    )
    strategy_weights = BalanceWeights(
        damage_weight=0.25,
        block_weight=4.0,
        kill_bonus=5.0,
        lethal_detection=True,
        block_threshold=12,
        opportunistic_attack=False,
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.SAFE,
        current_damage=0,
        balance_weights=classifier_weights,
    )

    class StaticClassifier:
        def classify_turn(self, _context):
            return timing_ctx

    class FixedStrategy:
        def __init__(self):
            self.calls = []

        def get_balance_weights(self, timing, context, received_timing_ctx):
            self.calls.append((timing, context, received_timing_ctx))
            return strategy_weights

    class CapturingPlanner:
        def set_timing_context(self, timing_context):
            self.timing_context = timing_context

        def plan_turn(self, _context):
            return []

    defend = _card("Defend_R", "Defend", card_type=CardType.SKILL)
    defend.uuid = "defend"
    context = SimpleNamespace(
        turn=1,
        energy_available=1,
        playable_cards=[defend],
        monsters_alive=[SimpleNamespace(current_hp=20, block=0, monster_index=0)],
    )
    base_planner = CapturingPlanner()
    strategy = FixedStrategy()
    planner = TimingAwareCombatPlanner(
        base_planner=base_planner,
        classifier=StaticClassifier(),
        strategy=strategy,
    )

    assert planner.plan_with_timing(context) == []
    assert base_planner.timing_context.balance_weights is strategy_weights
    assert strategy.calls == [(TurnTiming.SAFE, context, timing_ctx)]


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


def test_timing_targeted_lethal_search_uses_nunchaku_counter_nine():
    strike_1 = _card("Strike_R", "Strike", cost=1)
    strike_1.uuid = "strike-1"
    strike_2 = _card("Strike_R", "Strike", cost=1)
    strike_2.uuid = "strike-2"
    monster = SimpleNamespace(current_hp=12, block=0, monster_index=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike_1, strike_2],
        monsters_alive=[monster],
        game=SimpleNamespace(
            relics=[SimpleNamespace(relic_id="Nunchaku", name="Nunchaku", counter=9)],
        ),
    )
    planner = TimingAwareCombatPlanner(data_loader=_loader_with_basic_ironclad_cards())

    sequence = planner._find_targeted_lethal_sequence(
        context,
        context.playable_cards,
        context.monsters_alive,
        context.energy_available,
    )

    assert [action.card.uuid for action in sequence] == ["strike-1", "strike-2"]
    assert [action.target_monster for action in sequence] == [monster, monster]


def test_timing_vulnerable_target_check_accepts_numeric_string_hp():
    dead_target = SimpleNamespace(current_hp="0", block=0)
    live_target = SimpleNamespace(current_hp="12", block=0)
    context = SimpleNamespace(vulnerable_stacks={0: 0, 1: 1})

    assert TimingAwareCombatPlanner()._all_alive_targets_vulnerable(
        context,
        [dead_target, live_target],
    )


def test_timing_vulnerable_target_check_ignores_nonfinite_hp():
    invalid_target = SimpleNamespace(current_hp=float("inf"), block=0)
    live_target = SimpleNamespace(current_hp=12, block=0)
    context = SimpleNamespace(vulnerable_stacks={1: 1})

    assert TimingAwareCombatPlanner()._all_alive_targets_vulnerable(
        context,
        [invalid_target, live_target],
    )


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


def test_timing_lethal_sequence_targets_name_only_attacks_without_has_target(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike_a = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        uuid="strike-a",
        is_playable=True,
    )
    strike_b = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        uuid="strike-b",
        is_playable=True,
    )
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


def test_timing_damage_estimate_accepts_string_damage_field():
    card = SimpleNamespace(
        card_id="Strike_R",
        name="Strike",
        type=CardType.ATTACK,
        damage="6",
    )
    context = SimpleNamespace(turn=1, strength=2, energy_available=1)

    damage = TimingAwareCombatPlanner()._estimate_card_damage(card, context)

    assert damage == 8


def test_timing_damage_estimate_accepts_decimal_string_damage_field():
    card = SimpleNamespace(
        card_id="Custom Attack",
        name="Custom Attack",
        type=CardType.ATTACK,
        damage="6.0",
    )
    context = SimpleNamespace(turn=1, strength=2, energy_available=1)

    damage = TimingAwareCombatPlanner()._estimate_card_damage(card, context)

    assert damage == 8


def test_timing_block_estimate_accepts_string_block_field():
    card = SimpleNamespace(
        card_id="Defend_R",
        name="Defend",
        type=CardType.SKILL,
        block="5",
    )

    block = TimingAwareCombatPlanner()._estimate_card_block(card)

    assert block == 5


def test_timing_monster_effective_hp_accepts_decimal_string_hp_and_block():
    monster = SimpleNamespace(current_hp="20.0", block="3.0")

    hp = TimingAwareCombatPlanner()._monster_effective_hp(monster)

    assert hp == 23


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


def test_timing_fallback_targets_name_only_single_target_attack_without_has_target(monkeypatch):
    monkeypatch.setattr(
        timing_planner,
        "game_data_loader",
        _loader_with_basic_ironclad_cards(),
        raising=False,
    )
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        uuid="strike",
        is_playable=True,
    )
    target = SimpleNamespace(current_hp=30, block=0, monster_index=0)
    context = SimpleNamespace(
        turn=1,
        strength=0,
        energy_available=1,
        playable_cards=[strike],
        monsters_alive=[target],
    )
    timing_ctx = TimingContext(
        turn_timing=TurnTiming.BURST_WINDOW,
        current_damage=0,
        balance_weights=BalanceWeights(damage_weight=1.0, block_weight=0.1),
    )

    actions = TimingAwareCombatPlanner()._fallback_plan(context, timing_ctx)

    assert len(actions) == 1
    assert actions[0].card is strike
    assert actions[0].target_monster is target
