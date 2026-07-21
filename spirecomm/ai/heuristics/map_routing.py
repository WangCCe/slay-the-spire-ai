"""
Adaptive map router with HP-aware decision making.

Implements expert strategies for map navigation:
- Act 1: Aggressive (take 2-3 elites, Ironclad is strongest early)
- Act 2+: Conservative (avoid elites unless high HP)
- Dynamic rest site priority based on HP
- Smart campfire choices
"""

import sys
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from ..decision.base import DecisionContext
from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_upgrades import card_upgrade_count, is_card_upgraded
from spirecomm.ai.heuristics.potions import game_real_potions, potion_can_use
from spirecomm.spire.identifiers import relic_id
from spirecomm.spire.map import Node
from spirecomm.spire.screen import RestOption


ADAPTIVE_SUPPORTED_CHARACTER = "IRONCLAD"
ADAPTIVE_MIN_ABSOLUTE_HP = 48
ADAPTIVE_MIN_HP_PCT = 0.75
ADAPTIVE_RECOVERY_EXCEPTION_HP_PCT = 0.90
ADAPTIVE_MIN_ELITE_LOCAL_FLOOR = 6
ADAPTIVE_MIN_DECK_READINESS = 5
ADAPTIVE_EXCEPTIONAL_DECK_READINESS = 7
ADAPTIVE_MAX_RESOURCE_SUPPORT = 2
ADAPTIVE_MAX_RECOVERY_DISTANCE = 2
ADAPTIVE_COMBAT_POTION_NAMES = (
    "Fire Potion", "Attack Potion", "Strength Potion", "Flex Potion",
    "Dexterity Potion", "Skill Potion", "Power Potion", "Fear Potion",
    "Duplication Potion", "Distilled Chaos", "Explosive Potion",
    "Swift Potion", "Energy Potion", "Entropic Brew",
)
ADAPTIVE_RELIC_SUPPORT_WEIGHTS = {
    "Preserved Insect": 2,
    "Akabeko": 1,
    "Vajra": 1,
    "Bag of Marbles": 1,
    "Anchor": 1,
    "Orichalcum": 1,
    "Oddly Smooth Stone": 1,
    "Lantern": 1,
    "Blood Vial": 1,
    "Meat on the Bone": 1,
}
ADAPTIVE_ROUTE_SYMBOLS = frozenset(("M", "E", "$", "?", "T", "R"))


@dataclass(frozen=True)
class AdaptiveRouteState:
    player_class: str
    act: int
    current_hp: int
    max_hp: int
    hp_pct: float
    deck_readiness: int
    potion_support: int
    relic_support: int
    elite_seen: bool
    last_rest_floor: Optional[int]


@dataclass(frozen=True)
class RouteCandidateFeatures:
    mode: str
    path: Tuple[int, ...]
    symbols: Tuple[str, ...]
    elite_floors: Tuple[int, ...]
    first_elite_index: Optional[int]
    rest_before_distance: Optional[int]
    rest_after_distance: Optional[int]


@dataclass(frozen=True)
class AdaptiveEliteAssessment:
    allowed: bool
    optional_elite_budget: int
    reasons: Tuple[str, ...]


