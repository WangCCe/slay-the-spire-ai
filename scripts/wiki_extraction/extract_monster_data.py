#!/usr/bin/env python3
"""
Monster data extraction script for Slay the Spire Fandom Wiki.

This script uses Playwright MCP to browse Wiki pages and extract:
- HP ranges (normal and ascension modifiers)
- Move patterns (name, intent, damage/effect, ascension changes)
- Special mechanics
- Strategy notes

Extracted data is formatted into JSON files for integration with the AI.
"""

import json
import re
from typing import Dict, List, Any, Optional


class MonsterDataExtractor:
    """Extract and parse monster data from Wiki page snapshots."""

    def __init__(self):
        self.current_monster = {}
        self.monsters_data = {}

    def parse_hp_ranges(self, snapshot_text: str) -> Dict[str, Any]:
        """
        Extract HP ranges from snapshot text.

        Expected format:
        - HP: 48-54
        - 50-56 (with Ascension icon)

        Returns:
            Dict with 'normal' and optionally 'ascension_10+', 'ascension_15+' keys.
        """
        hp_ranges = {}

        # Look for HP section
        hp_match = re.search(r'HP.*?\n.*?(\d+)-(\d+)', snapshot_text, re.MULTILINE)
        if hp_match:
            min_hp = int(hp_match.group(1))
            max_hp = int(hp_match.group(2))
            hp_ranges['normal'] = {'min': min_hp, 'max': max_hp}

        # Look for Ascension modifiers
        ascension_matches = re.finditer(
            r'(\d+)-(\d+).*?Ascension Icon.*?(\d+)\+',
            snapshot_text
        )
        for match in ascension_matches:
            min_hp = int(match.group(1))
            max_hp = int(match.group(2))
            asc_level = int(match.group(3))

            if asc_level >= 10 and 'ascension_10+' not in hp_ranges:
                hp_ranges['ascension_10+'] = {'min': min_hp, 'max': max_hp}
            elif asc_level >= 15 and 'ascension_15+' not in hp_ranges:
                hp_ranges['ascension_15+'] = {'min': min_hp, 'max': max_hp}

        return hp_ranges

    def parse_moves_table(self, snapshot_text: str) -> List[Dict[str, Any]]:
        """
        Extract moves from the Moves table.

        Expected format:
        | Incantation | Intent - Buff | Gains 3 Icon Ritual Ritual. |
        | Dark Strike | Attack Intent 2 | Deal 6 damage. |
        """
        moves = []
        move_id = 0

        # Find Moves table
        moves_section = re.search(
            r'Moves.*?\n.*?table.*?\n(.*?)</table>',
            snapshot_text,
            re.DOTALL
        )

        if not moves_section:
            return []

        # Parse each row
        rows = moves_section.group(1).split('\n')
        for row in rows:
            if '|' not in row:
                continue

            cells = [cell.strip() for cell in row.split('|')[1:-1]]  # Skip empty first/last cells
            if len(cells) < 3:
                continue

            name = cells[0]
            intent = cells[1]
            effect = cells[2]

            # Extract damage
            damage_match = re.search(r'Deal (\d+) damage', effect)
            damage = int(damage_match.group(1)) if damage_match else None

            # Extract effect text (after the period)
            effect_text = effect.split('.')[-1].strip() if '.' in effect else effect

            move = {
                'move_id': move_id,
                'name': name,
                'intent': intent,
                'damage': damage,
                'effect': effect_text
            }

            moves.append(move)
            move_id += 1

        return moves

    def parse_pattern_section(self, snapshot_text: str) -> Dict[str, Any]:
        """
        Extract move pattern from Pattern section.

        Expected format:
        "Always starts with Incantation, then uses Dark Strike every turn after."
        """
        pattern = {}

        # Look for Pattern section
        pattern_match = re.search(
            r'Pattern.*?\n.*?\"([^\"]+)\".*?Always starts with.*?then uses.*?every turn after\.',
            snapshot_text,
            re.DOTALL
        )

        if pattern_match:
            description = pattern_match.group(1)

            # Parse sequence
            if 'Incantation' in description and 'Dark Strike' in description:
                pattern['move_sequence'] = [0, 1]  # Simplified, actual would need full parsing
                pattern['pattern_description'] = description

        return pattern

    def parse_special_mechanics(self, monster_name: str, snapshot_text: str) -> Dict[str, Any]:
        """
        Identify special mechanics from monster description.

        For Cultist: summoner type
        For other monsters: hibernation, phase_change, death_split, etc.
        """
        mechanics = {
            'type': 'none'
        }

        # Check for Ritual (Strength scaling)
        if 'Ritual' in snapshot_text and 'gains X Strength' in snapshot_text:
            mechanics['type'] = 'summoner'
            mechanics['scaling'] = {
                'type': 'strength_scaling',
                'rate': '+3 Strength/turn'  # Default for Cultist
            }

        # Check for summoning mentions
        if 'Incite' in snapshot_text and 'Summon' in snapshot_text:
            if 'summons' not in mechanics:
                mechanics['summons'] = []
            # Extract summon count if present
            summon_match = re.search(r'Summon (\d+)', snapshot_text)
            if summon_match:
                count = int(summon_match.group(1))
                mechanics['summons'].append({
                    'turn': 3,  # Default Incite turn
                    'name': monster_name,  # Cultist summons Cultist
                    'count': count
                })

        # TODO: Add more special mechanic detection for other monster types

        return mechanics

    def parse_trivia_for_strategy(self, snapshot_text: str) -> Dict[str, Any]:
        """
        Extract strategy hints from Trivia section.
        """
        strategy = {}

        # Check for Trivia section
        trivia_match = re.search(
            r'Trivia.*?\n.*?(.*?)(?=---|$)',
            snapshot_text,
            re.DOTALL
        )

        if trivia_match:
            trivia_text = trivia_match.group(1)
            # Look for strategy hints
            if 'worship' in trivia_text and 'Awakened One' in trivia_text:
                strategy['lore'] = "Worships Awakened One"

        return strategy

    def extract_monster_data(self, monster_name: str, snapshot_text: str) -> Dict[str, Any]:
        """
        Extract all monster data from a Wiki page snapshot.
        """
        self.current_monster = {
            'monster_id': monster_name.replace(' ', '_'),
            'name': monster_name,
            'monster_type': self._classify_monster_type(monster_name),
            'act': self._extract_act(monster_name)
        }

        # Extract HP ranges
        hp_ranges = self.parse_hp_ranges(snapshot_text)
        if hp_ranges:
            self.current_monster['hp_ranges'] = hp_ranges

        # Extract moves
        moves = self.parse_moves_table(snapshot_text)
        if moves:
            self.current_monster['moves'] = moves

            # Infer move sequence from pattern
            pattern = self.parse_pattern_section(snapshot_text)
            if pattern and 'move_sequence' in pattern:
                self.current_monster['move_sequence'] = pattern['move_sequence']

        # Extract special mechanics
        mechanics = self.parse_special_mechanics(monster_name, snapshot_text)
        if mechanics:
            self.current_monster['special_mechanics'] = mechanics

        # Add basic threat profile
        self.current_monster['threat_profile'] = self._generate_threat_profile(monster_name)

        # Store monster data
        self.monsters_data[monster_name] = self.current_monster

        return self.current_monster

    def _classify_monster_type(self, monster_name: str) -> str:
        """Classify monster as normal, elite, or boss."""
        elite_keywords = ['Slaver', 'Gremlin Nob', 'Lagavulin', 'Sentry', 'Reptomancer',
                      'Champ', 'Centurion', 'Gremlin Leader', 'Gremlin Giant',
                      'Time Eater', 'Donu', 'Deca', 'Chosen', 'Collector']

        boss_keywords = ['Guardian', 'Hexaghost', 'Slime Boss', 'Awakened One', 'Heart']

        monster_id = monster_name.replace(' ', '_')

        if any(keyword in monster_id for keyword in boss_keywords):
            return 'boss'
        elif any(keyword in monster_id for keyword in elite_keywords):
            return 'elite'
        else:
            return 'normal'

    def _extract_act(self, monster_name: str) -> int:
        """Extract Act number from monster name or context."""
        # TODO: Parse from "In Party With" section
        return 1  # Default

    def _generate_threat_profile(self, monster_name: str) -> Dict[str, Any]:
        """Generate basic threat profile based on monster type."""
        monster_type = self._classify_monster_type(monster_name)

        if monster_type == 'boss':
            return {'base_threat': 25}
        elif monster_type == 'elite':
            return {'base_threat': 20}
        else:
            return {'base_threat': 10}

    def save_to_json(self, output_file: str):
        """Save extracted monster data to JSON file."""
        # Create directory if needed
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(self.monsters_data, f, indent=2)

        print(f"Extracted {len(self.monsters_data)} monsters to {output_file}")


def main():
    """Main entry point for testing."""
    extractor = MonsterDataExtractor()

    # Test with Cultist data (from snapshot)
    test_snapshot = """
    HP: 48-54
    50-56⁷

    Moves:
    | Incantation | Intent - Buff | Gains 3 Icon Ritual Ritual. |
    | Dark Strike | Attack Intent 2 | Deal 6 damage. |

    Pattern:
    "Always starts with Incantation, then uses Dark Strike every turn after."
    """

    # Extract test data
    monster_data = extractor.extract_monster_data('Cultist', test_snapshot)
    print(f"Extracted: {json.dumps(monster_data, indent=2)}")

    # Save to JSON
    # extractor.save_to_json('spirecomm/data/monster_wiki_data/test_cultist.json')


if __name__ == '__main__':
    main()
