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

    @staticmethod
    def _intent_name(intent: Any) -> str:
        return str(intent or '').upper().split('.')[-1]

    @classmethod
    def _is_attack_intent(cls, intent: Any) -> bool:
        return 'ATTACK' in cls._intent_name(intent)

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

            # Check if any monster has forced classification (always_classify_as)
            forced_timing = self._check_forced_classification(timing_analysis['monster_hints'])
            if forced_timing:
                turn_timing = forced_timing
                logger.info(f"[TIMING_CLASSIFIER] Using forced classification: {turn_timing.value}")
            else:
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
                current_intent = self._intent_name(getattr(monster, 'intent', 'UNKNOWN'))

                # Calculate HP percentage
                if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
                    hp_percent = monster.current_hp / max(monster.max_hp, 1)
                else:
                    hp_percent = 1.0

                # Get current damage
                current_damage = self._coerce_damage_value(getattr(monster, 'move_adjusted_damage', 0))
                current_damage = max(0, current_damage or 0)
                hits = max(1, self._coerce_int(getattr(monster, 'move_hits', 1), default=1))
                if self._is_attack_intent(current_intent):
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
                    next_intent = self._intent_name(next_move.get('intent', ''))

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

                    anchored_predictions = game_data_loader.predict_monster_moves(
                        monster.name,
                        current_turn,
                        hp_percent,
                    )
                    prediction = self._select_prediction_for_turn(
                        anchored_predictions,
                        monster.name,
                        target_turn,
                        hp_percent,
                    )

                    if prediction:
                        move = prediction.get('move', {})
                        intent = move.get('intent', '').upper()

                        # Check if attack
                        if 'ATTACK' in intent:
                            damage = self._resolve_move_damage(
                                monster.name,
                                move,
                                context,
                                target_turn=target_turn,
                            )
                            damage = self._apply_ascension_damage_modifiers(
                                monster.name,
                                move,
                                damage,
                                context,
                            )
                            hits = self._resolve_move_hits(move, context, target_turn=target_turn)
                            predicted_strength = self._predict_attack_strength(
                                monster,
                                anchored_predictions,
                                current_turn,
                                target_turn,
                                context,
                            )
                            total_damage += (damage + predicted_strength) * hits
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

                    anchored_predictions = game_data_loader.predict_monster_moves(
                        monster.name,
                        current_turn,
                        hp_percent,
                    )
                    prediction = self._select_prediction_for_turn(
                        anchored_predictions,
                        monster.name,
                        target_turn,
                        hp_percent,
                    )

                    if prediction:
                        move = prediction.get('move', {})
                        intent = move.get('intent', '').upper()

                        if 'ATTACK' in intent:
                            damage = self._resolve_move_damage(
                                monster.name, move, context, target_turn=target_turn)
                            hits = self._resolve_move_hits(move, context, target_turn=target_turn)

                            # Apply ascension modifiers to damage
                            damage = self._apply_ascension_damage_modifiers(
                                monster.name, move, damage, context
                            )

                            predicted_strength = self._predict_attack_strength(
                                monster,
                                anchored_predictions,
                                current_turn,
                                target_turn,
                                context,
                            )

                            total_damage += (damage + predicted_strength) * hits

                damage_curve.append(total_damage)

            return damage_curve

        except Exception as e:
            logger.warning(f"[DAMAGE_CURVE] Calculation failed: {e}")
            return [0] * look_ahead

    def _select_prediction_for_turn(
        self,
        anchored_predictions: List[Dict[str, Any]],
        monster_name: str,
        target_turn: int,
        hp_percent: float,
    ) -> Optional[Dict[str, Any]]:
        for prediction in anchored_predictions:
            if prediction.get('turn') == target_turn:
                return prediction

        try:
            from spirecomm.data.loader import game_data_loader

            fallback_predictions = game_data_loader.predict_monster_moves(
                monster_name,
                target_turn,
                hp_percent,
            )
            return fallback_predictions[0] if fallback_predictions else None
        except Exception:
            return None

    def _predict_attack_strength(
        self,
        monster,
        anchored_predictions: List[Dict[str, Any]],
        current_turn: int,
        target_turn: int,
        context,
    ) -> int:
        current_strength = getattr(monster, 'strength', 0)
        ascension_level = self._context_ascension_level(context)
        scripted_strength = self._predict_strength_from_move_sequence(
            anchored_predictions,
            current_turn,
            target_turn,
            current_strength,
            ascension_level,
        )
        scaling_strength = self._predict_future_strength(
            monster,
            current_turn,
            target_turn,
            current_strength,
            ascension_level,
        )
        return max(scripted_strength, scaling_strength)

    def _predict_strength_from_move_sequence(
        self,
        predictions: List[Dict[str, Any]],
        current_turn: int,
        target_turn: int,
        current_strength: int,
        ascension_level: int,
    ) -> int:
        predicted_strength = current_strength
        for prediction in predictions:
            turn = prediction.get('turn')
            if not isinstance(turn, int):
                continue
            if turn < current_turn or turn >= target_turn:
                continue
            predicted_strength += self._resolve_move_strength_gain(
                prediction.get('move', {}),
                ascension_level,
            )
        return predicted_strength

    def _resolve_move_strength_gain(self, move: Dict[str, Any], ascension_level: int) -> int:
        value = move.get('strength_gain', 0)
        if isinstance(value, (int, float)):
            strength_gain = int(value)
        else:
            return 0

        ascension_modifiers = move.get('ascension_modifiers', {})
        if isinstance(ascension_modifiers, dict):
            thresholds = [
                int(key.split('+')[0])
                for key in ascension_modifiers
                if isinstance(key, str) and key.endswith('+') and key.split('+')[0].isdigit()
            ]
            for threshold in sorted(thresholds, reverse=True):
                if ascension_level < threshold:
                    continue
                modifier = ascension_modifiers.get(f"{threshold}+", {})
                if isinstance(modifier, dict) and 'strength_gain' in modifier:
                    return int(modifier['strength_gain'])
                break

        return strength_gain

    def _resolve_move_damage(
        self,
        monster_name: str,
        move: Dict[str, Any],
        context,
        target_turn: Optional[int] = None,
    ) -> int:
        """Return a numeric damage estimate for wiki moves with ranges or formulas."""
        damage = self._coerce_damage_value(move.get('damage'))
        if damage is not None:
            return damage

        formula_damage = self._resolve_damage_formula(move.get('damage_formula'), target_turn)
        if formula_damage is not None:
            return formula_damage

        move_name = str(move.get('name', '')).lower()
        effect = str(move.get('effect', '')).lower()
        if monster_name.lower() == 'hexaghost' and move_name == 'divider':
            player_hp = 0
            if hasattr(context, 'game') and hasattr(context.game, 'current_hp'):
                player_hp = context.game.current_hp or 0
            elif hasattr(context, 'player_hp'):
                player_hp = context.player_hp or 0
            return ((int(player_hp) // 12) + 1) * 6

        if 'current player hp divided by 12' in effect:
            player_hp = getattr(context, 'player_hp', 0) or 0
            if hasattr(context, 'game') and hasattr(context.game, 'current_hp'):
                player_hp = context.game.current_hp or player_hp
            return ((int(player_hp) // 12) + 1) * 6

        return 0

    def _resolve_move_hits(
        self,
        move: Dict[str, Any],
        context,
        target_turn: Optional[int] = None,
    ) -> int:
        formula_hits = self._resolve_hits_formula(move.get('hits_formula'), target_turn)
        if formula_hits is not None:
            hits = formula_hits
        else:
            hits = self._coerce_int(move.get('hits', 1), default=1)

        ascension_mods = self._applicable_ascension_modifiers(
            move,
            context,
            required_keys=('hits',),
        )
        if ascension_mods:
            ascension_hits = self._coerce_damage_value(ascension_mods.get('hits'))
            if ascension_hits is not None:
                return ascension_hits

        return hits

    def _resolve_damage_formula(self, formula: Any, target_turn: Optional[int]) -> Optional[int]:
        if not isinstance(formula, dict):
            return None

        formula_type = formula.get('type')
        turn = int(target_turn or 1)

        if formula_type == 'linear_by_turn':
            base = self._coerce_int(formula.get('base'), default=0)
            per_turn = self._coerce_int(formula.get('per_turn'), default=0)
            turn_offset = self._coerce_int(formula.get('turn_offset'), default=0)
            return base + per_turn * max(0, turn + turn_offset)

        if formula_type == 'linear_after_turn':
            base = self._coerce_int(formula.get('base'), default=0)
            increment = self._coerce_int(formula.get('increment'), default=0)
            first_turn = self._coerce_int(formula.get('first_turn'), default=1)
            bonus = increment * max(0, turn - first_turn)
            max_bonus = self._coerce_damage_value(formula.get('max_bonus'))
            if max_bonus is not None:
                bonus = min(bonus, max_bonus)
            return base + bonus

        return None

    def _resolve_hits_formula(self, formula: Any, target_turn: Optional[int]) -> Optional[int]:
        if not isinstance(formula, dict):
            return None

        if formula.get('type') != 'ceil_turn_divisor':
            return None

        divisor = max(1, self._coerce_int(formula.get('divisor'), default=1))
        turn = max(1, int(target_turn or 1))
        hits = (turn + divisor - 1) // divisor
        min_hits = self._coerce_damage_value(formula.get('min_hits'))
        max_hits = self._coerce_damage_value(formula.get('max_hits'))
        if min_hits is not None:
            hits = max(hits, min_hits)
        if max_hits is not None:
            hits = min(hits, max_hits)
        return hits

    def _coerce_damage_value(self, value) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, dict):
            for key in ('max', 'damage', 'normal', 'base', 'min'):
                if key in value:
                    damage = self._coerce_damage_value(value[key])
                    if damage is not None:
                        return damage
            numeric_values = [
                damage
                for damage in (self._coerce_damage_value(v) for v in value.values())
                if damage is not None
            ]
            return max(numeric_values) if numeric_values else None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _coerce_int(self, value, default: int = 0) -> int:
        coerced = self._coerce_damage_value(value)
        return default if coerced is None else coerced

    def _context_ascension_level(self, context) -> int:
        if hasattr(context, 'game') and hasattr(context.game, 'ascension_level'):
            return int(context.game.ascension_level or 0)
        return int(getattr(context, 'ascension_level', 0) or 0)

    def _applicable_ascension_modifiers(
        self,
        move: Dict[str, Any],
        context,
        required_keys: Optional[Tuple[str, ...]] = None,
    ) -> Optional[Dict[str, Any]]:
        asc_mods = move.get('ascension_modifiers', {})
        if not isinstance(asc_mods, dict):
            return None

        thresholds = []
        for key in asc_mods:
            if not isinstance(key, str) or not key.endswith('+'):
                continue
            threshold_text = key[:-1]
            if threshold_text.isdigit():
                thresholds.append(int(threshold_text))

        ascension_level = self._context_ascension_level(context)
        for threshold in sorted(thresholds, reverse=True):
            if ascension_level < threshold:
                continue
            modifiers = asc_mods.get(f"{threshold}+")
            if not isinstance(modifiers, dict):
                continue
            if required_keys and not any(key in modifiers for key in required_keys):
                continue
            return modifiers

        return None

    def _apply_ascension_damage_modifiers(
        self,
        monster_name: str,
        move: Dict[str, Any],
        base_damage: int,
        context
    ) -> int:
        """
        Apply ascension-level modifiers to move damage.

        Args:
            monster_name: Name of the monster
            move: Move dictionary
            base_damage: Base damage value
            context: Decision context

        Returns:
            Damage adjusted for ascension level
        """
        try:
            # Get ascension level
            ascension_level = self._context_ascension_level(context)
            mods = self._applicable_ascension_modifiers(
                move,
                context,
                required_keys=('damage', 'damage_bonus'),
            )
            if not mods:
                return base_damage

            adjusted_damage = base_damage

            absolute_damage = self._coerce_damage_value(mods.get('damage'))
            if absolute_damage is not None:
                adjusted_damage = absolute_damage
                logger.debug(f"[ASCENSION_DAMAGE] {monster_name} A{ascension_level}+: "
                           f"damage {base_damage} -> {adjusted_damage}")
            elif 'damage_bonus' in mods:
                adjusted_damage += mods['damage_bonus']
                logger.debug(f"[ASCENSION_DAMAGE] {monster_name} A{ascension_level}+: "
                           f"damage {base_damage} + {mods['damage_bonus']} = {adjusted_damage}")

            return adjusted_damage

        except Exception as e:
            logger.warning(f"[ASCENSION_DAMAGE] Failed to apply modifiers for {monster_name}: {e}")
            return base_damage

    def _predict_future_strength(
        self,
        monster,
        current_turn: int,
        target_turn: int,
        current_strength: int,
        ascension_level: int = 0
    ) -> int:
        """
        Predict monster's Strength at a future turn, considering Ritual scaling.

        Args:
            monster: Monster object
            current_turn: Current turn number
            target_turn: Future turn to predict for
            current_strength: Monster's current Strength
            ascension_level: Game ascension level (affects Ritual values)

        Returns:
            Predicted Strength at target_turn
        """
        try:
            from spirecomm.data.loader import game_data_loader

            # Get monster's special mechanics
            monster_data = game_data_loader.get_enhanced_monster_data(monster.name)
            if not monster_data:
                return current_strength

            special_mechanics = monster_data.get('special_mechanics', {})
            if not special_mechanics:
                return current_strength

            mech_type = special_mechanics.get('type', '').lower()

            # Handle Ritual mechanics (Cultist)
            if 'ritual' in mech_type:
                ritual_value_dict = special_mechanics.get('ritual_value', {})
                # ritual_value can be a dict {'normal': 3, 'ascension_2+': 4, ...} or an int
                if isinstance(ritual_value_dict, dict):
                    # Select ritual value based on ascension level
                    if ascension_level >= 17:
                        ritual_value = ritual_value_dict.get('ascension_17+', 5)
                    elif ascension_level >= 2:
                        ritual_value = ritual_value_dict.get('ascension_2+', 4)
                    else:
                        ritual_value = ritual_value_dict.get('normal', 3)
                else:
                    ritual_value = int(ritual_value_dict) if ritual_value_dict else 3

                # Ritual triggers at end of each turn
                # Cultist: Turn 1 buff, Turn 1 end +3 Str, Turn 2 attack with +3, Turn 2 end +3 Str, etc.

                # Count how many times Ritual will trigger between current_turn and target_turn
                # Ritual triggers at end of turn, so:
                # - If we're on turn 1 predicting turn 2: Ritual triggers once (end of turn 1)
                # - If we're on turn 1 predicting turn 3: Ritual triggers twice (end of turn 1 and 2)

                ritual_triggers = target_turn - current_turn

                predicted_strength = current_strength + (ritual_triggers * ritual_value)

                logger.debug(f"[RITUAL_PREDICTION] {monster.name}: "
                           f"ascension={ascension_level}, ritual_value={ritual_value}, "
                           f"current_str={current_strength}, triggers={ritual_triggers}, "
                           f"predicted_str={predicted_strength}")

                return predicted_strength

            # Handle one-time Strength gains (Louse Grow, Fungi Beast Grow)
            # These need ascension-aware prediction too
            if 'strength_scaler' in mech_type or 'curl_up' in mech_type:
                # Check moves for Grow abilities with ascension modifiers
                moves_data = monster_data.get('moves', [])
                strength_per_trigger = 0

                for move in moves_data:
                    if move.get('name', '').lower() in ['grow', 'growth']:
                        base_str_gain = move.get('strength_gain', 0)
                        if base_str_gain > 0:
                            # Check for ascension modifiers
                            if 'ascension_modifiers' in move:
                                asc_mods = move['ascension_modifiers']
                                # Apply highest applicable ascension modifier
                                if ascension_level >= 17 and '17+' in asc_mods:
                                    strength_per_trigger = asc_mods['17+'].get('strength_gain', base_str_gain)
                                elif ascension_level >= 2 and '2+' in asc_mods:
                                    strength_per_trigger = asc_mods['2+'].get('strength_gain', base_str_gain)
                                else:
                                    strength_per_trigger = base_str_gain
                            else:
                                strength_per_trigger = base_str_gain
                            break

                # For one-time gains, we assume monster has already used Grow by turn 2+
                # This is a simplification - in reality, need to track if Grow was used
                if target_turn > current_turn:
                    # Assume Grow was used on turn 1 or 2
                    predicted_strength = current_strength + strength_per_trigger
                    logger.debug(f"[GROW_PREDICTION] {monster.name}: ascension={ascension_level}, "
                               f"strength_gain={strength_per_trigger}, predicted_str={predicted_strength}")
                    return predicted_strength

            # Handle other strength scaling mechanics
            elif mech_type == 'strength_scaler':
                strength_per_turn = special_mechanics.get('strength_per_turn', 0)
                if strength_per_turn > 0:
                    turns_passed = target_turn - current_turn
                    return current_strength + (turns_passed * strength_per_turn)

            # Default: no strength growth predicted
            return current_strength

        except Exception as e:
            logger.warning(f"[STRENGTH_PREDICTION] Failed for {monster.name}: {e}")
            return current_strength

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

    def _check_forced_classification(self, monster_hints: Dict[str, 'MonsterTimingHints']) -> Optional[TurnTiming]:
        """
        Check if any monster has forced classification via 'always_classify_as'.

        Args:
            monster_hints: Dictionary of monster name to timing hints

        Returns:
            TurnTiming if forced classification found, None otherwise
        """
        for monster_name, hints in monster_hints.items():
            if hasattr(hints, 'raw_data') and hints.raw_data:
                always_classify = hints.raw_data.get('always_classify_as')
                if always_classify:
                    try:
                        return TurnTiming(always_classify)
                    except ValueError:
                        logger.warning(f"[TIMING_CLASSIFIER] Invalid forced classification: {always_classify}")
        return None

    def _is_safe_intent(
        self,
        current_intent: str,
        next_intent: str,
        hints: MonsterTimingHints
    ) -> bool:
        """Check if intent indicates a safe turn."""
        current_intent = self._intent_name(current_intent)
        next_intent = self._intent_name(next_intent)

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
        current_intent = self._intent_name(current_intent)

        # High damage attack
        if self._is_attack_intent(current_intent) and current_damage > 15:
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
                anchored_predictions = game_data_loader.predict_monster_moves(
                    monster.name,
                    current_turn,
                    hp_percent,
                )
                for turn_offset in range(1, 3):
                    target_turn = current_turn + turn_offset
                    prediction = self._select_prediction_for_turn(
                        anchored_predictions,
                        monster.name,
                        target_turn,
                        hp_percent,
                    )

                    if prediction:
                        move = prediction.get('move', {})
                        intent = move.get('intent', '').upper()
                        if 'ATTACK' not in intent:
                            continue

                        damage = self._resolve_move_damage(
                            monster.name, move, context, target_turn=target_turn)
                        damage = self._apply_ascension_damage_modifiers(
                            monster.name,
                            move,
                            damage,
                            context,
                        )
                        hits = self._resolve_move_hits(move, context, target_turn=target_turn)
                        predicted_strength = self._predict_attack_strength(
                            monster,
                            anchored_predictions,
                            current_turn,
                            target_turn,
                            context,
                        )

                        if (damage + predicted_strength) * hits >= 20:
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
