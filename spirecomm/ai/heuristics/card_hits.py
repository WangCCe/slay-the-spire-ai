"""Shared card hit-count helpers for heuristic combat code."""

from typing import Any, Optional

from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_upgrades import card_upgrade_count


def fixed_attack_hit_count(card: Any) -> Optional[int]:
    card_name = canonical_card_name(card)
    upgrades = card_upgrade_count(card)

    if card_name == 'Twin Strike':
        return 2
    if card_name == 'Sword Boomerang':
        return 4 if upgrades > 0 else 3
    if card_name == 'Pummel':
        return 5 if upgrades > 0 else 4
    return None
