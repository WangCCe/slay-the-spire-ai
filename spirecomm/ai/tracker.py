"""
Game progress tracking for AI performance analysis.

This module provides the GameTracker class which records detailed statistics
for each game played, including combat performance, card choices, relics,
and decision quality.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


class GameTracker:
    """
    Track single game progress and performance.

    Records comprehensive statistics for each game including:
    - Basic game info (class, ascension, victory status)
    - Progress (floors, acts, elites/bosses killed)
    - Combat performance (turns, HP loss)
    - Card choices (obtained and skipped)
    - Relics obtained
    - Decision quality metrics
    """

    # Type annotations for all attributes
    player_class: Optional[str]
    ascension_level: int
    victory: bool
    final_floor: int
    final_act: int
    final_score: int

    def __init__(self):
        """Initialize all tracking fields."""
        # Game timing
        self.game_start_time = datetime.now()
        self.game_end_time: Optional[datetime] = None

        # Basic info
        self.player_class: Optional[str] = None
        self.ascension_level: int = 0
        self.victory: bool = False
        self.final_floor: int = 0
        self.final_act: int = 0
        self.final_score: int = 0

        # Progress tracking
        self.combats: List[Dict[str, Any]] = []  # List of combat records
        self.current_combat: Optional[Dict[str, Any]] = None
        self.elite_kills: int = 0
        self.boss_kills: int = 0

        # Death information
        self.death_floor: Optional[int] = None
        self.death_act: Optional[int] = None
        self.death_cause: Optional[str] = None  # "elite", "boss", "monster", "event"
        self.death_hp_pct: Optional[float] = None
        self.current_hp_at_death: Optional[int] = None

        # Card tracking
        self.cards_obtained: List[str] = []  # Card IDs obtained
        self.cards_skipped: int = 0

        # Relic tracking
        self.relics: List[str] = []  # Relic IDs obtained

        # Potion tracking
        self.potions_used: int = 0

        # Decision statistics
        self.total_decisions: int = 0
        self.combat_decisions: int = 0
        self.decision_confidences: List[float] = []  # List of confidence scores
        self.fallback_count: int = 0

    def start_combat(self, floor: int, act: int, room_type: str):
        """
        Record the start of a combat.

        Args:
            floor: Current floor number
            act: Current act number
            room_type: Type of room ("monster", "elite", "boss")
        """
        self.current_combat = {
            'floor': floor,
            'act': act,
            'room_type': room_type,
            'start_time': datetime.now(),
            'turns': 0,
            'hp_at_start': None,  # Will be filled later
            'hp_at_end': None,
            'decisions': 0
        }

    def end_combat(self, hp_remaining: int, max_hp: int):
        """
        Record the end of current combat.

        Args:
            hp_remaining: Player HP after combat
            max_hp: Player max HP
        """
        if self.current_combat:
            self.current_combat['hp_at_end'] = hp_remaining
            self.current_combat['hp_at_start'] = max_hp  # Approximation

            # Track kills
            if self.current_combat['room_type'] == 'elite':
                self.elite_kills += 1
            elif self.current_combat['room_type'] == 'boss':
                self.boss_kills += 1

            # Store combat record
            self.combats.append(self.current_combat)
            self.current_combat = None

    def record_card_choice(self, chosen: Optional[str], skipped: int, available: List[str]):
        """
        Record a card reward choice.

        Args:
            chosen: Card ID of chosen card (None if skipped)
            skipped: Number of cards skipped
            available: List of available card IDs
        """
        import logging
        logging.info(f"[TRACKER] record_card_choice called")
        logging.info(f"[TRACKER]   chosen: {chosen}")
        logging.info(f"[TRACKER]   skipped: {skipped}")
        logging.info(f"[TRACKER]   available: {available}")
        logging.info(f"[TRACKER]   cards_obtained before: {len(self.cards_obtained) if self.cards_obtained else 0}")

        if chosen:
            self.cards_obtained.append(chosen)
            logging.info(f"[TRACKER]   appended '{chosen}' to cards_obtained")
            logging.info(f"[TRACKER]   cards_obtained after: {len(self.cards_obtained)}")
        self.cards_skipped += skipped

        logging.info(f"[TRACKER] record_card_choice complete\n")

    def record_relic(self, relic_id: str):
        """
        Record obtaining a relic.

        Args:
            relic_id: ID of the relic obtained
        """
        self.relics.append(relic_id)

    def record_potion_use(self):
        """Record using a potion."""
        self.potions_used += 1

    def record_decision(self, decision_type: str, confidence: float, used_fallback: bool = False):
        """
        Record an AI decision.

        Args:
            decision_type: Type of decision ("combat", "map", "reward", etc.)
            confidence: Confidence score (0.0 to 1.0)
            used_fallback: Whether fallback logic was used
        """
        self.total_decisions += 1
        if decision_type == "combat":
            self.combat_decisions += 1

        self.decision_confidences.append(confidence)
        if used_fallback:
            self.fallback_count += 1

    def record_game_over(self, victory: bool, final_state):
        """
        Record the end of game.

        Args:
            victory: Whether the game was won
            final_state: Final game state object
        """
        self.game_end_time = datetime.now()
        self.victory = victory

        # Extract info from final state
        if hasattr(final_state, 'floor'):
            self.final_floor = final_state.floor
            self.death_floor = final_state.floor

        if hasattr(final_state, 'act'):
            self.final_act = final_state.act
            self.death_act = final_state.act

        if hasattr(final_state, 'score'):
            self.final_score = final_state.score

        if hasattr(final_state, 'current_hp') and hasattr(final_state, 'max_hp'):
            self.current_hp_at_death = final_state.current_hp
            self.death_hp_pct = final_state.current_hp / final_state.max_hp if final_state.max_hp > 0 else 0

        # Determine death cause from room type
        if not victory and hasattr(final_state, 'screen'):
            # Could extract from screen info if available
            # For now, use simple heuristics
            if self.boss_kills > 0 and self.final_floor % 17 == 0:
                # Died on boss floor
                self.death_cause = "boss"
            elif self.elite_kills > 0 and self.final_floor in [5, 13, 16, 19, 26, 34, 37, 45]:
                # Died on elite floor
                self.death_cause = "elite"
            else:
                self.death_cause = "monster"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tracker data to dictionary for serialization.

        Returns:
            Dictionary with all tracking data
        """
        # Calculate averages
        avg_confidence = sum(self.decision_confidences) / len(self.decision_confidences) \
            if self.decision_confidences else 0.0

        avg_turns = sum(c['turns'] for c in self.combats) / len(self.combats) \
            if self.combats else 0.0

        # Calculate HP lost
        total_hp_lost = 0
        if self.combats:
            first_combat = self.combats[0]
            hp_at_start = first_combat.get('hp_at_start', 80)  # Default max HP
            hp_at_end = self.combats[-1].get('hp_at_end', hp_at_start)
            total_hp_lost = hp_at_start - hp_at_end

        return {
            'game_id': int(self.game_start_time.timestamp()),

            # Basic info
            'player_class': self.player_class,
            'ascension': self.ascension_level,
            'victory': self.victory,
            'final_floor': self.final_floor,
            'final_act': self.final_act,
            'final_score': self.final_score,

            # Death info
            'death_cause': self.death_cause,
            'death_floor': self.death_floor,
            'death_act': self.death_act,
            'hp_pct': round(self.death_hp_pct, 3) if self.death_hp_pct is not None else 0.0,
            'current_hp_at_death': self.current_hp_at_death,

            # Progress
            'combats': len(self.combats),
            'elite_kills': self.elite_kills,
            'boss_kills': self.boss_kills,
            'avg_turns_per_combat': round(avg_turns, 2),
            'total_hp_lost': total_hp_lost,

            # Cards and relics
            'cards_obtained': self.cards_obtained.copy(),
            'cards_skipped': self.cards_skipped,
            'relics': self.relics.copy(),
            'potions_used': self.potions_used,

            # Decision quality
            'total_decisions': self.total_decisions,
            'combat_decisions': self.combat_decisions,
            'avg_confidence': round(avg_confidence, 3),
            'fallback_count': self.fallback_count,

            # Timing
            'timestamp': self.game_start_time.isoformat(),
            'duration_seconds': int(((self.game_end_time or datetime.now()) - self.game_start_time).total_seconds())
        }

    def to_csv_row(self) -> str:
        """
        Convert tracker data to CSV row string.

        Returns:
            CSV-formatted string
        """
        data = self.to_dict()

        # Convert lists to semicolon-separated strings
        cards_str = ';'.join(data['cards_obtained']) if data['cards_obtained'] else ''
        relics_str = ';'.join(data['relics']) if data['relics'] else ''

        values = [
            data['game_id'],
            data['player_class'] or '',
            data['ascension'],
            str(data['victory']),
            data['final_floor'],
            data['final_act'],
            data['death_cause'] or '',
            str(data['hp_pct']),
            data['combats'],
            data['elite_kills'],
            data['boss_kills'],
            str(data['avg_turns_per_combat']),
            data['total_hp_lost'],
            f'"{cards_str}"',  # Quote strings with potential semicolons
            data['cards_skipped'],
            f'"{relics_str}"',
            data['potions_used'],
            data['total_decisions'],
            str(data['avg_confidence']),
            data['fallback_count'],
            data['timestamp']
        ]

        return ','.join(values)
