"""
State encoder for RL v2.
"""

from typing import List
import numpy as np

from spirecomm.spire.game import Game
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Intent, PlayerClass
from spirecomm.spire.screen import ScreenType
from spirecomm.ai.heuristics.card_costs import raw_card_cost
from spirecomm.ai.intent_utils import intent_is_attack, intent_tokens

from .id_mapping import IdMapper, load_default_id_mapper
from .types import EncodedStateV2


class StateEncoderV2:
    CARD_SLOTS = 10
    POTION_SLOTS = 5
    RELIC_SLOTS = 40
    MONSTER_SLOTS = 5

    PLAYER_FEATURES = 33
    MONSTER_FEATURES = 30
    HAND_FEATURES = 14
    CONTEXT_FEATURES = 5

    CONTINUOUS_DIM = (
        PLAYER_FEATURES
        + (MONSTER_SLOTS * MONSTER_FEATURES)
        + (CARD_SLOTS * HAND_FEATURES)
        + CONTEXT_FEATURES
    )

    KEYWORDS = [
        "Strength",
        "Dexterity",
        "Vulnerable",
        "Weak",
        "Frail",
        "Thorns",
        "Artifact",
        "Intangible",
        "Poison",
        "Regen",
        "Ritual",
        "Vigor",
        "Mantra",
        "Confused",
        "PlatedArmor",
        "Metallicize",
    ]

    KEYWORD_POWER_IDS = {
        "Strength": ["Strength"],
        "Dexterity": ["Dexterity"],
        "Vulnerable": ["Vulnerable"],
        "Weak": ["Weak"],
        "Frail": ["Frail"],
        "Thorns": ["Thorns"],
        "Artifact": ["Artifact"],
        "Intangible": ["Intangible", "IntangiblePlayer", "IntangiblePower"],
        "Poison": ["Poison"],
        "Regen": ["Regeneration", "Regen"],
        "Ritual": ["Ritual"],
        "Vigor": ["Vigor"],
        "Mantra": ["Mantra"],
        "Confused": ["Confusion", "Confused"],
        "PlatedArmor": ["PlatedArmor"],
        "Metallicize": ["Metallicize"],
    }

    TAGS = ["AOE", "Draw", "Energy", "Exhaust", "Ethereal", "Retain", "Innate"]

    INTENT_ORDER = [
        Intent.ATTACK,
        Intent.ATTACK_BUFF,
        Intent.ATTACK_DEBUFF,
        Intent.ATTACK_DEFEND,
        Intent.BUFF,
        Intent.DEBUFF,
        Intent.DEFEND,
        Intent.DEFEND_BUFF,
        Intent.DEFEND_DEBUFF,
    ]

    INTENT_ALIAS = {
        Intent.STRONG_DEBUFF: Intent.DEBUFF,
    }

    def __init__(self, id_mapper: IdMapper = None):
        self.feature_dim = self.CONTINUOUS_DIM
        self.id_mapper = id_mapper or load_default_id_mapper()

    def encode(self, game: Game) -> EncodedStateV2:
        features = []
        features.extend(self._encode_player(game))
        features.extend(self._encode_monsters(game))
        features.extend(self._encode_hand(game))
        features.extend(self._encode_context(game))

        continuous = np.array(features, dtype=np.float32)
        if continuous.size != self.CONTINUOUS_DIM:
            raise ValueError(
                f"StateEncoderV2 expected {self.CONTINUOUS_DIM} features, got {continuous.size}"
            )

        card_ids = np.array(self._encode_card_ids(game), dtype=np.int64)
        potion_ids = np.array(self._encode_potion_ids(game), dtype=np.int64)
        relic_ids = np.array(self._encode_relic_ids(game), dtype=np.int64)

        return EncodedStateV2(
            continuous=continuous,
            card_ids=card_ids,
            potion_ids=potion_ids,
            relic_ids=relic_ids,
        )

    def _encode_player(self, game: Game) -> List[float]:
        player = game.player
        if player is None:
            return [0.0] * self.PLAYER_FEATURES

        hp_ratio = self._safe_ratio(player.current_hp, player.max_hp, 1.0)
        energy_ratio = min(max(player.energy, 0), 5) / 5.0
        block_ratio = min(max(player.block, 0), 100) / 100.0
        floor_ratio = min(max(game.floor or 0, 0), 50) / 50.0

        keyword_values = [self._encode_keyword(player.powers, key) for key in self.KEYWORDS]

        draw_count = min(len(game.draw_pile or []), 100) / 100.0
        discard_count = min(len(game.discard_pile or []), 100) / 100.0
        exhaust_count = min(len(game.exhaust_pile or []), 100) / 100.0
        hand_count = min(len(game.hand or []), 100) / 100.0

        class_one_hot = self._encode_player_class(game.character)

        return [
            hp_ratio,
            energy_ratio,
            block_ratio,
            floor_ratio,
            *keyword_values,
            draw_count,
            discard_count,
            exhaust_count,
            hand_count,
            *class_one_hot,
        ]

    def _encode_monsters(self, game: Game) -> List[float]:
        features: List[float] = []
        monsters = game.monsters or []
        for idx in range(self.MONSTER_SLOTS):
            if idx < len(monsters):
                features.extend(self._encode_monster(monsters[idx]))
            else:
                features.extend([0.0] * self.MONSTER_FEATURES)
        return features

    def _encode_monster(self, monster) -> List[float]:
        max_hp = max(getattr(monster, "max_hp", 0) or 0, 0)
        current_hp = max(getattr(monster, "current_hp", 0) or 0, 0)
        hp_ratio = self._safe_ratio(current_hp, max_hp, 1.0)
        block_ratio = min(max(getattr(monster, "block", 0) or 0, 0), 100) / 100.0
        is_alive = 1.0 if current_hp > 0 and not getattr(monster, "is_gone", False) else 0.0

        intent = self._normalize_intent(getattr(monster, "intent", Intent.UNKNOWN))
        intent_one_hot = [1.0 if intent == value else 0.0 for value in self.INTENT_ORDER]

        intent_damage = np.tanh((getattr(monster, "move_adjusted_damage", 0) or 0) / 50.0)
        intent_hits = min(max(getattr(monster, "move_hits", 0) or 0, 0), 10) / 10.0

        keyword_values = [self._encode_keyword(monster.powers, key) for key in self.KEYWORDS]

        return [
            is_alive,
            hp_ratio,
            block_ratio,
            *intent_one_hot,
            intent_damage,
            intent_hits,
            *keyword_values,
        ]

    @classmethod
    def _normalize_intent(cls, intent):
        intent = cls.INTENT_ALIAS.get(intent, intent)
        if intent in cls.INTENT_ORDER:
            return intent

        tokens = intent_tokens(intent)
        if intent_is_attack(intent):
            if "BUFF" in tokens:
                return Intent.ATTACK_BUFF
            if "DEBUFF" in tokens:
                return Intent.ATTACK_DEBUFF
            if "DEFEND" in tokens or "BLOCK" in tokens:
                return Intent.ATTACK_DEFEND
            return Intent.ATTACK

        if "DEFEND" in tokens or "BLOCK" in tokens:
            if "BUFF" in tokens:
                return Intent.DEFEND_BUFF
            if "DEBUFF" in tokens:
                return Intent.DEFEND_DEBUFF
            return Intent.DEFEND
        if "DEBUFF" in tokens:
            return Intent.DEBUFF
        if "BUFF" in tokens:
            return Intent.BUFF
        return intent

    def _encode_hand(self, game: Game) -> List[float]:
        features: List[float] = []
        hand = game.hand or []
        for idx in range(self.CARD_SLOTS):
            if idx < len(hand):
                features.extend(self._encode_card_features(hand[idx]))
            else:
                features.extend([0.0] * self.HAND_FEATURES)
        return features

    def _encode_card_features(self, card: Card) -> List[float]:
        is_upgraded = 1.0 if getattr(card, "upgrades", 0) else 0.0
        cost = raw_card_cost(card)
        if cost < 0:
            cost_norm = 1.0
        else:
            cost_norm = min(cost, 5) / 5.0
        is_playable = 1.0 if getattr(card, "is_playable", False) else 0.0
        type_one_hot = self._encode_card_type(getattr(card, "type", None))
        tag_one_hot = self._encode_card_tags(card)

        return [
            is_upgraded,
            cost_norm,
            is_playable,
            *type_one_hot,
            *tag_one_hot,
        ]

    def _encode_context(self, game: Game) -> List[float]:
        screen_type = getattr(game, "screen_type", None)
        screen_one_hot = [0.0] * self.CONTEXT_FEATURES

        if screen_type in (None, ScreenType.NONE):
            if getattr(game, "in_combat", False):
                screen_one_hot[0] = 1.0  # COMBAT
        elif screen_type == ScreenType.MAP:
            screen_one_hot[1] = 1.0
        elif screen_type in (ScreenType.SHOP_SCREEN, ScreenType.SHOP_ROOM):
            screen_one_hot[2] = 1.0
        elif screen_type in (ScreenType.CARD_REWARD, ScreenType.COMBAT_REWARD, ScreenType.CHEST, ScreenType.BOSS_REWARD):
            screen_one_hot[3] = 1.0
        elif screen_type == ScreenType.REST:
            screen_one_hot[4] = 1.0

        return screen_one_hot

    def _encode_card_ids(self, game: Game) -> List[int]:
        ids = [0] * self.CARD_SLOTS
        hand = game.hand or []
        for idx in range(min(len(hand), self.CARD_SLOTS)):
            card_id = getattr(hand[idx], "card_id", None) or getattr(hand[idx], "name", None)
            ids[idx] = self.id_mapper.card_id(card_id)
        return ids

    def _encode_potion_ids(self, game: Game) -> List[int]:
        ids = [0] * self.POTION_SLOTS
        potions = game.potions or []
        for idx in range(min(len(potions), self.POTION_SLOTS)):
            potion = potions[idx]
            potion_id = getattr(potion, "potion_id", None) or getattr(potion, "name", None)
            if potion_id == "Potion Slot":
                ids[idx] = 0
            else:
                ids[idx] = self.id_mapper.potion_id(potion_id)
        return ids

    def _encode_relic_ids(self, game: Game) -> List[int]:
        ids = [0] * self.RELIC_SLOTS
        relics = game.relics or []
        for idx in range(min(len(relics), self.RELIC_SLOTS)):
            relic = relics[idx]
            relic_id = getattr(relic, "relic_id", None) or getattr(relic, "name", None)
            ids[idx] = self.id_mapper.relic_id(relic_id)
        return ids

    def _encode_card_tags(self, card: Card) -> List[float]:
        card_id = getattr(card, "card_id", None) or getattr(card, "name", None)
        tags = self.id_mapper.card_tag_list(card_id)
        return [1.0 if tag in tags else 0.0 for tag in self.TAGS]

    def _encode_card_type(self, card_type) -> List[float]:
        return [
            1.0 if card_type == CardType.ATTACK else 0.0,
            1.0 if card_type == CardType.SKILL else 0.0,
            1.0 if card_type == CardType.POWER else 0.0,
            1.0 if card_type in (CardType.STATUS, CardType.CURSE) else 0.0,
        ]

    def _encode_player_class(self, player_class) -> List[float]:
        return [
            1.0 if player_class == PlayerClass.IRONCLAD else 0.0,
            1.0 if player_class == PlayerClass.THE_SILENT else 0.0,
            1.0 if player_class == PlayerClass.DEFECT else 0.0,
            1.0 if str(player_class) == "PlayerClass.WATCHER" else 0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

    def _encode_keyword(self, powers, keyword_name: str) -> float:
        power_ids = self.KEYWORD_POWER_IDS.get(keyword_name, [])
        amount = 0.0
        for power in powers or []:
            power_id = getattr(power, "power_id", None)
            power_name = getattr(power, "power_name", None)
            if (power_id in power_ids) or (power_name in power_ids):
                amount = getattr(power, "amount", 0) or 0
                break
        if keyword_name in ("Strength", "Dexterity"):
            return float(np.tanh(amount / 10.0))
        return min(max(amount, 0), 20) / 20.0

    @staticmethod
    def _safe_ratio(numerator, denominator, default: float) -> float:
        if denominator is None or denominator <= 0:
            return default
        return min(max(numerator, 0), denominator) / float(denominator)
