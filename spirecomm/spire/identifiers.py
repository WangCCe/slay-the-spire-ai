def potion_id(potion):
    return (
        getattr(potion, "potion_id", None)
        or getattr(potion, "name", None)
        or getattr(potion, "id", None)
        or potion
    )


def relic_id(relic):
    return (
        getattr(relic, "relic_id", None)
        or getattr(relic, "name", None)
        or getattr(relic, "id", None)
        or relic
    )
