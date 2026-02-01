"""
Stable categorical ID mappings for RL v2.
"""

from dataclasses import dataclass
import json
import logging
import os
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def _sorted_unique(values: Iterable[str]) -> List[str]:
    return sorted({v for v in values if v})


def _extract_ids(items: List[dict], keys: List[str]) -> List[str]:
    ids = []
    for item in items:
        for key in keys:
            value = item.get(key)
            if value:
                ids.append(str(value))
                break
    return ids


@dataclass(frozen=True)
class IdMapper:
    card_ids: Dict[str, int]
    potion_ids: Dict[str, int]
    relic_ids: Dict[str, int]
    card_tags: Dict[str, List[str]]

    def card_id(self, raw_id: Optional[str]) -> int:
        return self.card_ids.get(str(raw_id), 0) if raw_id else 0

    def potion_id(self, raw_id: Optional[str]) -> int:
        return self.potion_ids.get(str(raw_id), 0) if raw_id else 0

    def relic_id(self, raw_id: Optional[str]) -> int:
        return self.relic_ids.get(str(raw_id), 0) if raw_id else 0

    @property
    def card_vocab_size(self) -> int:
        return max(self.card_ids.values(), default=0) + 1

    @property
    def potion_vocab_size(self) -> int:
        return max(self.potion_ids.values(), default=0) + 1

    @property
    def relic_vocab_size(self) -> int:
        return max(self.relic_ids.values(), default=0) + 1


def build_id_mapper(items_json_path: Optional[str]) -> IdMapper:
    if not items_json_path:
        logger.warning("No items.json path provided; using empty ID mappings.")
        return IdMapper(card_ids={}, potion_ids={}, relic_ids={}, card_tags={})

    if not os.path.exists(items_json_path):
        logger.warning("items.json not found at %s; using empty ID mappings.", items_json_path)
        return IdMapper(card_ids={}, potion_ids={}, relic_ids={}, card_tags={})

    try:
        with open(items_json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        logger.warning("Failed to read items.json from %s: %s", items_json_path, exc)
        return IdMapper(card_ids={}, potion_ids={}, relic_ids={}, card_tags={})

    cards_payload = payload.get("cards", [])
    card_values = _extract_ids(cards_payload, ["id", "name"])
    potion_values = _extract_ids(payload.get("potions", []), ["id", "name"])
    relic_values = _extract_ids(payload.get("relics", []), ["id", "name"])

    card_ids = {card_id: idx + 1 for idx, card_id in enumerate(_sorted_unique(card_values))}
    potion_ids = {potion_id: idx + 1 for idx, potion_id in enumerate(_sorted_unique(potion_values))}
    relic_ids = {relic_id: idx + 1 for idx, relic_id in enumerate(_sorted_unique(relic_values))}

    card_tags = _extract_card_tags(cards_payload)

    return IdMapper(
        card_ids=card_ids,
        potion_ids=potion_ids,
        relic_ids=relic_ids,
        card_tags=card_tags,
    )


def default_items_json_path() -> Optional[str]:
    env_path = os.environ.get("STS_ITEMS_JSON")
    if env_path:
        return env_path

    for candidate in ("export/items.json", os.path.join("export", "items.json")):
        if os.path.exists(candidate):
            return candidate

    return None


def load_default_id_mapper() -> IdMapper:
    return build_id_mapper(default_items_json_path())


def _extract_card_tags(cards: List[dict]) -> Dict[str, List[str]]:
    tags = {}
    for card in cards:
        card_id = card.get("id") or card.get("name")
        if not card_id:
            continue
        description = (card.get("description") or "").lower()
        card_tags = []
        if "all enemy" in description or "all enemies" in description:
            card_tags.append("AOE")
        if "draw" in description:
            card_tags.append("Draw")
        if "energy" in description:
            card_tags.append("Energy")
        if "exhaust" in description:
            card_tags.append("Exhaust")
        if "ethereal" in description:
            card_tags.append("Ethereal")
        if "retain" in description:
            card_tags.append("Retain")
        if "innate" in description:
            card_tags.append("Innate")
        tags[str(card_id)] = card_tags
    return tags
