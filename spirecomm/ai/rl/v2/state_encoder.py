"""
State encoder for RL v2.
"""

from typing import List
import numpy as np

from spirecomm.spire.game import Game
from spirecomm.spire.identifiers import potion_id, relic_id
from spirecomm.spire.card import Card
from spirecomm.spire.character import Intent
from spirecomm.spire.numeric import coerce_float
from spirecomm.spire.screen import ScreenType
from spirecomm.ai.heuristics.card_costs import raw_card_cost
from spirecomm.ai.heuristics.card_types import card_is_playable, card_type_name
from spirecomm.ai.heuristics.card_upgrades import is_card_upgraded
from spirecomm.ai.heuristics.combat_state import power_matches
from spirecomm.ai.heuristics.potions import game_real_potions
from spirecomm.ai.intent_utils import intent_is_attack, intent_tokens

from .id_mapping import IdMapper, load_default_id_mapper
from .monster_slots import compact_monster_slots, is_targetable_monster
from .types import EncodedStateV2


class StateEncoderV2:
    CARD_SLOTS = 10
    POTION_SLOTS = 5
    RELIC_SLOTS = 40
    MONSTER_SLOTS = 5
    ENERGY_RATIO_INDEX = 1

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
        energy = max(self._safe_float(getattr(player, "energy", 0), 0.0), 0.0)
        block = max(self._safe_float(getattr(player, "block", 0), 0.0), 0.0)
        floor = max(self._safe_float(getattr(game, "floor", 0), 0.0), 0.0)
        energy_ratio = min(energy, 5) / 5.0
        block_ratio = min(block, 100) / 100.0
        floor_ratio = min(floor, 50) / 50.0

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
        monsters = [
            monster
            for _, monster in compact_monster_slots(game, self.MONSTER_SLOTS)
        ]
        for idx in range(self.MONSTER_SLOTS):
            if idx < len(monsters):
                features.extend(self._encode_monster(monsters[idx]))
            else:
                features.extend([0.0] * self.MONSTER_FEATURES)
        return features

    def _encode_monster(self, monster) -> List[float]:
        max_hp = max(self._safe_float(getattr(monster, "max_hp", 0), 0.0), 0.0)
        current_hp = max(self._safe_float(getattr(monster, "current_hp", 0), 0.0), 0.0)
        hp_ratio = self._safe_ratio(current_hp, max_hp, 1.0)
        block = max(self._safe_float(getattr(monster, "block", 0), 0.0), 0.0)
        block_ratio = min(block, 100) / 100.0
        is_alive = 1.0 if is_targetable_monster(monster) else 0.0

        intent = self._normalize_intent(getattr(monster, "intent", Intent.UNKNOWN))
        intent_one_hot = [1.0 if intent == value else 0.0 for value in self.INTENT_ORDER]

        move_damage = self._safe_float(getattr(monster, "move_adjusted_damage", 0), 0.0)
        move_hits = max(self._safe_float(getattr(monster, "move_hits", 0), 0.0), 0.0)
        intent_damage = np.tanh(move_damage / 50.0)
        intent_hits = min(move_hits, 10) / 10.0

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
        is_upgraded = 1.0 if is_card_upgraded(card) else 0.0
        cost = raw_card_cost(card)
        if cost < 0:
            cost_norm = 1.0
        else:
            cost_norm = min(cost, 5) / 5.0
        is_playable = 1.0 if card_is_playable(card) else 0.0
        type_one_hot = self._encode_card_type(card)
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
        raw_potions = getattr(game, "potions", None)
        potions = raw_potions if raw_potions is not None else game_real_potions(game)
        potions = potions or []
        for idx in range(min(len(potions), self.POTION_SLOTS)):
            potion = potions[idx]
            potion_key = potion_id(potion)
            if potion_key == "Potion Slot":
                ids[idx] = 0
            else:
                ids[idx] = self.id_mapper.potion_id(potion_key)
        return ids

    def _encode_relic_ids(self, game: Game) -> List[int]:
        ids = [0] * self.RELIC_SLOTS
        relics = game.relics or []
        for idx in range(min(len(relics), self.RELIC_SLOTS)):
            relic = relics[idx]
            ids[idx] = self.id_mapper.relic_id(relic_id(relic))
        return ids

    def _encode_card_tags(self, card: Card) -> List[float]:
        card_id = getattr(card, "card_id", None) or getattr(card, "name", None)
        tags = self.id_mapper.card_tag_list(card_id)
        return [1.0 if tag in tags else 0.0 for tag in self.TAGS]

    def _encode_card_type(self, card_type) -> List[float]:
        normalized_card_type = card_type_name(card_type)
        return [
            1.0 if normalized_card_type == "ATTACK" else 0.0,
            1.0 if normalized_card_type == "SKILL" else 0.0,
            1.0 if normalized_card_type == "POWER" else 0.0,
            1.0 if normalized_card_type in ("STATUS", "CURSE") else 0.0,
        ]

    def _encode_player_class(self, player_class) -> List[float]:
        player_class_name = self._player_class_name(player_class)
        return [
            1.0 if player_class_name == "IRONCLAD" else 0.0,
            1.0 if player_class_name == "THE_SILENT" else 0.0,
            1.0 if player_class_name == "DEFECT" else 0.0,
            1.0 if player_class_name == "WATCHER" else 0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

    @staticmethod
    def _player_class_name(player_class) -> str:
        if player_class is None:
            return ""
        if hasattr(player_class, "name"):
            return str(player_class.name).upper()
        value = str(player_class).upper()
        if value.startswith("PLAYERCLASS."):
            return value.split(".", 1)[1]
        return value

    def _encode_keyword(self, powers, keyword_name: str) -> float:
        power_ids = self.KEYWORD_POWER_IDS.get(keyword_name, [])
        amount = 0.0
        for power in powers or []:
            if any(power_matches(power, power_id) for power_id in power_ids):
                amount = self._safe_float(getattr(power, "amount", 0), 0.0)
                break
        if keyword_name in ("Strength", "Dexterity"):
            return float(np.tanh(amount / 10.0))
        return min(max(amount, 0), 20) / 20.0

    @staticmethod
    def _safe_ratio(numerator, denominator, default: float) -> float:
        numerator = StateEncoderV2._safe_float(numerator, 0.0)
        denominator = StateEncoderV2._safe_float(denominator, 0.0)
        if denominator is None or denominator <= 0:
            return default
        return min(max(numerator, 0), denominator) / float(denominator)

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        return coerce_float(value, default)
