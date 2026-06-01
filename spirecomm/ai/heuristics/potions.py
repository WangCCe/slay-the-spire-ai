"""Helpers for potion fields that may be absent on partial game objects."""

from spirecomm.spire.identifiers import potion_id


def potion_can_use(potion) -> bool:
    return not hasattr(potion, "can_use") or bool(potion.can_use)


def game_real_potions(game):
    get_real_potions = getattr(game, "get_real_potions", None)
    if callable(get_real_potions):
        potions = get_real_potions() or []
    else:
        potions = getattr(game, "potions", None) or []
    return [
        potion
        for potion in potions
        if potion_id(potion) != "Potion Slot"
    ]


def game_potion_available(game) -> bool:
    if hasattr(game, "potion_available"):
        return bool(game.potion_available)
    return any(
        potion_can_use(potion)
        for potion in game_real_potions(game)
    )
