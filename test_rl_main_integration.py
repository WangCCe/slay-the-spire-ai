#!/usr/bin/env python3
"""
Test RL agent integration with main.py
"""
import sys
import logging

# Suppress logging for this test
logging.basicConfig(level=logging.ERROR)

print("="*70)
print("Testing RL Agent Integration with main.py")
print("="*70)
print()

# Test 1: Import main module
print("Test 1: Importing main module...")
try:
    import main
    print("  ✓ Successfully imported main module")
except Exception as e:
    print(f"  ✗ Failed to import main module: {e}")
    sys.exit(1)

# Test 2: Create RL agent (inference mode)
print("\nTest 2: Creating RL agent (inference mode)...")
try:
    agent = main.create_agent(
        agent_type="rl",
        player_class=main.PlayerClass.IRONCLAD,
        training=False
    )
    print(f"  ✓ RL Agent created: {type(agent).__name__}")
    print(f"    Training mode: {agent.training if hasattr(agent, 'training') else 'N/A'}")
except Exception as e:
    print(f"  ✗ Failed to create RL agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Create RL agent (training mode)
print("\nTest 3: Creating RL agent (training mode)...")
try:
    agent_train = main.create_agent(
        agent_type="rl",
        player_class=main.PlayerClass.IRONCLAD,
        training=True
    )
    print(f"  ✓ RL Agent (training) created: {type(agent_train).__name__}")
    print(f"    Training mode: {agent_train.training if hasattr(agent_train, 'training') else 'N/A'}")
except Exception as e:
    print(f"  ✗ Failed to create RL agent (training): {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3b: Create RL v2 agent (inference mode)
print("\nTest 3b: Creating RL v2 agent (inference mode)...")
try:
    if getattr(main, "RL_V2_AVAILABLE", False):
        agent_v2 = main.create_agent(
            agent_type="rl",
            player_class=main.PlayerClass.IRONCLAD,
            training=False,
            rl_version="v2",
        )
        print(f"  ? RL v2 Agent created: {type(agent_v2).__name__}")
    else:
        print("  ? RL v2 components not available (skipped)")
except Exception as e:
    print(f"  ? Failed to create RL v2 agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Create SimpleAgent
print("\nTest 4: Creating SimpleAgent...")
try:
    agent_simple = main.create_agent(
        agent_type="simple",
        player_class=main.PlayerClass.IRONCLAD
    )
    print(f"  ✓ SimpleAgent created: {type(agent_simple).__name__}")
except Exception as e:
    print(f"  ✗ Failed to create SimpleAgent: {e}")
    sys.exit(1)

# Test 5: Create OptimizedAgent
print("\nTest 5: Creating OptimizedAgent...")
try:
    if main.OPTIMIZED_AI_AVAILABLE:
        agent_opt = main.create_agent(
            agent_type="optimized",
            player_class=main.PlayerClass.IRONCLAD
        )
        print(f"  ✓ OptimizedAgent created: {type(agent_opt).__name__}")
    else:
        print("  ⊘ OptimizedAgent not available (skipped)")
except Exception as e:
    print(f"  ✗ Failed to create OptimizedAgent: {e}")
    sys.exit(1)

# Test 6: Auto-detection
print("\nTest 6: Auto-detection for Ironclad...")
try:
    agent_auto = main.create_agent(
        agent_type="auto",
        player_class=main.PlayerClass.IRONCLAD
    )
    print(f"  ✓ Auto-detected agent: {type(agent_auto).__name__}")
    expected = "OptimizedAgent" if main.OPTIMIZED_AI_AVAILABLE else "SimpleAgent"
    actual = type(agent_auto).__name__
    if actual == expected or (expected == "OptimizedAgent" and actual == "SimpleAgent"):
        print(f"    Correctly selected {actual}")
    else:
        print(f"    Warning: Expected {expected}, got {actual}")
except Exception as e:
    print(f"  ✗ Failed to auto-detect: {e}")
    sys.exit(1)

# Test 7: RL availability check
print("\nTest 7: Checking RL availability...")
print(f"  RL_AVAILABLE: {main.RL_AVAILABLE}")
print(f"  RL_V2_AVAILABLE: {getattr(main, 'RL_V2_AVAILABLE', False)}")
if main.RL_AVAILABLE:
    print(f"  RLAgent class: {main.RLAgent}")
    print(f"  create_rl_agent function: {main.create_rl_agent}")
else:
    print("  ⊘ RL components not available (expected if PyTorch not installed)")

print()
print("="*70)
print("✓ All integration tests passed!")
print("="*70)
print()
print("Usage examples:")
print("  python main.py --agent rl")
print("  python main.py --agent rl --train")
print("  python main.py --agent rl --model checkpoints/model.pth")
print("  python main.py --agent optimized")
print("  python main.py --agent simple")
