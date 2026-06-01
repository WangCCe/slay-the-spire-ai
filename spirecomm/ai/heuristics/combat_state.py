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
