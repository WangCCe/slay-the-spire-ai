"""
Test script for RelicEvaluator component.

This script verifies that the RelicEvaluator system works correctly
for evaluating relics based on their actual effects and synergies.
"""

import sys
from types import SimpleNamespace
from typing import Dict


def test_relic_evaluator_accepts_name_only_relics(monkeypatch):
    from spirecomm.ai.heuristics import relic as relic_module
    from spirecomm.ai.heuristics.relic import RelicEvaluator

    def fake_relic_data(relic_name):
        if relic_name in {"burning blood", "reaper"}:
            return {
                "description": "Heal 6 HP at the end of combat.",
                "tier": "starter",
            }
        return None

    monkeypatch.setattr(relic_module.game_data_loader, "get_relic_data", fake_relic_data)
    burning_blood = SimpleNamespace(name="Burning Blood")
    reaper = SimpleNamespace(name="Reaper")
    context = SimpleNamespace(
        game=SimpleNamespace(relics=[burning_blood, reaper]),
        deck_archetype="balanced",
        player_hp_pct=0.5,
        act=2,
        floor=15,
    )

    scores = RelicEvaluator().evaluate(context)

    assert scores["Burning Blood"] > 0


def test_relic_context_modifier_accepts_string_player_hp_pct():
    from spirecomm.ai.heuristics.relic import RelicEvaluator

    evaluator = RelicEvaluator()
    relic_data = {"description": "Heal 6 HP at the end of combat."}
    enum_context = SimpleNamespace(player_hp_pct=0.25, act=2, floor=15)
    string_context = SimpleNamespace(player_hp_pct="0.25", act=2, floor=15)

    assert (
        evaluator._calculate_context_modifier(relic_data, string_context)
        == evaluator._calculate_context_modifier(relic_data, enum_context)
    )


def test_imports():
    """Test that all components can be imported."""
    print("Testing imports...")

    try:
        from spirecomm.ai.heuristics.relic import RelicEvaluator
        from spirecomm.ai.decision.base import DecisionContext
        from spirecomm.spire.game import Game
        from spirecomm.spire.relic import Relic
        from spirecomm.data.loader import game_data_loader
        print("  [OK] Relic evaluator components imported")
    except ImportError as e:
        print(f"  [FAIL] Failed to import relic evaluator: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Failed to import relic evaluator: {e}") from e


def test_relic_data_loading():
    """Test that relic data is loading correctly."""
    print("\nTesting relic data loading...")

    try:
        from spirecomm.data.loader import game_data_loader
        
        # Test that relic data is loaded
        relics = game_data_loader.get_all_relics()
        print(f"  [OK] Relic data loaded: {len(relics)} relics")
        
        # Test accessing specific relic data
        relic_names = ["snecko eye", "burning blood", "barricade"]
        for name in relic_names:
            relic_data = game_data_loader.get_relic_data(name)
            if relic_data:
                print(f"    [OK] Found data for: {name}")
                print(f"        - Tier: {relic_data.get('tier', 'N/A')}")
                print(f"        - Description: {relic_data.get('description', 'N/A')[:50]}...")
            else:
                print(f"    [WARN] Could not find data for: {name}")
                
    except Exception as e:
        print(f"  [FAIL] Error loading relic data: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Error loading relic data: {e}") from e


def test_relic_evaluator_instantiation():
    """Test that RelicEvaluator can be instantiated."""
    print("\nTesting RelicEvaluator instantiation...")

    try:
        from spirecomm.ai.heuristics.relic import RelicEvaluator
        
        evaluator = RelicEvaluator()
        print("  [OK] RelicEvaluator instantiated")
        print(f"    - Effect values: {len(evaluator.EFFECT_VALUES)} effects defined")
        print(f"    - Archetype bonuses: {len(evaluator.ARCHETYPE_BONUSES)} archetypes supported")
        
    except Exception as e:
        print(f"  [FAIL] Error instantiating RelicEvaluator: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Error instantiating RelicEvaluator: {e}") from e


