"""
Shared helpers for live monster incoming-damage estimates.
"""

import re
from typing import Any

from spirecomm.ai.intent_utils import intent_is_attack, intent_is_unknown
from spirecomm.data.loader import game_data_loader


LIVE_MONSTER_ID_TO_WIKI_NAME = {
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
}


def _monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(monster, dict):
        return monster.get(field_name, default)
    return getattr(monster, field_name, default)


def _normalize_monster_id(monster_id: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(monster_id).lower())


def canonical_live_monster_name(monster: Any) -> str:
    monster_id = _monster_field(monster, 'monster_id', '') or ''
    mapped_name = LIVE_MONSTER_ID_TO_WIKI_NAME.get(_normalize_monster_id(monster_id))
    if mapped_name:
        return mapped_name
    return str(_monster_field(monster, 'name', '') or '')


def numeric_damage_value(value: Any) -> int:
    if isinstance(value, (list, tuple)):
        values = [numeric_damage_value(item) for item in value]
        return max(values) if values else 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def known_unknown_move_has_no_immediate_damage(monster: Any) -> bool:
    if not intent_is_unknown(_monster_field(monster, 'intent')):
        return False

    move_id = _monster_field(monster, 'move_id')
    if move_id is None:
        return False
    if numeric_damage_value(_monster_field(monster, 'move_adjusted_damage', 0)) > 0:
        return False

    try:
        moves = game_data_loader.get_monster_moves(canonical_live_monster_name(monster))
    except Exception:
        return False

    for move in moves:
        if move.get('move_id') != move_id:
            continue
        if intent_is_attack(move.get('intent', '')):
            return False
        return numeric_damage_value(move.get('damage', 0)) <= 0
    return False
