"""Shared compact monster-slot mapping for RL v2."""

from typing import List, Tuple

from spirecomm.spire.numeric import coerce_float


def is_targetable_monster(monster) -> bool:
    current_hp = coerce_float(getattr(monster, "current_hp", 0), 0.0)
    return (
        current_hp > 0
        and not getattr(monster, "is_gone", False)
        and not getattr(monster, "half_dead", False)
    )


def compact_monster_slots(game, limit: int) -> List[Tuple[int, object]]:
    monsters = getattr(game, "monsters", None) or []
    slots = [
        (raw_index, monster)
        for raw_index, monster in enumerate(monsters)
        if is_targetable_monster(monster)
    ]
    return slots[:limit]
