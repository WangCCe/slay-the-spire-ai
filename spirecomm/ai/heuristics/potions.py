"""Helpers for potion fields that may be absent on partial game objects."""

from spirecomm.spire.identifiers import potion_id


def potion_can_use(potion) -> bool:
    return not hasattr(potion, "can_use") or bool(potion.can_use)


def game_potion_available(game) -> bool:
    if hasattr(game, "potion_available"):
        return bool(game.potion_available)
    potions = getattr(game, "potions", None) or []
    return any(
        potion_id(potion) != "Potion Slot" and potion_can_use(potion)
        for potion in potions
    )
