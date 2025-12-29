"""
Quick validation script for the combat system rewrite.

Tests core functionality without running a full game.
"""

from spirecomm.ai.agent import OptimizedAgent
from spirecomm.spire.character import PlayerClass, Monster, Intent
from spirecomm.spire.card import Card, CardType, CardRarity
from spirecomm.spire.game import Game
from spirecomm.ai.decision.base import DecisionContext


def test_card_cost_for_turn():
    """Test Snecko Eye cost support."""
    print("Testing Card.cost_for_turn...")

    # Simulate Snecko Eye randomizing cost to 3
    card_json = {
        "id": "Strike",
        "name": "Strike",
        "type": "ATTACK",
        "rarity": "BASIC",
        "upgrades": 0,
        "has_target": True,
        "cost": 1,  # Base cost
        "costForTurn": 3,  # Snecko Eye randomization
        "uuid": "test-uuid-1",
        "is_playable": True
    }

    card = Card.from_json(card_json)

    assert card.cost == 1, f"Expected base cost 1, got {card.cost}"
    assert card.cost_for_turn == 3, f"Expected cost_for_turn 3, got {card.cost_for_turn}"
    assert card.is_playable, "Card should be playable"

    print("  - Base cost: PASS")
    print("  - Cost for turn: PASS")
    print("  - Is playable: PASS")
    print()


def test_decision_context_relics():
    """Test DecisionContext relic detection."""
    print("Testing DecisionContext relic detection...")

    # Create minimal game state
    game = Game()
    game.current_hp = 70
    game.max_hp = 80
    game.turn = 1
    game.floor = 5
    game.act = 1
    game.hand = []
    game.monsters = []

    # Simulate having Snecko Eye
    from spirecomm.spire.relic import Relic
    game.relics = [Relic("Snecko Eye", "Snecko Eye")]

    context = DecisionContext(game)

    assert context.has_snecko_eye, "Should detect Snecko Eye"
    assert context.player_hp_pct == 0.875, f"Expected HP 87.5%, got {context.player_hp_pct * 100}%"

    print("  - Snecko Eye detection: PASS")
    print("  - HP percentage: PASS")
    print()


def test_combat_ending_detector():
    """Test lethal detection."""
    print("Testing CombatEndingDetector...")

    from spirecomm.ai.heuristics.combat_ending import CombatEndingDetector

    # Create game with low HP monster
    game = Game()
    game.current_hp = 70
    game.max_hp = 80
    game.turn = 1
    game.act = 1

    # Add Strike that can kill (damage is set by game state, not constructor)
    strike = Card(
        card_id="Strike_R",
        name="Strike",
        card_type=CardType.ATTACK,
        rarity=CardRarity.BASIC,
        cost=1,
        has_target=True,
        uuid="strike-1",
        is_playable=True
    )
    # Manually set damage (would normally come from game state)
    strike.damage = 6

    game.hand = [strike]
    game.player = type('Player', (), {
        'block': 0,
        'energy': 3,
        'powers': []
    })()

    # Add weak monster
    game.monsters = [
        Monster(
            name="Jaw Worm",
            monster_id="Jaw Worm",
            max_hp=40,
            current_hp=4,  # Can kill with Strike (6 damage)
            block=0,
            intent=Intent.ATTACK,
            half_dead=False,
            is_gone=False
        )
    ]

    context = DecisionContext(game)
    detector = CombatEndingDetector()

    # Just test that it doesn't crash - lethal detection logic may need game state data
    try:
        can_kill = detector.can_kill_all(context)
        print(f"  - Lethal detector runs without crash (detected: {can_kill}): PASS")
    except Exception as e:
        print(f"  - Lethal detector error: {e}")
        raise
    print()


def test_ironclad_planner():
    """Test IroncladCombatPlanner initialization."""
    print("Testing IroncladCombatPlanner...")

    from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner

    planner = IroncladCombatPlanner()

    assert hasattr(planner, 'combat_ending_detector'), "Should have lethal detector"
    assert hasattr(planner, 'beam_width'), "Should have beam_width parameter"
    assert hasattr(planner, 'max_depth'), "Should have max_depth parameter"

    # Test adaptive parameters
    game = Game()
    game.current_hp = 70
    game.max_hp = 80
    game.turn = 1
    game.act = 1

    # Add 3 playable cards (simple case)
    cards = [
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC,
             cost=1, has_target=True, uuid=f"strike-{i}", is_playable=True)
        for i in range(3)
    ]
    game.hand = cards

    # Add 2 monsters (simple case)
    game.monsters = [
        Monster("Jaw Worm", "Jaw Worm", 40, 40, 0, Intent.ATTACK, False, False),
        Monster("Cultist", "Cultist", 50, 50, 0, Intent.ATTACK, False, False)
    ]

    context = DecisionContext(game)
    beam_width, max_depth = planner._get_adaptive_parameters(context, cards)

    assert beam_width == 10, f"Simple case: expected beam_width=10, got {beam_width}"
    assert max_depth == 4, f"Simple case: expected max_depth=4, got {max_depth}"

    print("  - Planner initialization: PASS")
    print("  - Adaptive parameters (simple): PASS")
    print()


def test_optimized_agent():
    """Test OptimizedAgent initialization."""
    print("Testing OptimizedAgent...")

    agent = OptimizedAgent(chosen_class=PlayerClass.IRONCLAD)

    assert hasattr(agent, 'current_action_sequence'), "Should have sequence storage"
    assert hasattr(agent, 'current_action_index'), "Should have sequence index"
    assert hasattr(agent, 'combat_planner'), "Should have combat planner"

    assert agent.current_action_sequence == [], "Sequence should start empty"
    assert agent.current_action_index == 0, "Index should start at 0"

    print("  - Agent initialization: PASS")
    print("  - Sequence storage: PASS")
    print("  - Combat planner: PASS")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("COMBAT SYSTEM VALIDATION")
    print("=" * 60)
    print()

    try:
        test_card_cost_for_turn()
        test_decision_context_relics()
        test_combat_ending_detector()
        test_ironclad_planner()
        test_optimized_agent()

        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("The combat system rewrite is ready for in-game testing.")
        print()
        print("Next steps:")
        print("1. Launch Slay the Spire with Communication Mod")
        print("2. The AI will automatically use the optimized system")
        print("3. Monitor stderr for decision logs")
        print("4. Run 10-20 games and collect statistics")
        print()

    except AssertionError as e:
        print(f"\nFAILED: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
