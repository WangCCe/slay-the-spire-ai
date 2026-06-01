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


def fiend_fire_exhaust_count(card: Any, context: Any) -> int:
    hand_cards = getattr(getattr(context, 'game', None), 'hand', None)
    if not hand_cards:
        hand_cards = getattr(context, 'playable_cards', []) or []

    played_uuid = getattr(card, 'uuid', None)
    count = 0
    for hand_card in hand_cards:
        if hand_card is card:
            continue
        if played_uuid and getattr(hand_card, 'uuid', None) == played_uuid:
            continue
        count += 1
    return max(0, count)
