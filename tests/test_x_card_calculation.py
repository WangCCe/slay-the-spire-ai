#!/usr/bin/env python3
"""
Test script to verify X-card calculation logic.

Tests Body Slam, Rage, Whirlwind, and Bludgeon calculations
in various scenarios.
"""

import sys
sys.path.insert(0, '/mnt/d/PycharmProjects/slay-the-spire-ai')

from spirecomm.ai.heuristics.simulation import FastCombatSimulator, SimulationState
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.spire.card import Card
from spirecomm.spire.card import CardType, CardRarity
from spirecomm.spire.game import Game
from spirecomm.spire.character import Player

class MockCard:
    """Simple mock Card object for testing."""
    def __init__(self, card_id, cost=1, upgrades=0):
        self.card_id = card_id
        self.cost = cost
        self.upgrades = upgrades
        self.name = card_id
        self.type = CardType.ATTACK if 'Slam' in card_id or 'Bludgeon' in card_id or 'Whirlwind' in card_id else CardType.SKILL

def create_test_context(player_hp=80, player_block=0, energy=3, strength=0):
    """Create a test DecisionContext."""
    game = Game()
    game.current_hp = player_hp
    game.max_hp = 80
    game.turn = 1
    game.floor = 1
    game.act = 1

    player = Player(max_hp=80)
    player.energy = energy
    player.block = player_block
    game.player = player

    context = DecisionContext(game)
    # Mock monsters
    context.monsters_alive = []
    context.strength = strength
    return context

def create_test_state(context, player_block=20):
    """Create a test SimulationState."""
    state = SimulationState(context)
    state.player_block = player_block
    state.player_energy = context.energy_available
    return state

def test_body_slam_damage():
    """Test Body Slam damage calculation."""
    print("=" * 80)
    print("TEST: Body Slam Damage Calculation")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)

    # Test 1: Body Slam with 0 block
    print("\n[Test 1] Body Slam with 0 block")
    context = create_test_context(player_block=0)
    state = create_test_state(context, player_block=0)
    card = MockCard('Body Slam')
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    assert damage == 0, f"Expected 0 damage, got {damage}"
    print("  ✓ PASS")

    # Test 2: Body Slam with 20 block
    print("\n[Test 2] Body Slam with 20 block")
    context = create_test_context(player_block=20)
    state = create_test_state(context, player_block=20)
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    assert damage == 20, f"Expected 20 damage, got {damage}"
    print("  ✓ PASS")

    # Test 3: Body Slam with 50 block (high value)
    print("\n[Test 3] Body Slam with 50 block (high value)")
    state = create_test_state(context, player_block=50)
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    assert damage == 50, f"Expected 50 damage, got {damage}"
    print("  ✓ PASS")

    print("\n✓ All Body Slam tests passed!")

def test_bludgeon_scaling():
    """Test Bludgeon damage scaling with block."""
    print("\n" + "=" * 80)
    print("TEST: Bludgeon Damage Scaling")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)
    card = MockCard('Bludgeon')

    # Test 1: 0 block = 12 damage
    print("\n[Test 1] Bludgeon with 0 block")
    context = create_test_context(player_block=0)
    state = create_test_state(context, player_block=0)
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    assert damage == 12, f"Expected 12 damage, got {damage}"
    print("  ✓ PASS")

    # Test 2: 50 block = 17 damage (12 + 50//10)
    print("\n[Test 2] Bludgeon with 50 block")
    state = create_test_state(context, player_block=50)
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    expected = 12 + 50 // 10
    assert damage == expected, f"Expected {expected} damage, got {damage}"
    print("  ✓ PASS")

    # Test 3: 200 block = 30 damage (capped)
    print("\n[Test 3] Bludgeon with 200 block (capped at 30)")
    state = create_test_state(context, player_block=200)
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    assert damage == 30, f"Expected 30 damage (capped), got {damage}"
    print("  ✓ PASS")

    print("\n✓ All Bludgeon tests passed!")

def test_whirlwind_aoe():
    """Test Whirlwind AOE calculation."""
    print("\n" + "=" * 80)
    print("TEST: Whirlwind AOE Damage")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)
    card = MockCard('Whirlwind')

    # Test 1: 3 energy
    print("\n[Test 1] Whirlwind with 3 energy")
    context = create_test_context(energy=3)
    state = create_test_state(context, player_block=0)
    state.player_energy = 3
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Energy: {state.player_energy}")
    print(f"  Calculated Damage (per target): {damage}")
    assert damage == 3, f"Expected 3 damage, got {damage}"
    print("  ✓ PASS")

    print("\n✓ Whirlwind test passed!")

