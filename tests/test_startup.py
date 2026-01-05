"""
Quick test to verify the AI can start and respond to basic game states.
"""

import sys
import json
from spirecomm.communication.coordinator import Coordinator
from spirecomm.ai.agent import OptimizedAgent, SimpleAgent, OPTIMIZED_AI_AVAILABLE


def test_agent_startup():
    """Test that agents can be created successfully."""
    print("Testing agent startup...")

    # Test SimpleAgent
    print("\n1. Testing SimpleAgent...")
    try:
        simple_agent = SimpleAgent()
        print(f"   SimpleAgent created: {type(simple_agent).__name__}")
    except Exception as e:
        print(f"   ERROR creating SimpleAgent: {e}")
        return False

    # Test OptimizedAgent
    print("\n2. Testing OptimizedAgent...")
    if OPTIMIZED_AI_AVAILABLE:
        try:
            optimized_agent = OptimizedAgent()
            print(f"   OptimizedAgent created: {type(optimized_agent).__name__}")
            print(f"   Has combat planner: {hasattr(optimized_agent, 'combat_planner')}")
            print(f"   Has sequence storage: {hasattr(optimized_agent, 'current_action_sequence')}")
            if optimized_agent.combat_planner:
                print(f"   Combat planner type: {type(optimized_agent.combat_planner).__name__}")
        except Exception as e:
            print(f"   ERROR creating OptimizedAgent: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("   OptimizedAgent not available (missing dependencies)")

    print("\n3. All agents started successfully!")
    return True


def test_json_parsing():
    """Test that we can parse game state JSON."""
    print("\n\nTesting JSON parsing...")

    # Minimal game state
    game_state_json = {
        "screen_type": "HAND_SELECT",
        "hand": [],
        "monsters": [],
        "current_hp": 70,
        "max_hp": 80,
        "energy": 3,
        "turn": 1,
        "floor": 1,
        "act": 1
    }

    print(f"\n1. Created test game state: {json.dumps(game_state_json, indent=2)}")

    # Try to parse it
    try:
        from spirecomm.spire.game import Game
        game = Game.from_json(game_state_json)
        print(f"\n2. Parsed game successfully")
        print(f"   Current HP: {game.current_hp}/{game.max_hp}")
        print(f"   Energy: {game.player.energy if hasattr(game, 'player') else 'N/A'}")
        return True
    except Exception as e:
        print(f"\n2. ERROR parsing game: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all startup tests."""
    print("=" * 60)
    print("AI STARTUP TEST")
    print("=" * 60)

    success = True

    # Test agent creation
    if not test_agent_startup():
        success = False

    # Test JSON parsing
    if not test_json_parsing():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("ALL TESTS PASSED - AI is ready!")
    else:
        print("SOME TESTS FAILED - Check errors above")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
