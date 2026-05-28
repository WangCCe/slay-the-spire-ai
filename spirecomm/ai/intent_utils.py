from spirecomm.spire.character import Intent


def intent_is_unknown(intent) -> bool:
    if intent is None:
        return False
    if intent in (Intent.NONE, Intent.UNKNOWN):
        return True

    return str(intent).upper() in (
        "NONE",
        "INTENT.NONE",
        "UNKNOWN",
        "INTENT.UNKNOWN",
    )


def intent_is_attack(intent) -> bool:
    if intent is None:
        return False
    if hasattr(intent, "is_attack"):
        return intent.is_attack()

    return "ATTACK" in str(intent).upper()


def monster_intends_attack(monster, missing_intent_counts: bool = True) -> bool:
    if not hasattr(monster, "intent"):
        return missing_intent_counts

    intent = getattr(monster, "intent", None)
    if intent is None:
        return missing_intent_counts

    return intent_is_attack(intent)
