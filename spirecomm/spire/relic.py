def _safe_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default


class Relic:

    def __init__(self, relic_id, name, counter=0, price=0):
        self.relic_id = relic_id
        self.name = name
        self.counter = counter
        self.price = price

    @classmethod
    def from_json(cls, json_object):
        return cls(
            json_object["id"],
            json_object["name"],
            _safe_int(json_object["counter"], 0),
            _safe_int(json_object.get("price", 0), 0),
        )