def test_rage_block():
    """Test Rage block calculation."""
    print("\n" + "=" * 80)
    print("TEST: Rage Block Calculation")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)
    card = MockCard('Rage')

    # Test 1: 2 max energy
    print("\n[Test 1] Rage with 2 max energy")
    context = create_test_context(energy=2)
    state = create_test_state(context, player_block=0)
    state.player_energy = 2
    block = planner._calculate_x_block(card, state, context)
    print(f"  Max Energy (approx): {state.player_energy + card.cost}")
    print(f"  Calculated Block: {block}")
    assert block == 2, f"Expected 2 block, got {block}"
    print("  ✓ PASS")

    # Test 2: 3 max energy
    print("\n[Test 2] Rage with 3 max energy")
    context = create_test_context(energy=3)
    state = create_test_state(context, player_block=0)
    state.player_energy = 3
    block = planner._calculate_x_block(card, state, context)
    print(f"  Max Energy (approx): {state.player_energy + card.cost}")
    print(f"  Calculated Block: {block}")
    assert block == 3, f"Expected 3 block, got {block}"
    print("  ✓ PASS")

    print("\n✓ All Rage tests passed!")

def test_upgraded_cards():
    """Test that upgraded cards (+) work correctly."""
    print("\n" + "=" * 80)
    print("TEST: Upgraded Cards (Body Slam+, Rage+, etc.)")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)

    # Test 1: Body Slam+
    print("\n[Test 1] Body Slam+ with 25 block")
    context = create_test_context(player_block=25)
    state = create_test_state(context, player_block=25)
    card = MockCard('Body Slam+')
    card.card_id = 'Body Slam+'
    card.upgrades = 1
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Card: {card.card_id}")
    print(f"  Player Block: {state.player_block}")
    print(f"  Calculated Damage: {damage}")
    assert damage == 25, f"Expected 25 damage, got {damage}"
    print("  ✓ PASS")

    # Test 2: Rage+
    print("\n[Test 2] Rage+ with 3 max energy")
    context = create_test_context(energy=3)
    state = create_test_state(context, player_block=0)
    state.player_energy = 3
    card = MockCard('Rage+')
    card.card_id = 'Rage+'
    card.upgrades = 1
    block = planner._calculate_x_block(card, state, context)
    print(f"  Card: {card.card_id}")
    print(f"  Max Energy (approx): {state.player_energy + card.cost}")
    print(f"  Calculated Block: {block}")
    assert block == 3, f"Expected 3 block, got {block}"
    print("  ✓ PASS")

    print("\n✓ All upgraded card tests passed!")

def test_edge_cases():
    """Test edge cases like 0 energy, unknown cards."""
    print("\n" + "=" * 80)
    print("TEST: Edge Cases")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)

    # Test 1: Unknown card returns 0
    print("\n[Test 1] Unknown card returns 0")
    context = create_test_context()
    state = create_test_state(context)
    card = MockCard('UnknownCard')
    damage = planner._calculate_x_damage(card, state, context)
    block = planner._calculate_x_block(card, state, context)
    print(f"  Card: UnknownCard")
    print(f"  Calculated Damage: {damage}")
    print(f"  Calculated Block: {block}")
    assert damage == 0, f"Expected 0 damage for unknown card, got {damage}"
    assert block == 0, f"Expected 0 block for unknown card, got {block}"
    print("  ✓ PASS")

    # Test 2: Whirlwind with 1 energy (minimum)
    print("\n[Test 2] Whirlwind with 1 energy (minimum)")
    context = create_test_context(energy=1)
    state = create_test_state(context, player_block=0)
    state.player_energy = 1
    card = MockCard('Whirlwind')
    damage = planner._calculate_x_damage(card, state, context)
    print(f"  Player Energy: {state.player_energy}")
    print(f"  Calculated Damage: {damage}")
    assert damage >= 1, f"Expected at least 1 damage, got {damage}"
    print("  ✓ PASS")

    print("\n✓ All edge case tests passed!")

def test_self_damage_cards():
    """Test that HP-cost cards reduce player HP even when killing enemies."""
    print("\n" + "=" * 80)
    print("TEST: Self-Damage Cards (Hemokinesis)")
    print("=" * 80)

    evaluator = SynergyCardEvaluator()
    planner = FastCombatSimulator(evaluator)
    context = create_test_context(player_hp=5)
    state = create_test_state(context, player_block=0)
    card = MockCard('Hemokinesis')

    new_state = planner.simulate_card_play(state, card, context=context)
    expected_hp = max(0, 5 - 2)

    print("\n[Test 1] Hemokinesis applies self-damage")
    print(f"  Starting HP: 5")
    print(f"  Expected HP after play: {expected_hp}")
    print(f"  Actual HP after play: {new_state.player_hp}")
    assert new_state.player_hp == expected_hp, (
        f"Expected player HP to drop to {expected_hp}, got {new_state.player_hp}"
    )
    print("  ✓ PASS")

    print("\n✓ Self-damage card tests passed!")

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("X-CARD CALCULATION TEST SUITE")
    print("=" * 80)

    try:
        test_body_slam_damage()
        test_bludgeon_scaling()
        test_whirlwind_aoe()
        test_rage_block()
        test_upgraded_cards()
        test_edge_cases()
        test_self_damage_cards()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
