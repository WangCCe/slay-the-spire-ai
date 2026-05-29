"""
Shared helpers for Slay the Spire monster identifiers.
"""

import re
from typing import Any


LIVE_MONSTER_ID_TO_WIKI_NAME = {
    'awakenedone': 'Awakened One',
    'fungibeast': 'Fungi Beast',
    'slaverred': 'Red Slaver',
    'redslaver': 'Red Slaver',
    'slaverblue': 'Blue Slaver',
    'blueslaver': 'Blue Slaver',
    'fuzzylousenormal': 'Red Louse',
    'fuzzylousedefensive': 'Green Louse',
    'jawworm': 'Jaw Worm',
    'gremlinnob': 'Gremlin Nob',
    'slimeboss': 'Slime Boss',
    'sphericguardian': 'Spheric Guardian',
    'theguardian': 'The Guardian',
    'bronzeautomaton': 'Bronze Automaton',
    'bronzeorb': 'Bronze Orb',
}


def monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(monster, dict):
        return monster.get(field_name, default)
    return getattr(monster, field_name, default)


def normalize_monster_id(monster_id: Any) -> str:
    return re.sub(r'[^a-z0-9]', '', str(monster_id).lower())


def canonical_live_monster_name(monster: Any) -> str:
    monster_id = monster_field(monster, 'monster_id', '') or ''
    mapped_name = LIVE_MONSTER_ID_TO_WIKI_NAME.get(normalize_monster_id(monster_id))
    if mapped_name:
        return mapped_name
    return str(monster_field(monster, 'name', '') or '')
