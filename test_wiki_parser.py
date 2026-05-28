#!/usr/bin/env python3
"""
Test script to verify wiki parser integration with GameDataLoader.

Tests:
1. Wiki data loading
2. Damage/block extraction for sample cards
3. X-card detection
4. AOE detection
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spirecomm.data.loader import GameDataLoader

def test_wiki_parser():
    print("=" * 60)
    print("Testing Wiki Parser Integration")
    print("=" * 60)

    # Initialize loader
    loader = GameDataLoader()

    # Test 1: Wiki data loading
    print("\n[Test 1] Loading wiki data...")
    loader._load_wiki_data()
    if loader._wiki_data:
        print(f"✓ Wiki data loaded: {len(loader._wiki_data)} cards")
    else:
        print("✗ Wiki data not loaded (file may not exist)")
        print("  This is expected if wiki-card-data.txt is missing")
    assert loader._wiki_data

    # Test 2: Sample cards with upgrade values
    print("\n[Test 2] Testing damage extraction from wiki data...")

    test_cards = [
        ('Bash', 8, 10, False),
        ('Bash+', 10, 10, True),
        ('Defend', None, None, False),  # Defend has block, not damage
        ('Cleave', 8, 11, False),
        ('Iron Wave', 5, 7, False),
    ]

    for card_name, expected_base, expected_upgraded, is_upgrade in test_cards:
        card_data = {'name': card_name}
        damage = loader._parse_card_damage(card_data)
        expected = expected_upgraded if is_upgrade else expected_base
        status = "✓" if damage == expected else "✗"
        print(f"{status} {card_name}: {damage} (expected {expected})")
        assert damage == expected

    # Test 3: Block extraction
    print("\n[Test 3] Testing block extraction from wiki data...")

    test_block_cards = [
        ('Defend', 5, 8, False),
        ('Defend+', 8, 8, True),
        ('Iron Wave', 5, 7, False),
    ]

    for card_name, expected_base, expected_upgraded, is_upgrade in test_block_cards:
        card_data = {'name': card_name}
        block = loader._parse_card_block(card_data)
        expected = expected_upgraded if is_upgrade else expected_base
        status = "✓" if block == expected else "✗"
        print(f"{status} {card_name}: {block} (expected {expected})")
        assert block == expected

    # Test 4: X-card detection
    print("\n[Test 4] Testing X-card detection...")

    x_cards = [
        ('Body Slam', 0, True),   # X-damage card
        ('Whirlwind', 0, True),   # X-damage AOE card
        ('Bash', 8, False),       # Normal damage card
        ('Cleave', 8, False),     # Normal AOE card
    ]

    for card_name, expected_damage, is_x_card in x_cards:
        card_data = {'name': card_name}
        damage = loader._parse_card_damage(card_data)
        # X-cards return 0, normal cards return their damage
        is_correct = damage == expected_damage
        status = "✓" if is_correct else "✗"
        x_status = "X-card" if is_x_card else "Normal"
        print(f"{status} {card_name}: {damage} ({x_status})")
        assert is_correct

    # Test X-block cards
    print("\n  [Test 4b] Testing X-block card detection...")
    x_block_cards = [
        ('Rage', 0, True),       # X-block card
        ('Defend', 5, False),    # Normal block card
    ]

    for card_name, expected_block, is_x_card in x_block_cards:
        card_data = {'name': card_name}
        block = loader._parse_card_block(card_data)
        is_correct = block == expected_block
        status = "✓" if is_correct else "✗"
        x_status = "X-block" if is_x_card else "Normal"
        print(f"{status} {card_name}: {block} ({x_status})")
        assert is_correct

    # Test 5: AOE detection
    print("\n[Test 5] Testing AOE detection...")

    aoe_cards = [
        ('Cleave', True),
        ('Whirlwind', True),
        ('Immolate', True),
        ('Bash', False),
        ('Strike', False),
    ]

    for card_name, expected_aoe in aoe_cards:
        card_data = {'name': card_name, 'description': 'Deal damage.'}
        is_aoe = loader._is_card_aoe(card_data)
        status = "✓" if is_aoe == expected_aoe else "✗"
        print(f"{status} {card_name}: {'AOE' if is_aoe else 'Single-target'} (expected {'AOE' if expected_aoe else 'Single-target'})")
        assert is_aoe == expected_aoe

    # Test 6: CARD_METADATA reduction
    print("\n[Test 6] Verifying CARD_METADATA reduction...")
    from spirecomm.data.loader import CARD_METADATA

    card_count = len(CARD_METADATA)
    has_reason = all('reason' in CARD_METADATA[card] for card in CARD_METADATA)

    print(f"✓ CARD_METADATA entries: {card_count} (target: ~16)")
    print(f"✓ All entries have 'reason' field: {has_reason}")

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("Wiki parser integration appears to be working correctly!")
    print(f"Loaded {len(loader._wiki_data) if loader._wiki_data else 0} cards from wiki data")
    print(f"CARD_METADATA reduced to {card_count} entries (dynamic cards only)")
    assert has_reason

if __name__ == '__main__':
    try:
        test_wiki_parser()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
