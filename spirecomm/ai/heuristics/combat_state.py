"""Shared helpers for reading combat state values from partial contexts."""

from typing import Any

from spirecomm.spire.numeric import coerce_int


def card_play_key(card: Any):
    if card is None:
        return None
    return getattr(card, 'uuid', None) or id(card)


def mark_card_played(played_cards: set, card: Any) -> None:
    if card is None:
        return
    key = card_play_key(card)
    if key is not None:
        played_cards.add(key)
    played_cards.add(id(card))


def is_card_played(played_cards: set, card: Any) -> bool:
    if card is None:
        return False
    key = card_play_key(card)
    return key in played_cards or id(card) in played_cards


def power_name(power: Any):
    return (
        getattr(power, 'name', None)
        or getattr(power, 'power_name', None)
        or getattr(power, 'power_id', None)
    )


def power_identifier(power: Any):
    return (
        getattr(power, 'power_id', None)
        or getattr(power, 'power_name', None)
        or getattr(power, 'name', None)
    )


def power_signature(power: Any):
    return (power_identifier(power), getattr(power, 'amount', None))


def power_matches(power: Any, name: str) -> bool:
    return any(
        getattr(power, attr, None) == name
        for attr in ('name', 'power_name', 'power_id')
    )


def power_amount(powers, name: str, missing_amount: int = 0) -> int:
    for power in powers or []:
        if power_matches(power, name):
            amount = getattr(power, 'amount', None)
            value = amount if amount is not None else missing_amount
            return coerce_int(value, 0)
    return 0


def _context_player(context: Any):
    player = getattr(context, 'player', None)
    if player is not None:
        return player

    return getattr(getattr(context, 'game', None), 'player', None)


def player_power_amount(context: Any, name: str) -> int:
    player = _context_player(context)
    powers = getattr(player, 'powers', []) if player is not None else []
    return power_amount(powers, name, 0)


def player_debuff_stacks(context: Any, name: str) -> int:
    player = _context_player(context)
    powers = getattr(player, 'powers', []) if player is not None else []
    return power_amount(powers, name, 1)


def player_has_power(context: Any, name: str) -> bool:
    player = _context_player(context)
    powers = getattr(player, 'powers', []) if player is not None else []
    return any(power_matches(power, name) for power in powers)


def monster_power_amount(monster: Any, name: str) -> int:
    direct_amount = getattr(monster, name.lower(), None)
    if direct_amount is not None:
        return max(0, coerce_int(direct_amount, 0))

    powers = getattr(monster, 'powers', []) or []
    return power_amount(powers, name, 1)


def player_block_value(context: Any) -> int:
    block = getattr(context, 'player_block', None)
    if block is None:
        player = _context_player(context)
        block = getattr(player, 'block', 0)

    return max(0, coerce_int(block or 0, 0))


def _coerce_non_negative_int_or_none(value):
    if value is None:
        return None
    coerced = coerce_int(value, None)
    if coerced is None:
        return None
    return max(0, coerced)


def _first_non_negative_int(candidates, default: int = 0) -> int:
    for candidate in candidates:
        value = _coerce_non_negative_int_or_none(candidate)
        if value is not None:
            return value
    return default


def player_hp_values(context: Any) -> tuple[int, int]:
    game = getattr(context, 'game', None)
    context_player = getattr(context, 'player', None)
    game_player = getattr(game, 'player', None)

    current_hp = _first_non_negative_int(
        (
            getattr(game, 'current_hp', None),
            getattr(context, 'player_hp', None),
            getattr(context_player, 'current_hp', None),
            getattr(game_player, 'current_hp', None),
        )
    )
    max_hp = _first_non_negative_int(
        (
            getattr(game, 'max_hp', None),
            getattr(context, 'player_max_hp', None),
            getattr(context_player, 'max_hp', None),
            getattr(game_player, 'max_hp', None),
        )
    )
    return current_hp, max_hp


def draw_pile_count(context: Any) -> int:
    game = getattr(context, 'game', None)
    for owner in (game, context):
        draw_pile = getattr(owner, 'draw_pile', None)
        if draw_pile is not None:
            try:
                return max(0, len(draw_pile))
            except TypeError:
                return max(0, coerce_int(draw_pile, 0))

    for owner in (game, context):
        size = getattr(owner, 'draw_pile_size', None)
        if size is not None:
            return max(0, coerce_int(size, 0))

    return 0
