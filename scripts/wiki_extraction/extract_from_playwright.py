#!/usr/bin/env python3
"""
Extract monster data using Playwright MCP browser snapshots.

This script processes structured JSON data from Playwright browser evaluation
and formats it into the enhanced monster database format.
"""

import json
import re
import sys
from typing import Dict, List, Any, Optional


def parse_hp_from_text(text: str) -> Dict[str, Any]:
    """
    Parse HP ranges from Wiki text.

    Expected formats:
    - HP 48-54
    - 50-56 7+ (ascension modifier)

    Returns dict with 'normal' and optional 'ascension_10+', 'ascension_15+'
    """
    hp_ranges = {}

    # Extract normal HP (first occurrence of "XX-XX")
    normal_match = re.search(r'(\d+)-(\d+)', text)
    if normal_match:
        min_hp = int(normal_match.group(1))
        max_hp = int(normal_match.group(2))
        hp_ranges['normal'] = {'min': min_hp, 'max': max_hp}

    # Extract ascension modifiers (format: "XX-YY N+")
    ascension_matches = re.findall(r'(\d+)-(\d+)\s*(\d+)\+', text)
    for min_hp, max_hp, asc_level in ascension_matches:
        asc_key = f'ascension_{asc_level}+'
        # Use the highest ascension if multiple match
        if asc_key not in hp_ranges:
            hp_ranges[asc_key] = {'min': int(min_hp), 'max': int(max_hp)}

    return hp_ranges


