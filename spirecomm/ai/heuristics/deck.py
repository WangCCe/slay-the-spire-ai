"""
Deck analysis and archetype detection.

This module provides utilities for analyzing deck composition and detecting
the strategic archetype (poison, strength, block, etc.) of a deck.
"""

from typing import Dict, List, Tuple
from spirecomm.spire.card import Card
from spirecomm.ai.decision.base import DecisionContext


class DeckAnalyzer:
    """
    Analyze deck composition and detect strategic archetypes.

    This class provides methods to understand the current deck's strategy,
    which helps inform card selection and combat decisions.
    """

    # Card categories for archetype detection
    POISON_CARDS = {'Noxious Fumes', 'Deadly Poison', 'Poison Stab', 'Catalyst', 'Bane',
                   'Crippling Poison', 'Malaise', 'Bouncing Flask', 'Venomology'}

    STRENGTH_CARDS = {'Demon Form', 'Inflame', 'Limit Break', 'Flex', 'Spot Weakness',
                     'Body Slam', 'Heavy Blade', 'Pummel', 'Perfected Strike'}

    BLOCK_CARDS = {'Iron Wave', 'Defend_R', 'Defend_G', 'Defend_B', 'Blaze', 'Impervious',
                  'Shrug It Off', 'Entrench', 'Flame Barrier', 'Ghostly Armor'}

    DRAW_CARDS = {'Adrenaline', 'Impatience', 'Acrobatics', 'Battle Trance', 'Deep Breath',
                 'Violence', 'Quick Slash', 'Tactician', 'Expertise'}

    SCALING_CARDS = {'Noxious Fumes', 'A Thousand Cuts', 'Demon Form', 'Infinite Blades',
                    'After Image', 'Barrier', 'Corruption', 'Juggernaut'}

    # Card power tiers for quality assessment
    BAD_CURSES = {'Burn', 'Injury', 'Wound', 'Slimed', 'Doubt', 'Regret', 'Shame',
                 'Pain', 'Decay', 'Normality', 'Pride', 'Parasite', 'Clumsy', 'Necronomicurse'}

    def __init__(self):
        """Initialize the deck analyzer."""
        self.card_categories = {
            'poison': self.POISON_CARDS,
            'strength': self.STRENGTH_CARDS,
            'block': self.BLOCK_CARDS,
            'draw': self.DRAW_CARDS,
            'scaling': self.SCALING_CARDS
        }

    def get_archetype(self, context: DecisionContext) -> str:
        """
        Determine the deck's archetype.

        Args:
            context: Decision context containing game state

        Returns:
            Archetype string: 'poison', 'strength', 'block', 'draw', 'scaling', 'balanced', 'unknown'
        """
        return context.deck_archetype

    def get_archetype_score(self, context: DecisionContext) -> Dict[str, float]:
        """
        Get scores for all possible archetypes.

        Returns a dictionary mapping archetype names to their strength in the current deck.
        Useful for understanding hybrid decks.

        Args:
            context: Decision context

        Returns:
            Dictionary with archetype scores (0-1)
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return {archetype: 0.0 for archetype in self.card_categories.keys()}

        deck_size = len(context.game.deck)
        scores = {}

        for archetype, card_set in self.card_categories.items():
            count = sum(1 for card in context.game.deck if card.card_id in card_set)
            # Normalize by deck size, but cap at 1.0
            scores[archetype] = min(1.0, count / max(deck_size * 0.15, 1))

        return scores

    def evaluate_deck_quality(self, context: DecisionContext) -> float:
        """
        Evaluate overall deck quality from 0-1.

        Considers:
        - Average card power (using legacy priorities as baseline)
        - Deck size (smaller is generally better)
        - Synergy within the deck
        - Curse/bad card count

        Args:
            context: Decision context

        Returns:
            Quality score from 0 (terrible) to 1 (excellent)
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return 0.5

        deck = context.game.deck
        deck_size = len(deck)

        # Start with base score
        quality = 0.5

        # 1. Deck size penalty/gain
        if deck_size <= 10:
            quality += 0.1
        elif deck_size >= 20:
            quality -= (deck_size - 20) * 0.02
        elif deck_size <= 15:
            quality += 0.05

        # 2. Curse/bad card penalty
        bad_cards = sum(1 for card in deck if card.card_id in self.BAD_CURSES)
        quality -= bad_cards * 0.05

        # 3. Synergy bonus - use context's precomputed synergies
        avg_synergy = sum(context.card_synergies.values()) / len(context.card_synergies)
        quality += avg_synergy * 0.3

        # 4. Archetype clarity bonus
        archetype_scores = self.get_archetype_score(context)
        max_archetype_score = max(archetype_scores.values())
        if max_archetype_score > 0.5:
            quality += 0.1  # Bonus for having clear strategy

        # Clamp to valid range
        return max(0.0, min(1.0, quality))

    def get_deck_stats(self, context: DecisionContext) -> Dict[str, any]:
        """
        Get comprehensive deck statistics.

        Args:
            context: Decision context

        Returns:
            Dictionary with various deck metrics
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return {
                'size': 0,
                'avg_cost': 0,
                'attack_count': 0,
                'skill_count': 0,
                'power_count': 0,
                'curse_count': 0,
                'upgraded_count': 0,
                'upgrade_rate': 0
            }

        deck = context.game.deck

        stats = {
            'size': len(deck),
            'avg_cost': sum(c.cost for c in deck) / len(deck) if deck else 0,
            'attack_count': sum(1 for c in deck if hasattr(c, 'type') and str(c.type) == 'ATTACK'),
            'skill_count': sum(1 for c in deck if hasattr(c, 'type') and str(c.type) == 'SKILL'),
            'power_count': sum(1 for c in deck if hasattr(c, 'type') and str(c.type) == 'POWER'),
            'curse_count': sum(1 for c in deck if c.card_id in self.BAD_CURSES),
            'upgraded_count': sum(1 for c in deck if hasattr(c, 'upgrades') and c.upgrades > 0),
            'archetype': context.deck_archetype,
            'archetype_scores': self.get_archetype_score(context),
            'quality': self.evaluate_deck_quality(context)
        }

        if stats['size'] > 0:
            stats['upgrade_rate'] = stats['upgraded_count'] / stats['size']

        return stats

    def needs_cards_of_type(self, context: DecisionContext, card_type: str) -> bool:
        """
        Determine if deck needs more cards of a specific type.

        Useful for reward selection - if we already have too many attacks,
        we probably don't need more.

        Args:
            context: Decision context
            card_type: Type of card ('attack', 'skill', 'power', 'poison', etc.)

        Returns:
            True if deck would benefit from more of this card type
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return True

        deck = context.game.deck

        if card_type == 'attack':
            attack_count = sum(1 for c in deck if hasattr(c, 'type') and str(c.type) == 'ATTACK')
            return attack_count < len(deck) * 0.4  # Don't want more than 40% attacks

        elif card_type == 'skill':
            skill_count = sum(1 for c in deck if hasattr(c, 'type') and str(c.type) == 'SKILL')
            return skill_count < len(deck) * 0.5

        elif card_type == 'power':
            power_count = sum(1 for c in deck if hasattr(c, 'type') and str(c.type) == 'POWER')
            return power_count < 5  # Powers are rare, cap at 5

        elif card_type in self.card_categories:
            # Archetype-specific cards
            count = sum(1 for c in deck if c.card_id in self.card_categories[card_type])
            # Want enough to support archetype but not too many
            target = len(deck) * 0.15
            return count < target + 2

        return True

    def find_weakest_card(self, context: DecisionContext, exclude: List[str] = None) -> Card:
        """
        Find the weakest card in the deck (good for purging).

        Considers card power, curses, and deck archetype.

        Args:
            context: Decision context
            exclude: List of card IDs to exclude from consideration

        Returns:
            The card that would be best to remove
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return None

        exclude = exclude or []
        deck = [c for c in context.game.deck if c.card_id not in exclude]

        if not deck:
            return None

        # Priority for removal: curses > bad cards > off-archetype > weak cards
        def removal_priority(card):
            # Curses first
            if card.card_id in self.BAD_CURSES:
                return 100  # High priority to remove

            # Off-archetype cards
            if context.deck_archetype in self.card_categories:
                archetype_cards = self.card_categories[context.deck_archetype]
                if card.card_id not in archetype_cards:
                    # Check if it fits a different archetype
                    fits_other = any(
                        card.card_id in card_set
                        for arch, card_set in self.card_categories.items()
                        if arch != context.deck_archetype
                    )
                    if fits_other:
                        return 50  # Medium priority
                    return 30  # Low priority

            return 0  # Keep cards that fit archetype

        return max(deck, key=removal_priority)
