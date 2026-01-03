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
from spirecomm.data.loader import game_data_loader


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

        # Deck analysis - dynamically import DeckAnalyzer to avoid circular imports
        try:
            from spirecomm.ai.heuristics.deck import DeckAnalyzer
            analyzer = DeckAnalyzer()
            
            # Use DeckAnalyzer to get deck archetype
            self.deck_archetype = analyzer.get_archetype(self)
            
            # Calculate synergies using enhanced method
            # First get archetype scores
            archetype_scores = analyzer.get_archetype_score(self)
            self.archetype_scores = archetype_scores  # Save for access by evaluators
            self.archetype_score = max(archetype_scores.values()) if archetype_scores else 0.0  # Max score as confidence

            # Initialize synergies dictionary
            self.card_synergies = {
                'poison': archetype_scores.get('poison', 0.0) * 0.7,
                'strength': archetype_scores.get('strength', 0.0) * 0.7,
                'draw': archetype_scores.get('draw', 0.0) * 0.7,
                'exhaust': archetype_scores.get('exhaust', 0.0) * 0.7,
                'block': archetype_scores.get('block', 0.0) * 0.7,
                'vulnerable': 0.0,
                'weak': 0.0,
                'scaling': archetype_scores.get('scaling', 0.0) * 0.7,
                'storm': archetype_scores.get('storm', 0.0) * 0.7,
                'heal': archetype_scores.get('heal', 0.0) * 0.7,
                'malice': archetype_scores.get('malice', 0.0) * 0.7,
                'combo': archetype_scores.get('combo', 0.0) * 0.7
            }
        except ImportError as e:
            # Fall back to original methods if DeckAnalyzer is not available
            self.deck_archetype = self._analyze_deck_archetype()
            self.card_synergies = self._calculate_synergies()
            # Set default values for archetype scores
            self.archetype_scores = {}
            self.archetype_score = 0.0

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
        self.thorns_stacks = {}  # monster_index -> stacks

        # 为每个怪物初始化 debuff 追踪（使用索引作为 key）
        for i, monster in enumerate(self.monsters_alive):
            self.vulnerable_stacks[i] = self._get_monster_power_amount(monster, "Vulnerable")
            self.weak_stacks[i] = self._get_monster_power_amount(monster, "Weak")
            self.frail_stacks[i] = self._get_monster_power_amount(monster, "Frail")
            self.thorns_stacks[i] = self._get_monster_power_amount(monster, "Thorns")

        # === 新增：战斗评估 ===
        self.can_end_combat_this_turn = False  # 将由 CombatEndingDetector 计算

    def _calculate_incoming_damage(self) -> int:
        """Calculate total incoming damage from all monsters.

        Only counts damage from monsters with ATTACK intents.
        Monsters with non-attack intents (DEBUG, DEFEND, BUFF, etc.) are ignored.
        """
        if not hasattr(self.game, 'monsters'):
            return 0

        total = 0
        for monster in self.game.monsters:
            if not monster.is_gone and not monster.half_dead:
                # Check if monster is attacking this turn
                is_attacking = False
                if hasattr(monster, 'intent') and monster.intent is not None:
                    try:
                        from spirecomm.spire.character import Intent
                        intent_str = str(monster.intent).upper()

                        # Only count attack intents
                        if any(attack_type in intent_str for attack_type in ['ATTACK', 'ATTACK_BUFF', 'ATTACK_DEBUFF', 'ATTACK_DEFEND']):
                            is_attacking = True
                    except:
                        # If intent parsing fails, check move_adjusted_damage as fallback
                        is_attacking = True

                # Skip non-attacking monsters (DEFEND, BUFF, DEBUG, STUNNED, etc.)
                if not is_attacking:
                    continue

                # Calculate damage from attacking monsters
                if hasattr(monster, 'move_adjusted_damage') and monster.move_adjusted_damage is not None:
                    hits = hasattr(monster, 'move_hits') and monster.move_hits or 1
                    total += monster.move_adjusted_damage * hits
                elif hasattr(monster, 'intent') and monster.intent == Intent.NONE:
                    # Unknown intent, estimate based on act
                    total += 5 * self.act
        return total

    def compute_threat(self, monster) -> int:
        """
        Calculate the threat level of a monster for targeting decisions.

        Higher threat means the monster should be prioritized for:
        - Killing (can be defeated this turn)
        - Debuffing (apply Vulnerable/Weak to reduce incoming damage)
        - High-priority targeting (focus damage on most dangerous enemy)

        Threat components:
        - Expected damage next turn (from move_adjusted_damage)
        - Debuff threat (applies Weak/Vulnerable: +10)
        - Scaling threat (buffs/growth over time: +15)
        - AOE threat (buffs other monsters: +8)

        Args:
            monster: Monster to evaluate

        Returns:
            Threat score (higher = more threatening)
        """
        threat = 0

        # Import Intent enum for comparison
        try:
            from spirecomm.spire.character import Intent
            intent_type = monster.intent if hasattr(monster, 'intent') else None
        except:
            intent_type = None

        # 1. Expected damage from intent
        if hasattr(monster, 'move_adjusted_damage') and monster.move_adjusted_damage is not None:
            # Use actual damage from game state
            hits = hasattr(monster, 'move_hits') and monster.move_hits or 1
            threat += monster.move_adjusted_damage * hits

            # Add strength to damage (scaling threat)
            if hasattr(monster, 'strength') and monster.strength > 0:
                threat += monster.strength * hits

        # 2. Debuff threat (Weak/Vulnerable are dangerous)
        if intent_type:
            intent_str = str(intent_type).upper() if intent_type else ''

            # Check if monster applies debuffs
            if 'DEBUFF_WEAK' in intent_str or 'DEBUFF_VULNERABLE' in intent_str:
                threat += 10  # Debuff application is high threat
            elif 'WEAK' in intent_str or 'VULNERABLE' in intent_str:
                # Some monsters have WEAK/VULNERABLE as their name
                # Only add threat if it's actually applying a debuff
                if hasattr(monster, 'move_base_damage'):
                    # If it has damage, it's probably an attack+debuff
                    threat += 10

        # 3. Scaling threat (elite/boss monsters that grow stronger)
        if hasattr(monster, 'name'):
            name = monster.name.lower()
            # Known scaling monsters
            scaling_monsters = [
                'gremlin nob', 'gremlin thief', 'gremlin face',
                'slaver', 'sentry', 'hexaghost', 'champ',
                'the guardian', 'bronze automaton',
                'the collector', 'awakened one',
                'reptomancer', 'centurion', 'healer'
            ]
            if any(scaling_name in name for scaling_name in scaling_monsters):
                threat += 15  # Scaling threat

            # Boss threat (Act bosses are very dangerous)
            if 'boss' in name or any(boss in name for boss in ['hexaghost', 'slime boss', 'the guardian']):
                threat += 20  # Extra threat for bosses

        # 4. AOE threat (buffs other monsters)
        if intent_type:
            intent_str = str(intent_type).upper() if intent_type else ''
            if 'BUFF' in intent_str:
                threat += 8  # Buffing allies is threatening

        # 5. High HP threat (more HP = more dangerous if left alive)
        if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
            hp_ratio = monster.current_hp / max(monster.max_hp, 1)
            if hp_ratio > 0.5:  # Monster above 50% HP
                threat += int(hp_ratio * 5)  # Up to +5 for high HP

        return threat

    def _analyze_deck_archetype(self) -> str:
        """
        Analyze deck to determine archetype.

        Returns:
            Archetype string: 'poison', 'strength', 'block', 'scaling', 'draw', 'balanced', 'unknown'
        """
        if not hasattr(self.game, 'deck') or not self.game.deck:
            return 'unknown'

        # Use game data to analyze deck archetype
        poison_count = 0
        strength_count = 0
        block_count = 0
        draw_count = 0
        scaling_count = 0
        card_count = len(self.game.deck)

        for card in self.game.deck:
            card_name = card.card_id.replace('+', '')  # Remove + from upgraded cards
            card_data = game_data_loader.get_card_data(card_name)
            
            if card_data:
                description = card_data.get('description', '').lower()
                card_type = card_data.get('type', '').lower()
                cost = card_data.get('cost', '0')
                
                # Count archetype-specific cards
                if 'poison' in description or 'catalyst' in card.card_id.lower():
                    poison_count += 1
                
                if card_type == 'attack' and ('strength' in description or 'deal' in description):
                    strength_count += 1
                
                if card_type == 'skill' and ('block' in description or 'gain' in description):
                    block_count += 1
                
                if 'draw' in description or 'draw' in card.card_id.lower():
                    draw_count += 1
                
                if any(keyword in description for keyword in ['strength', 'dexterity', 'poison', 'thorns']):
                    scaling_count += 1

        # Normalize counts to percentages
        if card_count > 0:
            poison_pct = poison_count / card_count
            strength_pct = strength_count / card_count
            block_pct = block_count / card_count
            draw_pct = draw_count / card_count
            scaling_pct = scaling_count / card_count
        else:
            return 'unknown'

        # Determine archetype based on dominant strategy
        if poison_pct > 0.2:  # More than 20% poison cards
            return 'poison'
        elif strength_pct > 0.3:  # More than 30% strength-based attack cards
            return 'strength'
        elif block_pct > 0.3:  # More than 30% block cards
            return 'block'
        elif scaling_pct > 0.25:  # More than 25% scaling cards
            return 'scaling'
        elif draw_pct > 0.25:  # More than 25% draw cards
            return 'draw'
        else:
            return 'balanced'  # No clear archetype

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
            'block': 0.0,
            'vulnerable': 0.0,
            'weak': 0.0,
            'scaling': 0.0
        }

        if not hasattr(self.game, 'deck') or not self.game.deck:
            return synergies

        deck_cards = self.game.deck
        card_count = len(deck_cards)
        max_synergy = card_count * 0.3  # Normalization factor

        # Track archetype-specific cards
        archetype_count = {
            'poison': 0,
            'strength': 0,
            'draw': 0,
            'exhaust': 0,
            'block': 0,
            'vulnerable': 0,
            'weak': 0,
            'scaling': 0
        }

        # First pass: count cards by archetype
        for card in deck_cards:
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            
            if card_data:
                description = card_data.get('description', '').lower()
                
                if 'poison' in description or 'noxious' in description:
                    archetype_count['poison'] += 1
                
                if 'strength' in description or 'gain' in description:
                    archetype_count['strength'] += 1
                
                if 'draw' in description or 'discard' in description:
                    archetype_count['draw'] += 1
                
                if 'exhaust' in description:
                    archetype_count['exhaust'] += 1
                
                if 'block' in description:
                    archetype_count['block'] += 1
                
                if 'vulnerable' in description:
                    archetype_count['vulnerable'] += 1
                
                if 'weak' in description:
                    archetype_count['weak'] += 1
                
                if any(keyword in description for keyword in ['strength', 'dexterity', 'poison', 'thorns']):
                    archetype_count['scaling'] += 1

        # Second pass: calculate synergies based on card combinations
        for i in range(len(deck_cards)):
            for j in range(i + 1, len(deck_cards)):
                card1 = deck_cards[i]
                card2 = deck_cards[j]
                
                card1_name = card1.card_id.replace('+', '')
                card2_name = card2.card_id.replace('+', '')
                
                card1_data = game_data_loader.get_card_data(card1_name)
                card2_data = game_data_loader.get_card_data(card2_name)
                
                if card1_data and card2_data:
                    desc1 = card1_data.get('description', '').lower()
                    desc2 = card2_data.get('description', '').lower()
                    
                    # Calculate synergies between specific card types
                    if ('poison' in desc1 and 'poison' in desc2) or ('catalyst' in card1.card_id.lower() and 'poison' in desc2):
                        synergies['poison'] += 0.05
                    
                    if ('strength' in desc1 and 'strength' in desc2) or ('strength' in desc1 and 'attack' in card2_data.get('type', '').lower()):
                        synergies['strength'] += 0.05
                    
                    if ('draw' in desc1 and 'draw' in desc2) or ('draw' in desc1 and 'discard' in desc2):
                        synergies['draw'] += 0.05
                    
                    if ('block' in desc1 and 'block' in desc2) or ('block' in desc1 and card2_data.get('type', '').lower() == 'power'):
                        synergies['block'] += 0.03
                    
                    if ('vulnerable' in desc1 and card2_data.get('type', '').lower() == 'attack'):
                        synergies['vulnerable'] += 0.04
                    
                    if ('weak' in desc1 and card2_data.get('type', '').lower() == 'attack'):
                        synergies['weak'] += 0.04

        # Normalize synergies to 0-1 range
        for key in synergies:
            synergies[key] = min(1.0, synergies[key] / max_synergy)

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
