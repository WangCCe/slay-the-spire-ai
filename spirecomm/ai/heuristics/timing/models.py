"""
Data models for timing-aware combat decision making.

This module defines the core data structures used throughout the timing strategy system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

from spirecomm.ai.intent_utils import intent_is_attack


class TurnTiming(Enum):
    """
    Classification of turn timing for strategic combat decisions.

    Each timing category represents a different threat level and opportunity pattern,
    which informs the optimal offensive/defensive balance.
    """
    SAFE = "SAFE"  # Low/no damage expected (monster buffing/defending)
    THREAT_SPIKE = "THREAT_SPIKE"  # High damage this turn (must block)
    PREPARATION = "PREPARATION"  # Moderate damage but spike coming (build block)
    BURST_WINDOW = "BURST_WINDOW"  # Monster vulnerable (aggressive damage)
    BALANCED = "BALANCED"  # Standard turn (mixed threats)
    UNKNOWN = "UNKNOWN"  # Insufficient data (default to balanced)


@dataclass
class SafeWindow:
    """
    A time interval where monsters deal low/no damage.

    Safe windows represent opportunities to:
    - Attack aggressively without block
    - Build powers/setup cards
    - Conserve energy for future threats

    Attributes:
        start_turn: First turn of safe window
        end_turn: Last turn of safe window
        expected_damage: Total damage during window (typically 0-10)
        confidence: Prediction confidence (0.0-1.0) based on Wiki pattern certainty
        monsters_safe: List of monster names that are safe during this window
    """
    start_turn: int
    end_turn: int
    expected_damage: int
    confidence: float
    monsters_safe: List[str] = field(default_factory=list)

    def is_turn_in_window(self, turn: int) -> bool:
        """Check if a turn falls within this safe window."""
        return self.start_turn <= turn <= self.end_turn

    def __str__(self) -> str:
        return (f"SafeWindow(turns {self.start_turn}-{self.end_turn}, "
                f"damage={self.expected_damage}, confidence={self.confidence:.2f})")


@dataclass
class BalanceWeights:
    """
    Dynamic scoring weights for combat simulation based on timing context.

    These weights are used in beam search scoring to prioritize offense vs defense.
    They adapt dynamically based on turn timing classification.

    Attributes:
        damage_weight: Offense priority (higher = more aggressive)
        block_weight: Defense priority (higher = more defensive)
        kill_bonus: Monster kill incentive
        lethal_detection: Whether to check for all-kill this turn
        block_threshold: Minimum block before considering offense
        opportunistic_attack: Attack if lethal check passes
    """
    damage_weight: float = 2.0
    block_weight: float = 1.5
    kill_bonus: float = 100.0
    lethal_detection: bool = True
    block_threshold: int = 0
    opportunistic_attack: bool = True

    @staticmethod
    def safe_turn_weights() -> 'BalanceWeights':
        """Weights for safe turns (monster buffing/defending)."""
        return BalanceWeights(
            damage_weight=2.5,      # Boost offense
            block_weight=0.5,       # Reduce defense
            kill_bonus=120.0,       # Extra incentive to kill
            lethal_detection=True,
            block_threshold=0,
            opportunistic_attack=True
        )

    @staticmethod
    def threat_spike_weights() -> 'BalanceWeights':
        """Weights for high-damage turns (must block)."""
        return BalanceWeights(
            damage_weight=0.8,      # Reduce offense
            block_weight=3.0,       # Boost defense
            kill_bonus=80.0,        # Lower kill bonus (don't overextend)
            lethal_detection=True,
            block_threshold=20,     # Require block before offense
            opportunistic_attack=True
        )

    @staticmethod
    def preparation_weights() -> 'BalanceWeights':
        """Weights for preparation turns (spike coming soon)."""
        return BalanceWeights(
            damage_weight=1.2,      # Slightly offensive
            block_weight=2.2,       # Build block for spike
            kill_bonus=100.0,
            lethal_detection=True,
            block_threshold=15,     # Some block needed
            opportunistic_attack=True
        )

    @staticmethod
    def burst_window_weights() -> 'BalanceWeights':
        """Weights for burst windows (monster vulnerable)."""
        return BalanceWeights(
            damage_weight=3.0,      # Maximum offense
            block_weight=0.8,       # Minimal defense
            kill_bonus=150.0,       # High kill incentive
            lethal_detection=True,
            block_threshold=0,
            opportunistic_attack=True
        )

    @staticmethod
    def balanced_weights() -> 'BalanceWeights':
        """Standard balanced weights."""
        return BalanceWeights(
            damage_weight=2.0,
            block_weight=1.5,
            kill_bonus=100.0,
            lethal_detection=True,
            block_threshold=0,
            opportunistic_attack=True
        )


@dataclass
class MonsterTimingHints:
    """
    Timing-specific strategy hints extracted from Wiki monster data.

    These hints guide turn timing decisions without hardcoding logic.

    Attributes:
        safe_turn_indicators: Move intents that indicate low damage turn (e.g., ["BUFF", "DEFEND"])
        spike_turn_indicators: Move intents that indicate high damage turn (e.g., ["ATTACK_DEBUFF"])
        preparation_windows: Turns before spikes where we should build block
        burst_opportunities: Turns where monster is vulnerable to burst damage
        preferred_response: Default action per timing category (timing → action mapping)
        raw_data: Original Wiki timing_strategy dict (for advanced features like always_classify_as)
    """
    safe_turn_indicators: List[str] = field(default_factory=list)
    spike_turn_indicators: List[str] = field(default_factory=list)
    preparation_windows: List[Dict[str, Any]] = field(default_factory=list)
    burst_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    preferred_response: Dict[str, str] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def is_safe_turn(self, move_intent: str) -> bool:
        """Check if a move intent indicates a safe turn."""
        if intent_is_attack(move_intent):
            return False
        intent_upper = move_intent.upper()
        return any(indicator in intent_upper for indicator in self.safe_turn_indicators)

    def is_spike_turn(self, move_intent: str) -> bool:
        """Check if a move intent indicates a threat spike."""
        if any(intent_is_attack(indicator) for indicator in self.spike_turn_indicators):
            if not intent_is_attack(move_intent):
                return False
        intent_upper = move_intent.upper()
        return any(indicator in intent_upper for indicator in self.spike_turn_indicators)

    def get_preferred_response(self, timing: TurnTiming) -> str:
        """Get preferred action for a timing category."""
        timing_str = timing.value if isinstance(timing, TurnTiming) else str(timing)
        return self.preferred_response.get(timing_str, "balanced")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonsterTimingHints':
        """Create MonsterTimingHints from dictionary (typically from JSON)."""
        return cls(
            safe_turn_indicators=data.get('safe_turn_indicators', []),
            spike_turn_indicators=data.get('spike_turn_indicators', []),
            preparation_windows=data.get('preparation_windows', []),
            burst_opportunities=data.get('burst_opportunities', []),
            preferred_response=data.get('preferred_response', {}),
            raw_data=data  # Store complete original data for advanced features
        )


@dataclass
class TimingContext:
    """
    Complete timing analysis for current game state.

    This context object bundles all timing-related information for easy
    passing through the decision pipeline.

    Attributes:
        turn_timing: Classification of current turn
        current_damage: Expected damage this turn
        future_damage_curve: List of predicted damage for next N turns
        safe_windows: List of detected safe windows
        balance_weights: Dynamic weights for this timing
        monster_hints: Per-monster timing hints from Wiki
        confidence: Overall prediction confidence (0.0-1.0)
    """
    turn_timing: TurnTiming
    current_damage: int
    future_damage_curve: List[int] = field(default_factory=list)
    safe_windows: List[SafeWindow] = field(default_factory=list)
    balance_weights: BalanceWeights = field(default_factory=BalanceWeights.balanced_weights)
    monster_hints: Dict[str, MonsterTimingHints] = field(default_factory=dict)
    confidence: float = 0.8

    def is_safe_turn(self) -> bool:
        """Check if current turn is classified as safe."""
        return self.turn_timing == TurnTiming.SAFE

    def is_threat_spike(self) -> bool:
        """Check if current turn is a threat spike."""
        return self.turn_timing == TurnTiming.THREAT_SPIKE

    def has_safe_window_upcoming(self, turns_ahead: int = 3) -> bool:
        """Check if a safe window is coming up in next N turns."""
        for window in self.safe_windows:
            if 0 < window.start_turn - self.current_turn_offset() <= turns_ahead:
                return True
        return False

    def current_turn_offset(self) -> int:
        """Helper to get current turn offset (for safe window checks)."""
        # This will be set by the classifier
        return getattr(self, '_current_turn', 1)

    def __str__(self) -> str:
        return (f"TimingContext(timing={self.turn_timing.value}, "
                f"damage={self.current_damage}, confidence={self.confidence:.2f})")
