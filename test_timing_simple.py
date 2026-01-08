"""
Simple test to verify timing module imports and basic functionality.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("TIMING MODULE VERIFICATION TEST")
print("=" * 60)
print()

# Test 1: Import timing modules
print("[TEST 1] Importing timing modules...")
try:
    from spirecomm.ai.heuristics.timing import (
        TurnTiming,
        BalanceWeights,
        TurnTimingClassifier,
        CombatBalanceStrategy,
        TimingContext
    )
    print("✅ PASS: All timing modules imported successfully")
except Exception as e:
    print(f"❌ FAIL: Import error: {e}")
    sys.exit(1)

print()

# Test 2: Import IroncladCombatPlanner
print("[TEST 2] Importing IroncladCombatPlanner...")
try:
    from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
    print("✅ PASS: IroncladCombatPlanner imported successfully")
except Exception as e:
    print(f"❌ FAIL: Import error: {e}")
    sys.exit(1)

print()

# Test 3: Create planner and verify timing components
print("[TEST 3] Creating IroncladCombatPlanner with timing awareness...")
try:
    planner = IroncladCombatPlanner()
    assert hasattr(planner, 'timing_classifier'), "Missing timing_classifier"
    assert hasattr(planner, 'balance_strategy'), "Missing balance_strategy"
    assert hasattr(planner.simulator, 'set_timing_context'), "Missing set_timing_context method"
    print("✅ PASS: IroncladCombatPlanner has all timing components")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 4: Test TurnTiming enum
print("[TEST 4] Testing TurnTiming enum...")
try:
    assert TurnTiming.SAFE.value == "SAFE"
    assert TurnTiming.THREAT_SPIKE.value == "THREAT_SPIKE"
    assert TurnTiming.PREPARATION.value == "PREPARATION"
    assert TurnTiming.BURST_WINDOW.value == "BURST_WINDOW"
    assert TurnTiming.BALANCED.value == "BALANCED"
    assert TurnTiming.UNKNOWN.value == "UNKNOWN"
    print("✅ PASS: All TurnTiming values correct")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 5: Test BalanceWeights
print("[TEST 5] Testing BalanceWeights...")
try:
    weights_safe = BalanceWeights.safe_turn_weights()
    assert weights_safe.damage_weight > weights_safe.block_weight, "SAFE should favor damage"
    print(f"  SAFE weights: damage={weights_safe.damage_weight:.2f}, block={weights_safe.block_weight:.2f}")

    weights_threat = BalanceWeights.threat_spike_weights()
    assert weights_threat.block_weight > weights_threat.damage_weight, "THREAT_SPIKE should favor block"
    print(f"  THREAT_SPIKE weights: damage={weights_threat.damage_weight:.2f}, block={weights_threat.block_weight:.2f}")

    print("✅ PASS: BalanceWeights profiles correct")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 6: Test timing classifier and strategy creation
print("[TEST 6] Creating TurnTimingClassifier and CombatBalanceStrategy...")
try:
    classifier = TurnTimingClassifier()
    strategy = CombatBalanceStrategy()
    print("✅ PASS: Timing components created successfully")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

print()

# Summary
print("=" * 60)
print("ALL TESTS PASSED ✅")
print("=" * 60)
print()
print("Timing awareness system is correctly integrated!")
print()
print("Next steps to verify in actual gameplay:")
print("1. Restart Slay the Spire with Communication Mod")
print("2. Start a new run with Ironclad")
print("3. Enter combat and check ai_debug.log for:")
print("   - [TIMING_INIT] IroncladCombatPlanner initialized")
print("   - [TIMING_CLASSIFY] Turn X: SAFE/THREAT_SPIKE/etc")
print("   - [TIMING_WEIGHTS] Using SAFE weights: damage=X.XX, block=X.XX")
print()
print("Expected behavior:")
print("- Cultist turn 1 (Ritual/BUFF): Should classify as SAFE, use aggressive damage")
print("- Cultist turn 2+ (Attack): Should classify as THREAT_SPIKE, use defensive block")
print("- Jaw Worm Bellow (DEFEND): Should classify as SAFE, attack aggressively")
print()
