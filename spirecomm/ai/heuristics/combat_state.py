"""Shared helpers for reading combat state values from partial contexts."""

from typing import Any


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
            return amount if amount is not None else missing_amount
    return 0


def player_power_amount(context: Any, name: str) -> int:
    player = getattr(getattr(context, 'game', None), 'player', None)
    powers = getattr(player, 'powers', []) if player is not None else []
    return power_amount(powers, name, 0)


def player_debuff_stacks(context: Any, name: str) -> int:
    player = getattr(getattr(context, 'game', None), 'player', None)
    powers = getattr(player, 'powers', []) if player is not None else []
    return power_amount(powers, name, 1)


def player_has_power(context: Any, name: str) -> bool:
    player = getattr(getattr(context, 'game', None), 'player', None)
    powers = getattr(player, 'powers', []) if player is not None else []
    return any(power_matches(power, name) for power in powers)


def monster_power_amount(monster: Any, name: str) -> int:
    direct_amount = getattr(monster, name.lower(), None)
    if direct_amount is not None:
        try:
            return max(0, int(direct_amount))
        except (TypeError, ValueError):
            return 0

    powers = getattr(monster, 'powers', []) or []
    return power_amount(powers, name, 1)


def player_block_value(context: Any) -> int:
    block = getattr(context, 'player_block', None)
    if block is None:
        player = getattr(getattr(context, 'game', None), 'player', None)
        block = getattr(player, 'block', 0)

    try:
        return max(0, int(block or 0))
    except (TypeError, ValueError):
        return 0


def draw_pile_count(context: Any) -> int:
    game = getattr(context, 'game', None)
    for owner in (game, context):
        draw_pile = getattr(owner, 'draw_pile', None)
        if draw_pile is not None:
            try:
                return max(0, len(draw_pile))
            except TypeError:
                try:
                    return max(0, int(draw_pile))
                except (TypeError, ValueError):
                    return 0

    for owner in (game, context):
        size = getattr(owner, 'draw_pile_size', None)
        if size is not None:
            try:
                return max(0, int(size))
            except (TypeError, ValueError):
                return 0

    return 0
