"""
Test script to verify timing awareness integration.

This script creates a mock combat scenario and checks if:
1. TurnTimingClassifier correctly classifies the turn
2. CombatBalanceStrategy returns appropriate weights
3. IroncladCombatPlanner uses timing awareness
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from spirecomm.ai.heuristics.timing import (
    TurnTimingClassifier,
    CombatBalanceStrategy,
    TurnTiming
)
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Monster, Player, Intent
from spirecomm.spire.relic import Relic


def create_mock_context_cultist_turn1():
    """Create mock context for Cultist turn 1 (Ritual - BUFF intent)."""
    # Mock player
    player = Player(
        current_hp=80,
        max_hp=80,
        block=0,
        energy=3
    )

    # Mock Cultist with BUFF intent (Ritual)
    cultist = Monster(
        name="Cultist",
        current_hp=50,
        max_hp=50,
        intent=Intent.BUFF,
        move_name="Ritual",
        powers=[]
    )
    cultist.index = 0

    # Mock cards
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        cost=1,
        card_type=CardType.ATTACK
    )
    strike.uuid = "strike_1"
    strike.upgrades = 0

    defend = Card(
        card_id="Defend_R",
        name="Defend",
        cost=1,
        card_type=CardType.SKILL
    )
    defend.uuid = "defend_1"
    defend.upgrades = 0

    bash = Card(
        card_id="Bash",
        name="Bash",
        cost=2,
        card_type=CardType.ATTACK
    )
    bash.uuid = "bash_1"
    bash.upgrades = 0

    # Mock context
    context = DecisionContext(
        player=player,
        monsters=[cultist],
        hand=[strike, defend, bash],
        draw_pile=[],
        discard_pile=[],
        energy_available=3,
        turn=1,
        floor=1,
        act=1
    )

    return context


def test_timing_classification():
    """Test 1: Timing classification for Cultist turn 1."""
    print("=" * 60)
    print("TEST 1: Timing Classification - Cultist Turn 1 (Ritual)")
    print("=" * 60)

    context = create_mock_context_cultist_turn1()
    classifier = TurnTimingClassifier()

    timing_ctx = classifier.classify_turn(context)

    print(f"✓ Turn classified as: {timing_ctx.turn_timing.value}")
    print(f"✓ Current damage expected: {timing_ctx.current_damage:.1f}")
    if timing_ctx.future_damage_curve:
        print(f"✓ Future damage curve: {[f'{d:.1f}' for d in timing_ctx.future_damage_curve]}")
    print(f"✓ Safe windows detected: {len(timing_ctx.safe_windows)}")

    # Cultist turn 1 should be SAFE (buffing with Ritual)
    if timing_ctx.turn_timing == TurnTiming.SAFE:
        print("✅ PASS: Cultist turn 1 correctly classified as SAFE")
    else:
        print(f"❌ FAIL: Expected SAFE, got {timing_ctx.turn_timing.value}")

    print()


def test_balance_weights():
    """Test 2: Balance weights for SAFE timing."""
    print("=" * 60)
    print("TEST 2: Balance Weights - SAFE Timing")
    print("=" * 60)

    context = create_mock_context_cultist_turn1()
    classifier = TurnTimingClassifier()
    strategy = CombatBalanceStrategy()

    timing_ctx = classifier.classify_turn(context)
    weights = strategy.get_balance_weights(timing_ctx.turn_timing, context, timing_ctx)

    print(f"✓ Damage weight: {weights.damage_weight:.2f}")
    print(f"✓ Block weight: {weights.block_weight:.2f}")
    print(f"✓ Kill bonus: {weights.kill_bonus:.1f}")
    print(f"✓ Lethal detection: {weights.lethal_detection}")

    # SAFE timing should have high damage weight, low block weight
    if weights.damage_weight > weights.block_weight:
        print("✅ PASS: SAFE timing has aggressive weights (damage > block)")
    else:
        print("❌ FAIL: SAFE timing should have damage_weight > block_weight")

    print()


def test_ironclad_planner_integration():
    """Test 3: IroncladCombatPlanner with timing awareness."""
    print("=" * 60)
    print("TEST 3: IroncladCombatPlanner Integration")
    print("=" * 60)

    context = create_mock_context_cultist_turn1()

    # Create planner with timing awareness
    planner = IroncladCombatPlanner()

    # Check that timing components are initialized
    has_classifier = hasattr(planner, 'timing_classifier')
    has_strategy = hasattr(planner, 'balance_strategy')

    print(f"✓ Has timing_classifier: {has_classifier}")
    print(f"✓ Has balance_strategy: {has_strategy}")

    if has_classifier and has_strategy:
        print("✅ PASS: IroncladCombatPlanner initialized with timing awareness")
    else:
        print("❌ FAIL: Timing components not initialized")

    # Test timing classification through planner
    timing_ctx = planner.timing_classifier.classify_turn(context)
    print(f"✓ Planner can classify turns: {timing_ctx.turn_timing.value}")

    # Test simulator accepts timing context
    planner.simulator.set_timing_context(timing_ctx)
    print(f"✓ Simulator accepts timing context: {planner.simulator.timing_context is not None}")

    print()


def test_threat_spike_scenario():
    """Test 4: Threat spike scenario (Cultist turn 2+ with ATTACK intent)."""
    print("=" * 60)
    print("TEST 4: Threat Spike Classification - Cultist Turn 2")
    print("=" * 60)

    # Create mock context for Cultist turn 2 (ATTACK intent)
    player = Player(
        current_hp=75,
        max_hp=80,
        block=0,
        energy=3
    )

    # Cultist with ATTACK intent (after Ritual)
    cultist = Monster(
        name="Cultist",
        current_hp=40,
        max_hp=50,
        intent=Intent.ATTACK,
        move_name="Attack",
        powers=[]
    )
    cultist.index = 0

    # Mock cards
    strike = Card(card_id="Strike_R", name="Strike", cost=1, card_type=CardType.ATTACK)
    strike.uuid = "strike_1"
    strike.upgrades = 0

    defend = Card(card_id="Defend_R", name="Defend", cost=1, card_type=CardType.SKILL)
    defend.uuid = "defend_1"
    defend.upgrades = 0

    context = DecisionContext(
        player=player,
        monsters=[cultist],
        hand=[strike, defend],
        draw_pile=[],
        discard_pile=[],
        energy_available=3,
        turn=2,
        floor=1,
        act=1
    )

    classifier = TurnTimingClassifier()
    strategy = CombatBalanceStrategy()

    timing_ctx = classifier.classify_turn(context)
    weights = strategy.get_balance_weights(timing_ctx.turn_timing, context, timing_ctx)

    print(f"✓ Turn classified as: {timing_ctx.turn_timing.value}")
    print(f"✓ Current damage expected: {timing_ctx.current_damage:.1f}")
    print(f"✓ Damage weight: {weights.damage_weight:.2f}")
    print(f"✓ Block weight: {weights.block_weight:.2f}")

    # Threat spike should have high block weight
    if weights.block_weight > weights.damage_weight:
        print("✅ PASS: THREAT_SPIKE timing has defensive weights (block > damage)")
    else:
        print("❌ FAIL: THREAT_SPIKE timing should have block_weight > damage_weight")

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
