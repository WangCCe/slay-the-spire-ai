"""
Shared helpers for live monster incoming-damage estimates.
"""

from typing import Any

from spirecomm.ai.intent_utils import intent_is_attack, intent_is_unknown
from spirecomm.ai.monster_names import canonical_live_monster_name, monster_field
from spirecomm.data.loader import game_data_loader
from spirecomm.spire.numeric import coerce_int

EXPLODER_EXPLOSION_DAMAGE = 30


def _monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    return monster_field(monster, field_name, default)


def _power_field(power: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(power, dict):
        return power.get(field_name, default)
    return getattr(power, field_name, default)


def numeric_damage_value(value: Any) -> int:
    if isinstance(value, (list, tuple)):
        values = [numeric_damage_value(item) for item in value]
        return max(values) if values else 0
    return max(0, coerce_int(value or 0, 0))


def positive_hit_count(value: Any) -> int:
    return max(1, coerce_int(value or 1, 1))


def _normalized_identifier(value: Any) -> str:
    return ''.join(ch for ch in str(value or '').lower() if ch.isalnum())


def _monster_power_amount(monster: Any, *power_names: str) -> int:
    wanted = {_normalized_identifier(name) for name in power_names}
    for power in _monster_field(monster, 'powers', []) or []:
        identifiers = (
            _power_field(power, 'power_id'),
            _power_field(power, 'id'),
            _power_field(power, 'power_name'),
            _power_field(power, 'name'),
        )
        if not any(_normalized_identifier(identifier) in wanted for identifier in identifiers):
            continue
        return max(0, coerce_int(_power_field(power, 'amount', 1), 1))
    return 0


def _monster_is_exploder(monster: Any) -> bool:
    identifiers = (
        _monster_field(monster, 'monster_id'),
        _monster_field(monster, 'id'),
        _monster_field(monster, 'name'),
        canonical_live_monster_name(monster),
    )
    return any('exploder' in _normalized_identifier(identifier) for identifier in identifiers)


def exploder_explosion_damage(monster: Any) -> int:
    """Return current-turn Exploder explosion damage from live power countdown."""
    if not _monster_is_exploder(monster):
        return 0

    countdown = _monster_field(monster, 'explosive', None)
    if countdown is None:
        countdown = _monster_field(monster, 'explosive_countdown', None)
    if countdown is None:
        countdown = _monster_power_amount(monster, 'Explosive', 'ExplosivePower')
    countdown = max(0, coerce_int(countdown, 0))
    return EXPLODER_EXPLOSION_DAMAGE if countdown == 1 else 0


def live_unknown_move_has_no_immediate_damage(monster: Any) -> bool:
    if not intent_is_unknown(_monster_field(monster, 'intent')):
        return False

    identifiers = (
        _monster_field(monster, 'monster_id'),
        _monster_field(monster, 'name'),
        canonical_live_monster_name(monster),
    )
    if not any('hexaghost' in _normalized_identifier(value) for value in identifiers):
        return False

    move_id = coerce_int(_monster_field(monster, 'move_id'), default=-1)
    if move_id not in (0, 5):
        return False
    if positive_hit_count(_monster_field(monster, 'move_hits', 1)) > 1:
        return False
    return numeric_damage_value(_monster_field(monster, 'move_adjusted_damage', 0)) <= 5


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

    if live_unknown_move_has_no_immediate_damage(monster):
        return 0

    explosion_damage = exploder_explosion_damage(monster)
    if explosion_damage > 0:
        return explosion_damage

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

    if live_unknown_move_has_no_immediate_damage(monster):
        return True

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
