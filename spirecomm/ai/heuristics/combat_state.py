"""Shared helpers for reading combat state values from partial contexts."""

from typing import Any


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
