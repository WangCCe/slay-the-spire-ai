"""
Enhanced Monster Database with comprehensive Wiki data.

This module provides detailed monster information extracted from the Slay the Spire Fandom Wiki,
including moves, patterns, special mechanics, and threat profiles for proactive AI decision-making.

Key features:
- Move pattern prediction for future threat assessment
- Special mechanics classification (summoner, hibernation, phase_change, etc.)
- Multi-dimensional threat profiles (base, scaling, special situations)
- Recommended strategies for each monster type
"""

import json
import os
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from spirecomm.ai.intent_utils import intent_is_attack, intent_tokens
from spirecomm.ai.monster_names import LIVE_MONSTER_ID_TO_WIKI_NAME, normalize_monster_id


class EnhancedMonsterDatabase:
    """
    Enhanced monster database with Wiki-extracted data.

    Loads monster data from JSON files and provides query interfaces for:
    - Move patterns and predictions
    - Special mechanics
    - Threat profiles
    - HP ranges with ascension modifiers
    """

    def __init__(self):
        """Initialize the database by loading all monster data files."""
        self._data = {}
        self._load_all_data()

    def _load_all_data(self):
        """Load monster data from all JSON files."""
        logger = logging.getLogger(__name__)
        # Base path for monster data
        base_path = Path(__file__).parent.parent.parent / "data" / "monster_wiki_data"

        # Load all monster data files
        data_files = [
            "act1_elites_bosses.json",
            "act2_elites_bosses.json",
            "act3_elites_bosses.json",
            "act1_normal_monsters.json",  # Added: Act 1 normal monsters (Cultist, Jaw Worm, etc.)
            "act2_normal_monsters.json",
            "act3_normal_monsters.json",
        ]

        for filename in data_files:
            filepath = base_path / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        monster_data = json.load(f)
                        # Handle both dict format (elites/bosses) and list format (normal monsters)
                        if isinstance(monster_data, dict):
                            # Dict format: {monster_name: monster_data}
                            self._data.update(monster_data)
                        elif isinstance(monster_data, list):
                            # List format: [{monster_data}, {monster_data}, ...]
                            # Use 'name' field as key
                            for monster in monster_data:
                                if 'name' in monster:
                                    self._data[monster['name']] = monster
                        loaded_count = len(monster_data) if isinstance(monster_data, dict) else len(monster_data)
                        logger.info("Loaded %s monsters from %s", loaded_count, filename)
                except Exception as e:
                    logger.warning("Failed to load %s: %s", filename, e)
            else:
                logger.warning("Monster data file not found: %s", filepath)

    def get_monster_data(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete monster data by name.

        Args:
            monster_name: Name of the monster (e.g., "Cultist", "Lagavulin", "The Champ")

        Returns:
            Dictionary with monster data, or None if not found
        """
        if not str(monster_name or "").strip():
            return None

        # Try exact match first
        if monster_name in self._data:
            return self._data[monster_name]

        mapped_name = LIVE_MONSTER_ID_TO_WIKI_NAME.get(normalize_monster_id(monster_name))
        if mapped_name in self._data:
            return self._data[mapped_name]

        # Some mechanics records refer to spawned monsters by monster_id.
        normalized_monster_id = normalize_monster_id(monster_name)
        for value in self._data.values():
            if normalize_monster_id(value.get("monster_id", "")) == normalized_monster_id:
                return value

        # Try case-insensitive match
        for key, value in self._data.items():
            if key.lower() == monster_name.lower():
                return value

        # Try explicit aliases from data records
        for value in self._data.values():
            aliases = value.get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    if str(alias).lower() == monster_name.lower():
                        return value

        # Try unambiguous partial match (for names like "The Champ" vs "Champ").
        normalized_name = monster_name.lower()
        partial_matches = [
            value
            for key, value in self._data.items()
            if normalized_name in key.lower() or key.lower() in normalized_name
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]

        return None

    def get_moves(self, monster_name: str) -> List[Dict[str, Any]]:
        """
        Get list of moves for a monster.

        Args:
            monster_name: Name of the monster

        Returns:
            List of move dictionaries with move_id, name, intent, damage, effect
        """
        monster_data = self.get_monster_data(monster_name)
        if monster_data and "moves" in monster_data:
            return monster_data["moves"]
        return []

    def get_move_by_id(self, monster_name: str, move_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific move by ID.

        Args:
            monster_name: Name of the monster
            move_id: Move ID (0-indexed)

        Returns:
            Move dictionary or None if not found
        """
        moves = self.get_moves(monster_name)
        for move in moves:
            if move.get("move_id") == move_id:
                return move
        return None

    def get_move_by_name(self, monster_name: str, move_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific move by name.

        Args:
            monster_name: Name of the monster
            move_name: Move name

        Returns:
            Move dictionary or None if not found
        """
        moves = self.get_moves(monster_name)
        for move in moves:
            if move.get("name") == move_name:
                return move
        return None

    def get_pattern(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get move pattern information for a monster.

        Args:
            monster_name: Name of the monster

        Returns:
            Pattern dictionary with description, probabilities, constraints, phases
        """
        monster_data = self.get_monster_data(monster_name)
        if monster_data and "pattern" in monster_data:
            return monster_data["pattern"]
        return None

    def get_special_mechanics(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get special mechanics for a monster.

        Args:
            monster_name: Name of the monster

        Returns:
            Special mechanics dictionary with type and additional details
        """
        monster_data = self.get_monster_data(monster_name)
        if monster_data and "special_mechanics" in monster_data:
            return monster_data["special_mechanics"]
        return None

    def get_threat_profile(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get threat profile for a monster.

        Args:
            monster_name: Name of the monster

        Returns:
            Threat profile dictionary with base_threat, scaling_threat, etc.
        """
        monster_data = self.get_monster_data(monster_name)
        if monster_data and "threat_profile" in monster_data:
            return monster_data["threat_profile"]
        return None

    def get_hp_range(self, monster_name: str, ascension_level: int = 0) -> Tuple[int, int]:
        """
        Get HP range for a monster with ascension modifiers.

        Args:
            monster_name: Name of the monster
            ascension_level: Current ascension level (default 0)

        Returns:
            Tuple of (min_hp, max_hp)
        """
        monster_data = self.get_monster_data(monster_name)
        if not monster_data or "hp_ranges" not in monster_data:
            return (50, 60)  # Default fallback

        hp_ranges = monster_data["hp_ranges"]

        # Check ascension modifiers
        for asc_key in sorted(hp_ranges.keys(), reverse=True):
            if asc_key.startswith("ascension_"):
                asc_threshold = int(asc_key.split("_")[1].split("+")[0])
                if ascension_level >= asc_threshold:
                    range_data = hp_ranges[asc_key]
                    hp_range = self._extract_hp_range_tuple(range_data, monster_name)
                    if hp_range:
                        return hp_range

        # Default to normal range
        if "normal" in hp_ranges:
            hp_range = self._extract_hp_range_tuple(hp_ranges["normal"], monster_name)
            if hp_range:
                return hp_range

        hp_range = self._extract_hp_range_tuple(hp_ranges, monster_name)
        if hp_range:
            return hp_range

        return (50, 60)  # Final fallback

    def _extract_hp_range_tuple(
        self,
        range_data: Any,
        monster_name: str,
    ) -> Optional[Tuple[int, int]]:
        if not isinstance(range_data, dict):
            return None

        if "min" in range_data and "max" in range_data:
            return (range_data["min"], range_data["max"])

        normalized_name = str(monster_name or "").lower()
        for key, nested_range in range_data.items():
            if str(key).lower() != normalized_name:
                continue
            return self._extract_hp_range_tuple(nested_range, monster_name)
        return None

    def get_monster_type(self, monster_name: str) -> str:
        """
        Get monster type (normal, elite, boss).

        Args:
            monster_name: Name of the monster

        Returns:
            Monster type string
        """
        monster_data = self.get_monster_data(monster_name)
        if monster_data and "monster_type" in monster_data:
            return monster_data["monster_type"]
        return "normal"  # Default

    def predict_next_moves(
        self,
        monster_name: str,
        current_turn: int,
        monster_hp_percent: float,
        ascension_level: int = 0,
        other_enemy_count: Optional[int] = None,
        other_enemy_names: Optional[List[str]] = None,
        same_monster_index: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Predict next moves for a monster based on its pattern.

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn (1-indexed)
            monster_hp_percent: Current HP as percentage (0.0 to 1.0)
            ascension_level: Current ascension level (default 0)
            other_enemy_count: Number of other live enemies, if known
            other_enemy_names: Names of other live enemies, if known
            same_monster_index: Zero-based position among live monsters with the same name

        Returns:
            List of predicted moves for next 3 turns
        """
        pattern = self.get_pattern(monster_name)
        moves = self.get_moves(monster_name)
        special_mechanics = self.get_special_mechanics(monster_name)

        if not pattern or not moves:
            return []

        predictions = []

        forced_move = self._hp_forced_move(pattern, monster_hp_percent)

        # Check for HP-triggered forced moves.
        if forced_move:
            self._append_named_move_prediction(
                predictions,
                monster_name,
                forced_move,
                current_turn,
                confidence=1.0,
            )
            probability_table = pattern.get("probabilities") or pattern.get("move_probabilities")
            prediction_limit = pattern.get("prediction_limit", 2)
            if isinstance(probability_table, dict):
                for i in range(1, 3):
                    target_turn = current_turn + i
                    ascension_probs = self._ascension_pattern_override(
                        pattern,
                        "probabilities",
                        ascension_level,
                    )
                    probs = (
                        ascension_probs
                        if isinstance(ascension_probs, dict)
                        else self._select_probability_table(
                            probability_table,
                            target_turn,
                            monster_hp_percent,
                            other_enemy_names,
                        )
                    )
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        probs,
                        target_turn,
                        limit=prediction_limit,
                    )

        # Check for shared boss records with per-member deterministic patterns.
        elif "member_patterns" in pattern:
            member_name, member_pattern = self._select_member_pattern(
                pattern["member_patterns"],
                monster_name,
            )
            if member_pattern:
                self._append_sequence_predictions(
                    predictions,
                    monster_name,
                    member_pattern.get("move_sequence", []),
                    current_turn,
                    member_name=member_name,
                )

        # Check for move_sequence
        elif "move_sequence" in pattern:
            move_ids = pattern["move_sequence"]
            sequence_length = len(move_ids)
            for i in range(3):
                next_index = (current_turn + i - 1) % sequence_length
                move_id = move_ids[next_index]
                move = self.get_move_by_id(monster_name, move_id)
                if move:
                    predictions.append({
                        "turn": current_turn + i,
                        "move": move,
                        "confidence": 1.0  # Certain prediction
                    })

        # Check for explicit HP-threshold mode sequences (e.g., Guardian)
        elif "hp_threshold_modes" in pattern:
            modes = pattern["hp_threshold_modes"]
            threshold = (
                pattern.get("defensive_trigger", {}).get("hp_below")
                if isinstance(pattern.get("defensive_trigger"), dict)
                else None
            )
            mode_key = "low_hp" if threshold is not None and monster_hp_percent < threshold else "high_hp"
            sequence = modes.get(mode_key) or modes.get("normal") or []
            self._append_sequence_predictions(predictions, monster_name, sequence, current_turn)

        # Check for turn-threshold patterns (e.g., Giant Head countdown into It Is Time)
        elif "turn_thresholds" in pattern:
            thresholds = self._ascension_adjusted_turn_thresholds(
                pattern.get("turn_thresholds", []),
                special_mechanics,
                ascension_level,
            )
            for i in range(3):
                target_turn = current_turn + i
                threshold = self._select_turn_threshold(thresholds, target_turn)
                if not threshold:
                    continue

                move_name = threshold.get("move")
                if move_name:
                    move = self.get_move_by_name(monster_name, move_name)
                    if move:
                        predictions.append({
                            "turn": target_turn,
                            "move": move,
                            "confidence": threshold.get("confidence", 1.0),
                        })
                    continue

                self._append_probability_predictions(
                    predictions,
                    moves,
                    threshold.get("probabilities", {}),
                    target_turn,
                    limit=threshold.get("prediction_limit", pattern.get("prediction_limit", 2)),
                )

        # Check for enemy-count-dependent probability tables (e.g., Gremlin Leader)
        elif "probability_by_enemy_count" in pattern:
            probabilities = self._select_probability_by_enemy_count(
                pattern.get("probability_by_enemy_count", {}),
                other_enemy_count,
            )
            self._append_probability_predictions(
                predictions,
                moves,
                probabilities,
                current_turn,
                limit=pattern.get("prediction_limit", 2),
            )

        # Check for deterministic moves chosen by whether other enemies are alive.
        elif "enemy_count_moves" in pattern:
            move_name = self._select_move_by_enemy_count(
                pattern.get("enemy_count_moves", {}),
                other_enemy_count,
            )
            if move_name:
                self._append_named_move_prediction(
                    predictions,
                    monster_name,
                    move_name,
                    current_turn,
                    confidence=1.0,
                )

        # Check for Collector probabilities that depend on whether Torch Heads are alive.
        elif (
            other_enemy_names is not None
            and "probabilities_with_torch_heads" in pattern
            and "probabilities_with_dead_torch_head" in pattern
        ):
            if current_turn == 1 and pattern.get("initial_move"):
                self._append_named_move_prediction(
                    predictions,
                    monster_name,
                    pattern["initial_move"],
                    current_turn,
                    confidence=1.0,
                )
            elif current_turn == 4:
                self._append_named_move_prediction(
                    predictions,
                    monster_name,
                    "Mega Debuff",
                    current_turn,
                    confidence=1.0,
                )
            else:
                probabilities = (
                    pattern["probabilities_with_torch_heads"]
                    if self._torch_head_count(other_enemy_names) >= 2
                    else pattern["probabilities_with_dead_torch_head"]
                )
                self._append_probability_predictions(
                    predictions,
                    moves,
                    probabilities,
                    current_turn,
                limit=len(probabilities),
            )

        # Check for Sentry alternating pattern, whose opener depends on encounter position.
        elif pattern.get("move_pattern") == "alternating":
            sequence = self._alternating_move_sequence(
                monster_name,
                moves,
                pattern,
                other_enemy_names,
                same_monster_index,
            )
            self._append_sequence_predictions(
                predictions,
                monster_name,
                sequence,
                current_turn,
            )

        # Check for phase-based patterns
        elif "phases" in pattern:
            current_phase = self._get_threshold_phase(pattern["phases"], monster_hp_percent)
            transition_phase = self._get_transition_phase_after_threshold(
                pattern["phases"],
                monster_hp_percent,
            )
            active_phase = current_phase or self._get_pre_threshold_phase(
                pattern["phases"],
                monster_hp_percent,
            )

            if transition_phase:
                transition_move = transition_phase.get("transition_move")
                if transition_move:
                    self._append_named_move_prediction(
                        predictions,
                        monster_name,
                        transition_move,
                        current_turn,
                        confidence=1.0,
                    )
                for i, move_name in enumerate(transition_phase.get("pattern", [])):
                    if move_name != "random":
                        self._append_named_move_prediction(
                            predictions,
                            monster_name,
                            move_name,
                            current_turn + i + 1,
                            confidence=0.9,
                        )

            elif current_phase and "pattern" in current_phase:
                # Handle simple patterns like ["Execute", "random", "random", "Execute"]
                pattern_list = current_phase["pattern"]
                for i, move_name in enumerate(pattern_list):
                    if move_name != "random":
                        # Find move by name
                        for move in moves:
                            if move["name"] == move_name:
                                predictions.append({
                                    "turn": current_turn + i,
                                    "move": move,
                                    "confidence": 0.9
                                })
                                break

            elif active_phase and "probabilities" in active_phase:
                for i in range(3):
                    target_turn = current_turn + i
                    forced_move = self._phase_forced_move(active_phase, target_turn)
                    if forced_move:
                        self._append_named_move_prediction(
                            predictions,
                            monster_name,
                            forced_move,
                            target_turn,
                            confidence=1.0,
                        )
                        continue

                    self._append_probability_predictions(
                        predictions,
                        moves,
                        active_phase.get("probabilities", {}),
                        target_turn,
                        limit=pattern.get("prediction_limit", 2),
                    )

        # Check for simple one-move monsters (e.g., Spike Slime (S))
        elif "only_move" in pattern:
            self._append_sequence_predictions(predictions, monster_name, [pattern["only_move"]], current_turn)

        # Check for explicit turn-one probabilities with a separate later pattern.
        elif "turn_1_probabilities" in pattern:
            ascension_opening = self._move_sequence_from_value(
                self._ascension_pattern_override(pattern, "opening", ascension_level)
            )
            for i in range(3):
                target_turn = current_turn + i
                if 1 <= target_turn <= len(ascension_opening):
                    self._append_named_move_prediction(
                        predictions,
                        monster_name,
                        ascension_opening[target_turn - 1],
                        target_turn,
                        confidence=1.0,
                    )
                    continue

                if target_turn == 1:
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        pattern.get("turn_1_probabilities", {}),
                        target_turn,
                        limit=pattern.get("prediction_limit", 2),
                    )
                    continue

                subsequent_probs = pattern.get("subsequent_probabilities")
                if isinstance(subsequent_probs, dict):
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        subsequent_probs,
                        target_turn,
                        limit=pattern.get("prediction_limit", 2),
                    )
                    continue

                if pattern.get("subsequent_pattern") == "alternating":
                    move_names = list(pattern.get("turn_1_probabilities", {}).keys())
                    if not move_names:
                        continue
                    move_name = move_names[(target_turn - 1) % len(move_names)]
                    move = self.get_move_by_name(monster_name, move_name)
                    if move:
                        predictions.append({
                            "turn": target_turn,
                            "move": move,
                            "confidence": 0.5,
                        })

        # Check for probabilities (less certain prediction)
        elif "probabilities" in pattern or "move_probabilities" in pattern:
            probability_table = pattern.get("probabilities") or pattern.get("move_probabilities")
            prediction_limit = pattern.get("prediction_limit", 2)
            if "initial_move" in pattern:
                for i in range(3):
                    target_turn = current_turn + i
                    if target_turn == 1:
                        self._append_named_move_prediction(
                            predictions,
                            monster_name,
                            pattern["initial_move"],
                            target_turn,
                            confidence=1.0,
                        )
                        continue

                    ascension_probs = self._ascension_pattern_override(
                        pattern,
                        "probabilities",
                        ascension_level,
                    )
                    probs = (
                        ascension_probs
                        if isinstance(ascension_probs, dict)
                        else self._select_probability_table(
                            probability_table,
                            target_turn,
                            monster_hp_percent,
                            other_enemy_names,
                        )
                    )
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        probs,
                        target_turn,
                        limit=prediction_limit,
                    )
            else:
                ascension_probs = self._ascension_pattern_override(
                    pattern,
                    "probabilities",
                    ascension_level,
                )
                probs = (
                    ascension_probs
                    if isinstance(ascension_probs, dict)
                    else self._select_probability_table(
                        probability_table,
                        current_turn,
                        monster_hp_percent,
                        other_enemy_names,
                    )
                )
                self._append_probability_predictions(
                    predictions,
                    moves,
                    probs,
                    current_turn,
                    limit=prediction_limit,
                )

        # Check for opening + subsequent_pattern format (e.g., Cultist)
        elif "opening" in pattern and "subsequent_pattern" in pattern:
            opening_moves = pattern["opening"]
            subsequent_pattern = pattern["subsequent_pattern"]

            # Parse subsequent pattern to extract move name
            # Format: "Dark Strike every turn" -> "Dark Strike"
            # Split by "every" and take first part, then strip
            if isinstance(subsequent_pattern, str):
                parts = subsequent_pattern.split(" every")
                subsequent_move_name = parts[0].strip() if parts else None
            else:
                subsequent_move_name = None

            for i in range(3):
                target_turn = current_turn + i

                # Turn 1: use opening move
                if target_turn == 1 and opening_moves:
                    move_name = opening_moves[0]
                    move = self.get_move_by_name(monster_name, move_name)
                    if move:
                        predictions.append({
                            "turn": target_turn,
                            "move": move,
                            "confidence": 1.0
                        })
                # Turn 2+: use subsequent pattern
                elif subsequent_move_name:
                    move = self.get_move_by_name(monster_name, subsequent_move_name)
                    if move:
                        predictions.append({
                            "turn": target_turn,
                            "move": move,
                            "confidence": 1.0
                        })

        # Check for opening + alternating phase probabilities format (e.g., normal Chosen)
        elif "opening" in pattern:
            opening_moves = self._move_sequence_from_value(
                self._ascension_pattern_override(pattern, "opening", ascension_level)
            )
            if not opening_moves:
                opening_moves = self._move_sequence_from_value(pattern["opening"])
            opening_length = len(opening_moves)
            then_moves = pattern.get("then", [])
            if not isinstance(then_moves, list):
                then_moves = []
            fixed_sequence = opening_moves + then_moves
            alternating_moves = pattern.get("alternating", [])
            if not isinstance(alternating_moves, list):
                alternating_moves = []

            for i in range(3):
                target_turn = current_turn + i

                if 1 <= target_turn <= len(fixed_sequence):
                    move = self.get_move_by_name(monster_name, fixed_sequence[target_turn - 1])
                    if move:
                        predictions.append({
                            "turn": target_turn,
                            "move": move,
                            "confidence": 1.0
                        })
                    continue

                if alternating_moves:
                    alternating_index = (target_turn - len(fixed_sequence) - 1) % len(alternating_moves)
                    move = self.get_move_by_name(monster_name, alternating_moves[alternating_index])
                    if move:
                        predictions.append({
                            "turn": target_turn,
                            "move": move,
                            "confidence": 1.0
                        })
                    continue

                subsequent_cycle = self._move_sequence_from_value(
                    self._ascension_pattern_override(pattern, "subsequent_cycle", ascension_level)
                )
                if not subsequent_cycle:
                    subsequent_cycle = self._move_sequence_from_value(pattern.get("subsequent_cycle"))
                if subsequent_cycle and target_turn > len(fixed_sequence):
                    cycle_index = (target_turn - len(fixed_sequence) - 1) % len(subsequent_cycle)
                    self._append_named_move_prediction(
                        predictions,
                        monster_name,
                        subsequent_cycle[cycle_index],
                        target_turn,
                        confidence=1.0,
                    )
                    continue

                pre_entangle_sequence = self._pre_entangle_sequence(pattern, ascension_level)
                if pre_entangle_sequence and target_turn > opening_length:
                    sequence_index = (target_turn - opening_length - 1) % len(pre_entangle_sequence)
                    entangle_chance = pattern.get("entangle_trigger_chance", 0)
                    if not isinstance(entangle_chance, (int, float)):
                        entangle_chance = 0
                    self._append_named_move_prediction(
                        predictions,
                        monster_name,
                        pre_entangle_sequence[sequence_index],
                        target_turn,
                        confidence=max(0.0, 1.0 - entangle_chance),
                    )
                    if entangle_chance > 0:
                        self._append_named_move_prediction(
                            predictions,
                            monster_name,
                            "Entangle",
                            target_turn,
                            confidence=entangle_chance,
                        )
                    continue

                turn_options = pattern.get(f"turn_{target_turn}_options", [])
                if isinstance(turn_options, list) and turn_options:
                    confidence = 1.0 / len(turn_options)
                    for move_name in turn_options:
                        if not isinstance(move_name, str):
                            continue
                        self._append_named_move_prediction(
                            predictions,
                            monster_name,
                            move_name,
                            target_turn,
                            confidence=confidence,
                        )
                    continue

                phase_key = self._phase_probability_key(pattern, target_turn, opening_length)
                if phase_key:
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        pattern.get(phase_key, {}),
                        target_turn,
                    )

        # Check for simple named move cycles
        elif "move_cycle" in pattern:
            self._append_sequence_predictions(predictions, monster_name, pattern["move_cycle"], current_turn)

        # Special handling for initial moves
        if "initial_move" in pattern and current_turn == 1:
            initial_move_name = pattern["initial_move"]
            already_predicted = any(
                prediction.get("turn") == current_turn
                and prediction.get("move", {}).get("name") == initial_move_name
                for prediction in predictions
            )
            if not already_predicted:
                for move in moves:
                    if move["name"] == initial_move_name:
                        predictions.insert(0, {
                            "turn": current_turn,
                            "move": move,
                            "confidence": 1.0
                        })
                        break

        return self._limit_predictions_with_boundary_ties(predictions)

    def _get_threshold_phase(
        self,
        phases: List[Dict[str, Any]],
        monster_hp_percent: float,
    ) -> Optional[Dict[str, Any]]:
        for phase in phases:
            if "hp_threshold" in phase and monster_hp_percent < (phase["hp_threshold"] / 100.0):
                return phase
        return None

    def _get_pre_threshold_phase(
        self,
        phases: List[Dict[str, Any]],
        monster_hp_percent: float,
    ) -> Optional[Dict[str, Any]]:
        for phase in phases:
            threshold = phase.get("hp_threshold")
            if isinstance(threshold, (int, float)) and monster_hp_percent >= threshold / 100.0:
                return phase
        return None

    def _get_transition_phase_after_threshold(
        self,
        phases: List[Dict[str, Any]],
        monster_hp_percent: float,
    ) -> Optional[Dict[str, Any]]:
        for idx, phase in enumerate(phases):
            if "hp_threshold" not in phase:
                continue
            if monster_hp_percent >= (phase["hp_threshold"] / 100.0):
                continue
            for next_phase in phases[idx + 1:]:
                if next_phase.get("transition_move"):
                    return next_phase
        return None

    def _phase_forced_move(self, phase: Dict[str, Any], target_turn: int) -> Optional[str]:
        constraints = phase.get("constraints", [])
        if not isinstance(constraints, list):
            return None

        normalized_constraints = {str(constraint).lower() for constraint in constraints}
        if "taunt_every_4_turns" in normalized_constraints and target_turn % 4 == 0:
            return "Taunt"
        return None

    def _hp_forced_move(
        self,
        pattern: Dict[str, Any],
        monster_hp_percent: float,
    ) -> Optional[str]:
        constraints = pattern.get("constraints", [])
        if not isinstance(constraints, list):
            return None

        normalized_constraints = {str(constraint).lower() for constraint in constraints}
        if (
            "haste_once_below_50_percent_hp" in normalized_constraints
            and monster_hp_percent < 0.5
        ):
            return "Haste"
        return None

    def _limit_predictions_with_boundary_ties(
        self,
        predictions: List[Dict[str, Any]],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        if len(predictions) <= limit:
            return predictions

        limited = predictions[:limit]
        boundary_turn = limited[-1].get("turn")
        for prediction in predictions[limit:]:
            if prediction.get("turn") != boundary_turn:
                break
            limited.append(prediction)
        return limited

    def _append_named_move_prediction(
        self,
        predictions: List[Dict[str, Any]],
        monster_name: str,
        move_name: str,
        turn: int,
        confidence: float,
    ) -> None:
        move = self.get_move_by_name(monster_name, move_name)
        if move:
            predictions.append({
                "turn": turn,
                "move": move,
                "confidence": confidence,
            })

    def _append_sequence_predictions(
        self,
        predictions: List[Dict[str, Any]],
        monster_name: str,
        sequence: List[str],
        current_turn: int,
        member_name: Optional[str] = None,
    ) -> None:
        if not isinstance(sequence, list) or not sequence:
            return

        sequence_length = len(sequence)
        for i in range(3):
            target_turn = current_turn + i
            move_name = sequence[(target_turn - 1) % sequence_length]
            move = self._get_move_by_name_for_member(monster_name, move_name, member_name)
            if not move:
                continue
            predictions.append({
                "turn": target_turn,
                "move": move,
                "confidence": 1.0,
            })

    def _select_member_pattern(
        self,
        member_patterns: Dict[str, Any],
        monster_name: str,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        if not isinstance(member_patterns, dict):
            return None, None

        normalized_name = str(monster_name or "").lower()
        for member_name, member_pattern in member_patterns.items():
            normalized_member = str(member_name).lower()
            if normalized_member == normalized_name or normalized_member in normalized_name:
                if isinstance(member_pattern, dict):
                    return member_name, member_pattern
        return None, None

    def _get_move_by_name_for_member(
        self,
        monster_name: str,
        move_name: str,
        member_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        moves = self.get_moves(monster_name)
        normalized_member = str(member_name or "").lower()
        for move in moves:
            if move.get("name") != move_name:
                continue
            if normalized_member and str(move.get("monster", "")).lower() != normalized_member:
                continue
            return move
        return None

    def _select_turn_threshold(self, thresholds: List[Dict[str, Any]], target_turn: int) -> Optional[Dict[str, Any]]:
        if not isinstance(thresholds, list):
            return None

        selected = None
        for threshold in thresholds:
            if not isinstance(threshold, dict):
                continue
            from_turn = threshold.get("from_turn", 1)
            if target_turn >= from_turn and (selected is None or from_turn >= selected.get("from_turn", 1)):
                selected = threshold
        return selected

    def _ascension_adjusted_turn_thresholds(
        self,
        thresholds: List[Dict[str, Any]],
        special_mechanics: Optional[Dict[str, Any]],
        ascension_level: int,
    ) -> List[Dict[str, Any]]:
        if not isinstance(thresholds, list):
            return []
        if (
            not isinstance(special_mechanics, dict)
            or ascension_level < 18
            or not isinstance(special_mechanics.get("ascension_18_first_turn"), int)
        ):
            return thresholds

        first_turn = special_mechanics["ascension_18_first_turn"]
        adjusted = []
        for threshold in thresholds:
            if not isinstance(threshold, dict):
                adjusted.append(threshold)
                continue
            threshold_copy = dict(threshold)
            if threshold_copy.get("move") == "It Is Time":
                threshold_copy["from_turn"] = first_turn
            adjusted.append(threshold_copy)
        return adjusted

    def _phase_probability_key(self, pattern: Dict[str, Any], target_turn: int, opening_length: int) -> Optional[str]:
        phase_keys = sorted(
            key for key in pattern
            if key.startswith("phase_") and key.endswith("_probabilities")
        )
        if not phase_keys or target_turn <= opening_length:
            return None

        phase_index = (target_turn - opening_length - 1) % len(phase_keys)
        return phase_keys[phase_index]

    def _ascension_pattern_override(
        self,
        pattern: Dict[str, Any],
        suffix: str,
        ascension_level: int,
    ) -> Any:
        if not isinstance(pattern, dict):
            return None

        selected_threshold = None
        selected_value = None
        for key, value in pattern.items():
            if not isinstance(key, str):
                continue
            match = re.match(rf"ascension_(\d+)\+_{re.escape(suffix)}$", key)
            if not match:
                continue
            threshold = int(match.group(1))
            if ascension_level < threshold:
                continue
            if selected_threshold is None or threshold > selected_threshold:
                selected_threshold = threshold
                selected_value = value
        return selected_value

    def _move_sequence_from_value(self, value: Any) -> List[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [move for move in value if isinstance(move, str)]
        return []

    def _pre_entangle_sequence(
        self,
        pattern: Dict[str, Any],
        ascension_level: int,
    ) -> List[str]:
        pre_entangle = pattern.get("pre_entangle_pattern")
        if not isinstance(pre_entangle, dict):
            return []

        if ascension_level >= 17:
            sequence = pre_entangle.get("ascension_17+")
            if isinstance(sequence, list):
                return self._move_sequence_from_value(sequence)

        sequence = pre_entangle.get("below_A17")
        if isinstance(sequence, list):
            return self._move_sequence_from_value(sequence)
        return []

    def _append_probability_predictions(
        self,
        predictions: List[Dict[str, Any]],
        moves: List[Dict[str, Any]],
        probabilities: Dict[str, Any],
        target_turn: int,
        limit: int = 2,
    ) -> None:
        if not isinstance(probabilities, dict):
            return

        sorted_probs = sorted(
            (
                (move_name, prob)
                for move_name, prob in probabilities.items()
                if isinstance(prob, (int, float))
            ),
            key=lambda x: x[1],
            reverse=True
        )
        if limit <= 0:
            return
        if len(sorted_probs) > limit:
            boundary_probability = sorted_probs[limit - 1][1]
            sorted_probs = [
                item for item in sorted_probs
                if item[1] >= boundary_probability
            ]
        for move_name, prob in sorted_probs:
            for move in moves:
                if self._normalize_move_name(move["name"]) == self._normalize_move_name(move_name):
                    predictions.append({
                        "turn": target_turn,
                        "move": move,
                        "confidence": prob
                    })
                    break

    def _normalize_move_name(self, move_name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", move_name.lower()).strip("_")

    def _torch_head_count(self, monster_names: List[str]) -> int:
        return sum(
            1
            for name in monster_names
            if self._normalize_move_name(str(name or "")) in {"torch_head", "torchhead"}
        )

    def _alternating_move_sequence(
        self,
        monster_name: str,
        moves: List[Dict[str, Any]],
        pattern: Dict[str, Any],
        other_enemy_names: Optional[List[str]],
        same_monster_index: Optional[int],
    ) -> List[str]:
        if self._normalize_move_name(monster_name) != "sentry":
            return []

        move_names = [move.get("name") for move in moves if isinstance(move.get("name"), str)]
        if set(move_names) != {"Beam", "Bolt"}:
            return []

        normalized_other_names = {
            self._normalize_move_name(str(name or ""))
            for name in (other_enemy_names or [])
        }
        if "spheric_guardian" in normalized_other_names:
            start_move = "Bolt"
        elif same_monster_index is None:
            return []
        elif same_monster_index % 2 == 1:
            start_move = "Beam"
        else:
            start_move = "Bolt"

        other_move = "Beam" if start_move == "Bolt" else "Bolt"
        return [start_move, other_move]

    def _select_probability_by_enemy_count(
        self,
        probability_tables: Dict[str, Any],
        other_enemy_count: Optional[int],
    ) -> Dict[str, Any]:
        if not isinstance(probability_tables, dict) or other_enemy_count is None:
            return {}

        for key, table in probability_tables.items():
            if not isinstance(key, str) or not isinstance(table, dict):
                continue

            exact_match = re.match(r"^(\d+)_enemies$", key)
            if exact_match and other_enemy_count == int(exact_match.group(1)):
                return table

            range_match = re.match(r"^(\d+)-(\d+)_enemies$", key)
            if not range_match:
                continue
            minimum = int(range_match.group(1))
            maximum = int(range_match.group(2))
            if minimum <= other_enemy_count <= maximum:
                return table
        return {}

    def _select_move_by_enemy_count(
        self,
        moves_by_enemy_count: Dict[str, Any],
        other_enemy_count: Optional[int],
    ) -> Optional[str]:
        if not isinstance(moves_by_enemy_count, dict) or other_enemy_count is None:
            return None

        key = "has_other_enemies" if other_enemy_count > 0 else "alone"
        move_name = moves_by_enemy_count.get(key)
        return move_name if isinstance(move_name, str) else None

    def _select_probability_table(
        self,
        probabilities: Dict[str, Any],
        current_turn: int,
        monster_hp_percent: float,
        other_enemy_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(probabilities, dict):
            return {}
        if all(isinstance(prob, (int, float)) for prob in probabilities.values()):
            return probabilities

        if monster_hp_percent < 0.5 and current_turn == 1:
            low_hp_table = probabilities.get("below_50_percent_hp_first_turn")
            if isinstance(low_hp_table, dict):
                return low_hp_table

        dagger_count = sum(
            1
            for name in (other_enemy_names or [])
            if self._normalize_move_name(str(name or "")) == "dagger"
        )
        selected_dagger_threshold = None
        selected_dagger_table = None
        for key, table in probabilities.items():
            match = re.match(r"(\d+)\+_daggers$", str(key))
            if not match or not isinstance(table, dict):
                continue
            threshold = int(match.group(1))
            if dagger_count < threshold:
                continue
            if selected_dagger_threshold is None or threshold > selected_dagger_threshold:
                selected_dagger_threshold = threshold
                selected_dagger_table = table
        if selected_dagger_table is not None:
            return selected_dagger_table

        normal_table = probabilities.get("normal")
        if isinstance(normal_table, dict):
            return normal_table

        for table in probabilities.values():
            if isinstance(table, dict) and all(isinstance(prob, (int, float)) for prob in table.values()):
                return table
        return {}

    def calculate_future_threat(self, monster_name: str, current_turn: int,
                               monster_hp_percent: float, current_strength: int = 0) -> int:
        """
        Calculate future threat based on predicted moves and scaling.

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn
            monster_hp_percent: Current HP as percentage
            current_strength: Current monster Strength (for scaling)

        Returns:
            Future threat score (higher = more dangerous)
        """
        threat_profile = self.get_threat_profile(monster_name)
        special_mechanics = self.get_special_mechanics(monster_name)
        predicted_moves = self.predict_next_moves(monster_name, current_turn, monster_hp_percent)

        if not threat_profile:
            return 20  # Default threat

        threat = threat_profile.get("base_threat", 20)

        # Add scaling threat
        scaling_threat = threat_profile.get("scaling_threat", 0)
        if scaling_threat > 0:
            # Estimate turns to kill based on HP
            estimated_ttd = int(10 * monster_hp_percent)  # Rough estimate
            threat += scaling_threat * estimated_ttd

        # Add Strength scaling threat
        if special_mechanics:
            mech_type = special_mechanics.get("type", "")
            if mech_type == "strength_scaler" or "ritual" in mech_type.lower():
                strength_scaling_threat = threat_profile.get("strength_scaling_threat", 4.0)
                threat += strength_scaling_threat * current_strength

        # Add threat from predicted moves
        for prediction in predicted_moves:
            move = prediction["move"]
            confidence = prediction["confidence"]

            # Add damage-based threat
            damage = self._numeric_damage_value(move.get("damage", 0))
            if damage > 0:
                hits = move.get("hits", 1)
                total_damage = damage * hits
                threat += total_damage * 0.3 * confidence

            # Add debuff threat
            if "weak_applied" in move or "vulnerable_applied" in move or "frail_applied" in move:
                threat += 3 * confidence

            # Add summon threat
            if "summons" in move:
                summon_threat = threat_profile.get("summoning_threat", 15)
                threat += summon_threat * confidence

        # Special mechanics threat
        if special_mechanics:
            mech_type = special_mechanics.get("type", "")

            # Summoner threat
            if mech_type == "summoner":
                summon_threat = threat_profile.get("summoning_threat", 20)
                threat += summon_threat

            # Phase change threat
            if mech_type == "phase_change":
                phase = self._get_current_phase(special_mechanics, monster_hp_percent)
                if phase:
                    phase_threat_key = f"phase{phase}_threat"
                    if phase_threat_key in threat_profile:
                        threat += threat_profile[phase_threat_key] - threat_profile.get("base_threat", 20)

            # Hibernation threat
            if mech_type == "hibernation":
                # Check if monster is still sleeping (turn < hibernation_turns)
                hibernation_turns = special_mechanics.get("hibernation_turns", 3)
                if current_turn <= hibernation_turns:
                    hibernation_threat = threat_profile.get("hibernation_threat", threat // 4)
                    threat = hibernation_threat
                else:
                    awakened_threat = threat_profile.get("awakened_threat", threat * 1.5)
                    threat = awakened_threat

        return int(threat)

    def _get_current_phase(self, special_mechanics: Dict, monster_hp_percent: float) -> Optional[int]:
        """Helper to determine current phase based on HP."""
        if "phases" in special_mechanics:
            for phase in special_mechanics["phases"]:
                if "hp_threshold" in phase:
                    if monster_hp_percent < (phase["hp_threshold"] / 100.0):
                        return phase.get("phase", 2)
        return None

    def is_summoner(self, monster_name: str) -> bool:
        """Check if monster is a summoner type."""
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics:
            return "summoner" in str(mechanics.get("type", "")).lower()
        return False

    def is_hibernating(self, monster_name: str, current_turn: int) -> bool:
        """Check if monster is currently hibernating."""
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics and mechanics.get("type") == "hibernation":
            hibernation_turns = mechanics.get("hibernation_turns", 3)
            return current_turn <= hibernation_turns
        return False

    def has_phase_change(self, monster_name: str) -> bool:
        """Check if monster has phase change mechanics."""
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics:
            mech_type = mechanics.get("type", "")
            return mech_type == "phase_change" or "phases" in mechanics
        return False

    def has_death_split(self, monster_name: str) -> bool:
        """Check if monster splits on death."""
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics:
            return mechanics.get("type") in {"death_split", "split"}
        return False

    def get_recommended_strategy(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get recommended strategy for fighting a monster.

        Args:
            monster_name: Name of the monster

        Returns:
            Strategy dictionary with primary, secondary, and note
        """
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics and "recommended_strategy" in mechanics:
            return mechanics["recommended_strategy"]
        return None

    def get_timing_hints(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get timing-specific strategy hints for a monster.

        These hints guide turn timing decisions without hardcoding logic.

        Args:
            monster_name: Name of the monster

        Returns:
            Dictionary with timing hints:
            {
                "safe_turn_indicators": ["BUFF", "DEFEND"],
                "spike_turn_indicators": ["ATTACK_DEBUFF"],
                "preparation_windows": [...],
                "burst_opportunities": [...],
                "preferred_response": {
                    "SAFE": "aggressive_damage",
                    "THREAT_SPIKE": "block_then_attack"
                }
            }
        """
        monster_data = self.get_monster_data(monster_name)
        if monster_data and "timing_strategy" in monster_data:
            return monster_data["timing_strategy"]
        return None

    def is_safe_turn(self, monster_name: str, current_turn: int,
                    monster_hp_percent: float = 1.0) -> bool:
        """
        Check if current turn is a "safe turn" for a monster.

        Safe turns are when the monster buffs/defends instead of attacking.

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn
            monster_hp_percent: Monster HP as percentage (for phase detection)

        Returns:
            True if monster is not attacking this turn
        """
        # Get timing hints
        hints = self.get_timing_hints(monster_name)
        if hints:
            # Check current move against safe turn indicators
            safe_indicators = hints.get("safe_turn_indicators", [])
            if safe_indicators:
                # Predict current move
                predicted_moves = self.predict_next_moves(
                    monster_name, current_turn, monster_hp_percent
                )
                if predicted_moves:
                    current_move = predicted_moves[0].get("move", {})
                    current_intent = current_move.get("intent", "")
                    if intent_is_attack(current_intent):
                        return False
                    current_intent_name = str(current_intent or "").upper()

                    # Check if intent matches safe indicators
                    for indicator in safe_indicators:
                        if indicator.upper() in current_intent_name:
                            return True

        # Fallback: check if current move is non-attack
        predicted_moves = self.predict_next_moves(
            monster_name, current_turn, monster_hp_percent
        )
        if predicted_moves:
            current_move = predicted_moves[0].get("move", {})
            current_intent = current_move.get("intent", "")

            # Non-attack intents are safe
            non_attack_intents = {"BUFF", "DEFEND", "DEBUFF", "DEBUG", "NONE", "STUN", "SLEEP"}
            return (
                not intent_is_attack(current_intent)
                and bool(intent_tokens(current_intent) & non_attack_intents)
            )

        return False

    def get_big_attack_pattern(self, monster_name: str) -> List[Dict[str, Any]]:
        """
        Get big attack patterns for a monster.

        Returns upcoming big attacks with turn numbers and damage.

        Args:
            monster_name: Name of the monster

        Returns:
            List of big attack patterns:
            [
                {"turn": 3, "damage": 25, "move": "Strong Attack"},
                {"turn": 6, "damage": 30, "move": "Ultimate"}
            ]
        """
        monster_data = self.get_monster_data(monster_name)
        if not monster_data:
            return []

        big_attacks = []
        moves = monster_data.get("moves", [])
        pattern = monster_data.get("pattern", {})

        # Check for big attack moves
        for move in moves:
            damage = self._numeric_damage_value(move.get("damage", 0))
            if intent_is_attack(move.get("intent", "")) and damage >= 20:  # Threshold for "big"
                # Try to find turn number from pattern
                move_name = move.get("name", "")
                big_attacks.append({
                    "move": move_name,
                    "damage": damage,
                    "intent": move.get("intent", ""),
                    "turn": None  # Turn number depends on current state
                })

        # Check pattern for explicit big attack turns
        if "big_attack_turns" in pattern:
            big_attacks.extend(pattern["big_attack_turns"])

        return big_attacks

    def _numeric_damage_value(self, damage: Any) -> int:
        if isinstance(damage, (int, float)):
            return int(damage)
        if isinstance(damage, dict):
            for key in ("max", "normal", "base", "min"):
                value = damage.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
            numeric_values = [
                value for value in damage.values()
                if isinstance(value, (int, float))
            ]
            return int(max(numeric_values, default=0))
        return 0

    def get_all_monsters(self) -> List[str]:
        """Get list of all monster names in the database."""
        return list(self._data.keys())

    def get_monsters_by_type(self, monster_type: str) -> List[str]:
        """
        Get all monsters of a specific type.

        Args:
            monster_type: "normal", "elite", or "boss"

        Returns:
            List of monster names
        """
        result = []
        for monster_name, data in self._data.items():
            if data.get("monster_type") == monster_type:
                result.append(monster_name)
        return result

    def is_duo_boss(self, monster_name: str) -> bool:
        """Check if monster is a duo boss (two monsters fighting together)."""
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics:
            return mechanics.get("type") == "duo_boss"
        return False

    def get_minions(self, monster_name: str) -> List[str]:
        """
        Get list of minions a monster can summon.

        Args:
            monster_name: Name of the monster

        Returns:
            List of minion names
        """
        mechanics = self.get_special_mechanics(monster_name)
        if mechanics:
            return mechanics.get("summons", [])
        return []


# Global singleton instance
_enhanced_db_instance = None


def get_enhanced_monster_db() -> EnhancedMonsterDatabase:
    """Get the global enhanced monster database instance."""
    global _enhanced_db_instance
    if _enhanced_db_instance is None:
        _enhanced_db_instance = EnhancedMonsterDatabase()
    return _enhanced_db_instance


# Convenience functions for backward compatibility
def get_enhanced_monster_data(monster_name: str) -> Optional[Dict[str, Any]]:
    """Get complete monster data (convenience function)."""
    return get_enhanced_monster_db().get_monster_data(monster_name)


def get_monster_moves(monster_name: str) -> List[Dict[str, Any]]:
    """Get monster moves (convenience function)."""
    return get_enhanced_monster_db().get_moves(monster_name)


def get_monster_pattern(monster_name: str) -> Optional[Dict[str, Any]]:
    """Get monster pattern (convenience function)."""
    return get_enhanced_monster_db().get_pattern(monster_name)


def predict_monster_moves(
    monster_name: str,
    current_turn: int,
    monster_hp_percent: float,
    ascension_level: int = 0,
    other_enemy_count: Optional[int] = None,
    other_enemy_names: Optional[List[str]] = None,
    same_monster_index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Predict monster moves (convenience function)."""
    return get_enhanced_monster_db().predict_next_moves(
        monster_name,
        current_turn,
        monster_hp_percent,
        ascension_level=ascension_level,
        other_enemy_count=other_enemy_count,
        other_enemy_names=other_enemy_names,
        same_monster_index=same_monster_index,
    )


def calculate_future_threat(monster_name: str, current_turn: int,
                            monster_hp_percent: float, current_strength: int = 0) -> int:
    """Calculate future threat (convenience function)."""
    return get_enhanced_monster_db().calculate_future_threat(
        monster_name, current_turn, monster_hp_percent, current_strength
    )


def get_monster_timing_hints(monster_name: str) -> Optional[Dict[str, Any]]:
    """Get timing hints for a monster (convenience function)."""
    return get_enhanced_monster_db().get_timing_hints(monster_name)


def is_monster_safe_turn(monster_name: str, current_turn: int,
                        monster_hp_percent: float = 1.0) -> bool:
    """Check if current turn is safe for a monster (convenience function)."""
    return get_enhanced_monster_db().is_safe_turn(
        monster_name, current_turn, monster_hp_percent
    )


def get_monster_big_attack_pattern(monster_name: str) -> List[Dict[str, Any]]:
    """Get big attack pattern for a monster (convenience function)."""
    return get_enhanced_monster_db().get_big_attack_pattern(monster_name)
