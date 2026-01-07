"""
Turn Timing Classifier - Analyzes combat state to classify turn timing.

This module provides intelligent classification of combat turns based on monster
intent patterns and Wiki move predictions.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from .models import (
    TurnTiming,
    SafeWindow,
    TimingContext,
    MonsterTimingHints,
    BalanceWeights,
)

logger = logging.getLogger(__name__)


class TurnTimingClassifier:
    """
    Classify combat turns based on monster intent patterns and Wiki data.

    The classifier analyzes:
    - Current monster intents
    - Predicted future moves (from Wiki patterns)
    - Monster-specific timing hints
    - Damage curves over next 3 turns

    This enables proactive combat decisions (e.g., "build block now, big hit in 2 turns").
    """

    def __init__(self):
        """Initialize the classifier."""
        self._cache = {}  # Cache for timing analysis results

    def classify_turn(self, context) -> TimingContext:
        """
        Classify the current turn's timing and build complete timing context.

        Args:
            context: DecisionContext with game state

        Returns:
            TimingContext with turn classification and all timing analysis
        """
        try:
            # Get basic turn info
            current_turn = getattr(context, 'turn', 1)
            monsters = getattr(context, 'monsters_alive', [])

            if not monsters:
                # No monsters - default to balanced
                return self._create_default_context(current_turn)

            # Analyze timing for all monsters
            timing_analysis = self._analyze_monster_timing(context, monsters, current_turn)

            # Classify overall turn timing
            turn_timing = self._classify_overall_timing(timing_analysis, context)

            # Detect safe windows
            safe_windows = self._detect_safe_windows(context, monsters, current_turn)

            # Calculate damage curve
            damage_curve = self._calculate_damage_curve(context, monsters, current_turn, look_ahead=3)

            # Get balance weights for this timing
            weights = self._get_balance_weights_for_timing(turn_timing, context)

            # Build timing context
            timing_ctx = TimingContext(
                turn_timing=turn_timing,
                current_damage=timing_analysis['current_damage'],
                future_damage_curve=damage_curve,
                safe_windows=safe_windows,
                balance_weights=weights,
                monster_hints=timing_analysis['monster_hints'],
                confidence=timing_analysis['confidence']
            )
            timing_ctx._current_turn = current_turn

            # Log classification
            logger.info(
                f"[TIMING_CLASSIFIER] Turn {current_turn}: {turn_timing.value}, "
                f"current_damage={timing_analysis['current_damage']}, "
                f"future_damage={damage_curve}, "
                f"safe_windows={len(safe_windows)}, "
                f"confidence={timing_analysis['confidence']:.2f}"
            )

            return timing_ctx

        except Exception as e:
            logger.warning(f"[TIMING_CLASSIFIER] Classification failed: {e}")
            return self._create_default_context(getattr(context, 'turn', 1))

    def _analyze_monster_timing(
        self,
        context,
        monsters: List,
        current_turn: int
    ) -> Dict[str, Any]:
        """
        Analyze timing for each monster.

        Returns:
            Dict with timing analysis aggregated across all monsters
        """
        try:
            from spirecomm.data.loader import game_data_loader

            total_current_damage = 0
            monster_hints = {}
            safe_monster_count = 0
            spike_monster_count = 0
            total_confidence = 0.0

            for monster in monsters:
                monster_name = monster.name

                # Get current intent
                current_intent = str(getattr(monster, 'intent', 'UNKNOWN')).upper()

                # Calculate HP percentage
                if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
                    hp_percent = monster.current_hp / max(monster.max_hp, 1)
                else:
                    hp_percent = 1.0

                # Get current damage
                current_damage = getattr(monster, 'move_adjusted_damage', 0)
                hits = getattr(monster, 'move_hits', 1)
                total_current_damage += current_damage * hits

                # Get Wiki timing hints
                hints = game_data_loader.get_monster_timing_hints(monster_name)
                if hints:
                    monster_hints[monster_name] = MonsterTimingHints.from_dict(hints)
                else:
                    # Create default hints
                    monster_hints[monster_name] = MonsterTimingHints()

                # Predict next moves
                predicted_moves = game_data_loader.predict_monster_moves(
                    monster_name, current_turn, hp_percent
                )

                if predicted_moves:
                    next_move = predicted_moves[0].get('move', {})
                    next_intent = next_move.get('intent', '').upper()

                    # Check if current turn is safe (monster buffing/defending)
                    if self._is_safe_intent(current_intent, next_intent, monster_hints[monster_name]):
                        safe_monster_count += 1

                    # Check if current turn is a spike (high damage attack)
                    if self._is_spike_intent(current_intent, current_damage, monster_hints[monster_name]):
                        spike_monster_count += 1

                    # Accumulate confidence
                    confidence = predicted_moves[0].get('confidence', 0.5)
                    total_confidence += confidence

            # Calculate aggregate confidence
            avg_confidence = total_confidence / len(monsters) if monsters else 0.5

            return {
                'current_damage': total_current_damage,
                'monster_hints': monster_hints,
                'safe_monster_count': safe_monster_count,
                'spike_monster_count': spike_monster_count,
                'total_monsters': len(monsters),
                'confidence': avg_confidence
            }

        except Exception as e:
            logger.warning(f"[TIMING_ANALYSIS] Monster timing analysis failed: {e}")
            return {
                'current_damage': 0,
                'monster_hints': {},
                'safe_monster_count': 0,
                'spike_monster_count': 0,
                'total_monsters': 0,
                'confidence': 0.0
            }

    def _classify_overall_timing(self, analysis: Dict, context) -> TurnTiming:
        """
        Classify overall turn timing based on monster analysis.

        Classification priority:
        1. THREAT_SPIKE - High damage incoming
        2. SAFE - All monsters buffing/defending
        3. BURST_WINDOW - Monster vulnerable
        4. PREPARATION - Spike coming soon
        5. BALANCED - Standard turn
        """
        current_damage = analysis['current_damage']
        safe_count = analysis['safe_monster_count']
        spike_count = analysis['spike_monster_count']
        total_monsters = analysis['total_monsters']

        # Check for threat spike (high damage this turn)
        if current_damage > 25 or (current_damage > 15 and spike_count > 0):
            return TurnTiming.THREAT_SPIKE

        # Check for safe turn (all monsters non-attacking)
        if safe_count == total_monsters and total_monsters > 0:
            return TurnTiming.SAFE

        # Check for burst window (monster vulnerable at low HP)
        if self._has_burst_opportunity(context):
            return TurnTiming.BURST_WINDOW

        # Check for preparation (spike coming in 1-2 turns)
        if self._spike_imminent(context):
            return TurnTiming.PREPARATION

        # Default to balanced
        return TurnTiming.BALANCED

    def _detect_safe_windows(
        self,
        context,
        monsters: List,
        current_turn: int,
        look_ahead: int = 5
    ) -> List[SafeWindow]:
        """
        Detect future windows where damage risk is low.

        Args:
            context: Decision context
            monsters: List of alive monsters
            current_turn: Current turn number
            look_ahead: How many turns to look ahead

        Returns:
            List of SafeWindow objects
        """
        try:
            from spirecomm.data.loader import game_data_loader

            safe_windows = []
            turn_damages = {}  # turn -> total damage

            # Calculate damage for each future turn
            for turn_offset in range(look_ahead):
                target_turn = current_turn + turn_offset
                total_damage = 0
                monsters_safe = []

                for monster in monsters:
                    # Get HP percentage
                    if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
                        hp_percent = monster.current_hp / max(monster.max_hp, 1)
                    else:
                        hp_percent = 1.0

                    # Predict moves for this turn
                    predicted_moves = game_data_loader.predict_monster_moves(
                        monster.name, target_turn, hp_percent
                    )

                    if predicted_moves and turn_offset < len(predicted_moves):
                        move = predicted_moves[turn_offset].get('move', {})
                        intent = move.get('intent', '').upper()

                        # Check if attack
                        if 'ATTACK' in intent:
                            damage = move.get('damage', 0)
                            hits = move.get('hits', 1)
                            total_damage += damage * hits
                        else:
                            # Non-attack move = safe
                            monsters_safe.append(monster.name)

                turn_damages[target_turn] = total_damage

                # Detect safe window (low damage)
                if total_damage < 10:  # Threshold for "safe"
                    safe_windows.append(SafeWindow(
                        start_turn=target_turn,
                        end_turn=target_turn,
                        expected_damage=total_damage,
                        confidence=0.8,
                        monsters_safe=list(set(monsters_safe))
                    ))

            # Merge consecutive safe windows
            merged_windows = self._merge_consecutive_windows(safe_windows)

            if merged_windows:
                logger.debug(
                    f"[SAFE_WINDOWS] Detected {len(merged_windows)} safe windows: "
                    f"{[str(w) for w in merged_windows]}"
                )

            return merged_windows

        except Exception as e:
            logger.warning(f"[SAFE_WINDOWS] Detection failed: {e}")
            return []

    def _calculate_damage_curve(
        self,
        context,
        monsters: List,
        current_turn: int,
        look_ahead: int = 3
    ) -> List[int]:
        """
        Calculate predicted damage for next N turns.

        Returns:
            List of damage values [turn+1, turn+2, ..., turn+N]
        """
        try:
            from spirecomm.data.loader import game_data_loader

            damage_curve = []

            for turn_offset in range(1, look_ahead + 1):
                target_turn = current_turn + turn_offset
                total_damage = 0

                for monster in monsters:
                    # Get HP percentage
                    if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
                        hp_percent = monster.current_hp / max(monster.max_hp, 1)
                    else:
                        hp_percent = 1.0

                    # Get predicted moves
                    predicted_moves = game_data_loader.predict_monster_moves(
                        monster.name, target_turn, hp_percent
                    )

                    if predicted_moves and turn_offset <= len(predicted_moves):
                        move = predicted_moves[turn_offset - 1].get('move', {})
                        intent = move.get('intent', '').upper()

                        if 'ATTACK' in intent:
                            damage = move.get('damage', 0)
                            hits = move.get('hits', 1)

                            # Add monster strength
                            strength = getattr(monster, 'strength', 0)
                            total_damage += (damage + strength) * hits

                damage_curve.append(total_damage)

            return damage_curve

        except Exception as e:
            logger.warning(f"[DAMAGE_CURVE] Calculation failed: {e}")
            return [0] * look_ahead

    def _get_balance_weights_for_timing(
        self,
        timing: TurnTiming,
        context
    ) -> BalanceWeights:
        """Get appropriate balance weights for a timing classification."""
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

    def _is_safe_intent(
        self,
        current_intent: str,
        next_intent: str,
        hints: MonsterTimingHints
    ) -> bool:
        """Check if intent indicates a safe turn."""
        # Non-attack intents are generally safe
        non_attack_intents = ['BUFF', 'DEFEND', 'DEBUFF', 'DEBUG', 'NONE', 'STUN', 'SLEEP']

        if current_intent in non_attack_intents:
            return True

        # Check Wiki hints
        if hints.is_safe_turn(current_intent):
            return True

        return False

    def _is_spike_intent(
        self,
        current_intent: str,
        current_damage: int,
        hints: MonsterTimingHints
    ) -> bool:
        """Check if intent indicates a threat spike."""
        # High damage attack
        if current_damage > 15:
            return True

        # Check Wiki hints
        if hints.is_spike_turn(current_intent):
            return True

        return False

    def _has_burst_opportunity(self, context) -> bool:
        """Check if current situation is a burst window (monster vulnerable)."""
        # This is a simplified check - can be enhanced with more sophisticated logic
        # For now, check if any monster is below 30% HP
        monsters = getattr(context, 'monsters_alive', [])

        for monster in monsters:
            if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
                hp_percent = monster.current_hp / max(monster.max_hp, 1)
                if hp_percent < 0.3 and hp_percent > 0.1:
                    # Low HP but not dead - burst opportunity
                    return True

        return False

    def _spike_imminent(self, context) -> bool:
        """Check if a big attack is coming in 1-2 turns."""
        try:
            from spirecomm.data.loader import game_data_loader

            current_turn = getattr(context, 'turn', 1)
            monsters = getattr(context, 'monsters_alive', [])

            for monster in monsters:
                # Get HP percentage
                if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
                    hp_percent = monster.current_hp / max(monster.max_hp, 1)
                else:
                    hp_percent = 1.0

                # Check next 2 turns
                for turn_offset in range(1, 3):
                    target_turn = current_turn + turn_offset
                    predicted_moves = game_data_loader.predict_monster_moves(
                        monster.name, target_turn, hp_percent
                    )

                    if predicted_moves and turn_offset <= len(predicted_moves):
                        move = predicted_moves[turn_offset - 1].get('move', {})
                        damage = move.get('damage', 0)

                        if damage >= 20:
                            # Big attack imminent
                            return True

            return False

        except Exception as e:
            logger.warning(f"[SPIKE_IMMINENT] Check failed: {e}")
            return False

    def _merge_consecutive_windows(self, windows: List[SafeWindow]) -> List[SafeWindow]:
        """Merge consecutive safe windows into larger windows."""
        if not windows:
            return []

        merged = []
        current = windows[0]

        for window in windows[1:]:
            if window.start_turn == current.end_turn + 1:
                # Consecutive - merge
                current = SafeWindow(
                    start_turn=current.start_turn,
                    end_turn=window.end_turn,
                    expected_damage=current.expected_damage + window.expected_damage,
                    confidence=min(current.confidence, window.confidence),
                    monsters_safe=list(set(current.monsters_safe + window.monsters_safe))
                )
            else:
                # Not consecutive - save current and start new
                merged.append(current)
                current = window

        merged.append(current)
        return merged

    def _create_default_context(self, current_turn: int) -> TimingContext:
        """Create default timing context when analysis fails."""
        return TimingContext(
            turn_timing=TurnTiming.BALANCED,
            current_damage=0,
            future_damage_curve=[0, 0, 0],
            safe_windows=[],
            balance_weights=BalanceWeights.balanced_weights(),
            monster_hints={},
            confidence=0.0
        )