def parse_moves_from_playwright(moves_data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Parse moves from Playwright-extracted table data.

    Args:
        moves_data: List of dicts with 'name', 'intent', 'effect' keys

    Returns:
        List of move objects with move_id, name, intent, damage, effect
    """
    moves = []
    for i, move_data in enumerate(moves_data):
        name = move_data.get('name', '').strip()
        effect = move_data.get('effect', '').strip()

        # Extract damage from effect text
        damage_match = re.search(r'Deal (\d+) damage', effect)
        damage = int(damage_match.group(1)) if damage_match else None

        # Extract Strength gain from effect
        strength_match = re.search(r'Gains (\d+).*?(?:Ritual|Strength)', effect)
        strength = int(strength_match.group(1)) if strength_match else None

        move = {
            'move_id': i,
            'name': name,
            'intent': move_data.get('intent', 'UNKNOWN').strip(),
            'damage': damage,
            'effect': effect
        }

        # Add strength data if present
        if strength:
            move['strength_gain'] = strength

        moves.append(move)

    return moves


def parse_pattern_from_text(pattern_text: str) -> Dict[str, Any]:
    """
    Parse move pattern from description text.

    Expected format:
    "Always starts with Incantation, then uses Dark Strike every turn after."

    Returns dict with pattern description and inferred move sequence
    """
    pattern = {
        'description': pattern_text.strip()
    }

    # Try to extract move sequence from pattern
    # This is a simplified version - may need manual review
    if 'starts with' in pattern_text and 'every turn after' in pattern_text:
        # Pattern like: "starts with X, then uses Y every turn after"
        start_match = re.search(r'starts with (\w+)', pattern_text, re.IGNORECASE)
        repeat_match = re.search(r'then uses (\w+) every turn after', pattern_text, re.IGNORECASE)

        if start_match and repeat_match:
            # This is a simplified pattern - actual implementation needs more context
            # For now, just store the description
            pass

    return pattern


def classify_special_mechanics(monster_name: str, moves: List[Dict], pattern: Dict) -> Dict[str, Any]:
    """
    Classify special mechanics from monster data.

    Returns dict with type (summoner, hibernation, phase_change, death_split, none)
    and additional details.
    """
    mechanics = {
        'type': 'none'
    }

    # Check for Ritual (Strength scaling summoner)
    for move in moves:
        if move.get('strength_gain') and move.get('strength_gain') > 0:
            mechanics['type'] = 'summoner'
            mechanics['scaling'] = {
                'type': 'strength_scaling',
                'rate': f"+{move['strength_gain']} Strength/turn"
            }
            break

    # TODO: Add more detection logic for other monster types
    # - Hibernation: Check for "Sleep" intent
    # - Phase change: Check for HP threshold mentions
    # - Death split: Check for "splits into" text
    # - Summoning: Check for "Summon" in move effects

    return mechanics


def generate_threat_profile(monster_name: str, mechanics: Dict, moves: List[Dict]) -> Dict[str, Any]:
    """
    Generate threat profile based on monster characteristics.

    Returns dict with base_threat, scaling_threat, and special threat values.
    """
    threat = {
        'base_threat': 10  # Default for normal monsters
    }

    # Adjust based on monster type
    if 'Cultist' in monster_name:
        threat['base_threat'] = 15
        threat['scaling_threat'] = 3.0  # +3 Strength per turn is dangerous

    # TODO: Add more sophisticated threat calculation
    # - Check for high damage moves
    # - Account for summoning danger
    # - Consider AOE threat

    return threat


def extract_monster_from_playwright(monster_name: str, playwright_data: Dict) -> Dict[str, Any]:
    """
    Extract complete monster data from Playwright browser evaluation result.

    Args:
        monster_name: Name of the monster (e.g., "Cultist")
        playwright_data: Dict returned by browser_evaluate with hpText, moves, patternText, allText

    Returns:
        Complete monster data dict ready for JSON storage
    """
    # Parse HP ranges
    hp_ranges = parse_hp_from_text(playwright_data.get('allText', ''))

    # Parse moves
    moves = parse_moves_from_playwright(playwright_data.get('moves', []))

    # Parse pattern
    pattern = parse_pattern_from_text(playwright_data.get('patternText', ''))

    # Classify special mechanics
    mechanics = classify_special_mechanics(monster_name, moves, pattern)

    # Generate threat profile
    threat_profile = generate_threat_profile(monster_name, mechanics, moves)

    # Classify monster type
    monster_type = 'normal'  # Default, should be overridden manually
    if 'Boss' in monster_name or monster_name in ['Guardian', 'Hexaghost', 'Slime Boss', 'Awakened One', 'The Guardian']:
        monster_type = 'boss'
    elif any(keyword in monster_name for keyword in ['Slaver', 'Gremlin', 'Lagavulin', 'Sentry', 'Reptomancer', 'Champ', 'Centurion', 'Chosen', 'Collector']):
        monster_type = 'elite'

    # Build complete monster data
    monster_data = {
        'monster_id': monster_name.replace(' ', '_').replace('(', '').replace(')', ''),
        'name': monster_name,
        'monster_type': monster_type,
        'hp_ranges': hp_ranges,
        'moves': moves,
        'pattern': pattern,
        'special_mechanics': mechanics,
        'threat_profile': threat_profile
    }

    return monster_data


def main():
    """Main entry point for manual testing with Playwright data."""
    # Example: Use the Cultist data we extracted
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Test with hardcoded Cultist data
        test_data = {
            'hpText': 'HP\n48-54\n\n50-56 7+',
            'moves': [
                {'name': 'Incantation', 'intent': '', 'effect': 'Gains 3  Ritual.'},
                {'name': 'Dark Strike', 'intent': '', 'effect': 'Deal 6 damage.'}
            ],
            'patternText': 'Always starts with  Incantation, then uses  Dark Strike every turn after.\n',
            'allText': 'Cultist\nHP\n48-54\n\n50-56 7+'
        }

        monster_data = extract_monster_from_playwright('Cultist', test_data)
        print(json.dumps(monster_data, indent=2))

        # Save to file
        output_file = 'spirecomm/data/monster_wiki_data/test_cultist.json'
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump({'Cultist': monster_data}, f, indent=2)
        print(f"\nSaved to {output_file}")

    else:
        print("Usage: python extract_from_playwright.py --test")
        print("This will test extraction with hardcoded Cultist data")
        print("\nFor production use, pipe Playwright data to this script")


if __name__ == '__main__':
    main()