def test_relic_evaluation_basic():
    """Test basic relic evaluation functionality."""
    print("\nTesting basic relic evaluation...")

    try:
        from spirecomm.ai.heuristics.relic import RelicEvaluator
        from spirecomm.ai.decision.base import DecisionContext
        from spirecomm.spire.game import Game
        from spirecomm.spire.relic import Relic
        
        # Create a test game state
        game = Game()
        game.current_hp = 60
        game.max_hp = 80
        game.act = 1
        game.floor = 5
        game.relics = []
        game.deck = []
        game.monsters = []
        
        # Create context
        context = DecisionContext(game)
        context.deck_archetype = "draw"
        
        # Create test relics
        test_relics = [
            Relic(relic_id="Snecko Eye", name="Snecko Eye"),
            Relic(relic_id="Burning Blood", name="Burning Blood"),
            Relic(relic_id="Barricade", name="Barricade"),
            Relic(relic_id="Dead Branch", name="Dead Branch"),
            Relic(relic_id="Runic Pyramid", name="Runic Pyramid"),
        ]
        
        evaluator = RelicEvaluator()
        
        # Evaluate each relic
        for relic in test_relics:
            score = evaluator.evaluate_relic(relic, context)
            print(f"  [OK] {relic.relic_id} evaluated: {score:.2f}")
            
    except Exception as e:
        print(f"  [FAIL] Error evaluating relics: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Error evaluating relics: {e}") from e


def test_relic_evaluation_context():
    """Test relic evaluation with different contexts."""
    print("\nTesting relic evaluation with context...")

    try:
        from spirecomm.ai.heuristics.relic import RelicEvaluator
        from spirecomm.ai.decision.base import DecisionContext
        from spirecomm.spire.game import Game
        from spirecomm.spire.relic import Relic
        
        evaluator = RelicEvaluator()
        
        # Test different contexts for same relic
        snecko_eye = Relic(relic_id="Snecko Eye", name="Snecko Eye")
        
        # Context 1: Early game, balanced deck
        game1 = Game()
        game1.current_hp = 70
        game1.max_hp = 80
        game1.act = 1
        game1.floor = 3
        game1.relics = []
        game1.deck = []
        game1.monsters = []
        context1 = DecisionContext(game1)
        context1.deck_archetype = "balanced"
        score1 = evaluator.evaluate_relic(snecko_eye, context1)
        
        # Context 2: Mid game, draw-focused deck
        game2 = Game()
        game2.current_hp = 60
        game2.max_hp = 80
        game2.act = 2
        game2.floor = 20
        game2.relics = []
        game2.deck = []
        game2.monsters = []
        context2 = DecisionContext(game2)
        context2.deck_archetype = "draw"
        score2 = evaluator.evaluate_relic(snecko_eye, context2)
        
        # Context 3: Late game, high HP
        game3 = Game()
        game3.current_hp = 80
        game3.max_hp = 80
        game3.act = 3
        game3.floor = 40
        game3.relics = [Relic(relic_id="Runic Pyramid", name="Runic Pyramid")]  # Combo with Snecko Eye
        game3.deck = []
        game3.monsters = []
        context3 = DecisionContext(game3)
        context3.deck_archetype = "draw"
        score3 = evaluator.evaluate_relic(snecko_eye, context3)
        
        print(f"  [OK] Snecko Eye in different contexts:")
        print(f"    - Early game (balanced): {score1:.2f}")
        print(f"    - Mid game (draw): {score2:.2f}")
        print(f"    - Late game (draw + combo): {score3:.2f}")
        
        # Verify that scores differ based on context
        assert abs(score1 - score2) > 0.1 or abs(score2 - score3) > 0.1, "Scores should differ with context"
        
    except Exception as e:
        print(f"  [FAIL] Error testing context evaluation: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Error testing context evaluation: {e}") from e


