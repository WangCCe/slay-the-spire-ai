"""Helpers for potion fields that may be absent on partial game objects."""

from spirecomm.spire.identifiers import potion_id


def potion_can_use(potion) -> bool:
    return not hasattr(potion, "can_use") or bool(potion.can_use)


def _normalized_potion_identifier(value) -> str:
    return str(value or "").lower().replace(" ", "").replace("_", "").replace("-", "")


def potion_is_exhaust_hand_select(potion) -> bool:
    if potion is None:
        return False
    effect_type = str(getattr(potion, "effect_type", "") or "").lower()
    identifiers = {
        _normalized_potion_identifier(getattr(potion, "potion_id", "")),
        _normalized_potion_identifier(getattr(potion, "name", "")),
        _normalized_potion_identifier(potion_id(potion)),
    }
    return effect_type == "exhaust_hand_select" or bool(
        identifiers & {"elixir", "elixirpotion"}
    )


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