class AdaptiveMapRouter:
    """
    HP-aware map routing for all character classes.

    Key principles:
    - Act 1: Take elites when HP is good (character-specific advantages)
    - Act 2+: Be more conservative with elites
    - Rest sites are critical when HP < 50%
    - Avoid ? events that might be risky when low HP
    """

    # Base node priorities (from SimpleAgent)
    BASE_NODE_PRIORITIES = {
        'M': 50,      # Monster
        'E': -10,     # Elite (risky by default)
        '$': 100,     # Shop
        '?': 75,      # Unknown
        'T': 75,      # Treasure
        'R': 25,      # Rest
    }

    ACT1_PREMIUM_ATTACKS = {
        "Pommel Strike", "Anger", "Clothesline", "Uppercut",
        "Hemokinesis", "Carnage", "Cleave", "Headbutt",
        "Twin Strike", "Whirlwind", "Iron Wave", "Perfected Strike",
        "Immolate", "Bludgeon", "Sever Soul", "Wild Strike",
    }

    ACT1_STRONG_BLOCKS = {
        "Shrug It Off", "Flame Barrier", "Power Through",
        "Ghostly Armor", "Metallicize", "Impervious", "Disarm",
    }

    def __init__(self, player_class='IRONCLAD', elite_mode: str = None):
        """Initialize map router.

        Args:
            player_class: Character class (IRONCLAD, THE_SILENT, THE_DEFECT)
            elite_mode: Elite routing strategy ("conservative" or "aggressive", default: "aggressive")
        """
        self.player_class = player_class
        self.elite_mode = (elite_mode or "aggressive").lower()
        logging.getLogger(__name__).info(
            "[MAP_ROUTING] elite_mode=%s (player_class=%s)",
            self.elite_mode,
            self.player_class,
        )

    @staticmethod
    def _card_name(card) -> str:
        return canonical_card_name(card)

    @staticmethod
    def _compact_identifier(value) -> str:
        return "".join(ch for ch in str(value or "") if ch.isalnum()).lower()

    @staticmethod
    def _non_negative_float(value) -> float:
        try:
            return max(0.0, float(value or 0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _non_negative_int(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    def adaptive_deck_readiness(self, context: DecisionContext) -> int:
        """Return the adaptive policy's deck-only Act 1 readiness score."""
        game = getattr(context, "game", None)
        deck = list(getattr(game, "deck", []) or [])
        card_names = [self._card_name(card) for card in deck]
        upgraded_ids = {
            self._card_name(card)
            for card in deck
            if is_card_upgraded(card)
        }
        return (
            min(4, sum(name in self.ACT1_PREMIUM_ATTACKS for name in card_names))
            + min(2, sum(name in self.ACT1_STRONG_BLOCKS for name in card_names))
            + int("Bash" in upgraded_ids)
        )

    def adaptive_potion_support(self, context: DecisionContext) -> int:
        """Count usable, real combat potions for the adaptive policy."""
        game = getattr(context, "game", context)
        allowed = {
            self._compact_identifier(potion_name)
            for potion_name in ADAPTIVE_COMBAT_POTION_NAMES
        }
        return min(
            ADAPTIVE_MAX_RESOURCE_SUPPORT,
            sum(
                1
                for potion in game_real_potions(game)
                if potion_can_use(potion)
                and (
                    self._compact_identifier(getattr(potion, "potion_id", "")) in allowed
                    or self._compact_identifier(getattr(potion, "name", "")) in allowed
                )
            ),
        )

    def adaptive_relic_support(self, relics) -> int:
        """Return capped support from the baseline's explicit relic allowlist."""
        weights = {
            self._compact_identifier(name): weight
            for name, weight in ADAPTIVE_RELIC_SUPPORT_WEIGHTS.items()
        }
        return min(
            ADAPTIVE_MAX_RESOURCE_SUPPORT,
            sum(
                weights.get(self._compact_identifier(relic_id(relic)), 0)
                for relic in (relics or [])
            ),
        )

    def build_adaptive_state(
            self,
            context: DecisionContext,
            *,
            elite_seen: bool = False,
            last_rest_floor: Optional[int] = None,
    ) -> AdaptiveRouteState:
        """Normalize the current game state without selecting a route."""
        game = getattr(context, "game", None)
        current_hp = self._non_negative_int(getattr(game, "current_hp", 0))
        max_hp = self._non_negative_int(getattr(game, "max_hp", 0))
        hp_pct = current_hp / max_hp if max_hp else 0.0
        normalized_last_rest_floor = None
        if last_rest_floor is not None:
            try:
                normalized_last_rest_floor = int(last_rest_floor)
            except (TypeError, ValueError):
                normalized_last_rest_floor = -1
        return AdaptiveRouteState(
            player_class=str(self.player_class or "").upper(),
            act=self._non_negative_int(getattr(context, "act", 0)),
            current_hp=current_hp,
            max_hp=max_hp,
            hp_pct=hp_pct,
            deck_readiness=self.adaptive_deck_readiness(context),
            potion_support=self.adaptive_potion_support(context),
            relic_support=self.adaptive_relic_support(getattr(game, "relics", []) or []),
            elite_seen=bool(elite_seen),
            last_rest_floor=normalized_last_rest_floor,
        )

    def describe_candidate(self, mode, path, symbols) -> RouteCandidateFeatures:
        """Describe a candidate from its own inputs without touching route state."""
        normalized_path = self._normalize_adaptive_path(path)
        normalized_symbols = self._normalize_adaptive_symbols(symbols)
        if normalized_path is None or normalized_symbols is None:
            normalized_path = tuple()
            normalized_symbols = tuple()

        elite_indexes = tuple(
            index for index, symbol in enumerate(normalized_symbols)
            if symbol == "E"
        )
        first_elite_index = elite_indexes[0] if elite_indexes else None
        rest_before_distance = None
        rest_after_distance = None
        if first_elite_index is not None:
            prior_rests = [
                index for index, symbol in enumerate(normalized_symbols[:first_elite_index])
                if symbol == "R"
            ]
            later_rests = [
                index
                for index, symbol in enumerate(normalized_symbols[first_elite_index + 1:], first_elite_index + 1)
                if symbol == "R"
            ]
            if prior_rests:
                rest_before_distance = first_elite_index - prior_rests[-1]
            if later_rests:
                rest_after_distance = later_rests[0] - first_elite_index

        return RouteCandidateFeatures(
            mode=str(mode or "").lower(),
            path=normalized_path,
            symbols=normalized_symbols,
            elite_floors=tuple(index + 1 for index in elite_indexes),
            first_elite_index=first_elite_index,
            rest_before_distance=rest_before_distance,
            rest_after_distance=rest_after_distance,
        )

    @staticmethod
    def _normalize_adaptive_path(path) -> Optional[Tuple[int, ...]]:
        try:
            values = tuple(path)
        except TypeError:
            return None
        normalized = []
        for value in values:
            if isinstance(value, bool):
                return None
            try:
                coordinate = int(value)
            except (TypeError, ValueError):
                return None
            if coordinate < 0 or (isinstance(value, float) and not value.is_integer()):
                return None
            normalized.append(coordinate)
        return tuple(normalized)

    @staticmethod
    def _normalize_adaptive_symbols(symbols) -> Optional[Tuple[str, ...]]:
        try:
            values = tuple(symbols)
        except TypeError:
            return None
        if not all(isinstance(symbol, str) and symbol in ADAPTIVE_ROUTE_SYMBOLS for symbol in values):
            return None
        return values

    @staticmethod
    def _adaptive_assessment(allowed: bool, reason: str) -> AdaptiveEliteAssessment:
        return AdaptiveEliteAssessment(
            allowed=allowed,
            optional_elite_budget=int(allowed),
            reasons=(reason,),
        )

    def assess_optional_elite(
            self,
            state: AdaptiveRouteState,
            conservative: RouteCandidateFeatures,
            aggressive: RouteCandidateFeatures,
    ) -> AdaptiveEliteAssessment:
        """Apply the ordered, fail-closed adaptive optional-elite gates."""
        if not isinstance(state, AdaptiveRouteState) or state.player_class != ADAPTIVE_SUPPORTED_CHARACTER:
            return self._adaptive_assessment(False, "unsupported_character")
        if isinstance(state.act, int) and not isinstance(state.act, bool) and state.act >= 2:
            return self._adaptive_assessment(False, "later_act_optional_elite")
        if not self._valid_adaptive_state(state) or not self._valid_adaptive_candidate(conservative) \
                or not self._valid_adaptive_candidate(aggressive):
            return self._adaptive_assessment(False, "malformed_state")
        if state.current_hp < ADAPTIVE_MIN_ABSOLUTE_HP:
            return self._adaptive_assessment(False, "hp_below_absolute_floor")
        if state.hp_pct < ADAPTIVE_MIN_HP_PCT:
            return self._adaptive_assessment(False, "hp_below_relative_floor")
        if aggressive.first_elite_index is not None \
                and aggressive.elite_floors[0] < ADAPTIVE_MIN_ELITE_LOCAL_FLOOR:
            return self._adaptive_assessment(False, "elite_before_local_floor")
        if state.deck_readiness < ADAPTIVE_MIN_DECK_READINESS:
            return self._adaptive_assessment(False, "deck_not_ready")
        if state.potion_support < 1 \
                and state.deck_readiness < ADAPTIVE_EXCEPTIONAL_DECK_READINESS \
                and state.relic_support < ADAPTIVE_MAX_RESOURCE_SUPPORT:
            return self._adaptive_assessment(False, "resource_support_missing")
        if state.elite_seen:
            return self._adaptive_assessment(False, "elite_already_seen")
        if len(conservative.elite_floors) != 0 or len(aggressive.elite_floors) != 1:
            return self._adaptive_assessment(False, "candidate_counts_not_zero_vs_one")
        has_recovery = (
            (aggressive.rest_before_distance is not None
             and aggressive.rest_before_distance <= ADAPTIVE_MAX_RECOVERY_DISTANCE)
            or (aggressive.rest_after_distance is not None
                and aggressive.rest_after_distance <= ADAPTIVE_MAX_RECOVERY_DISTANCE)
        )
        recovery_exception = (
            state.hp_pct >= ADAPTIVE_RECOVERY_EXCEPTION_HP_PCT
            and state.deck_readiness == ADAPTIVE_EXCEPTIONAL_DECK_READINESS
            and state.potion_support >= 1
        )
        if not has_recovery and not recovery_exception:
            return self._adaptive_assessment(False, "recovery_window_missing")
        return self._adaptive_assessment(True, "optional_elite_allowed")

    @staticmethod
    def _valid_adaptive_state(state: AdaptiveRouteState) -> bool:
        if state.act != 1 or not isinstance(state.elite_seen, bool):
            return False
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (
                state.current_hp,
                state.max_hp,
                state.deck_readiness,
                state.potion_support,
                state.relic_support,
        )):
            return False
        if state.max_hp <= 0 or state.current_hp < 0 or state.current_hp > state.max_hp:
            return False
        if not isinstance(state.hp_pct, (int, float)) or not 0.0 <= state.hp_pct <= 1.0:
            return False
        if abs(state.hp_pct - (state.current_hp / state.max_hp)) > 0.000001:
            return False
        if not 0 <= state.deck_readiness <= ADAPTIVE_EXCEPTIONAL_DECK_READINESS:
            return False
        if not 0 <= state.potion_support <= ADAPTIVE_MAX_RESOURCE_SUPPORT:
            return False
        if not 0 <= state.relic_support <= ADAPTIVE_MAX_RESOURCE_SUPPORT:
            return False
        return state.last_rest_floor is None or (
            isinstance(state.last_rest_floor, int) and state.last_rest_floor >= 0
        )

    @staticmethod
    def _valid_adaptive_candidate(candidate: RouteCandidateFeatures) -> bool:
        if not isinstance(candidate, RouteCandidateFeatures):
            return False
        if not candidate.path or len(candidate.path) != len(candidate.symbols):
            return False
        elite_indexes = tuple(
            index for index, symbol in enumerate(candidate.symbols)
            if symbol == "E"
        )
        if candidate.elite_floors != tuple(index + 1 for index in elite_indexes):
            return False
        expected_first = elite_indexes[0] if elite_indexes else None
        if candidate.first_elite_index != expected_first:
            return False
        return all(symbol in ADAPTIVE_ROUTE_SYMBOLS for symbol in candidate.symbols)

    def calculate_node_priority(self, node: Node, context: DecisionContext) -> int:
        """
        Calculate dynamic priority for a map node.

        Adjusts base priorities based on:
        - Current act number
        - HP percentage
        - Player class (Ironclad can be more aggressive in Act 1)
        """
        symbol = node.symbol
        base_priority = self.BASE_NODE_PRIORITIES.get(symbol, 0)
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        act = self._non_negative_int(getattr(context, 'act', 0))
        floor = self._non_negative_int(getattr(context, 'floor', 0))

        # Act 1: Character-specific strategies
        if act == 1:
            base_priority = self._adjust_act_1_priority(symbol, base_priority, hp_pct, floor, context)

        # Act 2+: More conservative
        elif act >= 2:
            base_priority = self._adjust_act_2_plus_priority(symbol, base_priority, hp_pct)

        # Generic HP-based adjustments for all acts
        base_priority = self._adjust_for_hp(symbol, base_priority, hp_pct, act=act, floor=floor)

        return base_priority

    def _adjust_act_1_priority(self, symbol: str, base: int, hp_pct: float, floor: int, context: DecisionContext) -> int:
        """Act 1 priorities - Ironclad takes elites only after readiness checks."""
        # Ironclad prioritizes rest sites for card upgrades, avoids elites consistently
        if self.player_class == 'IRONCLAD':
            if symbol == 'E':  # Elite
                # Optional elite routing mode for experimentation.
                if self.elite_mode == "aggressive":
                    readiness = self._act_1_elite_readiness_score(context)
                    if readiness >= 5:
                        return base + 450 + readiness * 30
                    if readiness >= 3 and floor >= 8 and hp_pct >= 0.7:
                        return base + 80
                    logging.getLogger(__name__).info(
                        "[MAP_ROUTING] Act1 elite gated: floor=%s hp=%.1f%% readiness=%s",
                        floor,
                        hp_pct * 100,
                        readiness,
                    )
                    return base - 260
                # Conservative mode is for first-win validation: make elites a
                # route-blocking penalty unless every reachable path is forced.
                return base - 5000

            if self._act_1_needs_combat_rewards(context, floor, hp_pct):
                if symbol == 'M':
                    return base + 30
                if symbol == '?':
                    return base - 20
                if symbol == '$' and self._act_1_low_value_early_shop(context, floor):
                    return base - 35

            if symbol == 'R':  # Rest
                # Prioritize rest sites for card upgrades even when healthy
                if hp_pct > 0.75:
                    return base + 50  # Worth it for upgrades (was -50)
                elif hp_pct < 0.4:
                    return base + 300  # Urgent healing
                else:
                    return base + 100  # Generally good for upgrades

        # Silent can also be aggressive with poison, adjusted for A20
        elif self.player_class == 'THE_SILENT':
            if symbol == 'E':
                if floor <= 7:
                    return base - 150  # Avoid early elites
                elif hp_pct > 0.6:
                    return base + 100  # More cautious than before

        # Defect is weakest early, more conservative
        elif self.player_class == 'THE_DEFECT':
            if symbol == 'E':
                return base - 100  # More cautious for Defect in A20

        return base

    def _act_1_needs_combat_rewards(self, context: DecisionContext, floor: int, hp_pct: float) -> bool:
        """Act 1 weak decks need normal fights before events/shops starve rewards."""
        if floor >= 15 or hp_pct < 0.55:
            return False

        game = getattr(context, "game", None)
        deck = list(getattr(game, "deck", []) or [])
        if not deck:
            return False

        card_names = [self._card_name(card) for card in deck]
        premium_attacks = sum(1 for card_name in card_names if card_name in self.ACT1_PREMIUM_ATTACKS)
        strong_blocks = sum(1 for card_name in card_names if card_name in self.ACT1_STRONG_BLOCKS)

        if floor <= 6:
            return len(deck) <= 11 or premium_attacks < 2
        if floor <= 12:
            return len(deck) <= 14 or premium_attacks < 3 or (premium_attacks + strong_blocks) < 5
        return len(deck) <= 15 or premium_attacks < 4

    def _act_1_low_value_early_shop(self, context: DecisionContext, floor: int) -> bool:
        if floor > 8:
            return False
        game = getattr(context, "game", None)
        gold = self._non_negative_int(getattr(game, "gold", 0))
        return gold < 180

    def _act_1_elite_readiness_score(self, context: DecisionContext) -> int:
        """Estimate if the deck is ready for Nob/Lagavulin/Sentries."""
        game = getattr(context, "game", None)
        deck = list(getattr(game, "deck", []) or [])
        potions = list(game_real_potions(game))
        relics = list(getattr(game, "relics", []) or [])

        card_names = [self._card_name(card) for card in deck]
        upgraded_ids = {
            self._card_name(card)
            for card in deck
            if is_card_upgraded(card)
        }

        fight_potions = {
            "Fire Potion", "Attack Potion", "Strength Potion", "Flex Potion",
            "Dexterity Potion", "Skill Potion", "Power Potion", "Fear Potion",
            "Duplication Potion", "Distilled Chaos", "Explosive Potion",
            "Swift Potion", "Energy Potion", "Entropic Brew",
        }
        fight_potion_keys = {
            self._compact_identifier(potion_name)
            for potion_name in fight_potions
        }

        score = 0
        score += min(4, sum(1 for card_name in card_names if card_name in self.ACT1_PREMIUM_ATTACKS))
        score += min(2, sum(1 for card_name in card_names if card_name in self.ACT1_STRONG_BLOCKS))
        if "Bash" in upgraded_ids:
            score += 1
        score += min(
            2,
            sum(
                1
                for potion in potions
                if (
                    self._compact_identifier(getattr(potion, "potion_id", ""))
                    in fight_potion_keys
                    or self._compact_identifier(getattr(potion, "name", ""))
                    in fight_potion_keys
                )
                and getattr(potion, "can_use", True)
            ),
        )
        score += min(2, max(0, len(relics) - 1))
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        if hp_pct >= 0.85:
            score += 1
        elif hp_pct < 0.65:
            score -= 2

        floor = self._non_negative_int(getattr(context, "floor", 0))
        if floor <= 6:
            score -= 2
        elif floor >= 10:
            score += 1

        return score

    def _adjust_act_2_plus_priority(self, symbol: str, base: int, hp_pct: float) -> int:
        """Act 2+ priorities - first-win conservative mode avoids optional elites."""
        if symbol == 'E':  # Elite
            if self.elite_mode == "conservative":
                return base - 5000

            # Aggressive elite routing in Act 2
            if hp_pct < 0.2:
                return base - 100  # Avoid elites when very low HP
            elif hp_pct < 0.65:
                return base + 50   # Cautious but willing
            else:
                return base + 200  # Strongly prefer elites when healthy

        elif symbol == 'M':  # Monster
            # Avoid normal monsters in Act 2
            return base - 100

        elif symbol == 'R':  # Rest
            if hp_pct < 0.5:
                return base + 400  # Critical need
            elif hp_pct < 0.7:
                return base + 150  # Good to have
            else:
                return base - 50   # Can skip

        elif symbol == '?':  # Unknown
            # Favor events in Act 2
            if hp_pct < 0.2:
                return base - 50   # Risky events when low HP
            else:
                return base + 100  # Strongly prefer events

        return base

    def _adjust_for_hp(self, symbol: str, base: int, hp_pct: float, act: int = None, floor: int = None) -> int:
        """Generic HP-based adjustments."""
        act = self._non_negative_int(act) if act is not None else None
        floor = self._non_negative_int(floor) if floor is not None else None

        # Critical HP: prioritize survival
        if hp_pct < 0.25:
            if symbol == 'R':
                return base + 300
            elif symbol == 'E':
                return base - 300
            elif symbol == 'M':
                return base - 100  # Even normal fights are risky

        # Very healthy: can afford risks
        elif hp_pct > 0.85:
            if symbol == 'E' and not (act == 1 and floor is not None and floor <= 7):
                return base + 50
            elif symbol == 'R':
                return base - 150

        return base

    def choose_campfire_option(self, options: List[RestOption], context: DecisionContext) -> RestOption:
        """
        Choose best campfire option based on game state.

        Priority logic based on expert strategies:
        - REST: When HP < 50% or before boss
        - SMITH: When HP > 60% and have good upgrade targets
        - LIFT: When deck is small and lean
        - DIG: When need gold/cards and HP is good
        """
        if not options:
            return RestOption.REST

        if RestOption.REST in options:
            force_rest, reason = self._should_force_rest(context)
            if force_rest:
                hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
                logging.getLogger(__name__).info(
                    "[REST_GUARD] Map router forcing REST reason=%s hp_pct=%.1f%% floor=%s",
                    reason,
                    hp_pct * 100,
                    getattr(context, "floor", 0),
                )
                return RestOption.REST

        scores = {}

        # Calculate scores for each available option
        if RestOption.REST in options:
            scores[RestOption.REST] = self._score_rest_option(context)

        if RestOption.SMITH in options:
            scores[RestOption.SMITH] = self._score_smith_option(context)

        if RestOption.LIFT in options:
            scores[RestOption.LIFT] = self._score_lift_option(context)

        if RestOption.DIG in options:
            scores[RestOption.DIG] = self._score_dig_option(context)

        # Return highest priority option
        best_option = max(scores.keys(), key=lambda k: scores[k])
        return best_option

    def _score_rest_option(self, context: DecisionContext) -> int:
        """Score REST option."""
        score = 50
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        floor = self._non_negative_int(getattr(context, 'floor', 0))

        # Is this pre-boss?
        is_pre_boss = (floor % 17) in [15, 16]

        # Critical need
        if hp_pct < 0.3:
            score += 150
        elif hp_pct < 0.5:
            score += 80
        if is_pre_boss and hp_pct < 0.6:
            score += 150  # Definitely rest before boss
        elif is_pre_boss and hp_pct < 0.8:
            score += 100  # Rest before boss

        return score

    def _should_force_rest(self, context: DecisionContext) -> tuple[bool, str]:
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        act = self._non_negative_int(getattr(context, 'act', 0))
        floor = self._non_negative_int(getattr(context, 'floor', 0))
        is_pre_boss = (floor % 17) in (15, 16)

        if hp_pct < 0.5:
            return True, "low_hp"
        if act == 1 and floor <= 7 and hp_pct < 0.6:
            return True, "early_act1_low_margin"
        if is_pre_boss and hp_pct < 0.8:
            return True, "pre_boss"
        return False, ""

    def _score_smith_option(self, context: DecisionContext) -> int:
        """Score SMITH option."""
        score = 40
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))

        # Need HP to afford not healing
        if hp_pct > 0.6:
            score += 70
        elif hp_pct > 0.4:
            score += 30  # Risky but might be worth it
        else:
            score -= 50  # Too risky

        # Check for upgrade targets
        upgradeable_count = self._count_upgradeable_cards(context)
        score += upgradeable_count * 15

        return score

    def _score_lift_option(self, context: DecisionContext) -> int:
        """Score LIFT option."""
        score = 30

        if not hasattr(context.game, 'deck'):
            return score

        deck_size = len(context.game.deck)

        # Small decks benefit most
        if deck_size <= 12:
            score += 60
        elif deck_size <= 15:
            score += 40
        elif deck_size <= 18:
            score += 20
        elif deck_size >= 25:
            score -= 50  # Don't add to bloated deck
        elif deck_size >= 20:
            score -= 20

        # Check for card removal needs
        strike_count = sum(1 for c in context.game.deck if self._card_name(c) == 'Strike')
        if strike_count >= 3:
            score += 30  # Need to remove cards

        return score

    def _score_dig_option(self, context: DecisionContext) -> int:
        """Score DIG option."""
        score = 20
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))

        # Need to be healthy to risk it
        if hp_pct < 0.5:
            score -= 30

        # Need gold for card removal?
        if hasattr(context.game, 'gold'):
            if context.game.gold < 300:
                score += 40  # Need gold
            elif context.game.gold < 500:
                score += 20

        # Need cards? (only if deck is small)
        if hasattr(context.game, 'deck'):
            deck_size = len(context.game.deck)
            if deck_size <= 15 and hp_pct > 0.7:
                score += 30  # Can afford to add card
            elif deck_size >= 20:
                score -= 30  # Don't want more cards

        return score

    def _count_upgradeable_cards(self, context: DecisionContext) -> int:
        """Count cards that would benefit from upgrading."""
        if not hasattr(context.game, 'deck'):
            return 0

        count = 0
        for card in context.game.deck:
            # Unupgraded cards
            if card_upgrade_count(card) == 0:
                # Skip strikes/defends (low priority)
                if self._card_name(card) not in ['Strike', 'Defend']:
                    count += 1

        return count
