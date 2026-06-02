"""
Shared helpers for live monster incoming-damage estimates.
"""

from typing import Any

from spirecomm.ai.intent_utils import intent_is_attack, intent_is_unknown
from spirecomm.ai.monster_names import canonical_live_monster_name, monster_field
from spirecomm.data.loader import game_data_loader
from spirecomm.spire.numeric import coerce_int


def _monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    return monster_field(monster, field_name, default)


def numeric_damage_value(value: Any) -> int:
    if isinstance(value, (list, tuple)):
        values = [numeric_damage_value(item) for item in value]
        return max(values) if values else 0
    return max(0, coerce_int(value or 0, 0))


def positive_hit_count(value: Any) -> int:
    return max(1, coerce_int(value or 1, 1))


def move_data_immediate_unknown_damage(move: Any) -> int:
    if not isinstance(move, dict):
        return 0
    if not intent_is_unknown(move.get('intent', '')):
        return 0

    damage = numeric_damage_value(move.get('damage', 0))
    if damage <= 0:
        return 0
    hits = positive_hit_count(move.get('hits', move.get('move_hits', 1)))
    return damage * hits


def known_unknown_move_immediate_damage(monster: Any) -> int:
    if not intent_is_unknown(_monster_field(monster, 'intent')):
        return 0

    live_damage = numeric_damage_value(_monster_field(monster, 'move_adjusted_damage', 0))
    if live_damage > 0:
        return live_damage * positive_hit_count(_monster_field(monster, 'move_hits', 1))

    move_id = _monster_field(monster, 'move_id')
    if move_id is None:
        return 0

    try:
        moves = game_data_loader.get_monster_moves(canonical_live_monster_name(monster))
    except Exception:
        return 0

    for move in moves:
        if move.get('move_id') != move_id:
            continue
        return move_data_immediate_unknown_damage(move)
    return 0


def known_unknown_move_has_no_immediate_damage(monster: Any) -> bool:
    if not intent_is_unknown(_monster_field(monster, 'intent')):
        return False

    move_id = _monster_field(monster, 'move_id')
    if move_id is None:
        return False
    if known_unknown_move_immediate_damage(monster) > 0:
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
