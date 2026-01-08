"""
Combat Balance Strategy - Determines optimal offensive/defensive balance.

This module implements the strategy pattern for mapping turn timing classifications
to concrete scoring weights used in beam search simulation.
"""

import logging
from typing import Optional

from .models import (
    TurnTiming,
    BalanceWeights,
    TimingContext,
)

logger = logging.getLogger(__name__)


class CombatBalanceStrategy:
    """
    Determine optimal offensive/defensive balance based on turn timing.

    Implements the "opportunistic defense" philosophy:
    - Attack if lethal (can kill all monsters this turn)
    - Otherwise defend based on timing classification
    - Exploit safe windows (monster buffing/defending)
    - Prepare for threat spikes (big attacks coming)

    This strategy enables dynamic weight adjustment without hardcoding values.
    """

    def __init__(self, player_hp_threshold: float = 0.5):
        """
        Initialize balance strategy.

        Args:
            player_hp_threshold: HP threshold below which to be more defensive (default 50%)
        """
        self.player_hp_threshold = player_hp_threshold

    def get_balance_weights(
        self,
        timing: TurnTiming,
        context,
        timing_ctx: Optional[TimingContext] = None
    ) -> BalanceWeights:
        """
        Get balance weights for a given timing classification.

        Args:
            timing: Turn timing classification
            context: Decision context for game state
            timing_ctx: Optional timing context for enhanced decisions

        Returns:
            BalanceWeights with appropriate offensive/defensive balance
        """
        try:
            # Check player HP (low HP = more defensive)
            player_hp_pct = self._get_player_hp_percent(context)
            if player_hp_pct < self.player_hp_threshold:
                # Low HP - be more defensive
                return self._get_defensive_adjusted_weights(timing, player_hp_pct)

            # Get base weights for timing
            weights = self._get_base_weights(timing)

            # Apply monster-specific adjustments from Wiki hints
            if timing_ctx:
                weights = self._apply_wiki_hints_adjustments(weights, timing_ctx)

            return weights

        except Exception as e:
            logger.warning(f"[BALANCE_STRATEGY] Weight calculation failed: {e}")
            return BalanceWeights.balanced_weights()

    def should_prioritize_lethal(
        self,
        timing: TurnTiming,
        context,
        timing_ctx: Optional[TimingContext] = None
    ) -> bool:
        """
        Determine if we should check for lethal this turn.

        Lethal detection is always enabled for opportunistic philosophy,
        but we can be smarter about when to prioritize it.

        Args:
            timing: Turn timing classification
            context: Decision context
            timing_ctx: Optional timing context

        Returns:
            True if lethal detection should be prioritized
        """
        # Always prioritize lethal on burst windows
        if timing == TurnTiming.BURST_WINDOW:
            return True

        # Don't prioritize lethal on threat spikes (survival first)
        if timing == TurnTiming.THREAT_SPIKE:
            return False

        # Default: prioritize lethal
        return True

    def calculate_block_threshold(
        self,
        timing: TurnTiming,
        context,
        timing_ctx: Optional[TimingContext] = None
    ) -> int:
        """
        Calculate minimum block needed before considering offense.

        This prevents wasteful attacks when we should be building defense.

        Args:
            timing: Turn timing classification
            context: Decision context
            timing_ctx: Optional timing context

        Returns:
            Minimum block threshold
        """
        if timing_ctx:
            # Use predicted next-turn damage
            if timing_ctx.future_damage_curve:
                next_damage = timing_ctx.future_damage_curve[0]
                # Block for 80% of next turn damage
                return int(next_damage * 0.8)

        # Fallback to current turn damage
        current_damage = self._estimate_current_damage(context)
        return int(current_damage * 0.7)

    def _get_base_weights(self, timing: TurnTiming) -> BalanceWeights:
        """Get base weights for a timing classification."""
        if timing == TurnTiming.SAFE:
            return BalanceWeights.safe_turn_weights()
        elif timing == TurnTiming.THREAT_SPIKE:
            return BalanceWeights.threat_spike_weights()
        elif timing == TurnTiming.PREPARATION:
            return BalanceWeights.preparation_weights()
        elif timing == TurnTiming.BURST_WINDOW:
            return BalanceWeights.burst_window_weights()
        else:
            return BalanceWeights.balanced_weights()

    def _get_defensive_adjusted_weights(
        self,
        timing: TurnTiming,
        player_hp_pct: float
    ) -> BalanceWeights:
        """
        Get defensively-adjusted weights for low HP situations.

        When player HP is low, we prioritize survival over damage.
        """
        base_weights = self._get_base_weights(timing)

        # Increase block priority, decrease damage priority
        adjustment_factor = 1.0 + (self.player_hp_threshold - player_hp_pct)

        return BalanceWeights(
            damage_weight=base_weights.damage_weight / adjustment_factor,
            block_weight=base_weights.block_weight * adjustment_factor,
            kill_bonus=base_weights.kill_bonus * 0.8,  # Lower kill priority when low HP
            lethal_detection=base_weights.lethal_detection,
            block_threshold=int(base_weights.block_threshold * 1.5),
            opportunistic_attack=base_weights.opportunistic_attack
        )

    def _apply_wiki_hints_adjustments(
        self,
        weights: BalanceWeights,
        timing_ctx: TimingContext
    ) -> BalanceWeights:
        """
        Apply adjustments from monster-specific Wiki hints.

        Some monsters have special timing patterns that override general rules.
        """
        # Check if any monster has specific timing recommendations
        for monster_name, hints in timing_ctx.monster_hints.items():
            preferred = hints.get_preferred_response(timing_ctx.turn_timing)

            if preferred == "ultra_defensive":
                # Be very defensive
                return BalanceWeights(
                    damage_weight=weights.damage_weight * 0.5,
                    block_weight=weights.block_weight * 1.5,
                    kill_bonus=weights.kill_bonus * 0.7,
                    lethal_detection=weights.lethal_detection,
                    block_threshold=int(weights.block_threshold * 2.0),
                    opportunistic_attack=weights.opportunistic_attack
                )
            elif preferred == "aggressive":
                # Be very aggressive
                return BalanceWeights(
                    damage_weight=weights.damage_weight * 1.5,
                    block_weight=weights.block_weight * 0.7,
                    kill_bonus=weights.kill_bonus * 1.3,
                    lethal_detection=weights.lethal_detection,
                    block_threshold=int(weights.block_threshold * 0.5),
                    opportunistic_attack=weights.opportunistic_attack
                )

        return weights

    def _get_player_hp_percent(self, context) -> float:
        """Get player HP as a percentage (0.0-1.0)."""
        try:
            player = getattr(context, 'player', None)
            if player and hasattr(player, 'current_hp') and hasattr(player, 'max_hp'):
                return player.current_hp / max(player.max_hp, 1)
        except:
            pass

        return 1.0  # Default to full HP

    def _estimate_current_damage(self, context) -> int:
        """Estimate current turn incoming damage."""
        try:
            monsters = getattr(context, 'monsters_alive', [])
            total_damage = 0

            for monster in monsters:
                # Get adjusted damage
                damage = getattr(monster, 'move_adjusted_damage', 0)
                hits = getattr(monster, 'move_hits', 1)
                total_damage += damage * hits

            return total_damage

        except Exception as e:
            logger.warning(f"[BALANCE_STRATEGY] Damage estimation failed: {e}")
            return 0
