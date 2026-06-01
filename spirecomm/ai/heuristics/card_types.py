"""Helpers for card type values that may arrive as enums or strings."""


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
