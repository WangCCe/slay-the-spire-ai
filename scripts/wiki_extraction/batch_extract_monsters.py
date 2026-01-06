#!/usr/bin/env python3
"""
Batch extraction script for Slay the Spire monster data from Fandom Wiki.

This script is designed to work with Playwright MCP to extract data from multiple
monster pages in sequence.

Usage:
1. Manually navigate to monster pages using Playwright MCP
2. Extract data using browser_evaluate
3. Pipe extracted JSON data to this script

Monster list to extract:
Act 1 Elites/Bosses (6): Slaver, Gremlin Giant, Lagavulin, Guardian, Slime Boss, Hexaghost
Act 2 Elites/Bosses (5): Gremlin Leader, Centurion, Champ, Reptomancer, Collector
Act 3 Elites/Bosses (4): Sentry, Chosen, Time Eater, Donu & Deca
High-Priority Normals (7): Cultist, Jaw Worm, Fungi Beast, Shield & Spear, Sneaky Gremlin, Book of Stabbing, Spiker
"""

import json
import re
import sys
from typing import Dict, List, Any
from extract_from_playwright import extract_monster_from_playwright


# List of monsters to extract with their Wiki URLs
MONSTERS_TO_EXTRACT = {
    # Act 1 Elites/Bosses
    "Slaver": "https://slay-the-spire.fandom.com/wiki/Slavers",
    "Gremlin Giant": "https://slay-the-spire.fandom.com/wiki/Gremlin_Giant",
    "Lagavulin": "https://slay-the-spire.fandom.com/wiki/Lagavulin",
    "Guardian": "https://slay-the-spire.fandom.com/wiki/Guardian",
    "Slime Boss": "https://slay-the-spire.fandom.com/wiki/Slime_Boss",
    "Hexaghost": "https://slay-the-spire.fandom.com/wiki/Hexaghost",

    # Act 2 Elites/Bosses
    "Gremlin Leader": "https://slay-the-spire.fandom.com/wiki/Gremlin_Leader",
    "Centurion": "https://slay-the-spire.fandom.com/wiki/Centurion",
    "Champ": "https://slay-the-spire.fandom.com/wiki/Champ",
    "Reptomancer": "https://slay-the-spire.fandom.com/wiki/Reptomancer",
    "Collector": "https://slay-the-spire.fandom.com/wiki/Collector",

    # Act 3 Elites/Bosses
    "Sentry": "https://slay-the-spire.fandom.com/wiki/Sentry",
    "Chosen": "https://slay-the-spire.fandom.com/wiki/Chosen",
    "Time Eater": "https://slay-the-spire.fandom.com/wiki/Time_Eater",
    "Donu": "https://slay-the-spire.fandom.com/wiki/Donu_%26_Deca",

    # High-Priority Normals
    "Cultist": "https://slay-the-spire.fandom.com/wiki/Cultist",
    "Jaw Worm": "https://slay-the-spire.fandom.com/wiki/Jaw_Worm",
    "Fungi Beast": "https://slay-the-spire.fandom.com/wiki/Fungi_Beast",
    "Shield & Spear": "https://slay-the-spire.fandom.com/wiki/Shield_%26_Spear",
    "Sneaky Gremlin": "https://slay-the-spire.fandom.com/wiki/Sneaky_Gremlin",
    "Book of Stabbing": "https://slay-the-spire.fandom.com/wiki/Book_of_Stabbing",
    "Spiker": "https://slay-the-spire.fandom.com/wiki/Spiker",
}


def extract_data_from_playwright_json(monster_name: str, playwright_json: str) -> Dict[str, Any]:
    """
    Extract monster data from Playwright browser_evaluate JSON result.

    Args:
        monster_name: Name of the monster
        playwright_json: JSON string from Playwright browser_evaluate

    Returns:
        Monster data dict
    """
    data = json.loads(playwright_json)
    return extract_monster_from_playwright(monster_name, data)


def save_monsters_to_json(monsters_data: Dict[str, Dict], output_file: str):
    """Save extracted monster data to JSON file."""
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(monsters_data, f, indent=2)

    print(f"Saved {len(monsters_data)} monsters to {output_file}")


def main():
    """Main entry point for batch extraction."""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            # Print list of monsters to extract
            print("Monsters to extract:")
            for i, (name, url) in enumerate(MONSTERS_TO_EXTRACT.items(), 1):
                print(f"{i}. {name}: {url}")
            print(f"\nTotal: {len(MONSTERS_TO_EXTRACT)} monsters")

        elif sys.argv[1] == '--import':
            # Import data from stdin
            if len(sys.argv) < 3:
                print("Usage: python batch_extract_monsters.py --import <monster_name> < <json_data>")
                sys.exit(1)

            monster_name = sys.argv[2]
            json_data = sys.stdin.read()

            try:
                monster_data = extract_data_from_playwright_json(monster_name, json_data)
                print(json.dumps(monster_data, indent=2))
            except Exception as e:
                print(f"Error extracting data: {e}", file=sys.stderr)
                sys.exit(1)

        elif sys.argv[1] == '--test':
            # Test with sample data
            test_data = {
                'Cultist': {
                    'monster_id': 'Cultist',
                    'name': 'Cultist',
                    'monster_type': 'normal',
                    'hp_ranges': {'normal': {'min': 48, 'max': 54}}
                }
            }
            save_monsters_to_json(test_data, 'spirecomm/data/monster_wiki_data/test_batch.json')

        else:
            print("Usage:")
            print("  python batch_extract_monsters.py --list")
            print("  python batch_extract_monsters.py --import <monster_name> < <json_data>")
            print("  python batch_extract_monsters.py --test")
    else:
        print("Slay the Spire Monster Data Batch Extraction")
        print("\nThis script is designed to work with Playwright MCP.")
        print("\nCommands:")
        print("  --list     List all monsters to extract")
        print("  --import   Import monster data from Playwright JSON")
        print("  --test      Test extraction with sample data")
        print("\nExample workflow:")
        print("  1. Use Playwright MCP to navigate to monster page")
        print("  2. Use browser_evaluate to extract data")
        print("  3. Pipe JSON to this script: echo '<json>' | python batch_extract_monsters.py --import Cultist")


if __name__ == '__main__':
    main()
