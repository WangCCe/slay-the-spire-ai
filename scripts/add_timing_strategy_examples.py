"""
Script to add timing_strategy to key Act 1 monsters.

This script demonstrates how to add timing hints to monster Wiki data.
Run this to enhance specific monsters with timing information.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spirecomm.ai.heuristics.timing.models import MonsterTimingHints


def add_cultist_timing_strategy(monster_data: dict) -> dict:
    """Add timing strategy for Cultist."""
    monster_data["timing_strategy"] = {
        "description": "Cultist Rituals on turn 1 (no damage), then attacks every turn with increasing Strength.",
        "safe_turn_indicators": ["BUFF"],
        "spike_turn_indicators": ["ATTACK"],
        "preparation_windows": [
            {
                "trigger": "after_ritual",
                "look_ahead": 1,
                "expected_damage": 9,
                "note": "After turn 1, Cultist will have +3 Strength and attack for 9 damage"
            }
        ],
        "burst_opportunities": [
            {
                "turn": 1,
                "reason": "Cultist is buffing (Ritual) - perfect time to attack"
            }
        ],
        "preferred_response": {
            "SAFE": "aggressive_damage",
            "THREAT_SPIKE": "block_then_attack",
            "PREPARATION": "build_block"
        }
    }
    return monster_data


def add_jaw_worm_timing_strategy(monster_data: dict) -> dict:
    """Add timing strategy for Jaw Worm."""
    monster_data["timing_strategy"] = {
        "description": "Simple attacker. Block on Bite turns, attack aggressively on Bellow (defend) turns.",
        "safe_turn_indicators": ["DEFEND"],
        "spike_turn_indicators": ["ATTACK"],
        "preparation_windows": [],
        "burst_opportunities": [
            {
                "trigger": "bellow_turn",
                "reason": "Jaw Worm gains block instead of attacking - safe to attack"
            }
        ],
        "preferred_response": {
            "SAFE": "attack",
            "THREAT_SPIKE": "block_if_damage > 8"
        }
    }
    return monster_data


def add_fungi_beast_timing_strategy(monster_data: dict) -> dict:
    """Add timing strategy for Fungi Beast."""
    monster_data["timing_strategy"] = {
        "description": "Alternates between Bite and Spore Cloud (applies Weak). Attack aggressively on Spore Cloud turns.",
        "safe_turn_indicators": ["DEBUFF"],
        "spike_turn_indicators": [],
        "preparation_windows": [],
        "burst_opportunities": [
            {
                "trigger": "spore_cloud_turn",
                "reason": "Fungi Beast is applying Weak instead of attacking - but Weak will reduce your damage next turn"
            }
        ],
        "preferred_response": {
            "SAFE": "attack_aggressive",
            "THREAT_SPIKE": "block"
        },
        "notes": "Spore Cloud applies 2 Weak, making attacks less effective next turn. Consider using block or non-attack cards on Spore Cloud turns."
    }
    return monster_data


def add_captive_timing_strategy(monster_data: dict) -> dict:
    """Add timing strategy for Captive."""
    monster_data["timing_strategy"] = {
        "description": "Completely harmless until hit. Can be ignored until ready to kill.",
        "safe_turn_indicators": ["STUN"],
        "spike_turn_indicators": ["ATTACK"],
        "preparation_windows": [],
        "burst_opportunities": [
            {
                "trigger": "stunned_state",
                "reason": "Captive is stunned and cannot act - free damage turn"
            }
        ],
        "preferred_response": {
            "SAFE": "ignore_or_attack",
            "THREAT_SPIKE": "block"
        }
    }
    return monster_data


def add_louse_timing_strategy(monster_data: dict, louse_type: str) -> dict:
    """Add timing strategy for Louse (Red or Green)."""
    monster_data["timing_strategy"] = {
        "description": f"{louse_type} Louse alternates between Bite (attack) and Grow (+3 Strength). Attack during Grow turns.",
        "safe_turn_indicators": ["BUFF"],
        "spike_turn_indicators": ["ATTACK"],
        "preparation_windows": [
            {
                "trigger": "after_strength_gain",
                "look_ahead": 1,
                "expected_damage": 10,
                "note": "After Grow, Bite damage increases by Strength"
            }
        ],
        "burst_opportunities": [
            {
                "trigger": "grow_turn",
                "reason": "Louse is gaining Strength instead of attacking - kill it fast!"
            }
        ],
        "preferred_response": {
            "SAFE": "aggressive_damage",
            "THREAT_SPIKE": "block_if_damage > 8",
            "PREPARATION": "build_block"
        }
    }
    return monster_data


def add_slime_boss_timing_strategy(monster_data: dict) -> dict:
    """Add timing strategy for Slime Boss."""
    monster_data["timing_strategy"] = {
        "description": "Slime Boss splits at 50% HP into 2 smaller slimes. Use AOE before split, single-target after.",
        "safe_turn_indicators": [],
        "spike_turn_indicators": ["ATTACK"],
        "preparation_windows": [],
        "burst_opportunities": [
            {
                "trigger": "before_split",
                "condition": "hp < 60%",
                "reason": "Kill before split to avoid fighting 2 monsters"
            }
        ],
        "preferred_response": {
            "SAFE": "attack",
            "THREAT_SPIKE": "block"
        },
        "notes": "Slime Boss uses Goop Spray, then Preparing, then Slam (repeat). At 50% HP, splits into Acid Slime L and Spike Slime L."
    }
    return monster_data


def process_monster_file(file_path: Path):
    """Add timing strategies to key monsters in the Act 1 normal monsters file."""
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        monsters = json.load(f)

    # Add timing strategies to key monsters
    timing_strategies = {
        "Cultist": add_cultist_timing_strategy,
        "Jaw Worm": add_jaw_worm_timing_strategy,
        "Fungi Beast": add_fungi_beast_timing_strategy,
        "Captive": add_captive_timing_strategy,
        "Red Louse": lambda m: add_louse_timing_strategy(m, "Red"),
        "Green Louse": lambda m: add_louse_timing_strategy(m, "Green"),
        "Slime Boss": add_slime_boss_timing_strategy,
    }

    enhanced_count = 0
    for monster in monsters:
        monster_name = monster.get("name", "")
        if monster_name in timing_strategies:
            monster = timing_strategies[monster_name](monster)
            enhanced_count += 1
            print(f"  ✓ Added timing_strategy for {monster_name}")

    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(monsters, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Enhanced {enhanced_count} monsters with timing_strategy")
    print(f"✓ Updated {file_path}")


if __name__ == "__main__":
    # Path to Act 1 normal monsters file
    monster_file = Path("/mnt/d/PycharmProjects/slay-the-spire-ai/spirecomm/data/monster_wiki_data/act1_normal_monsters.json")

    if not monster_file.exists():
        print(f"Error: {monster_file} not found!")
        sys.exit(1)

    print("=" * 60)
    print("Adding timing_strategy to Act 1 normal monsters")
    print("=" * 60)
    print()

    process_monster_file(monster_file)

    print()
    print("=" * 60)
    print("Done! Timing strategies added to key monsters.")
    print("=" * 60)
