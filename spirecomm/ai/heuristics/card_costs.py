"""Helpers for card cost values used by combat planners."""

from typing import Optional


def raw_card_cost(card) -> int:
    """Return the raw game cost, preserving -1 for X-cost cards."""
    cost = getattr(card, "cost_for_turn", None)
    if cost is None:
        cost = getattr(card, "cost", 0)
    if cost is None:
        return 0
    try:
        return int(cost)
    except (TypeError, ValueError):
        return 0


def is_x_cost_card(card) -> bool:
    return raw_card_cost(card) < 0


def effective_card_cost(card, available_energy: Optional[int] = None) -> int:
    """Return the energy this card consumes for planning.

    Slay the Spire represents X-cost cards as -1, but playing them consumes all
    currently available energy. Treating -1 as a numeric cost creates negative
    energy accounting in simulations and lethal checks.
    """
    cost = raw_card_cost(card)
    if cost < 0:
        if available_energy is None:
            return 0
        try:
            return max(0, int(available_energy))
        except (TypeError, ValueError):
            return 0
    return max(0, cost)


def whirlwind_damage(card, energy_spent: int, strength: int = 0) -> int:
    """Damage Whirlwind deals to each target for a planned energy spend."""
    per_hit = 8 if getattr(card, "upgrades", 0) > 0 else 5
    return max(0, energy_spent) * max(0, per_hit + strength)
