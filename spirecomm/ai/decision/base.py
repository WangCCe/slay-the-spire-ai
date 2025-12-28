"""
Base interfaces and classes for the decision framework.

This module defines the foundational abstractions used throughout the optimized AI system.
All decision components inherit from these base classes to ensure consistency and
enable easy testing/mocking.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from spirecomm.spire.game import Game
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster, Intent
from spirecomm.communication.action import Action


class DecisionContext:
    """
    Encapsulates all context needed for decision making.

    This class pre-computes expensive metrics once and makes them available
    to all decision components, ensuring consistency and efficiency.

    Attributes:
        game: The current game state
        player_hp_pct: Player's HP as percentage (0-1)
        energy_available: Current energy
        incoming_damage: Total damage from monsters this turn
        monsters_alive: List of alive monsters (not gone/half_dead)
        deck_archetype: Detected deck archetype ('poison', 'strength', 'block', etc.)
        card_synergies: Dictionary of synergy scores
        turn: Current turn number
        floor: Current floor number
        act: Current act number
    """

    def __init__(self, game: Game):
        self.game = game

        # Player stats - check if player exists
        if hasattr(game, 'current_hp') and hasattr(game, 'max_hp') and game.max_hp > 0:
            self.player_hp_pct = max(0, game.current_hp / max(game.max_hp, 1))
        else:
            self.player_hp_pct = 1.0  # Default to full HP

        if hasattr(game, 'player') and game.player is not None:
            self.energy_available = game.player.energy if hasattr(game.player, 'energy') else 3
        else:
            self.energy_available = 3  # Default energy

        self.turn = game.turn if hasattr(game, 'turn') else 1
        self.floor = game.floor if hasattr(game, 'floor') else 0
        self.act = game.act if hasattr(game, 'act') else 1

        # Combat state
        self.incoming_damage = self._calculate_incoming_damage()
        self.monsters_alive = [
            m for m in game.monsters
            if not m.is_gone and not m.half_dead and m.current_hp > 0
        ] if hasattr(game, 'monsters') else []

        # Deck analysis
        self.deck_archetype = self._analyze_deck_archetype()
        self.card_synergies = self._calculate_synergies()

        # Hand analysis
        self.hand_size = len(game.hand) if hasattr(game, 'hand') else 0
        self.playable_cards = [
            c for c in game.hand
            if hasattr(c, 'is_playable') and c.is_playable
        ] if hasattr(game, 'hand') else []

        # === 新增：遗物检测 ===
        self.has_snecko_eye = self._has_relic("Snecko Eye")
        self.has_burning_blood = self._has_relic("Burning Blood")
        self.has_busted_clock = self._has_relic("Busted Clock")
        self.has_orichalcum = self._has_relic("Orichalcum")
        self.has_paper_crane = self._has_relic("Paper Crane")

        # === 新增：玩家 Power 追踪 ===
        self.strength = self._get_player_power_amount("Strength")
        self.dexterity = self._get_player_power_amount("Dexterity")
        self.vulnerable_stacks = {}  # monster_index -> stacks
        self.weak_stacks = {}  # monster_index -> stacks
        self.frail_stacks = {}  # monster_index -> stacks

        # 为每个怪物初始化 debuff 追踪（使用索引作为 key）
        for i, monster in enumerate(self.monsters_alive):
            self.vulnerable_stacks[i] = self._get_monster_power_amount(monster, "Vulnerable")
            self.weak_stacks[i] = self._get_monster_power_amount(monster, "Weak")
            self.frail_stacks[i] = self._get_monster_power_amount(monster, "Frail")

        # === 新增：战斗评估 ===
        self.can_end_combat_this_turn = False  # 将由 CombatEndingDetector 计算

    def _calculate_incoming_damage(self) -> int:
        """Calculate total incoming damage from all monsters."""
        if not hasattr(self.game, 'monsters'):
            return 0

        total = 0
        for monster in self.game.monsters:
            if not monster.is_gone and not monster.half_dead:
                if hasattr(monster, 'move_adjusted_damage') and monster.move_adjusted_damage is not None:
                    hits = hasattr(monster, 'move_hits') and monster.move_hits or 1
                    total += monster.move_adjusted_damage * hits
                elif hasattr(monster, 'intent') and monster.intent == Intent.NONE:
                    # Unknown intent, estimate based on act
                    total += 5 * self.act
        return total

    def _analyze_deck_archetype(self) -> str:
        """
        Analyze deck to determine archetype.

        Returns:
            Archetype string: 'poison', 'strength', 'block', 'scaling', 'draw', 'balanced', 'unknown'
        """
        if not hasattr(self.game, 'deck') or not self.game.deck:
            return 'unknown'

        # Count card types by keywords
        poison_count = sum(1 for c in self.game.deck if 'poison' in c.card_id.lower() or c.card_id == 'Catalyst')
        strength_count = sum(1 for c in self.game.deck if c.card_id in ['Demon Form', 'Inflame', 'Limit Break', 'Flex'])
        block_count = sum(1 for c in self.game.deck if 'defend' in c.card_id.lower() or c.card_id in ['Iron Wave', 'Blaze'])
        draw_count = sum(1 for c in self.game.deck if c.card_id in ['Adrenaline', 'Impatience', 'Acrobatics'])
        scaling_count = sum(1 for c in self.game.deck if c.card_id in ['Noxious Fumes', 'A Thousand Cuts', 'Demon Form', 'Infinite Blades'])

        # Determine archetype based on dominant strategy
        counts = {
            'poison': poison_count,
            'strength': strength_count,
            'block': block_count,
            'draw': draw_count,
            'scaling': scaling_count
        }

        max_count = max(counts.values())
        if max_count < 3:
            return 'balanced'  # No clear archetype

        for archetype, count in counts.items():
            if count == max_count:
                return archetype

        return 'unknown'

    def _calculate_synergies(self) -> Dict[str, float]:
        """
        Calculate synergy scores for different card interactions.

        Returns:
            Dictionary mapping synergy types to scores (0-1)
        """
        synergies = {
            'poison': 0.0,
            'strength': 0.0,
            'draw': 0.0,
            'exhaust': 0.0,
            'block': 0.0
        }

        if not hasattr(self.game, 'deck'):
            return synergies

        for card in self.game.deck:
            card_id = card.card_id.lower()

            # Poison synergies
            if 'poison' in card_id or 'noxious' in card_id or 'catalyst' in card_id:
                synergies['poison'] += 0.1

            # Strength synergies
            if card.card_id in ['Demon Form', 'Inflame', 'Limit Break', 'Flex']:
                synergies['strength'] += 0.15

            # Draw synergies
            if 'draw' in card_id or card.card_id in ['Adrenaline', 'Impatience', 'Acrobatics']:
                synergies['draw'] += 0.1

            # Exhaust synergies
            if 'exhaust' in card_id or card.card_id in ['Evolve', 'Feel No Pain', 'Deadly Poison']:
                synergies['exhaust'] += 0.1

            # Block synergies
            if 'defend' in card_id or 'block' in card_id or card.card_id in ['Iron Wave', 'Blaze']:
                synergies['block'] += 0.05

        # Clamp to 0-1
        for key in synergies:
            synergies[key] = min(1.0, synergies[key])

        return synergies

    def _has_relic(self, relic_id: str) -> bool:
        """
        Check if player has specific relic.

        Args:
            relic_id: The relic identifier (e.g., "Snecko Eye")

        Returns:
            True if player has this relic
        """
        if not hasattr(self.game, 'relics'):
            return False
        return any(r.relic_id == relic_id for r in self.game.relics)

    def _get_player_power_amount(self, power_id: str) -> int:
        """
        Get amount of specific player power.

        Args:
            power_id: The power identifier (e.g., "Strength")

        Returns:
            Amount of the power, or 0 if not found
        """
        if not hasattr(self.game, 'player') or not hasattr(self.game.player, 'powers'):
            return 0
        for power in self.game.player.powers:
            if power.power_id == power_id:
                return power.amount if hasattr(power, 'amount') else 0
        return 0

    def _get_monster_power_amount(self, monster: Monster, power_id: str) -> int:
        """
        Get amount of specific monster power/debuff.

        Args:
            monster: The monster to check
            power_id: The power identifier (e.g., "Vulnerable")

        Returns:
            Amount of the power, or 0 if not found
        """
        if not hasattr(monster, 'powers'):
            return 0
        for power in monster.powers:
            if power.power_id == power_id:
                return power.amount if hasattr(power, 'amount') else 0
        return 0

    def __repr__(self) -> str:
        return (f"DecisionContext(hp={self.player_hp_pct:.2f}, energy={self.energy_available}, "
                f"archetype={self.deck_archetype}, monsters={len(self.monsters_alive)})")


class DecisionEngine(ABC):
    """
    Base class for all decision components.

    All evaluators and planners inherit from this class, which provides
    a consistent interface for decision making.
    """

    @abstractmethod
    def evaluate(self, context: DecisionContext) -> Any:
        """
        Return evaluation score or decision.

        Args:
            context: The decision context containing game state

        Returns:
            Evaluation result (type varies by subclass)
        """
        pass

    @abstractmethod
    def get_confidence(self, context: DecisionContext) -> float:
        """
        Return confidence 0-1 in this decision.

        Higher confidence means the evaluator is more certain of its recommendation.
        This can be used for weighted voting or fallback strategies.

        Args:
            context: The decision context

        Returns:
            Confidence value between 0 and 1
        """
        pass


class CardEvaluator(DecisionEngine):
    """
    Evaluate card value in current context.

    Card evaluators assign a numeric score to cards based on their current
    strategic value, considering the game state, deck composition, etc.
    """

    @abstractmethod
    def evaluate_card(self, card: Card, context: DecisionContext) -> float:
        """
        Returns card value score (higher is better).

        Args:
            card: The card to evaluate
            context: Current decision context

        Returns:
            Numeric score where higher values indicate better cards
        """
        pass

    def evaluate(self, context: DecisionContext) -> None:
        """Not applicable for CardEvaluator - use evaluate_card instead."""
        raise NotImplementedError("Use evaluate_card() instead")


class CombatPlanner(DecisionEngine):
    """
    Plan optimal combat action sequence.

    Combat planners analyze the current state and determine the best
    sequence of actions to take during a combat turn.
    """

    @abstractmethod
    def plan_turn(self, context: DecisionContext) -> List[Action]:
        """
        Returns ordered list of actions for this turn.

        Args:
            context: Current decision context

        Returns:
            List of actions to execute in order. Empty list means end turn.
        """
        pass

    def evaluate(self, context: DecisionContext) -> List[Action]:
        """
        Alias for plan_turn for DecisionEngine interface.

        Args:
            context: Current decision context

        Returns:
            List of actions to execute
        """
        return self.plan_turn(context)


class StateEvaluator(DecisionEngine):
    """
    Evaluate game state and estimate win probability.

    State evaluators analyze the current game situation and provide
    an estimate of the player's chances of winning.
    """

    @abstractmethod
    def evaluate_state(self, context: DecisionContext) -> float:
        """
        Returns win probability 0-1.

        Args:
            context: Current decision context

        Returns:
            Probability of winning (0 to 1)
        """
        pass

    def evaluate(self, context: DecisionContext) -> float:
        """
        Alias for evaluate_state for DecisionEngine interface.

        Args:
            context: Current decision context

        Returns:
            Win probability 0-1
        """
        return self.evaluate_state(context)
