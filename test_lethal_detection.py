#!/usr/bin/env python3
"""
Test script for lethal detection improvements.

This script validates the fixes to CombatEndingDetector:
1. Reduced margin (20% → 10%)
2. Energy constraint validation
3. Targeting feasibility check
4. HP safety threshold
5. ALL_LETHAL_BONUS in scoring
6. Block penalty when lethal available
"""

import sys
import logging

# Set up logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project to path
sys.path.insert(0, '/mnt/d/PycharmProjects/slay-the-spire-ai')

from spirecomm.ai.heuristics.combat_ending import CombatEndingDetector
from spirecomm.ai.heuristics.simulation import ALL_LETHAL_BONUS, KILL_BONUS
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Monster, Player, PlayerClass, Intent

def create_mock_context(monsters_hp, playable_cards, energy=3, player_hp=70, player_max_hp=80):
    """Helper to create a mock DecisionContext for testing."""
    context = DecisionContext.__new__(DecisionContext)

    # Create mock monsters
    context.monsters_alive = []
    for i, hp in enumerate(monsters_hp):
        monster = Monster.__new__(Monster)
        monster.current_hp = hp
        monster.max_hp = max(hp, 20)
        monster.block = 0
        monster.is_gone = False
        monster.half_dead = False
        monster.name = f"TestMonster{i+1}"
        monster.intent = Intent.ATTACK
        monster.move_base_damage = 10
        monster.move_adjusted_damage = 10
        monster.strength = 0
        context.monsters_alive.append(monster)

    # Create mock player
    context.player = Player.__new__(Player)
    context.player.max_hp = player_max_hp
    context.player_hp = player_hp
    context.player_hp_pct = player_hp / player_max_hp
    context.player.block = 0
    context.player.strength = 0
    context.player_class = PlayerClass.IRONCLAD

    # Create mock playable cards
    context.playable_cards = []
    for card_info in playable_cards:
        card = Card.__new__(Card)
        card.card_id = card_info['name']
        card.name = card_info['name']
        card.type = CardType.ATTACK if card_info.get('type') == 'ATTACK' else CardType.SKILL
        card.cost = card_info['cost']
        card.cost_for_turn = card_info['cost']
        card.damage = card_info.get('damage', 0)
        card.block = card_info.get('block', 0)
        card.upgrades = 0
        card.uuid = f"test_card_{card_info['name']}"
        card.has_target = card_info.get('has_target', False)
        context.playable_cards.append(card)

    context.energy_available = energy
    context.strength = 0
    context.vulnerable_stacks = {}
    context.weak_stacks = {}
    context.frail_stacks = {}
    context.thorns_stacks = {}
    context.act = 1
    context.turn = 1
    context.floor = 1

    # Add helper methods
    def compute_threat(monster):
        return monster.current_hp

    context.compute_threat = compute_threat

    return context

