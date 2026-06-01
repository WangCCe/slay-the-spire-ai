"""Helpers for potion fields that may be absent on partial game objects."""


def potion_can_use(potion) -> bool:
    return not hasattr(potion, "can_use") or bool(potion.can_use)
