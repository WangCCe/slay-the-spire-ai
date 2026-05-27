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
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


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
        # Try exact match first
        if monster_name in self._data:
            return self._data[monster_name]

        # Some mechanics records refer to spawned monsters by monster_id.
        for value in self._data.values():
            if str(value.get("monster_id", "")).lower() == monster_name.lower():
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

        # Try partial match (for names like "The Champ" vs "Champ")
        for key, value in self._data.items():
            if monster_name.lower() in key.lower() or key.lower() in monster_name.lower():
                return value

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
                    if isinstance(range_data, dict):
                        if "min" in range_data and "max" in range_data:
                            return (range_data["min"], range_data["max"])
                    # Handle duo monsters (Donu & Deca)
                    elif isinstance(range_data, dict) and monster_name in range_data:
                        return (range_data[monster_name]["min"], range_data[monster_name]["max"])

        # Default to normal range
        if "normal" in hp_ranges:
            normal_range = hp_ranges["normal"]
            if isinstance(normal_range, dict):
                if "min" in normal_range and "max" in normal_range:
                    return (normal_range["min"], normal_range["max"])
                # Handle duo monsters
                elif monster_name in normal_range:
                    return (normal_range[monster_name]["min"], normal_range[monster_name]["max"])

        return (50, 60)  # Final fallback

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

    def predict_next_moves(self, monster_name: str, current_turn: int,
                           monster_hp_percent: float) -> List[Dict[str, Any]]:
        """
        Predict next moves for a monster based on its pattern.

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn (1-indexed)
            monster_hp_percent: Current HP as percentage (0.0 to 1.0)

        Returns:
            List of predicted moves for next 3 turns
        """
        pattern = self.get_pattern(monster_name)
        moves = self.get_moves(monster_name)
        special_mechanics = self.get_special_mechanics(monster_name)

        if not pattern or not moves:
            return []

        predictions = []

        # Check for move_sequence
        if "move_sequence" in pattern:
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

        # Check for phase-based patterns
        elif "phases" in pattern:
            # Determine current phase
            current_phase = None
            for phase in pattern["phases"]:
                if "hp_threshold" in phase:
                    if monster_hp_percent < (phase["hp_threshold"] / 100.0):
                        current_phase = phase
                        break

            if current_phase and "pattern" in current_phase:
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

        # Check for simple one-move monsters (e.g., Spike Slime (S))
        elif "only_move" in pattern:
            self._append_sequence_predictions(predictions, monster_name, [pattern["only_move"]], current_turn)

        # Check for explicit turn-one probabilities with a separate later pattern.
        elif "turn_1_probabilities" in pattern:
            for i in range(3):
                target_turn = current_turn + i
                if target_turn == 1:
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        pattern.get("turn_1_probabilities", {}),
                        target_turn,
                    )
                    continue

                subsequent_probs = pattern.get("subsequent_probabilities")
                if isinstance(subsequent_probs, dict):
                    self._append_probability_predictions(
                        predictions,
                        moves,
                        subsequent_probs,
                        target_turn,
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
            probs = self._select_probability_table(
                pattern.get("probabilities") or pattern.get("move_probabilities"),
                current_turn,
                monster_hp_percent,
            )
            # Predict most likely moves
            if isinstance(probs, dict):
                # Get top 2 most likely moves
                sorted_probs = sorted(
                    (
                        (move_name, prob)
                        for move_name, prob in probs.items()
                        if isinstance(prob, (int, float))
                    ),
                    key=lambda x: x[1],
                    reverse=True
                )[:2]
                for move_name, prob in sorted_probs:
                    for move in moves:
                        if self._normalize_move_name(move["name"]) == self._normalize_move_name(move_name):
                            predictions.append({
                                "turn": current_turn,
                                "move": move,
                                "confidence": prob
                            })
                            break

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
            opening_moves = pattern["opening"]
            opening_length = len(opening_moves) if isinstance(opening_moves, list) else 0
            then_moves = pattern.get("then", [])
            if not isinstance(then_moves, list):
                then_moves = []
            fixed_sequence = opening_moves + then_moves if isinstance(opening_moves, list) else then_moves
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
            for move in moves:
                if move["name"] == initial_move_name:
                    predictions.insert(0, {
                        "turn": current_turn,
                        "move": move,
                        "confidence": 1.0
                    })
                    break

        return predictions[:3]  # Return at most 3 predictions

    def _append_sequence_predictions(
        self,
        predictions: List[Dict[str, Any]],
        monster_name: str,
        sequence: List[str],
        current_turn: int,
    ) -> None:
        if not isinstance(sequence, list) or not sequence:
            return

        sequence_length = len(sequence)
        for i in range(3):
            target_turn = current_turn + i
            move_name = sequence[(target_turn - 1) % sequence_length]
            move = self.get_move_by_name(monster_name, move_name)
            if not move:
                continue
            predictions.append({
                "turn": target_turn,
                "move": move,
                "confidence": 1.0,
            })

    def _phase_probability_key(self, pattern: Dict[str, Any], target_turn: int, opening_length: int) -> Optional[str]:
        phase_keys = sorted(
            key for key in pattern
            if key.startswith("phase_") and key.endswith("_probabilities")
        )
        if not phase_keys or target_turn <= opening_length:
            return None

        phase_index = (target_turn - opening_length - 1) % len(phase_keys)
        return phase_keys[phase_index]

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
        )[:limit]
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
        return move_name.lower().replace(" ", "_")

    def _select_probability_table(
        self,
        probabilities: Dict[str, Any],
        current_turn: int,
        monster_hp_percent: float,
    ) -> Dict[str, Any]:
        if not isinstance(probabilities, dict):
            return {}
        if all(isinstance(prob, (int, float)) for prob in probabilities.values()):
            return probabilities

        if monster_hp_percent < 0.5 and current_turn == 1:
            low_hp_table = probabilities.get("below_50_percent_hp_first_turn")
            if isinstance(low_hp_table, dict):
                return low_hp_table

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
            return mechanics.get("type") == "summoner"
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
                    current_intent = current_move.get("intent", "").upper()

                    # Check if intent matches safe indicators
                    for indicator in safe_indicators:
                        if indicator.upper() in current_intent:
                            return True

        # Fallback: check if current move is non-attack
        predicted_moves = self.predict_next_moves(
            monster_name, current_turn, monster_hp_percent
        )
        if predicted_moves:
            current_move = predicted_moves[0].get("move", {})
            current_intent = current_move.get("intent", "").upper()

            # Non-attack intents are safe
            non_attack_intents = ["BUFF", "DEFEND", "DEBUFF", "DEBUG", "NONE", "STUN", "SLEEP"]
            return current_intent in non_attack_intents

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
            if damage >= 20:  # Threshold for "big"
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


def predict_monster_moves(monster_name: str, current_turn: int,
                         monster_hp_percent: float) -> List[Dict[str, Any]]:
    """Predict monster moves (convenience function)."""
    return get_enhanced_monster_db().predict_next_moves(
        monster_name, current_turn, monster_hp_percent
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
