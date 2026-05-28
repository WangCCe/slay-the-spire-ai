"""
Test script to verify timing awareness integration.

This script creates a mock combat scenario and checks if:
1. TurnTimingClassifier correctly classifies the turn
2. CombatBalanceStrategy returns appropriate weights
3. IroncladCombatPlanner uses timing awareness
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from spirecomm.ai.heuristics.timing import (
    TurnTimingClassifier,
    CombatBalanceStrategy,
    TurnTiming
)
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.spire.card import CardType
from spirecomm.spire.character import Player


def _card(card_id, name, cost, card_type):
    return SimpleNamespace(
        card_id=card_id,
        name=name,
        cost=cost,
        type=card_type,
        card_type=card_type,
        uuid=f"{card_id.lower()}_1",
        upgrades=0,
        is_playable=True,
    )


def _monster(name, current_hp, max_hp, intent, move_adjusted_damage=0, move_hits=1):
    return SimpleNamespace(
        name=name,
        current_hp=current_hp,
        max_hp=max_hp,
        block=0,
        intent=intent,
        half_dead=False,
        is_gone=False,
        powers=[],
        strength=0,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=move_hits,
    )


def _mock_context(player, monsters, hand, turn, floor=1, act=1):
    game = SimpleNamespace(
        current_hp=player.current_hp,
        max_hp=player.max_hp,
        player=player,
        monsters=monsters,
        hand=hand,
        ascension_level=0,
    )
    return SimpleNamespace(
        game=game,
        player=player,
        monsters_alive=monsters,
        hand=hand,
        playable_cards=hand,
        draw_pile=[],
        discard_pile=[],
        energy_available=player.energy,
        turn=turn,
        floor=floor,
        act=act,
        player_hp=player.current_hp,
        player_hp_pct=player.current_hp / max(player.max_hp, 1),
        incoming_damage=sum(
            max(0, getattr(monster, "move_adjusted_damage", 0))
            * max(1, getattr(monster, "move_hits", 1))
            for monster in monsters
            if "ATTACK" in str(getattr(monster, "intent", "")).upper()
        ),
        vulnerable_stacks={i: 0 for i, _ in enumerate(monsters)},
        weak_stacks={i: 0 for i, _ in enumerate(monsters)},
        frail_stacks={i: 0 for i, _ in enumerate(monsters)},
        thorns_stacks={i: 0 for i, _ in enumerate(monsters)},
    )
def create_mock_context_buff_turn():
    """Create mock context for a generic turn-1 BUFF intent."""
    # Mock player
    player = Player(
        current_hp=80,
        max_hp=80,
        block=0,
        energy=3
    )

    # Jaw Worm has prediction data but no forced timing override, so this tests
    # the base BUFF classification path through the real data loader.
    monster = _monster("Jaw Worm", current_hp=50, max_hp=50, intent="BUFF")
    monster.index = 0

    # Mock cards
    strike = _card("Strike_R", "Strike", cost=1, card_type=CardType.ATTACK)
    defend = _card("Defend_R", "Defend", cost=1, card_type=CardType.SKILL)
    bash = _card("Bash", "Bash", cost=2, card_type=CardType.ATTACK)

    return _mock_context(player, [monster], [strike, defend, bash], turn=1)


def test_timing_classification():
    """Test 1: Timing classification for a generic turn-1 BUFF intent."""
    print("=" * 60)
    print("TEST 1: Timing Classification - Generic Buff Turn")
    print("=" * 60)

    context = create_mock_context_buff_turn()
    classifier = TurnTimingClassifier()

    timing_ctx = classifier.classify_turn(context)

    print(f"✓ Turn classified as: {timing_ctx.turn_timing.value}")
    print(f"✓ Current damage expected: {timing_ctx.current_damage:.1f}")
    if timing_ctx.future_damage_curve:
        print(f"✓ Future damage curve: {[f'{d:.1f}' for d in timing_ctx.future_damage_curve]}")
    print(f"✓ Safe windows detected: {len(timing_ctx.safe_windows)}")

    assert timing_ctx.turn_timing == TurnTiming.SAFE
    print("✅ PASS: Generic buff turn correctly classified as SAFE")

    print()


def test_balance_weights():
    """Test 2: Balance weights for SAFE timing."""
    print("=" * 60)
    print("TEST 2: Balance Weights - SAFE Timing")
    print("=" * 60)

    context = create_mock_context_buff_turn()
    classifier = TurnTimingClassifier()
    strategy = CombatBalanceStrategy()

    timing_ctx = classifier.classify_turn(context)
    weights = strategy.get_balance_weights(timing_ctx.turn_timing, context, timing_ctx)

    print(f"✓ Damage weight: {weights.damage_weight:.2f}")
    print(f"✓ Block weight: {weights.block_weight:.2f}")
    print(f"✓ Kill bonus: {weights.kill_bonus:.1f}")
    print(f"✓ Lethal detection: {weights.lethal_detection}")

    assert weights.damage_weight > weights.block_weight
    print("✅ PASS: SAFE timing has aggressive weights (damage > block)")

    print()


def test_ironclad_planner_integration():
    """Test 3: IroncladCombatPlanner with timing awareness."""
    print("=" * 60)
    print("TEST 3: IroncladCombatPlanner Integration")
    print("=" * 60)

    context = create_mock_context_buff_turn()

    # Create planner with timing awareness
    planner = IroncladCombatPlanner()

    # Check that timing components are initialized
    has_classifier = hasattr(planner, 'timing_classifier')
    has_strategy = hasattr(planner, 'balance_strategy')

    print(f"✓ Has timing_classifier: {has_classifier}")
    print(f"✓ Has balance_strategy: {has_strategy}")

    assert has_classifier and has_strategy
    print("✅ PASS: IroncladCombatPlanner initialized with timing awareness")

    # Test timing classification through planner
    timing_ctx = planner.timing_classifier.classify_turn(context)
    print(f"✓ Planner can classify turns: {timing_ctx.turn_timing.value}")

    # Test simulator accepts timing context
    planner.simulator.set_timing_context(timing_ctx)
    print(f"✓ Simulator accepts timing context: {planner.simulator.timing_context is not None}")

    print()


def test_threat_spike_scenario():
    """Test 4: Threat spike scenario with a generic ATTACK intent."""
    print("=" * 60)
    print("TEST 4: Threat Spike Classification - Generic Attack Turn")
    print("=" * 60)

    # Create mock context for Cultist turn 2 (ATTACK intent)
    player = Player(
        current_hp=75,
        max_hp=80,
        block=0,
        energy=3
    )

    # Jaw Worm has prediction data but no forced timing override, so this tests
    # the base high-damage attack classification path through the real data loader.
    monster = _monster(
        "Jaw Worm",
        current_hp=40,
        max_hp=50,
        intent="ATTACK",
        move_adjusted_damage=20,
    )
    monster.index = 0
    # Mock cards
    strike = _card("Strike_R", "Strike", cost=1, card_type=CardType.ATTACK)
    defend = _card("Defend_R", "Defend", cost=1, card_type=CardType.SKILL)
    context = _mock_context(player, [monster], [strike, defend], turn=2)

    classifier = TurnTimingClassifier()
    strategy = CombatBalanceStrategy()

    timing_ctx = classifier.classify_turn(context)
    weights = strategy.get_balance_weights(timing_ctx.turn_timing, context, timing_ctx)

    print(f"✓ Turn classified as: {timing_ctx.turn_timing.value}")
    print(f"✓ Current damage expected: {timing_ctx.current_damage:.1f}")
    print(f"✓ Damage weight: {weights.damage_weight:.2f}")
    print(f"✓ Block weight: {weights.block_weight:.2f}")

    assert weights.block_weight > weights.damage_weight
    print("✅ PASS: THREAT_SPIKE timing has defensive weights (block > damage)")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TIMING AWARENESS INTEGRATION TEST")
    print("=" * 60)
    print()

    try:
        test_timing_classification()
        test_balance_weights()
        test_ironclad_planner_integration()
        test_threat_spike_scenario()

        print("=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
        print("\n✅ Timing awareness system is working correctly!")
        print("\nNext steps:")
        print("1. Run actual game with Communication Mod")
        print("2. Check ai_debug.log for [TIMING_CLASSIFY] and [TIMING_WEIGHTS] messages")
        print("3. Verify AI behavior matches timing (aggressive on SAFE, defensive on THREAT_SPIKE)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
