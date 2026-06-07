"""Helpers for detecting card exhaust behavior used by lightweight estimators."""

import re
from typing import Any, Optional

from .card_names import canonical_card_name


def _truthy_exhaust_flag(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def description_exhausts_itself(description: Any) -> bool:
    text = str(description or "").replace("\\n", "\n").lower().replace("#", "").strip()
    if not text:
        return False
    if any(line.strip() in {"exhaust", "exhaust."} for line in text.splitlines()):
        return True
    return bool(re.search(r"\bexhaust\.\s*$", text))


def card_exhausts_itself(card: Any, data_loader: Optional[Any] = None) -> bool:
    """Return whether playing this card directly exhausts the card itself."""
    if _truthy_exhaust_flag(getattr(card, "exhausts", False)):
        return True

    for attr_name in ("description", "raw_description", "text"):
        if description_exhausts_itself(getattr(card, attr_name, None)):
            return True

    if data_loader is None:
        return False

    try:
        card_data = data_loader.get_card_data(canonical_card_name(card)) or {}
    except Exception:
        return False

    for key in ("description", "raw_description", "rawDescription", "text"):
        if description_exhausts_itself(card_data.get(key)):
            return True

    return False
