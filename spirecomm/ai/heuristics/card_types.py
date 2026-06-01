"""Helpers for card type values that may arrive as enums or strings."""

from .card_names import canonical_card_name


COMMON_AOE_ATTACK_NAMES = frozenset(
    [
        "Cleave",
        "Whirlwind",
        "Immolate",
        "Thunderclap",
        "Reaper",
        "Dagger Spray",
        "Die Die Die",
        "All Out Attack",
        "Sweeping Beam",
        "Doom and Gloom",
        "Hyperbeam",
        "Conclude",
        "Consecrate",
    ]
)

COMMON_UNTARGETED_ATTACK_NAMES = COMMON_AOE_ATTACK_NAMES | frozenset(
    [
        "Sword Boomerang",
        "Blizzard",
        "Thunder Strike",
        "Ragnarok",
        "Dramatic Entrance",
    ]
)


def card_type_name(card_or_type) -> str:
    """Return a normalized card type name such as ``ATTACK`` or ``SKILL``."""
    if card_or_type is None:
        return ""
    card_type = getattr(card_or_type, "type", card_or_type)
    if card_type is None:
        return ""
    if hasattr(card_type, "name"):
        return str(card_type.name).upper()
    value = str(card_type).upper()
    if value.startswith("CARDTYPE."):
        return value.split(".", 1)[1]
    return value


def is_card_type(card_or_type, expected_type) -> bool:
    return card_type_name(card_or_type) == card_type_name(expected_type)


def is_attack_card(card_or_type) -> bool:
    return is_card_type(card_or_type, "ATTACK")


def card_requires_target(card, aoe_attack_names=None) -> bool:
    is_attack = is_attack_card(card)
    untargeted_attack_names = COMMON_UNTARGETED_ATTACK_NAMES | set(aoe_attack_names or ())
    if is_attack and canonical_card_name(card) in untargeted_attack_names:
        return False

    explicit_target_flag = getattr(card, "has_target", None)
    if explicit_target_flag is not None:
        return bool(explicit_target_flag)

    if not is_attack:
        return False

    return True
