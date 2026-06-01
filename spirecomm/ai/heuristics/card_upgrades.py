"""Shared card upgrade value helpers for heuristic combat code."""

import re
from typing import Any


_UPGRADE_SUFFIX_RE = re.compile(r'\+(\d*)$')


# Attack card upgrade damage bonuses. Cards with special dynamic handling
# still appear here when callers need a conservative fallback from base text.
DAMAGE_UPGRADE_BONUS = {
    # +0 damage (upgrades don't increase base damage)
    'Pummel': 0,
    'Sword Boomerang': 0,
    'Perfected Strike': 0,
    'Heavy Blade': 0,  # Complex: depends on Strength
    'Uppercut': 0,
    'Rampage': 0,  # Has separate scaling mechanism

    # +1 damage
    'Bite': 1,
    'Pommel Strike': 1,
    'Reaper': 1,

    # +2 damage
    'Anger': 2,
    'Bash': 2,
    'Feed': 2,
    'Iron Wave': 2,
    'Clothesline': 2,
    'Twin Strike': 2,
    'Shiv': 2,

    # +3 damage
    'Dropkick': 3,
    'Fiend Fire': 3,
    'Reckless Charge': 3,
    'Strike': 3,
    'Thunderclap': 3,
    'Lesson Learned': 3,
    'Flash of Steel': 3,
    'Swift Strike': 3,
    'Headbutt': 3,
    'Cleave': 3,
    'Bane': 3,
    'Skewer': 3,

    # +4 damage
    'Clash': 4,
    'Blood for Blood': 4,
    'Searing Blow': 4,
    'Dramatic Entrance': 4,
    'Smite': 4,

    # +5 damage
    'Wild Strike': 5,
    'Hemokinesis': 5,
    'Hand of Greed': 5,

    # +6 damage
    'Sever Soul': 6,

    # +7 damage
    'Immolate': 7,

    # +8 damage
    'Carnage': 8,

    # +10 damage
    'Bludgeon': 10,
    'Through Violence': 10,
}

BLOCK_UPGRADE_BONUS = {
    # Ironclad
    'Defend': 3,
    'Shrug It Off': 3,
    'Ghostly Armor': 3,
    'Power Through': 5,
    'Iron Wave': 2,
    'Sentinel': 3,
    'True Grit': 2,
    'Flame Barrier': 4,
    'Impervious': 10,

    # Colorless
    'Finesse': 2,
    'Good Instincts': 3,
    'Panic Button': 10,
    'Safety': 4,

    # Silent
    'Survivor': 3,
    'Backflip': 3,
    'Deflect': 3,
    'Dodge and Roll': 2,
    'Blur': 3,
    'Leg Sweep': 3,

    # Defect
    'Charge Battery': 3,
    'Hologram': 2,
    'Leap': 3,
    'Steam Barrier': 2,
    'Boot Sequence': 3,
    'Equilibrium': 3,
    'Force Field': 4,
    'Glacier': 3,
    'Reinforced Body': 2,
}


def _upgrade_count_from_name(card: Any) -> int:
    candidates = []
    if isinstance(card, str):
        candidates.append(card)
    candidates.extend(
        getattr(card, attr, None)
        for attr in ('name', 'card_id', 'id')
    )
    for candidate in candidates:
        if candidate is None:
            continue
        match = _UPGRADE_SUFFIX_RE.search(str(candidate))
        if match:
            return int(match.group(1) or 1)
    return 0


def card_upgrade_count(card: Any) -> int:
    """Return a non-negative integer upgrade count for partially populated card objects."""
    parsed = 0
    try:
        parsed = max(0, int(getattr(card, 'upgrades', 0) or 0))
    except (TypeError, ValueError):
        parsed = 0
    return parsed or _upgrade_count_from_name(card)


def is_card_upgraded(card: Any) -> bool:
    return card_upgrade_count(card) > 0


def known_damage_upgrade_bonus(card: Any, card_name: str) -> int:
    upgrades = card_upgrade_count(card)
    if upgrades <= 0:
        return 0
    if card_name == 'Searing Blow':
        return upgrades * (upgrades + 7) // 2
    return DAMAGE_UPGRADE_BONUS.get(card_name, 0)


def known_block_upgrade_bonus(card: Any, card_name: str) -> int:
    if card_upgrade_count(card) <= 0:
        return 0
    return BLOCK_UPGRADE_BONUS.get(card_name, 0)


def heavy_blade_strength_multiplier(card: Any) -> int:
    return 5 if is_card_upgraded(card) else 3


def perfected_strike_bonus_per_strike(card: Any) -> int:
    return 3 if is_card_upgraded(card) else 2
