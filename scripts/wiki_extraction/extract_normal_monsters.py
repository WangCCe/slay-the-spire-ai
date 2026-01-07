#!/usr/bin/env python3
"""
Batch extract normal monsters from Slay the Spire Wiki.

Extracts high-frequency normal monsters (non-elites/bosses) from all 3 acts.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "wiki_extraction"))

from extract_from_playwright import extract_monster_data

# High-priority normal monsters to extract
NORMAL_MONSTERS = {
    "Act 1": [
        "Jaw_Worm",
        "Louse",
        "Slime_(Small)",
        "Acid_Slime_(Medium)",
        "Spike_Slime_(Medium)",
        "Slime_(Large)",
        "Cultist",  # Already extracted, skip
        "Fungi_Beast",  # Also appears as elite
        "Sentry",
        "Spheric_Guardian",
        "Shield_Gremlin",
        "Fat_Gremlin",
        "Mad_Gremlin",
        "Gremlin_Medic",
        "Sneaky_Gremlin",
        "Gremlin_Wizard",
    ],
    "Act 2": [
        "Slaver",
        "Snake_Plant",
        "Sentry",  # Duplicate
        "Shield_and_Spear",
        "Red_Mausoleum_Mugger",
        "Mugger",
        "Outlaw",
        "Heatsink",
        "Fungo",
        "Exploder",
        "Thirst",
        "Book_of_Stabbing",
        "The_Birds",
    ],
    "Act 3": [
        "Spiker",
        "Snake_Plant",  # Duplicate
        "Transient",
        "Narcolepsy",
        "Shapes",
        "Sentry",  # Duplicate
        "Mugger",  # Duplicate
        "Healer",
        "Mind_Bloom",
        "Bronze_Automaton",
        "Mystic",
        "Grandmother",
    ]
}

ALREADY_EXTRACTED = [
    "Cultist",  # Act 1
    "Lagavulin",  # Act 1 Elite
    "Hexaghost",  # Act 1 Boss
    "Slime_Boss",  # Act 1 Boss
    "Blue_Slaver",  # Act 1 Elite
    "Red_Slaver",  # Act 1 Elite
    "Gremlin_Giant",  # Act 1 Elite
    "Guardian",  # Act 1 Boss
    "Gremlin_Leader",  # Act 2 Elite
    "The_Champ",  # Act 2 Boss
    "The_Collector",  # Act 2 Boss
    "Slime_Boss",  # Already extracted
    "Time_Eater",  # Act 3 Boss
    "The_Observer",  # Act 3 Boss
    "Awakened_One",  # Act 3 Boss
    "Reptomancer",  # Act 3 Elite
    "Donu_and_Deca",  # Act 3 Boss
]


async def extract_all_normal_monsters():
    """Extract all normal monsters."""

    # Output directory
    output_dir = Path("spirecomm/data/monster_wiki_data")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect unique monsters
    unique_monsters = set()
    for act, monsters in NORMAL_MONSTERS.items():
        for monster in monsters:
            # Skip already extracted
            if monster in ALREADY_EXTRACTED:
                print(f"Skipping {monster} (already extracted)")
                continue
            unique_monsters.add(monster)

    # Sort for consistent extraction order
    monster_list = sorted(unique_monsters)
    print(f"\nExtracting {len(monster_list)} unique normal monsters...\n")

    # Extract each monster
    results = {}
    for i, monster_name in enumerate(monster_list, 1):
        print(f"[{i}/{len(monster_list)}] Extracting {monster_name}...")

        try:
            # Extract using existing function
            wiki_name = monster_name.replace("_", " ")
            data = await extract_monster_data(wiki_name)

            if data:
                results[monster_name] = data
                print(f"  ✓ Extracted successfully")
            else:
                print(f"  ✗ Failed to extract")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Save results per act
    for act in ["Act 1", "Act 2", "Act 3"]:
        act_results = {}
        for monster_name, data in results.items():
            # Determine which act this monster belongs to
            for act_name, monsters in NORMAL_MONSTERS.items():
                if monster_name in monsters:
                    act_results[monster_name] = data
                    break

        if act_results:
            # Convert to list format
            output_data = list(act_results.values())

            # Save to file
            act_slug = act.lower().replace(" ", "_")
            output_file = output_dir / f"{act_slug}_normal_monsters.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"\nSaved {len(act_results)} monsters to {output_file}")

    # Summary
    print(f"\n{'='*70}")
    print(f"Extraction Complete!")
    print(f"{'='*70}")
    print(f"Total monsters attempted: {len(monster_list)}")
    print(f"Successfully extracted: {len(results)}")
    print(f"Failed: {len(monster_list) - len(results)}")
    print(f"{'='*70}\n")

    return results


if __name__ == "__main__":
    asyncio.run(extract_all_normal_monsters())
