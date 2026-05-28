"""
Timing-Aware Combat Planner - Integrates timing analysis with beam search.

This module bridges the timing strategy layer with the existing combat simulation,
enabling dynamic weight adjustment based on turn timing classification.
"""

import logging
from typing import List, Optional

from .models import TimingContext, TurnTiming, BalanceWeights
from .turn_classifier import TurnTimingClassifier
from .balance_strategy import CombatBalanceStrategy
from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_costs import effective_card_cost
from spirecomm.ai.heuristics.simulation import BLOCK_UPGRADE_BONUS, _known_damage_upgrade_bonus
from spirecomm.data.loader import game_data_loader
from spirecomm.spire.card import CardType

logger = logging.getLogger(__name__)


class TimingAwareCombatPlanner:
    """
    Integrates timing analysis into combat planning.

    This planner:
    1. Classifies turn timing using TurnTimingClassifier
    2. Gets appropriate balance weights from CombatBalanceStrategy
    3. Applies dynamic weights to beam search scoring
    4. Implements opportunistic lethal detection

    The planner wraps the existing FastCombatSimulator and enhances it
    with timing-aware decision making.
    """

    def __init__(
        self,
        base_planner=None,
        classifier: Optional[TurnTimingClassifier] = None,
        strategy: Optional[CombatBalanceStrategy] = None
    ):
        """
        Initialize timing-aware planner.

        Args:
            base_planner: Existing FastCombatSimulator to enhance (None = standalone)
            classifier: Turn timing classifier (default: create new)
            strategy: Balance strategy (default: create new)
        """
        self.base_planner = base_planner
        self.classifier = classifier or TurnTimingClassifier()
        self.strategy = strategy or CombatBalanceStrategy()

        # Cache for timing analysis (per turn)
        self._timing_cache = {}
        self._current_turn = 0

    def plan_with_timing(self, context) -> List:
        """
        Plan combat actions with timing awareness.

        This is the main entry point that replaces the standard plan_turn() call.

        Args:
            context: Decision context with game state

        Returns:
            List of actions to execute
        """
        # Check cache first
        current_turn = getattr(context, 'turn', 1)
        if current_turn == self._current_turn and hasattr(self, '_cached_actions'):
            return self._cached_actions

        # Step 1: Classify turn timing
        timing_ctx = self.classifier.classify_turn(context)

        # Log timing classification
        logger.info(
            f"[TIMING_PLANNER] Turn {current_turn}: {timing_ctx.turn_timing.value}, "
            f"current_damage={timing_ctx.current_damage}, "
            f"weights=(damage={timing_ctx.balance_weights.damage_weight:.2f}, "
            f"block={timing_ctx.balance_weights.block_weight:.2f})"
        )

        # Step 2: Check for lethal first (opportunistic philosophy)
        if self._can_kill_all_this_turn(context, timing_ctx):
            logger.info("[TIMING_PLANNER] Lethal detected - all-in attack sequence")
            actions = self._generate_lethal_sequence(context)
            self._cached_actions = actions
            self._current_turn = current_turn
            return actions

        # Step 3: Use base planner with timing weights
        if self.base_planner:
            # Store timing context for use in scoring
            if hasattr(self.base_planner, 'set_timing_context'):
                self.base_planner.set_timing_context(timing_ctx)

            # Plan with timing-aware scoring
            actions = self.base_planner.plan_turn(context)
        else:
            # Fallback: simple greedy plan
            actions = self._fallback_plan(context, timing_ctx)

        # Cache and return
        self._cached_actions = actions
        self._current_turn = current_turn
        return actions

    def get_timing_context(self, context) -> TimingContext:
        """
        Get timing classification for current context.

        Useful for debugging and logging.

        Args:
            context: Decision context

        Returns:
            TimingContext with full timing analysis
        """
        return self.classifier.classify_turn(context)

    def _can_kill_all_this_turn(self, context, timing_ctx: TimingContext) -> bool:
        """
        Check if we can kill all monsters this turn.

        Implements opportunistic philosophy: always check for lethal.

        Args:
            context: Decision context
            timing_ctx: Timing context

        Returns:
            True if lethal is possible
        """
        try:
            monsters = getattr(context, 'monsters_alive', [])
            if not monsters:
                return True  # No monsters = already lethal

            # Get playable cards
            playable_cards = getattr(context, 'playable_cards', [])
            if not playable_cards:
                return False

            # Calculate total potential damage
            total_damage = 0
            energy = getattr(context, 'energy_available', 3)

            for card in playable_cards:
                # Simple estimate: use card's base damage
                card_damage = self._estimate_card_damage(card, context)
                if card_damage > 0:
                    cost = effective_card_cost(card, energy)
                    if cost > energy:
                        continue

                    total_damage += card_damage
                    energy -= cost

                    if energy <= 0:
                        break

            # Check if damage is enough to kill all monsters
            total_hp = sum(
                m.current_hp + getattr(m, 'block', 0)
                for m in monsters
                if hasattr(m, 'current_hp')
            )

            can_kill = total_damage >= total_hp

            if can_kill:
                logger.debug(
                    f"[LETHAL_CHECK] Possible! damage={total_damage}, hp={total_hp}"
                )

            return can_kill

        except Exception as e:
            logger.warning(f"[LETHAL_CHECK] Failed: {e}")
            return False

    def _generate_lethal_sequence(self, context) -> List:
        """
        Generate all-in attack sequence for lethal.

        Args:
            context: Decision context

        Returns:
            List of attack actions
        """
        try:
            from spirecomm.communication.action import PlayCardAction

            playable_cards = getattr(context, 'playable_cards', [])
            monsters = getattr(context, 'monsters_alive', [])

            if not playable_cards or not monsters:
                return []

            # Sort cards by damage (highest first)
            attack_cards = []
            for card in playable_cards:
                damage = self._estimate_card_damage(card, context)
                if damage > 0:
                    attack_cards.append((card, damage))

            # Sort by damage descending
            attack_cards.sort(key=lambda x: x[1], reverse=True)

            # Generate actions (play highest damage cards until out of energy)
            actions = []
            energy = getattr(context, 'energy_available', 3)
            target = monsters[0]  # Default target

            for card, damage in attack_cards:
                cost = effective_card_cost(card, energy)

                if energy >= cost:
                    actions.append(PlayCardAction(card=card, target_monster=target))
                    energy -= cost

                if energy <= 0:
                    break

            logger.info(f"[LETHAL_SEQUENCE] Generated {len(actions)} attack actions")
            return actions

        except Exception as e:
            logger.warning(f"[LETHAL_SEQUENCE] Failed: {e}")
            return []

    def _fallback_plan(self, context, timing_ctx: TimingContext) -> List:
        """
        Fallback simple plan when base planner is unavailable.

        Uses timing weights to make greedy card choices.

        Args:
            context: Decision context
            timing_ctx: Timing context

        Returns:
            List of actions
        """
        try:
            from spirecomm.communication.action import PlayCardAction

            playable_cards = getattr(context, 'playable_cards', [])
            if not playable_cards:
                return []

            # Score cards based on timing weights
            weights = timing_ctx.balance_weights
            best_card = None
            best_score = float('-inf')

            for card in playable_cards:
                score = 0

                # Check if card deals damage
                damage = self._estimate_card_damage(card, context)
                score += damage * weights.damage_weight

                # Check if card provides block
                block = self._estimate_card_block(card)
                score += block * weights.block_weight

                if score > best_score:
                    best_score = score
                    best_card = card

            if best_card:
                # Find target if needed
                monsters = getattr(context, 'monsters_alive', [])
                target = monsters[0] if monsters else None

                return [PlayCardAction(card=best_card, target_monster=target)]

            return []

        except Exception as e:
            logger.warning(f"[FALLBACK_PLAN] Failed: {e}")
            return []

    def _estimate_card_damage(self, card, context) -> int:
        """Estimate card damage for timing decisions from methods or parsed data."""
        if getattr(card, 'type', None) not in (None, CardType.ATTACK):
            return 0

        if hasattr(card, 'damage_for'):
            try:
                strength = getattr(context, 'strength', 0)
                return max(0, int(card.damage_for(getattr(context, 'turn', 1), strength)))
            except Exception:
                pass

        base_damage = getattr(card, 'damage', 0) or 0
        if base_damage <= 0:
            try:
                card_name = canonical_card_name(card)
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    parsed_damage = game_data_loader._parse_card_damage(card_data)
                    if parsed_damage is not None:
                        base_damage = parsed_damage + _known_damage_upgrade_bonus(card, card_name)
            except Exception:
                base_damage = 0

        if base_damage <= 0:
            return 0

        return max(0, int(base_damage + getattr(context, 'strength', 0)))

    def _estimate_card_block(self, card) -> int:
        """Estimate card block for timing decisions from methods or parsed data."""
        if hasattr(card, 'block_for'):
            try:
                return max(0, int(card.block_for()))
            except Exception:
                pass

        block = getattr(card, 'block', 0) or 0
        if block <= 0:
            try:
                card_name = canonical_card_name(card)
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    parsed_block = game_data_loader._parse_card_block(card_data)
                    if parsed_block is not None:
                        block = parsed_block
                        if getattr(card, 'upgrades', 0) > 0:
                            block += BLOCK_UPGRADE_BONUS.get(card_name, 0)
            except Exception:
                block = 0

        return max(0, int(block))
