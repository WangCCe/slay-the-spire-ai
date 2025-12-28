"""
Quick test for game tracking functionality.
"""

from spirecomm.ai.agent import OptimizedAgent
from spirecomm.spire.game import Game
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.card import Card, CardType, CardRarity

def test_tracking():
    """Test that tracking doesn't crash the agent."""
    print("Creating OptimizedAgent...")
    agent = OptimizedAgent(chosen_class=PlayerClass.IRONCLAD)

    print(f"Agent has tracker: {hasattr(agent, 'game_tracker')}")
    print(f"Tracker initialized: {agent.game_tracker is not None}")

    # Create a minimal game state
    print("\nCreating game state...")
    game = Game()
    game.in_combat = False
    game.floor = 0
    game.act = 1
    game.current_hp = 80
    game.max_hp = 80
    game.room_type = "NeowRoom"

    # Test getting action
    print("Calling get_next_action_in_game...")
    try:
        result = agent.get_next_action_in_game(game)
        print(f"[OK] Success! Returned: {type(result).__name__ if result else 'None'}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Simulate entering combat
    print("\nSimulating combat start...")
    game.in_combat = True
    game.room_type = "MonsterRoom"
    game.floor = 1

    try:
        result = agent.get_next_action_in_game(game)
        print(f"[OK] Combat start handled! Returned: {type(result).__name__ if result else 'None'}")
        print(f"  Tracker recorded combat: {len(agent.game_tracker.combats) > 0}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Simulate combat end
    print("\nSimulating combat end...")
    game.in_combat = False
    game.current_hp = 75

    try:
        result = agent.get_next_action_in_game(game)
        print(f"[OK] Combat end handled! Returned: {type(result).__name__ if result else 'None'}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_tracking()
    exit(0 if success else 1)