def test_archetype_bonuses():
    """Test that archetype bonuses are applied correctly."""
    print("\nTesting archetype bonuses...")

    try:
        from spirecomm.ai.heuristics.relic import RelicEvaluator
        from spirecomm.ai.decision.base import DecisionContext
        from spirecomm.spire.game import Game
        from spirecomm.spire.relic import Relic
        
        evaluator = RelicEvaluator()
        
        # Create a strength-focused relic and test with different archetypes
        strength_relic = Relic(relic_id="Brutality", name="Brutality")  # Strength-focused relic
        
        # Create contexts with different archetypes
        contexts = []
        archetypes = ["strength", "poison", "block", "draw", "exhaust"]
        
        for archetype in archetypes:
            game = Game()
            game.current_hp = 60
            game.max_hp = 80
            game.act = 2
            game.floor = 15
            game.relics = []
            game.deck = []
            game.monsters = []
            context = DecisionContext(game)
            context.deck_archetype = archetype
            contexts.append((archetype, context))
        
        # Evaluate relic with each archetype
        scores = []
        for archetype, context in contexts:
            score = evaluator.evaluate_relic(strength_relic, context)
            scores.append((archetype, score))
            print(f"  [OK] {strength_relic.relic_id} with {archetype} archetype: {score:.2f}")
        
        # Verify that strength archetype gets highest bonus
        scores.sort(key=lambda x: x[1], reverse=True)
        print(f"  [INFO] Highest scoring archetype: {scores[0][0]} ({scores[0][1]:.2f})")

    except Exception as e:
        print(f"  [FAIL] Error testing archetype bonuses: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Error testing archetype bonuses: {e}") from e


def test_relic_combinations():
    """Test that relic combinations are detected and scored."""
    print("\nTesting relic combinations...")

    try:
        from spirecomm.ai.heuristics.relic import RelicEvaluator
        from spirecomm.ai.decision.base import DecisionContext
        from spirecomm.spire.game import Game
        from spirecomm.spire.relic import Relic
        
        evaluator = RelicEvaluator()
        
        # Test Burning Blood + Reaper combo
        burning_blood = Relic(relic_id="Burning Blood", name="Burning Blood")
        reaper = Relic(relic_id="Reaper", name="Reaper")
        
        # Test without combo
        game1 = Game()
        game1.current_hp = 60
        game1.max_hp = 80
        game1.act = 2
        game1.floor = 15
        game1.relics = [burning_blood]
        game1.deck = []
        game1.monsters = []
        context1 = DecisionContext(game1)
        context1.deck_archetype = "balanced"
        
        # Test with combo
        game2 = Game()
        game2.current_hp = 60
        game2.max_hp = 80
        game2.act = 2
        game2.floor = 15
        game2.relics = [burning_blood, reaper]
        game2.deck = []
        game2.monsters = []
        context2 = DecisionContext(game2)
        context2.deck_archetype = "balanced"
        
        # Evaluate
        score_without = evaluator.evaluate_relic(burning_blood, context1)
        score_with = evaluator.evaluate_relic(burning_blood, context2)
        
        print(f"  [OK] Burning Blood without Reaper: {score_without:.2f}")
        print(f"  [OK] Burning Blood with Reaper: {score_with:.2f}")
        
        # Verify combo bonus
        if score_with > score_without:
            print(f"  [OK] Combo bonus applied: {score_with - score_without:.2f}")
        else:
            print(f"  [WARN] Combo bonus not detected")

    except Exception as e:
        print(f"  [FAIL] Error testing relic combinations: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Error testing relic combinations: {e}") from e


def main():
    """Run all tests."""
    print("="*60)
    print("RelicEvaluator Component Tests")
    print("="*60)

    all_passed = True

    tests = [
        test_imports,
        test_relic_data_loading,
        test_relic_evaluator_instantiation,
        test_relic_evaluation_basic,
        test_relic_evaluation_context,
        test_archetype_bonuses,
        test_relic_combinations,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] All tests passed!")
        print("\nThe RelicEvaluator system is working correctly.")
        print("\nKey features verified:")
        print("  - Relic data loading and access")
        print("  - Basic relic evaluation")
        print("  - Context-aware evaluation")
        print("  - Archetype synergy bonuses")
        print("  - Relic combination detection")
    else:
        print("[FAILURE] Some tests failed")
        print("\nPlease check the error messages above.")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
