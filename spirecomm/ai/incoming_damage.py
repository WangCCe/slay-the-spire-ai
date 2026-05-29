"""
Shared helpers for live monster incoming-damage estimates.
"""

from typing import Any

from spirecomm.ai.intent_utils import intent_is_attack, intent_is_unknown
from spirecomm.ai.monster_names import canonical_live_monster_name, monster_field
from spirecomm.data.loader import game_data_loader


def _monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    return monster_field(monster, field_name, default)


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
