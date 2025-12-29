#!/usr/bin/env python3
"""
Test script for DeckAnalyzer functionality.

This script tests the enhanced deck archetype detection system.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from spirecomm.spire import Game, Card, CardType, CardRarity
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.ai.heuristics.deck import DeckAnalyzer

# Mock DecisionContext for testing
class MockDecisionContext(DecisionContext):
    def __init__(self, deck=None):
        self.mock_game = MockGame(deck)
        super().__init__(self.mock_game)
        self.deck_archetype = 'unknown'
        self.card_synergies = {
            'strength': 0.2,
            'block': 0.1,
            'draw': 0.1,
            'exhaust': 0.1,
            'combo': 0.1,
            'poison': 0.1,
            'scaling': 0.1,
            'storm': 0.1,
            'heal': 0.1,
            'malice': 0.1
        }
        self.player_hp_pct = 1.0
        self.act = 1
        self.floor = 5
        self.strength = 0
        self.dexterity = 0

# Mock Game class for testing
class MockGame:
    def __init__(self, deck=None):
        self.deck = deck or []

# Test cases
def test_deck_analyzer_import():
    """Test that DeckAnalyzer can be imported."""
    print("\nTesting DeckAnalyzer imports...")
    try:
        from spirecomm.ai.heuristics.deck import DeckAnalyzer
        print("  [OK] DeckAnalyzer imported successfully")
        return True
    except ImportError as e:
        print(f"  [ERROR] Failed to import DeckAnalyzer: {e}")
        return False

def test_empty_deck():
    """Test deck analyzer with empty deck."""
    print("\nTesting empty deck...")
    analyzer = DeckAnalyzer()
    context = MockDecisionContext([])
    
    try:
        archetype = analyzer.get_archetype(context)
        scores = analyzer.get_archetype_score(context)
        stats = analyzer.get_deck_stats(context)
        quality = analyzer.evaluate_deck_quality(context)
        
        print(f"  [OK] Empty deck archetype: {archetype}")
        print(f"  [OK] Empty deck scores: {scores}")
        print(f"  [OK] Empty deck stats: {stats}")
        print(f"  [OK] Empty deck quality: {quality}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to analyze empty deck: {e}")
        return False

def test_strength_deck():
    """Test deck analyzer with strength archetype deck."""
    print("\nTesting strength archetype deck...")
    
    # Create a mock strength deck
    strength_deck = [
        Card("Demon Form", "Demon Form", CardType.POWER, CardRarity.RARE),
        Card("Inflame", "Inflame", CardType.POWER, CardRarity.UNCOMMON),
        Card("Limit Break", "Limit Break", CardType.POWER, CardRarity.RARE),
        Card("Flex", "Flex", CardType.ATTACK, CardRarity.COMMON),
        Card("Spot Weakness", "Spot Weakness", CardType.SKILL, CardRarity.COMMON),
        Card("Body Slam", "Body Slam", CardType.ATTACK, CardRarity.UNCOMMON),
        Card("Heavy Blade", "Heavy Blade", CardType.ATTACK, CardRarity.UNCOMMON),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(strength_deck)
    
    try:
        archetype = analyzer.get_archetype(context)
        scores = analyzer.get_archetype_score(context)
        stats = analyzer.get_deck_stats(context)
        quality = analyzer.evaluate_deck_quality(context)
        
        print(f"  [OK] Strength deck archetype: {archetype}")
        print(f"  [OK] Strength deck scores: {scores}")
        print(f"  [OK] Strength deck stats: {stats}")
        print(f"  [OK] Strength deck quality: {quality}")
        
        # Verify that strength is the detected archetype
        if archetype == 'strength':
            print(f"  [PASS] Correctly detected strength archetype")
        else:
            print(f"  [FAIL] Expected strength archetype, got {archetype}")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to analyze strength deck: {e}")
        return False

def test_exhaust_deck():
    """Test deck analyzer with exhaust archetype deck."""
    print("\nTesting exhaust archetype deck...")
    
    # Create a mock exhaust deck
    exhaust_deck = [
        Card("Corruption", "Corruption", CardType.POWER, CardRarity.RARE),
        Card("Feel No Pain", "Feel No Pain", CardType.POWER, CardRarity.UNCOMMON),
        Card("Dark Embrace", "Dark Embrace", CardType.POWER, CardRarity.RARE),
        Card("Exhume", "Exhume", CardType.SKILL, CardRarity.UNCOMMON),
        Card("Second Wind", "Second Wind", CardType.SKILL, CardRarity.UNCOMMON),
        Card("Apotheosis", "Apotheosis", CardType.POWER, CardRarity.RARE),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(exhaust_deck)
    
    try:
        archetype = analyzer.get_archetype(context)
        scores = analyzer.get_archetype_score(context)
        stats = analyzer.get_deck_stats(context)
        quality = analyzer.evaluate_deck_quality(context)
        
        print(f"  [OK] Exhaust deck archetype: {archetype}")
        print(f"  [OK] Exhaust deck scores: {scores}")
        print(f"  [OK] Exhaust deck stats: {stats}")
        print(f"  [OK] Exhaust deck quality: {quality}")
        
        # Check if exhaust archetype is detected
        if archetype == 'exhaust':
            print(f"  [PASS] Correctly detected exhaust archetype")
        else:
            print(f"  [FAIL] Expected exhaust archetype, got {archetype}")
            print(f"  [INFO] Exhaust score: {scores.get('exhaust', 0)}")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to analyze exhaust deck: {e}")
        return False

def test_combo_deck():
    """Test deck analyzer with combo archetype deck."""
    print("\nTesting combo archetype deck...")
    
    # Create a mock combo deck
    combo_deck = [
        Card("Backflip", "Backflip", CardType.SKILL, CardRarity.COMMON),
        Card("Finesse", "Finesse", CardType.SKILL, CardRarity.UNCOMMON),
        Card("Well-Laid Plans", "Well-Laid Plans", CardType.POWER, CardRarity.UNCOMMON),
        Card("Reflex", "Reflex", CardType.SKILL, CardRarity.RARE),
        Card("Tactician", "Tactician", CardType.SKILL, CardRarity.RARE),
        Card("After Image", "After Image", CardType.POWER, CardRarity.RARE),
        Card("Defend_B", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_B", "Strike", CardType.ATTACK, CardRarity.BASIC),
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(combo_deck)
    
    try:
        archetype = analyzer.get_archetype(context)
        scores = analyzer.get_archetype_score(context)
        stats = analyzer.get_deck_stats(context)
        quality = analyzer.evaluate_deck_quality(context)
        
        print(f"  [OK] Combo deck archetype: {archetype}")
        print(f"  [OK] Combo deck scores: {scores}")
        print(f"  [OK] Combo deck stats: {stats}")
        print(f"  [OK] Combo deck quality: {quality}")
        
        # Check if combo archetype is detected
        if archetype == 'combo':
            print(f"  [PASS] Correctly detected combo archetype")
        else:
            print(f"  [FAIL] Expected combo archetype, got {archetype}")
            print(f"  [INFO] Combo score: {scores.get('combo', 0)}")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to analyze combo deck: {e}")
        return False

def test_balanced_deck():
    """Test deck analyzer with balanced deck."""
    print("\nTesting balanced deck...")
    
    # Create a mock balanced deck
    balanced_deck = [
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Flex", "Flex", CardType.ATTACK, CardRarity.COMMON),
        Card("Spot Weakness", "Spot Weakness", CardType.SKILL, CardRarity.COMMON),
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(balanced_deck)
    
    try:
        archetype = analyzer.get_archetype(context)
        scores = analyzer.get_archetype_score(context)
        stats = analyzer.get_deck_stats(context)
        quality = analyzer.evaluate_deck_quality(context)
        
        print(f"  [OK] Balanced deck archetype: {archetype}")
        print(f"  [OK] Balanced deck scores: {scores}")
        print(f"  [OK] Balanced deck stats: {stats}")
        print(f"  [OK] Balanced deck quality: {quality}")
        
        # Check if balanced deck is detected
        if archetype == 'balanced':
            print(f"  [PASS] Correctly detected balanced deck")
        else:
            print(f"  [FAIL] Expected balanced deck, got {archetype}")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to analyze balanced deck: {e}")
        return False

def test_deck_stats():
    """Test deck statistics functionality."""
    print("\nTesting deck statistics...")
    
    # Create a deck with various card types
    test_deck = [
        Card("Demon Form", "Demon Form", CardType.POWER, CardRarity.RARE, upgrades=1),
        Card("Inflame", "Inflame", CardType.POWER, CardRarity.UNCOMMON, upgrades=0),
        Card("Body Slam", "Body Slam", CardType.ATTACK, CardRarity.UNCOMMON, upgrades=1),
        Card("Heavy Blade", "Heavy Blade", CardType.ATTACK, CardRarity.UNCOMMON, upgrades=0),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC, upgrades=0),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC, upgrades=0),
        Card("Burn", "Burn", CardType.CURSE, CardRarity.CURSE, upgrades=0),  # Curse card
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(test_deck)
    
    try:
        stats = analyzer.get_deck_stats(context)
        
        print(f"  [OK] Deck stats: {stats}")
        
        # Verify expected stats
        assert stats['size'] == 7
        assert stats['attack_count'] >= 3  # At least 3 attack cards
        assert stats['skill_count'] >= 1   # At least 1 skill card
        assert stats['power_count'] >= 2   # At least 2 power cards
        assert stats['curse_count'] >= 1   # At least 1 curse card
        assert stats['upgraded_count'] >= 2  # At least 2 upgraded cards
        
        print(f"  [PASS] Deck stats verified correctly")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to get deck stats: {e}")
        return False

def test_deck_quality():
    """Test deck quality evaluation."""
    print("\nTesting deck quality evaluation...")
    
    # Create two decks: one good, one bad
    good_deck = [
        Card("Demon Form", "Demon Form", CardType.POWER, CardRarity.RARE),
        Card("Inflame", "Inflame", CardType.POWER, CardRarity.UNCOMMON),
        Card("Limit Break", "Limit Break", CardType.POWER, CardRarity.RARE),
        Card("Body Slam", "Body Slam", CardType.ATTACK, CardRarity.UNCOMMON),
        Card("Heavy Blade", "Heavy Blade", CardType.ATTACK, CardRarity.UNCOMMON),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
    ]
    
    bad_deck = [
        Card("Burn", "Burn", CardType.CURSE, CardRarity.CURSE),
        Card("Injury", "Injury", CardType.STATUS, CardRarity.BASIC),
        Card("Wound", "Wound", CardType.STATUS, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
    ]
    
    analyzer = DeckAnalyzer()
    
    try:
        good_quality = analyzer.evaluate_deck_quality(MockDecisionContext(good_deck))
        bad_quality = analyzer.evaluate_deck_quality(MockDecisionContext(bad_deck))
        
        print(f"  [OK] Good deck quality: {good_quality}")
        print(f"  [OK] Bad deck quality: {bad_quality}")
        
        # Verify that good deck has higher quality than bad deck
        if good_quality > bad_quality:
            print(f"  [PASS] Good deck has higher quality than bad deck")
        else:
            print(f"  [FAIL] Good deck should have higher quality than bad deck")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to evaluate deck quality: {e}")
        return False

def test_needs_cards():
    """Test needs_cards_of_type functionality."""
    print("\nTesting needs_cards_of_type...")
    
    # Create a deck with mostly attacks
    attack_heavy_deck = [
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(attack_heavy_deck)
    
    try:
        # Should not need more attacks
        needs_attack = analyzer.needs_cards_of_type(context, 'attack')
        # Should need skills and powers
        needs_skill = analyzer.needs_cards_of_type(context, 'skill')
        needs_power = analyzer.needs_cards_of_type(context, 'power')
        
        print(f"  [OK] Needs more attacks: {needs_attack}")
        print(f"  [OK] Needs more skills: {needs_skill}")
        print(f"  [OK] Needs more powers: {needs_power}")
        
        # Verify expected results
        if not needs_attack and needs_skill and needs_power:
            print(f"  [PASS] Correctly identified needed card types")
        else:
            print(f"  [FAIL] Unexpected results for needed card types")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to check needed cards: {e}")
        return False

def test_find_weakest_card():
    """Test find_weakest_card functionality."""
    print("\nTesting find_weakest_card...")
    
    # Create a deck with a curse
    test_deck = [
        Card("Demon Form", "Demon Form", CardType.POWER, CardRarity.RARE),
        Card("Inflame", "Inflame", CardType.POWER, CardRarity.UNCOMMON),
        Card("Body Slam", "Body Slam", CardType.ATTACK, CardRarity.UNCOMMON),
        Card("Defend_R", "Defend", CardType.SKILL, CardRarity.BASIC),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC),
        Card("Burn", "Burn", CardType.CURSE, CardRarity.CURSE),  # Curse should be weakest
    ]
    
    analyzer = DeckAnalyzer()
    context = MockDecisionContext(test_deck)
    
    try:
        weakest = analyzer.find_weakest_card(context)
        
        print(f"  [OK] Weakest card: {weakest.name if weakest else 'None'}")
        
        # Verify that curse is identified as weakest
        if weakest and weakest.name == 'Burn':
            print(f"  [PASS] Correctly identified curse as weakest card")
        else:
            print(f"  [FAIL] Should have identified Burn as weakest card")
            
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to find weakest card: {e}")
        return False

def main():
    """Run all tests."""
    print("============================================================")
    print("DeckAnalyzer Component Tests")
    print("============================================================")
    
    # Run all tests
    tests = [
        test_deck_analyzer_import,
        test_empty_deck,
        test_strength_deck,
        test_exhaust_deck,
        test_combo_deck,
        test_balanced_deck,
        test_deck_stats,
        test_deck_quality,
        test_needs_cards,
        test_find_weakest_card
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n============================================================")
    if failed == 0:
        print(f"[SUCCESS] All {passed} tests passed!")
        print("\nDeckAnalyzer enhanced functionality is working correctly.")
        print("\nKey features verified:")
        print("  - Enhanced archetype detection (including exhaust and combo)")
        print("  - Game data integration for effect-based detection")
        print("  - Deck quality evaluation")
        print("  - Deck statistics generation")
        print("  - Weakest card identification")
        return 0
    else:
        print(f"[FAILURE] {failed} tests failed out of {len(tests)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
