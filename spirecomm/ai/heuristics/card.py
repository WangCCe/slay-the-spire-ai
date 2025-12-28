"""
Synergy-based card evaluation.

This module implements an advanced card evaluator that goes beyond fixed priority lists
to consider card synergies, game state context, and deck composition.
"""

import math
from typing import Dict, List
from spirecomm.spire.card import Card
from spirecomm.spire.character import Intent
from spirecomm.ai.decision.base import DecisionContext, CardEvaluator
from spirecomm.ai.priorities import Priority, SilentPriority, IroncladPriority, DefectPowerPriority
from spirecomm.ai.heuristics.deck import DeckAnalyzer


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
            self.baseline_scores[card_id] = 100 - i * 0.5

        # Add "Skip" as a baseline reference
        if 'Skip' in priority.CARD_PRIORITY_LIST:
            skip_idx = priority.CARD_PRIORITY_LIST.index('Skip')
            self.baseline_scores['Skip'] = 100 - skip_idx * 0.5

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
        # 1. Baseline score from legacy priorities
        baseline = self.baseline_scores.get(card.card_id, 50)

        # 2. Contextual modifiers
        modifier = self._calculate_context_modifier(card, context)

        # 3. Deck synergy bonus
        synergy_bonus = self._calculate_synergy_bonus(card, context)

        # 4. Combo detection
        combo_bonus = self._detect_combo_potential(card, context)

        # Calculate final score
        final_score = (baseline * modifier) + synergy_bonus + combo_bonus

        return final_score

    def _calculate_context_modifier(self, card: Card, context: DecisionContext) -> float:
        """Calculate modifier based on current game state."""
        modifier = 1.0

        # Energy efficiency
        if card.cost > 0 and context.energy_available > 0:
            energy_ratio = context.energy_available / card.cost
            # Bonus if we have plenty of energy for this card
            modifier *= min(energy_ratio, 1.5)
        elif card.cost == 0:
            # Zero-cost cards are always efficient
            modifier *= 1.2

        # HP-dependent modifiers
        if context.player_hp_pct < 0.3:
            # Critical HP: prioritize defensive cards and healing
            if self._is_defensive_card(card):
                modifier *= 2.0
            elif self._is_offensive_card(card):
                modifier *= 0.7  # Less valuable when dying
        elif context.player_hp_pct > 0.8:
            # High HP: can afford to be aggressive
            if self._is_offensive_card(card):
                modifier *= 1.2

        # Monster intent adaptation
        if len(context.monsters_alive) > 0:
            incoming_threat = context.incoming_damage / max(context.game.current_hp, 1)

            if self._is_defensive_card(card):
                if incoming_threat > 0.3:
                    # Defense more valuable when threatened
                    modifier *= 1.5
                elif incoming_threat < 0.1:
                    # Defense less valuable when safe
                    modifier *= 0.6

            # Offensive cards against low HP monsters (finish them off)
            if self._is_offensive_card(card):
                low_hp_monsters = [m for m in context.monsters_alive if m.current_hp < 20]
                if len(low_hp_monsters) > 0:
                    modifier *= 1.3

        return modifier

    def _calculate_synergy_bonus(self, card: Card, context: DecisionContext) -> float:
        """Calculate bonus based on deck composition and synergies."""
        bonus = 0.0
        card_id_lower = card.card_id.lower()

        # Poison synergy
        if 'poison' in card_id_lower or card.card_id == 'Catalyst':
            poison_synergy = context.card_synergies.get('poison', 0)
            bonus += poison_synergy * 20 * self.SYNERGY_WEIGHTS['poison']

        # Strength synergy
        if card.card_id in ['Demon Form', 'Inflame', 'Limit Break', 'Flex']:
            strength_synergy = context.card_synergies.get('strength', 0)
            bonus += strength_synergy * 25 * self.SYNERGY_WEIGHTS['strength']

        # Draw synergy
        if 'draw' in card_id_lower or card.card_id in ['Adrenaline', 'Impatience', 'Acrobatics']:
            draw_synergy = context.card_synergies.get('draw', 0)
            bonus += draw_synergy * 15 * self.SYNERGY_WEIGHTS['draw']

        # Exhaust synergy
        if 'exhaust' in card_id_lower:
            exhaust_synergy = context.card_synergies.get('exhaust', 0)
            bonus += exhaust_synergy * 18 * self.SYNERGY_WEIGHTS['exhaust']

        # Scaling synergy
        if card.card_id in ['Noxious Fumes', 'A Thousand Cuts', 'Infinite Blades', 'Demon Form']:
            scaling_synergy = context.card_synergies.get('scaling', 0)
            bonus += scaling_synergy * 22 * self.SYNERGY_WEIGHTS['scaling']

        return bonus

    def _detect_combo_potential(self, card: Card, context: DecisionContext) -> float:
        """Detect card combinations in hand/deck."""
        combo_score = 0.0

        if not hasattr(context.game, 'deck'):
            return 0.0

        deck_card_ids = {c.card_id for c in context.game.deck}

        # Check specific combo synergies
        for (card1, card2), bonus in self.COMBO_SYNERGIES.items():
            if card.card_id == card1:
                if card2 == 'unupgraded':
                    # Special case: count unupgraded cards
                    unupgraded = sum(1 for c in context.game.deck
                                   if hasattr(c, 'upgrades') and c.upgrades == 0)
                    combo_score += unupgraded * bonus / 10
                elif card2 in deck_card_ids:
                    combo_score += bonus

        # Additional archetype-specific combo detection
        if context.deck_archetype == 'poison':
            if card.card_id == 'Catalyst':
                # Catalyst scales with poison count
                poison_count = sum(1 for c in context.game.deck
                                 if 'poison' in c.card_id.lower())
                combo_score += poison_count * 5

        elif context.deck_archetype == 'strength':
            if card.card_id == 'Body Slam':
                # Body Slam with high block synergy
                if context.game.player.block > 20:
                    combo_score += 15

        return combo_score

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is primarily defensive."""
        defensive_keywords = ['defend', 'block', 'blur', 'wave', 'glacier',
                            'iron wave', 'flame barrier', 'hand of greed']

        card_lower = card.card_id.lower()
        return any(keyword in card_lower for keyword in defensive_keywords)

    def _is_offensive_card(self, card: Card) -> bool:
        """Check if card is primarily offensive."""
        # Check if card type is ATTACK
        if hasattr(card, 'type') and str(card.type) == 'ATTACK':
            return True

        # Some skills that deal damage
        offensive_skills = ['noxious fumes', 'thousand cuts', 'infinite blades']
        card_lower = card.card_id.lower()
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
        if 0.4 <= context.player_hp_pct <= 0.8:
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
