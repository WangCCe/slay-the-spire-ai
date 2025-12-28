"""
Ironclad deck archetype manager for detecting and managing deck strategies.

Identifies and tracks three main Ironclad archetypes:
1. Strength Scaling (Demon Form, Limit Break, Spot Weakness)
2. Exhaust/Corruption (Corruption, Feel No Pain, Dark Embrace)
3. Body Slam/Barricade (Barricade, Entrench, Body Slam)
"""

from typing import Dict, List, Optional, Tuple
from ..decision.base import DecisionContext
from spirecomm.spire.card import Card


class IroncladArchetypeManager:
    """
    Manages Ironclad deck archetype detection and strategy.

    Helps the AI:
    - Identify current deck archetype
    - Suggest archetype pivots if current strategy isn't working
    - Provide archetype-specific card recommendations
    """

    # Archetype definitions
    ARCHETYPES = {
        'strength': {
            'core': ['Demon Form', 'Limit Break', 'Spot Weakness', 'Inflame'],
            'support': ['Reaper', 'Disarm', 'Flex', 'Body Slam', 'Heavy Blade'],
            'threshold': 0.35,  # 35% of deck = strength archetype
        },
        'exhaust': {
            'core': ['Corruption', 'Feel No Pain', 'Dark Embrace'],
            'support': ['Offering', 'Second Wind', 'Exhume', 'Combust'],
            'threshold': 0.30,
        },
        'body_slam': {
            'core': ['Barricade', 'Body Slam', 'Entrench'],
            'support': ['Iron Wave', 'Impervious', 'Flame Barrier', 'Calipers'],
            'threshold': 0.30,
        },
    }

    # Cards that indicate flexibility (early game)
    FLEXIBLE_CARDS = [
        'Bash', 'Iron Wave', 'Shrug It Off', 'True Grit', 'Pommel Strike',
        'Cleave', 'Uppercut', 'Headbutt', 'Anger',
    ]

    def detect_archetype(self, context: DecisionContext) -> str:
        """
        Detect current deck archetype.

        Returns:
            'strength', 'exhaust', 'body_slam', 'flexible', or 'unknown'
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return 'unknown'

        deck = context.game.deck
        deck_size = len(deck)

        if deck_size < 8:
            return 'flexible'  # Too early to tell

        # Calculate archetype scores
        archetype_scores = self.get_archetype_scores(deck)

        # Check if any archetype exceeds threshold
        max_archetype = None
        max_score = 0

        for archetype, score in archetype_scores.items():
            if score > max_score:
                max_score = score
                max_archetype = archetype

        # Check if archetype is well-established
        threshold = self.ARCHETYPES[max_archetype]['threshold'] if max_archetype else 0.3

        if max_score >= threshold:
            return max_archetype
        elif max_score >= 0.2:
            return 'flexible'  # Some direction but not committed
        else:
            return 'unknown'  # No clear archetype

    def get_archetype_scores(self, deck: List[Card]) -> Dict[str, float]:
        """
        Calculate archetype affinity scores.

        Returns:
            Dict mapping archetype name to score (0.0 to 1.0)
        """
        if not deck:
            return {'strength': 0.0, 'exhaust': 0.0, 'body_slam': 0.0}

        deck_size = len(deck)
        scores = {}

        for archetype, definition in self.ARCHETYPES.items():
            core_count = sum(1 for card in deck
                           if card.card_id in definition['core'])
            support_count = sum(1 for card in deck
                              if card.card_id in definition['support'])

            # Core cards count more (2x weight)
            weighted_count = (core_count * 2) + support_count
            score = weighted_count / deck_size
            scores[archetype] = score

        return scores

    def suggest_archetype_pivot(self, context: DecisionContext) -> Optional[str]:
        """
        Suggest archetype pivot if current strategy isn't working.

        Returns:
            New archetype to target, or None if current is fine
        """
        archetype_scores = self.get_archetype_scores(context.game.deck)
        current_archetype = self.detect_archetype(context)

        # If already flexible, suggest most promising archetype
        if current_archetype == 'flexible':
            max_archetype = max(archetype_scores.keys(),
                              key=lambda k: archetype_scores[k])
            if archetype_scores[max_archetype] >= 0.25:
                return max_archetype
            return None

        # Check if current archetype is weak
        if current_archetype != 'unknown':
            current_score = archetype_scores.get(current_archetype, 0)

            # Also check if another archetype is significantly stronger
            for other_archetype, other_score in archetype_scores.items():
                if other_archetype != current_archetype:
                    if other_score > current_score + 0.15:
                        # Significant advantage to pivot
                        return other_archetype

        return None

    def get_recommended_cards(self, archetype: str, context: DecisionContext) -> List[str]:
        """
        Get recommended cards for given archetype.

        Returns list of card IDs that would strengthen this archetype.
        """
        if archetype not in self.ARCHETYPES:
            return []

        # Check what we already have
        deck = context.game.deck if hasattr(context.game, 'deck') else []
        existing_cards = set(card.card_id for card in deck)

        recommended = []

        # Add core cards we don't have yet
        for core_card in self.ARCHETYPES[archetype]['core']:
            if core_card not in existing_cards:
                recommended.append(core_card)

        # Add support cards (up to certain limits)
        support_limits = {
            'strength': 8,
            'exhaust': 6,
            'body_slam': 6,
        }

        support_count = sum(1 for card in deck
                          if card.card_id in self.ARCHETYPES[archetype]['support'])

        for support_card in self.ARCHETYPES[archetype]['support']:
            if support_card not in existing_cards:
                if support_count < support_limits.get(archetype, 5):
                    recommended.append(support_card)

        return recommended

    def should_accept_card(self, card: Card, context: DecisionContext) -> Tuple[bool, str]:
        """
        Decide if a card fits the current deck strategy.

        Returns:
            (should_accept, reason)
        """
        archetype = self.detect_archetype(context)

        # If flexible, most cards are okay
        if archetype == 'flexible' or archetype == 'unknown':
            return (True, "Deck is flexible, exploring options")

        # Check if card fits archetype
        if archetype in self.ARCHETYPES:
            definition = self.ARCHETYPES[archetype]

            # Core card - always accept
            if card.card_id in definition['core']:
                return (True, f"Core {archetype} card")

            # Support card - accept if not too many
            if card.card_id in definition['support']:
                deck = context.game.deck
                support_count = sum(1 for c in deck
                                  if c.card_id in definition['support'])
                if support_count < 6:
                    return (True, f"Support {archetype} card")
                else:
                    return (False, f"Too many {archetype} support cards")

            # Card doesn't fit archetype
            return (False, f"Doesn't fit {archetype} archetype")

        return (True, "Acceptable card")

    def get_archetype_info(self, context: DecisionContext) -> Dict:
        """
        Get comprehensive archetype information.

        Returns dict with:
        - archetype: current archetype
        - archetype_score: confidence (0.0 to 1.0)
        - recommended_cards: list of card IDs to look for
        - pivot_suggestion: new archetype or None
        """
        archetype = self.detect_archetype(context)

        if not hasattr(context.game, 'deck'):
            return {
                'archetype': 'unknown',
                'archetype_score': 0.0,
                'recommended_cards': [],
                'pivot_suggestion': None,
            }

        scores = self.get_archetype_scores(context.game.deck)
        score = scores.get(archetype, 0.0)

        recommended = []
        if archetype != 'unknown':
            recommended = self.get_recommended_cards(archetype, context)

        pivot = self.suggest_archetype_pivot(context)

        return {
            'archetype': archetype,
            'archetype_score': score,
            'all_scores': scores,
            'recommended_cards': recommended,
            'pivot_suggestion': pivot,
        }
