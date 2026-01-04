#!/usr/bin/env python3
"""
Validation script for lethal detection improvements.

This script verifies that the code changes are syntactically correct
and the new constants/logic are in place.
"""

import ast
import sys

def check_file_syntax(filepath):
    """Check if a Python file has valid syntax."""
    with open(filepath, 'r') as f:
        source = f.read()
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def check_constant_exists(filepath, constant_name, expected_value=None):
    """Check if a constant is defined in a file."""
    with open(filepath, 'r') as f:
        source = f.read()

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == constant_name:
                    if expected_value is not None:
                        if isinstance(node.value, ast.Constant):
                            actual_value = node.value.value
                            if actual_value == expected_value:
                                return True, f"Found {constant_name} = {actual_value}"
                            else:
                                return False, f"Found {constant_name} = {actual_value}, expected {expected_value}"
                    return True, f"Found {constant_name}"

    return False, f"Constant {constant_name} not found"

def check_method_exists(filepath, class_name, method_name):
    """Check if a method exists in a class."""
    with open(filepath, 'r') as f:
        source = f.read()

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return True, f"Found method {class_name}.{method_name}()"

    return False, f"Method {class_name}.{method_name}() not found"

def main():
    print("="*80)
    print("LETHAL DETECTION IMPROVEMENTS - VALIDATION")
    print("="*80)

    all_passed = True

    # Check combat_ending.py
    print("\n1. Checking spirecomm/ai/heuristics/combat_ending.py")
    print("-" * 80)

    filepath = "spirecomm/ai/heuristics/combat_ending.py"
    valid, error = check_file_syntax(filepath)
    if valid:
        print("✓ Syntax is valid")
    else:
        print(f"✗ Syntax error: {error}")
        all_passed = False

    # Check for new methods
    checks = [
        ("CombatEndingDetector", "_calculate_affordable_damage"),
        ("CombatEndingDetector", "_can_target_all_monsters"),
    ]

    for class_name, method_name in checks:
        found, msg = check_method_exists(filepath, class_name, method_name)
        if found:
            print(f"✓ {msg}")
        else:
            print(f"✗ {msg}")
            all_passed = False

    # Check simulation.py
    print("\n2. Checking spirecomm/ai/heuristics/simulation.py")
    print("-" * 80)

    filepath = "spirecomm/ai/heuristics/simulation.py"
    valid, error = check_file_syntax(filepath)
    if valid:
        print("✓ Syntax is valid")
    else:
        print(f"✗ Syntax error: {error}")
        all_passed = False

    # Check for ALL_LETHAL_BONUS constant
    found, msg = check_constant_exists(filepath, "ALL_LETHAL_BONUS", expected_value=500)
    if found:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
        all_passed = False

    # Verify ALL_LETHAL_BONUS > KILL_BONUS
    found_kill, msg_kill = check_constant_exists(filepath, "KILL_BONUS")
    if found and found_kill:
        print(f"✓ KILL_BONUS defined")
        # Extract values
        with open(filepath, 'r') as f:
            source = f.read()
            tree = ast.parse(source)
            kill_bonus = None
            all_lethal_bonus = None
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if target.id == "KILL_BONUS" and isinstance(node.value, ast.Constant):
                                kill_bonus = node.value.value
                            elif target.id == "ALL_LETHAL_BONUS" and isinstance(node.value, ast.Constant):
                                all_lethal_bonus = node.value.value

            if kill_bonus is not None and all_lethal_bonus is not None:
                if all_lethal_bonus > kill_bonus:
                    print(f"✓ ALL_LETHAL_BONUS ({all_lethal_bonus}) > KILL_BONUS ({kill_bonus})")
                else:
                    print(f"✗ ALL_LETHAL_BONUS ({all_lethal_bonus}) should be > KILL_BONUS ({kill_bonus})")
                    all_passed = False

    # Summary
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("="*80)
        print("\nChanges implemented:")
        print("\n1. combat_ending.py:")
        print("   - Added logging to can_kill_all() and find_lethal_sequence()")
        print("   - Reduced margin from 20% (1.2) to 10% (1.1)")
        print("   - Added _calculate_affordable_damage() method (energy constraints)")
        print("   - Added _can_target_all_monsters() method (targeting validation)")
        print("   - Added HP safety threshold (>30 HP or >30%)")
        print("\n2. simulation.py:")
        print("   - Added ALL_LETHAL_BONUS = 500 (exponential bonus for killing all)")
        print("   - Added block penalty (70% reduction) when lethal available")
        print("\nNext steps:")
        print("1. Run games with Slay the Spire to test in real combat")
        print("2. Monitor ai_debug.log for [LETHAL_DETECTION] messages")
        print("3. Check for [ALL_LETHAL_BONUS] in beam search logs")
        print("4. Verify AI prioritizes lethal over defense")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("="*80)
        return 1

if __name__ == '__main__':
    sys.exit(main())