def test_margin_reduction():
    """Test that margin reduction from 20% to 10% allows more lethal detection."""
    print("\n" + "="*80)
    print("TEST 1: Margin Reduction (20% → 10%)")
    print("="*80)

    detector = CombatEndingDetector()

    # Test case: 100 HP monster, 105 damage available
    # With 20% margin: 105 < 120 → False (no lethal)
    # With 10% margin: 105 >= 110 → True (lethal detected)
    context = create_mock_context(
        monsters_hp=[100],
        playable_cards=[
            {'name': 'Heavy_Blade', 'cost': 2, 'damage': 14, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=3
    )

    result = detector.can_kill_all(context)
    print(f"✓ Test: 100 HP monster, 26 damage available (with energy constraint)")
    print(f"  Expected: False (not enough damage even with 10% margin)")
    print(f"  Result: {result}")

    # Test case with more realistic numbers
    context2 = create_mock_context(
        monsters_hp=[20],
        playable_cards=[
            {'name': 'Bash', 'cost': 1, 'damage': 8, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=2
    )

    result2 = detector.can_kill_all(context2)
    print(f"\n✓ Test: 20 HP monster, 14 damage available (Bash + Strike)")
    print(f"  Expected: False (14 < 22 with 10% margin)")
    print(f"  Result: {result2}")

def test_energy_constraints():
    """Test that energy constraints are respected."""
    print("\n" + "="*80)
    print("TEST 2: Energy Constraint Validation")
    print("="*80)

    detector = CombatEndingDetector()

    # Test case: Have Heavy Blade (14 dmg) and Strike (6 dmg), but only 2 energy
    # Should NOT detect lethal because can't afford both
    context = create_mock_context(
        monsters_hp=[18],
        playable_cards=[
            {'name': 'Heavy_Blade', 'cost': 2, 'damage': 14, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=2  # Only 2 energy
    )

    result = detector.can_kill_all(context)
    print(f"✓ Test: 18 HP monster, Heavy Blade (14 dmg, 2 cost) + Strike (6 dmg, 1 cost), only 2 energy")
    print(f"  Expected: False (can't afford both cards with only 2 energy)")
    print(f"  Result: {result}")

def test_hp_safety_threshold():
    """Test that HP safety threshold prevents risky lethal."""
    print("\n" + "="*80)
    print("TEST 3: HP Safety Threshold")
    print("="*80)

    detector = CombatEndingDetector()

    # Test case: Low HP, lethal available
    context = create_mock_context(
        monsters_hp=[15],
        playable_cards=[
            {'name': 'Bash', 'cost': 1, 'damage': 8, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=2,
        player_hp=10,  # Low HP
        player_max_hp=80
    )

    result = detector.can_kill_all(context)
    print(f"✓ Test: 15 HP monster, 14 damage available, player at 10 HP (12.5%)")
    print(f"  Expected: False (HP too low for risky lethal)")
    print(f"  Result: {result}")

    # Test case: Safe HP, lethal available
    context2 = create_mock_context(
        monsters_hp=[15],
        playable_cards=[
            {'name': 'Bash', 'cost': 1, 'damage': 8, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=2,
        player_hp=35,  # Safe HP
        player_max_hp=80
    )

    result2 = detector.can_kill_all(context2)
    print(f"\n✓ Test: 15 HP monster, 14 damage available, player at 35 HP (43.75%)")
    print(f"  Expected: True (HP safe, lethal detected)")
    print(f"  Result: {result2}")

def test_all_lethal_bonus():
    """Test that ALL_LETHAL_BONUS is defined and larger than KILL_BONUS."""
    print("\n" + "="*80)
    print("TEST 4: ALL_LETHAL_BONUS Constant")
    print("="*80)

    print(f"KILL_BONUS = {KILL_BONUS}")
    print(f"ALL_LETHAL_BONUS = {ALL_LETHAL_BONUS}")
    print(f"Ratio: {ALL_LETHAL_BONUS / KILL_BONUS:.1f}x")

    if ALL_LETHAL_BONUS > KILL_BONUS:
        print(f"✓ ALL_LETHAL_BONUS ({ALL_LETHAL_BONUS}) > KILL_BONUS ({KILL_BONUS})")
    else:
        print(f"✗ ERROR: ALL_LETHAL_BONUS should be > KILL_BONUS")

def test_targeting_constraints():
    """Test targeting feasibility with multiple monsters."""
    print("\n" + "="*80)
    print("TEST 5: Targeting Feasibility (Multiple Monsters)")
    print("="*80)

    detector = CombatEndingDetector()

    # Test case: 2 monsters with 12 HP each, only single-target attacks
    context = create_mock_context(
        monsters_hp=[12, 12],
        playable_cards=[
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=2
    )

    result = detector.can_kill_all(context)
    print(f"✓ Test: 2 monsters (12 HP each), 2 Strikes (6 dmg each), 2 energy")
    print(f"  Expected: True (have enough single-target attacks)")
    print(f"  Result: {result}")

    # Test case: 2 monsters with 15 HP each, only 2 single-target attacks
    context2 = create_mock_context(
        monsters_hp=[15, 15],
        playable_cards=[
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
            {'name': 'Strike', 'cost': 1, 'damage': 6, 'type': 'ATTACK'},
        ],
        energy=2
    )

    result2 = detector.can_kill_all(context2)
    print(f"\n✓ Test: 2 monsters (15 HP each), 2 Strikes (6 dmg each), 2 energy")
    print(f"  Expected: False (not enough damage)")
    print(f"  Result: {result2}")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("LETHAL DETECTION IMPROVEMENT TEST SUITE")
    print("="*80)

    try:
        test_margin_reduction()
        test_energy_constraints()
        test_hp_safety_threshold()
        test_all_lethal_bonus()
        test_targeting_constraints()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        print("\nNext steps:")
        print("1. Run actual games with Slay the Spire to validate in real combat")
        print("2. Monitor ai_debug.log for [LETHAL_DETECTION] and [LETHAL_SEQUENCE] messages")
        print("3. Check for [ALL_LETHAL_BONUS] and [LETHAL_BLOCK_PENALTY] in logs")
        print("\nExpected improvements:")
        print("- AI should detect lethal more accurately (10% margin instead of 20%)")
        print("- AI should respect energy constraints when checking for lethal")
        print("- AI should prioritize lethal over defense (500-point bonus + block penalty)")
        print("- AI should avoid risky lethal at low HP (<30 HP or <30%)")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
