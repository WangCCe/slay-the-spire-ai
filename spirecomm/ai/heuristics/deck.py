"""
Deck analysis and archetype detection.

This module provides utilities for analyzing deck composition and detecting
the strategic archetype (poison, strength, block, etc.) of a deck.
"""

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from spirecomm.spire.card import Card
from spirecomm.data.loader import game_data_loader
import re

# Avoid circular imports using TYPE_CHECKING
if TYPE_CHECKING:
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

    STORM_CARDS = {'Storm', 'Tempest', 'Blizzard', 'Cyclone', 'Thunder Strike', 'Lightning Strike'}

    HEAL_CARDS = {'Bandage Up', 'Second Wind', 'Rupture', 'Regeneration', 'Reaper', 'Bloodletting'}

    MALICE_CARDS = {'Cleave', 'Anger', 'Berserk', 'Whirlwind', 'Rampage', 'Frenzy'}

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
            'scaling': self.SCALING_CARDS,
            'storm': self.STORM_CARDS,
            'heal': self.HEAL_CARDS,
            'malice': self.MALICE_CARDS
        }

    def get_archetype(self, context: 'DecisionContext') -> str:
        """
        Determine the deck's archetype based on card composition and synergies.

        Args:
            context: Decision context containing game state

        Returns:
            Archetype string: 'poison', 'strength', 'block', 'draw', 'scaling', 'exhaust', 'combo', 'balanced', 'unknown'
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return 'unknown'
        
        # Get enhanced archetype scores
        archetype_scores = self.get_archetype_score(context)
        deck_size = len(context.game.deck)
        
        # Get the highest scoring archetype
        max_score = max(archetype_scores.values())
        
        # If multiple archetypes have the same max score, apply tie-breaker logic
        best_candidates = [arch for arch, score in archetype_scores.items() if score == max_score]
        
        # Always use priority order for tie-breakers, even when synergies are equal
        priority_order = ['combo', 'storm', 'poison', 'strength', 'scaling', 'heal', 'malice', 'draw', 'block', 'exhaust']
        
        if len(best_candidates) > 1:
            # Check if it's truly balanced (strength and block are tied)
            if set(best_candidates) == {'strength', 'block'}:
                return 'balanced'
            
            # For tie-breakers, first use synergy scores, then priority order
            if hasattr(context, 'card_synergies'):
                # Sort candidates by synergy score descending, then by priority order
                best_candidates.sort(key=lambda arch: (context.card_synergies.get(arch, 0), -priority_order.index(arch)), reverse=True)
                best_archetype = best_candidates[0]
            else:
                # Fall back to priority order
                best_archetype = next((arch for arch in priority_order if arch in best_candidates), best_candidates[0])
        else:
            best_archetype = best_candidates[0]
        
        # Check for balanced deck (no clear archetype - max score is too low)
        if max_score < 0.6:
            return 'balanced'
        
        return best_archetype

    def get_archetype_score(self, context: 'DecisionContext') -> Dict[str, float]:
        """
        Get scores for all possible archetypes including enhanced detection.

        Returns a dictionary mapping archetype names to their strength in the current deck.
        Useful for understanding hybrid decks.

        Args:
            context: Decision context

        Returns:
            Dictionary with archetype scores (0-1)
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            base_archetypes = list(self.card_categories.keys()) + ['exhaust', 'combo']
            return {archetype: 0.0 for archetype in base_archetypes}

        deck_size = len(context.game.deck)
        deck = context.game.deck
        scores = {}

        # Enhanced effect patterns for each archetype
        archetype_effect_patterns = {
            'poison': [r'poison', r'toxic', r'add.*poison'],
            'strength': [r'strength', r'gain.*strength'],
            'block': [r'block', r'shield', r'armor', r'gain.*block'],
            'draw': [r'draw', r'add.*card', r'gain.*card', r'draw.*card'],
            'scaling': [r'strength', r'dexterity', r'poison', r'thousand cuts', r'barrier', r'scale'],
            'storm': [r'storm', r'play.*unlimited', r'play.*any.*number', r'no.*limit.*play'],
            'heal': [r'heal', r'regain.*hp', r'gain.*hp', r'restore.*hp'],
            'malice': [r'damage.*all', r'aoe', r'cleave', r'whirlwind', r'rampage', r'frenzy']
        }

        # Detect cards by effect using game data for each archetype
        for archetype, base_cards in self.card_categories.items():
            count = 0
            
            # Count base archetype cards
            for card in deck:
                if card.card_id in base_cards:
                    count += 1
                
                # Enhanced detection using card descriptions from game data loader
                card_data = game_data_loader.get_card_data(card.name.lower())
                if card_data:
                    description = card_data.get('description', '').lower()
                    
                    # Check for effect patterns using regex
                    for pattern in archetype_effect_patterns[archetype]:
                        if re.search(pattern, description):
                            count += 0.5  # Partial credit for effect cards
                            break
            
            # Normalize and cap
            scores[archetype] = min(1.0, count / max(deck_size * 0.25, 3))
        
        # Add enhanced exhaust archetype detection
        exhaust_cards = {'Corruption', 'Feel No Pain', 'Dark Embrace', 'Exhume', 'Second Wind', 'Apotheosis'}
        exhaust_count = sum(1 for card in deck if card.card_id in exhaust_cards)
        
        # Enhanced exhaust detection using game data
        for card in deck:
            card_data = game_data_loader.get_card_data(card.name.lower())
            if card_data:
                description = card_data.get('description', '').lower()
                if any(keyword in description for keyword in ['exhaust.*draw', 'gain.*when.*exhaust', 'exhaust']):
                    exhaust_count += 0.5
        
        scores['exhaust'] = min(1.0, exhaust_count / max(deck_size * 0.25, 3))
        
        # Add enhanced combo archetype detection
        combo_cards = {'Backflip', 'Finesse', 'Well-Laid Plans', 'Reflex', 'Tactician', 'After Image'}
        combo_count = sum(1 for card in deck if card.card_id in combo_cards)
        
        # Enhanced combo detection using game data
        for card in deck:
            card_data = game_data_loader.get_card_data(card.name.lower())
            if card_data:
                description = card_data.get('description', '').lower()
                if any(keyword in description for keyword in ['cost.*0', 'retain', 'draw.*1', 'exhaust.*draw', 'gain.*energy']):
                    combo_count += 0.5
        
        scores['combo'] = min(1.0, combo_count / max(deck_size * 0.25, 3))

        return scores

    def evaluate_deck_quality(self, context: 'DecisionContext') -> float:
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

    def get_deck_stats(self, context: 'DecisionContext') -> Dict[str, any]:
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
            'attack_count': sum(1 for c in deck if hasattr(c, 'type') and c.type.name == 'ATTACK'),
            'skill_count': sum(1 for c in deck if hasattr(c, 'type') and c.type.name == 'SKILL'),
            'power_count': sum(1 for c in deck if hasattr(c, 'type') and c.type.name == 'POWER'),
            'curse_count': sum(1 for c in deck if c.card_id in self.BAD_CURSES),
            'upgraded_count': sum(1 for c in deck if hasattr(c, 'upgrades') and c.upgrades > 0),
            'archetype': self.get_archetype(context),
            'archetype_scores': self.get_archetype_score(context),
            'quality': self.evaluate_deck_quality(context)
        }

        if stats['size'] > 0:
            stats['upgrade_rate'] = stats['upgraded_count'] / stats['size']

        return stats

    def needs_cards_of_type(self, context: 'DecisionContext', card_type: str) -> bool:
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
            attack_count = sum(1 for c in deck if hasattr(c, 'type') and c.type.name == 'ATTACK')
            return attack_count < len(deck) * 0.4  # Don't want more than 40% attacks

        elif card_type == 'skill':
            skill_count = sum(1 for c in deck if hasattr(c, 'type') and c.type.name == 'SKILL')
            return skill_count < len(deck) * 0.5

        elif card_type == 'power':
            power_count = sum(1 for c in deck if hasattr(c, 'type') and c.type.name == 'POWER')
            return power_count < 5  # Powers are rare, cap at 5

        elif card_type in self.card_categories:
            # Archetype-specific cards
            count = sum(1 for c in deck if c.card_id in self.card_categories[card_type])
            # Want enough to support archetype but not too many
            target = len(deck) * 0.15
            return count < target + 2

        return True

    def find_weakest_card(self, context: 'DecisionContext', exclude: List[str] = None) -> Card:
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
            deck_archetype = self.get_archetype(context)
            if deck_archetype in self.card_categories:
                archetype_cards = self.card_categories[deck_archetype]
                if card.card_id not in archetype_cards:
                    # Check if it fits a different archetype
                    fits_other = any(
                        card.card_id in card_set
                        for arch, card_set in self.card_categories.items()
                        if arch != deck_archetype
                    )
                    if fits_other:
                        return 50  # Medium priority
                    return 30  # Low priority

            return 0  # Keep cards that fit archetype

        return max(deck, key=removal_priority)
