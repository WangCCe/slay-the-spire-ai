import math


def coerce_float(value, default=0.0):
    if value is None:
        return default
    try:
        coerced = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(coerced):
        return default
    return coerced


def coerce_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default
