"""Helpers for card cost values used by combat planners."""

import re
from typing import Any, Optional

from spirecomm.spire.numeric import coerce_int

from .card_names import canonical_card_name
from .card_upgrades import is_card_upgraded


def _safe_int(value: Any, default: int = 0) -> int:
    return coerce_int(value, default)


def raw_card_cost(card) -> int:
    """Return the raw game cost, preserving -1 for X-cost cards."""
    cost = getattr(card, "cost_for_turn", None)
    if cost is None:
        cost = getattr(card, "cost", 0)
    return _safe_int(cost, 0)


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
        return max(0, _safe_int(available_energy, 0))
    return max(0, cost)


def energy_refund_for_card(card, target_vulnerable: bool = False) -> int:
    if canonical_card_name(card) == "Dropkick" and target_vulnerable:
        return 1
    return 0


def effective_card_cost_after_refund(
    card,
    available_energy: Optional[int] = None,
    energy_refund: int = 0,
) -> int:
    refund = max(0, _safe_int(energy_refund, 0))
    return max(0, effective_card_cost(card, available_energy) - refund)


def playable_card_cost_after_refund(
    card,
    available_energy: Optional[int] = None,
    energy_refund: int = 0,
) -> int:
    """Return net cost after refund only when the card can be paid upfront.

    Refund cards such as Dropkick still require paying their normal cost before
    the refund resolves. Returning the upfront cost when it is unaffordable keeps
    existing ``cost > available_energy`` checks conservative and explicit.
    """
    upfront_cost = effective_card_cost(card, available_energy)
    if available_energy is not None:
        energy = max(0, _safe_int(available_energy, 0))
        if upfront_cost > energy:
            return upfront_cost

    return effective_card_cost_after_refund(card, available_energy, energy_refund)


def _normalized_game_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def context_has_relic(context, relic_name: str) -> bool:
    game = getattr(context, "game", None)
    relics = getattr(game, "relics", []) or []
    wanted = _normalized_game_id(relic_name)
    for relic in relics:
        names = [
            getattr(relic, "relic_id", None),
            getattr(relic, "name", None),
        ]
        if isinstance(relic, str):
            names.append(relic)
        if any(_normalized_game_id(name) == wanted for name in names):
            return True
    return False


def chemical_x_bonus(context) -> int:
    return 2 if context_has_relic(context, "Chemical X") else 0


def x_effect_energy(card, available_energy: Optional[int] = None, context=None) -> int:
    """Return the X value used by card effects, distinct from energy consumed."""
    energy = effective_card_cost(card, available_energy)
    if is_x_cost_card(card):
        energy += chemical_x_bonus(context)
    return energy


def whirlwind_damage(card, energy_spent: int, strength: int = 0) -> int:
    """Damage Whirlwind deals to each target for a planned energy spend."""
    per_hit = 8 if is_card_upgraded(card) else 5
    return max(0, energy_spent) * max(0, per_hit + strength)
