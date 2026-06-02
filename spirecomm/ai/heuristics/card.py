"""
Synergy-based card evaluation.

This module implements an advanced card evaluator that goes beyond fixed priority lists
to consider card synergies, game state context, and deck composition.
"""

import math
import re
from typing import Dict, List
from spirecomm.spire.card import Card
from spirecomm.spire.character import Intent
from spirecomm.data.loader import game_data_loader
from spirecomm.ai.decision.base import DecisionContext, CardEvaluator
from spirecomm.ai.priorities import Priority, SilentPriority, IroncladPriority, DefectPowerPriority
from spirecomm.ai.heuristics.deck import DeckAnalyzer
from spirecomm.ai.heuristics.card_costs import effective_card_cost
from spirecomm.ai.heuristics.card_names import canonical_card_name, card_data_key
from spirecomm.ai.heuristics.card_types import card_type_name
from spirecomm.ai.heuristics.card_upgrades import card_upgrade_count
from spirecomm.spire.numeric import coerce_float, coerce_int


class SynergyCardEvaluator(CardEvaluator):
    """
    Evaluates cards based on multiple factors:
    - Raw card power (from legacy priorities as baseline)
    - Synergy with current deck
    - Contextual value (HP, energy, monster intent)
    - Combo potential
    """

    # Synergy weights for different interactions
    SYNERGY_WEIGHTS = {
        'poison': 1.5,       # Poison cards scale with poison count
        'strength': 1.3,     # Strength cards scale with str
        'block': 0.8,        # Block cards less valuable with lots
        'draw': 1.2,         # Draw scales with deck density
        'exhaust': 1.4,      # Exhaust scales with bad cards
        'scaling': 1.6       # Scaling cards are very valuable
    }

    # Specific card combinations
    COMBO_SYNERGIES = {
        ('After Image', 'Adrenaline'): 20,
        ('After Image', 'Impatience'): 15,
        ('After Image', 'Acrobatics'): 15,
        ('Apotheosis', 'unupgraded'): 10,  # Bonus per unupgraded card
        ('Demon Form', 'Limit Break'): 25,
        ('Demon Form', 'Body Slam'): 20,
        ('Noxious Fumes', 'Catalyst'): 25,
        ('Noxious Fumes', 'Deadly Poison'): 15,
        ('Infinite Blades', 'Accuracy'): 20,
        ('Barricade', 'Entrench'): 25,
    }

    def __init__(self, player_class=None):
        """
        Initialize the evaluator.

        Args:
            player_class: The player class for legacy priority loading
        """
        self.deck_analyzer = DeckAnalyzer()
        self.baseline_scores = {}
        self.load_legacy_priorities(player_class)

    @staticmethod
    def _non_negative_int(value, default: int = 0) -> int:
        return max(0, coerce_int(value, default))

    @staticmethod
    def _positive_float(value, default: float = 1.0) -> float:
        numeric = coerce_float(value, default)
        return numeric if numeric > 0 else default

    @staticmethod
    def _non_negative_float(value) -> float:
        return max(0.0, coerce_float(value or 0, 0.0))

    def load_legacy_priorities(self, player_class):
        """Load baseline scores from legacy priority lists."""
        if player_class == 'THE_SILENT' or player_class is None:
            priority = SilentPriority()
        elif player_class == 'IRONCLAD':
            priority = IroncladPriority()
        elif player_class == 'DEFECT':
            priority = DefectPowerPriority()
        else:
            priority = SilentPriority()  # Default

        # Convert priority list to baseline scores (lower priority = better, so invert)
        for i, card_id in enumerate(priority.CARD_PRIORITY_LIST):
            # Convert to score where higher is better
            # Use a log-like scale to give more separation to top cards
            self.baseline_scores[canonical_card_name(card_id)] = 100 - i * 0.5

        # Add "Skip" as a baseline reference
        if 'Skip' in priority.CARD_PRIORITY_LIST:
            skip_idx = priority.CARD_PRIORITY_LIST.index('Skip')
            self.baseline_scores['Skip'] = 100 - skip_idx * 0.5

    @staticmethod
    def _card_data_key(card: Card) -> str:
        return card_data_key(card)

    @staticmethod
    def _card_name(card: Card) -> str:
        return canonical_card_name(card)

    def evaluate_card(self, card: Card, context: DecisionContext) -> float:
        """
        Evaluate card value in current context.

        Returns a score where higher is better.

        Args:
            card: The card to evaluate
            context: Current decision context

        Returns:
            Numeric value score
        """
        # 1. Get card information from game data
        card_data = game_data_loader.get_card_data(self._card_data_key(card))
        
        # 2. Baseline score from legacy priorities and game data
        baseline = self._calculate_baseline_score(card, card_data)

        # 3. Contextual modifiers
        modifier = self._calculate_context_modifier(card, context, card_data)

        # 4. Deck synergy bonus
        synergy_bonus = self._calculate_synergy_bonus(card, context, card_data)

        # 5. Combo detection
        combo_bonus = self._detect_combo_potential(card, context, card_data)

        # Calculate final score
        final_score = (baseline * modifier) + synergy_bonus + combo_bonus

        return final_score
    
    def _calculate_baseline_score(self, card: Card, card_data: Dict[str, any]) -> float:
        """Calculate baseline score using game data."""
        # Start with legacy priority baseline
        card_name = self._card_name(card)
        baseline = self.baseline_scores.get(card_name, 50)
        
        if card_data:
            # Adjust based on card rarity
            rarity = card_data.get('rarity', '').upper()
            rarity_bonus = {
                'BASIC': 0,
                'COMMON': 5,
                'UNCOMMON': 10,
                'RARE': 15,
                'SPECIAL': 10
            }.get(rarity, 0)
            baseline += rarity_bonus
            
            # Adjust based on card type
            card_type = card_data.get('type', '').upper()
            type_bonus = {
                'POWER': 5,  # Power cards are generally more valuable
                'ATTACK': 0,
                'SKILL': 0
            }.get(card_type, 0)
            baseline += type_bonus

            # Adjust based on energy cost efficiency
            cost = card_data.get('cost', 0)
            try:
                cost_value = int(cost)
            except (TypeError, ValueError):
                cost_value = None
            if cost_value is not None and cost_value >= 0:
                # More efficient cards (higher value per energy) get bonus
                description = card_data.get('description', '').lower()
                if 'damage' in description:
                    # Simple damage per energy calculation
                    damage_match = re.search(r'deal (\d+) damage', description)
                    if damage_match:
                        damage = int(damage_match.group(1))
                        if re.search(r'\btwice\b', description):
                            damage *= 2
                        else:
                            hits_match = re.search(r'damage(?:\s+to [^.]+?)?\s+(\d+)\s+times', description)
                            if hits_match:
                                damage *= int(hits_match.group(1))
                        if cost_value > 0:
                            efficiency = damage / cost_value
                            if efficiency > 5:  # More than 5 damage per energy is good
                                baseline += 10
                            elif efficiency > 3:  # More than 3 damage per energy is decent
                                baseline += 5
        
        return baseline

    def _calculate_context_modifier(self, card: Card, context: DecisionContext, card_data: Dict[str, any]) -> float:
        """Calculate modifier based on current game state."""
        modifier = 1.0

        # Energy efficiency
        available_energy = self._non_negative_int(
            getattr(context, 'energy_available', 0)
        )
        cost = effective_card_cost(card, available_energy)
        if cost > 0 and available_energy > 0:
            energy_ratio = available_energy / cost
            # Bonus if we have plenty of energy for this card
            modifier *= min(energy_ratio, 1.5)
        elif cost == 0:
            # Zero-cost cards are always efficient
            modifier *= 1.2

        # HP-dependent modifiers
        player_hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        if player_hp_pct < 0.3:
            # Critical HP: prioritize defensive cards and healing
            if self._is_defensive_card(card):
                modifier *= 2.0
            elif self._is_offensive_card(card):
                modifier *= 0.7  # Less valuable when dying
        elif player_hp_pct > 0.8:
            # High HP: can afford to be aggressive
            if self._is_offensive_card(card):
                modifier *= 1.2

        # Monster intent adaptation
        if len(context.monsters_alive) > 0:
            player_hp = self._positive_float(
                getattr(getattr(context, 'game', None), 'current_hp', 1),
                default=1.0,
            )
            incoming_damage = self._non_negative_float(getattr(context, 'incoming_damage', 0))
            incoming_threat = incoming_damage / player_hp

            if self._is_defensive_card(card):
                if incoming_threat > 0.3:
                    # Defense more valuable when threatened
                    modifier *= 1.5
                elif incoming_threat < 0.1:
                    # Defense less valuable when safe
                    modifier *= 0.6

            # Offensive cards against low HP monsters (finish them off)
            if self._is_offensive_card(card):
                low_hp_monsters = [
                    m
                    for m in context.monsters_alive
                    if self._non_negative_int(
                        getattr(m, 'current_hp', 0),
                        default=999,
                    ) < 20
                ]
                if len(low_hp_monsters) > 0:
                    modifier *= 1.3

        return modifier

    def _calculate_synergy_bonus(self, card: Card, context: DecisionContext, card_data: Dict[str, any]) -> float:
        """Calculate bonus based on deck composition and synergies."""
        bonus = 0.0
        card_name = self._card_name(card)
        card_name_lower = card_name.lower()
        has_poison = False
        has_strength = False
        has_draw = False
        has_exhaust = False
        has_scaling = False

        # Use game data to detect card synergies more accurately
        if card_data:
            description = card_data.get('description', '').lower()
            if 'poison' in description:
                has_poison = True
            if 'strength' in description or 'deal' in description:
                has_strength = True
            if 'draw' in description or 'draw' in card_name_lower:
                has_draw = True
            if 'exhaust' in description:
                has_exhaust = True
            # Check for scaling effects
            if any(keyword in description for keyword in ['increase', 'gain', 'apply', 'permanent']):
                has_scaling = True

        # Poison synergy
        if has_poison or card_name == 'Catalyst':
            poison_synergy = context.card_synergies.get('poison', 0)
            bonus += poison_synergy * 20 * self.SYNERGY_WEIGHTS['poison']

        # Strength synergy
        if has_strength or card_name in ['Demon Form', 'Inflame', 'Limit Break', 'Flex']:
            strength_synergy = context.card_synergies.get('strength', 0)
            bonus += strength_synergy * 25 * self.SYNERGY_WEIGHTS['strength']

        # Draw synergy
        if has_draw or 'draw' in card_name_lower or card_name in ['Adrenaline', 'Impatience', 'Acrobatics']:
            draw_synergy = context.card_synergies.get('draw', 0)
            bonus += draw_synergy * 15 * self.SYNERGY_WEIGHTS['draw']

        # Exhaust synergy
        if has_exhaust or 'exhaust' in card_name_lower:
            exhaust_synergy = context.card_synergies.get('exhaust', 0)
            bonus += exhaust_synergy * 18 * self.SYNERGY_WEIGHTS['exhaust']

        # Scaling synergy
        if has_scaling or card_name in ['Noxious Fumes', 'A Thousand Cuts', 'Infinite Blades', 'Demon Form']:
            scaling_synergy = context.card_synergies.get('scaling', 0)
            bonus += scaling_synergy * 22 * self.SYNERGY_WEIGHTS['scaling']

        return bonus

    def _detect_combo_potential(self, card: Card, context: DecisionContext, card_data: Dict[str, any]) -> float:
        """Detect card combinations in hand/deck."""
        combo_score = 0.0

        if not hasattr(context.game, 'deck'):
            return 0.0

        card_name = self._card_name(card)
        deck_card_names = {self._card_name(c) for c in context.game.deck}

        # Check specific combo synergies
        for (card1, card2), bonus in self.COMBO_SYNERGIES.items():
            if card_name == card1:
                if card2 == 'unupgraded':
                    # Special case: count unupgraded cards
                    unupgraded = sum(1 for c in context.game.deck
                                   if card_upgrade_count(c) == 0)
                    combo_score += unupgraded * bonus / 10
                elif card2 in deck_card_names:
                    combo_score += bonus
            elif card2 != 'unupgraded' and card_name == card2 and card1 in deck_card_names:
                combo_score += bonus

        # Additional archetype-specific combo detection
        if context.deck_archetype == 'poison':
            if card_name == 'Catalyst':
                # Catalyst scales with poison count
                poison_count = sum(1 for c in context.game.deck
                                 if 'poison' in self._card_name(c).lower())
                combo_score += poison_count * 5

        elif context.deck_archetype == 'strength':
            if card_name == 'Body Slam':
                # Body Slam with high block synergy
                player = getattr(context.game, 'player', None)
                player_block = self._non_negative_int(getattr(player, 'block', 0))
                if player_block > 20:
                    combo_score += 15

        return combo_score

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is primarily defensive."""
        defensive_keywords = ['defend', 'block', 'blur', 'wave', 'glacier',
                            'iron wave', 'flame barrier', 'protect']
        
        # Check card type first
        if card_type_name(card) == 'SKILL':
            # Get card information from game data
            card_data = game_data_loader.get_card_data(self._card_data_key(card))
            if card_data:
                description = card_data.get('description', '').lower()
                # If it has defensive keywords in description
                if any(keyword in description for keyword in defensive_keywords):
                    return True
        
        # Fallback to card name based detection
        card_lower = self._card_name(card).lower()
        return any(keyword in card_lower for keyword in defensive_keywords)

    def _is_offensive_card(self, card: Card) -> bool:
        """Check if card is primarily offensive."""
        # Check if card type is ATTACK
        if card_type_name(card) == 'ATTACK':
            return True
        
        # Check card data for offensive effects
        card_data = game_data_loader.get_card_data(self._card_data_key(card))
        if card_data:
            description = card_data.get('description', '').lower()
            # If it deals damage, it's offensive
            if 'damage' in description or 'deal' in description:
                return True
        
        # Fallback to skill-based detection
        offensive_skills = ['noxious fumes', 'thousand cuts', 'infinite blades']
        card_lower = self._card_name(card).lower()
        return any(skill in card_lower for skill in offensive_skills)

    def get_confidence(self, context: DecisionContext) -> float:
        """
        Return confidence in card evaluation.

        Higher confidence when:
        - Deck has clear archetype
        - Game state is stable
        - Deck is not too large
        """
        confidence = 0.5

        # Archetype clarity increases confidence
        archetype_scores = self.deck_analyzer.get_archetype_score(context)
        max_score = max(archetype_scores.values())
        confidence += max_score * 0.3

        # Stable HP increases confidence
        player_hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        if 0.4 <= player_hp_pct <= 0.8:
            confidence += 0.1

        # Reasonable deck size
        if hasattr(context.game, 'deck') and 10 <= len(context.game.deck) <= 20:
            confidence += 0.1

        return min(1.0, confidence)

    def rank_cards(self, cards: List[Card], context: DecisionContext) -> List[Card]:
        """
        Rank cards from best to worst.

        Args:
            cards: List of cards to rank
            context: Current decision context

        Returns:
            Sorted list of cards
        """
        return sorted(cards, key=lambda c: self.evaluate_card(c, context), reverse=True)

    def get_best_card(self, cards: List[Card], context: DecisionContext) -> Card:
        """
        Get the best card from a list.

        Args:
            cards: List of cards to choose from
            context: Current decision context

        Returns:
            The highest-value card
        """
        if not cards:
            return None
        return max(cards, key=lambda c: self.evaluate_card(c, context))

    def get_worst_card(self, cards: List[Card], context: DecisionContext) -> Card:
        """
        Get the worst card from a list.

        Args:
            cards: List of cards to choose from
            context: Current decision context

        Returns:
            The lowest-value card
        """
        if not cards:
            return None
        return min(cards, key=lambda c: self.evaluate_card(c, context))
