from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)

_UPGRADE_SUFFIX_RE = re.compile(r"\+(\d*)$")


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


class CardType(Enum):
    ATTACK = 1
    SKILL = 2
    POWER = 3
    STATUS = 4
    CURSE = 5


class CardRarity(Enum):
    BASIC = 1
    COMMON = 2
    UNCOMMON = 3
    RARE = 4
    SPECIAL = 5
    CURSE = 6


class Card:
    def __init__(self, card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, cost_for_turn=None, uuid="", misc=0, price=0, is_playable=False, exhausts=False):
        self.card_id = card_id
        self.name = name
        self.type = card_type
        self.rarity = rarity
        self.upgrades = upgrades
        self.has_target = has_target
        self.cost = cost
        self.cost_for_turn = cost_for_turn if cost_for_turn is not None else cost  # Actual cost this turn (for Snecko Eye, etc.)
        self.uuid = uuid
        self.misc = misc
        self.price = price
        self.is_playable = is_playable
        self.exhausts = exhausts

    @classmethod
    def from_json(cls, json_object):
        upgrades = max(0, _safe_int(json_object.get("upgrades", 0) or 0, 0))
        name = json_object.get("name", "")
        upgrade_suffix = _UPGRADE_SUFFIX_RE.search(name)
        if upgrades == 0 and upgrade_suffix:
            upgrades = int(upgrade_suffix.group(1) or 1)
            logger.info(f"[CARD_UPGRADE_FIX] name='{name}' indicates upgrade; treating upgrades={upgrades}")
        return cls(
            card_id=json_object["id"],
            name=name,
            card_type=CardType[json_object["type"]],
            rarity=CardRarity[json_object["rarity"]],
            upgrades=upgrades,
            has_target=json_object["has_target"],
            cost=json_object["cost"],
            cost_for_turn=json_object.get("costForTurn"),  # Actual cost this turn (modified by relics like Snecko Eye)
            uuid=json_object["uuid"],
            misc=json_object.get("misc", 0),
            price=json_object.get("price", 0),
            is_playable=json_object.get("is_playable", False),
            exhausts=json_object.get("exhausts", False)
        )

    def __eq__(self, other):
        # Handle case where other is not a Card object (e.g., primitive type)
        if not hasattr(other, 'uuid'):
            return False
        return self.uuid == other.uuid
