"""
Ironclad-specific card evaluator with expert strategy integration.

Based on A20 high-level player research and current meta strategies (2023-2025).
Key improvements over generic SynergyCardEvaluator:
- Expert-based card priority tiers
- Archetype-aware evaluation (strength, exhaust, body_slam)
- HP-aware risk assessment
- Energy curve management
- Act 1 aggressive strategy support
"""

from .card import SynergyCardEvaluator
from ..decision.base import DecisionContext
from spirecomm.spire.card import Card


class IroncladCardEvaluator(SynergyCardEvaluator):
    """
    Ironclad-specific card evaluator based on expert strategies.

    Key insights from high-level play:
    - Reaper is core card (not tier 4) - critical for strength decks
    - Shrug It Off is tier 0 (0 cost 8 block + draw)
    - Demon Form should be played by turn 2-3
    - Limit Break when Strength >= 5
    - Act 1: Take 2-3 elites (Ironclad is strongest early)
    - Keep deck small (<20 cards)
    """

    # Expert-based card priority adjustments
    PROMOTED_CARDS = {
        'Reaper': 95,        # From tier 4 → tier 1 (critical sustain)
        'Shrug It Off': 98,  # From tier 2 → tier 0 (best block card)
        'Feel No Pain': 90,  # Core exhaust synergy
        'Spot Weakness': 85, # Consistent strength gain
        'Disarm': 82,        # Powerful single-target defense
        'Headbutt': 88,      # Retrieval + damage + synergy
        'Perfected Strike': 85,  # Core attack card, excellent scaling
        'Iron Wave': 75,     # From default → tier 2 (excellent block+damage hybrid)
        'Flame Barrier': 70, # Good block+damage hybrid, synergizes with Body Slam
        'Impervious': 72,    # High block + draw, excellent for block decks
        'Barricade': 80,     # Core for Body Slam decks, enables infinite block
        'Entrench': 70,      # Synergizes with Barricade, excellent for Body Slam decks
        'Rage': 75,          # Excellent damage boost, especially with Strength
        'Whirlwind': 78,     # AOE damage, synergizes with Strength
        'Battle Trance': 80,  # Key card draw, essential for consistency
        'Double Tap': 72,    # Enables powerful combos, especially with heavy hitters
        'Immolate': 73,      # Excellent AOE damage + card draw, despite self-damage
        'Metallicize': 70,   # Good persistent block, great for early game
        'Feed': 72,          # Damage + max HP gain, excellent sustain
        'Heavy Blade': 75,   # Scales well with Strength, efficient damage
        'Fiend Fire': 70,     # Powerful AOE damage, synergizes with exhaust
    }

    DEMOTED_CARDS = {
        'Searing Blow': 20,  # Requires heavy upgrade investment
        'Wild Strike': 25,   # Adds random card, bloats deck
        'Flex': 65,          # Improved priority - good for strength decks and immediate use
        'Clash': 40,         # Still worse than other attacks
    }

    # Archetype-specific bonuses
    ARCHETYPE_BONUS_CARDS = {
        'strength': {
            'Demon Form': 35,
            'Limit Break': 35,
            'Inflame': 25,
            'Spot Weakness': 20,
            'Reaper': 30,
            'Disarm': 15,
            'Body Slam': 25,
            'Heavy Blade': 20,
        },
        'exhaust': {
            'Corruption': 35,
            'Feel No Pain': 30,
            'Dark Embrace': 25,
            'Offering': 20,
            'Second Wind': 15,
        },
        'body_slam': {
            'Barricade': 40,
            'Body Slam': 35,
            'Entrench': 30,
            'Iron Wave': 25,
            'Impervious': 20,
            'Flame Barrier': 20,
        },
    }

    # Act 1 damage priorities (early game aggression)
    ACT_1_DAMAGE_PRIORITY = {
        'Whirlwind', 'Pommel Strike', 'Cleave', 'Fiend Fire',
        'Inflame', 'Body Slam', 'Rampage', 'Heavy Blade', 'Headbutt',
        'Uppercut', 'Spot Weakness', 'Twin Strike', 'Reaper',
    }

    # HP-cost cards (spend HP to play)
    HP_COST_CARDS = {
        'Offering', 'Bloodletting', 'Hemokinesis',
    }

    # Self-damage cards (deal HP loss as a side effect)
    SELF_DAMAGE_CARDS = {
        'Immolate', 'Combust', 'Brutality',
    }

    def __init__(self, player_class='IRONCLAD'):
        """Initialize Ironclad evaluator with expert priorities."""
        super().__init__(player_class)

        # Override baseline scores with expert priorities
        for card_id, score in self.PROMOTED_CARDS.items():
            self.baseline_scores[card_id] = score

        for card_id, score in self.DEMOTED_CARDS.items():
            self.baseline_scores[card_id] = score

    def evaluate_card(self, card: Card, context: DecisionContext) -> float:
        """
        Evaluate card for Ironclad with expert strategy integration.

        Evaluation flow:
        1. Get baseline from expert priorities
        2. Apply HP-aware modifier (penalize risky cards at low HP)
        3. Apply archetype-specific bonus
        4. Consider energy curve
        5. Act 1 special handling (aggressive damage)
        """
        # 1. Baseline from expert priorities
        baseline = self.baseline_scores.get(card.card_id, 50)

        # 2. HP-aware modifier
        hp_modifier = self._calculate_hp_aware_modifier(card, context)

        # 3. Archetype bonus
        archetype_bonus = self._calculate_archetype_bonus(card, context)

        # 4. Energy curve consideration
        energy_modifier = self._evaluate_energy_curve(card, context)

        # 5. Act 1 aggression bonus
        act_bonus = self._calculate_act_1_bonus(card, context)

        # Final score
        final_score = (baseline * hp_modifier) + archetype_bonus + act_bonus

        # Apply energy curve modifier as multiplier
        final_score *= energy_modifier

        return max(0, min(100, final_score))

    def _calculate_hp_aware_modifier(self, card: Card, context: DecisionContext) -> float:
        """
        Adjust card value based on current HP situation.

        Rules:
        - HP < 30%: Heavy penalty for HP-cost/self-damage cards
        - HP < 50%: Moderate penalty for risky cards
        - HP > 80%: Can afford high-risk cards
        - HP < 40%: Bonus for defensive cards
        """
        modifier = 1.0
        hp_pct = context.player_hp_pct

        if hp_pct < 0.3:
            # Critical HP - avoid all HP costs
            if card.card_id in self.HP_COST_CARDS:
                return 0.1  # Almost never pick
            if card.card_id in self.SELF_DAMAGE_CARDS:
                modifier *= 0.3
            # Prioritize defense heavily
            if self._is_defensive_card(card):
                modifier *= 2.5

        elif hp_pct < 0.5:
            # Low HP - moderate caution
            if card.card_id in self.HP_COST_CARDS:
                modifier *= 0.4
            if card.card_id in self.SELF_DAMAGE_CARDS:
                modifier *= 0.7
            if self._is_defensive_card(card):
                modifier *= 1.5

        elif hp_pct > 0.8:
            # High HP - can take risks
            if card.card_id in ['Offering', 'Bloodletting', 'Hemokinesis']:
                modifier *= 1.3  # These are powerful when safe

        return modifier

    def _calculate_archetype_bonus(self, card: Card, context: DecisionContext) -> float:
        """
        Calculate archetype-specific bonus.

        If deck has clear archetype, bonus cards that fit it
        and penalize cards that don't.
        """
        archetype = context.deck_archetype

        # If no clear archetype or flexible, no bonus/penalty
        if archetype == 'unknown' or archetype == 'balanced' or archetype == 'flexible':
            return 0.0

        # Get archetype-specific bonuses
        archetype_cards = self.ARCHETYPE_BONUS_CARDS.get(archetype, {})

        # Check if card fits archetype
        if card.card_id in archetype_cards:
            return archetype_cards[card.card_id]

        # Small penalty for cards that don't fit archetype
        # (only if archetype is well-established)
        if context.archetype_score > 0.5:
            return -10

        return 0.0

    def _evaluate_energy_curve(self, card: Card, context: DecisionContext) -> float:
        """
        Evaluate if card fits deck's energy curve.

        Target distribution (for 15-card deck):
        - 0-cost: 2-3 cards (15-20%)
        - 1-cost: 3-4 cards (20-25%)
        - 2-cost: 5-6 cards (33-40%)
        - 3-cost: 2-3 cards (15-20%)
        - 4+ cost: 0-1 cards (0-10%)
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return 1.0

        deck = context.game.deck
        deck_size = len(deck)

        # Count cards by cost
        cost_counts = {}
        for c in deck:
            cost = c.cost if hasattr(c, 'cost') else 1
            cost_counts[cost] = cost_counts.get(cost, 0) + 1

        card_cost = card.cost if hasattr(card, 'cost') else 1

        # Ideal percentages
        ideal_percentages = {
            0: 0.18,   # 0-cost: ~15-20%
            1: 0.23,   # 1-cost: ~20-25%
            2: 0.37,   # 2-cost: ~33-40%
            3: 0.17,   # 3-cost: ~15-20%
        }

        current_pct = cost_counts.get(card_cost, 0) / deck_size
        ideal_pct = ideal_percentages.get(card_cost, 0.05)

        # Adjust modifier
        if current_pct > ideal_pct * 1.8:
            return 0.6  # Too many of this cost
        elif current_pct > ideal_pct * 1.4:
            return 0.8  # Slightly too many
        elif current_pct < ideal_pct * 0.4:
            return 1.3  # Need more of this cost
        else:
            return 1.0  # Good balance

    def _calculate_act_1_bonus(self, card: Card, context: DecisionContext) -> float:
        """
        Act 1 specific bonuses for early game aggression.

        Ironclad is strongest in Act 1. Prioritize:
        - Damage cards (to kill elites)
        - Win condition cards (Demon Form, Limit Break, Barricade)
        """
        if context.act != 1:
            return 0.0

        # Act 1 damage priority
        if card.card_id in self.ACT_1_DAMAGE_PRIORITY:
            deck_size = len(context.game.deck) if hasattr(context.game, 'deck') else 10
            if deck_size <= 12:
                return 15  # Early Act 1, prioritize damage

        # Win condition cards always good in Act 1
        if card.card_id in ['Demon Form', 'Limit Break', 'Corruption', 'Barricade']:
            return 20

        return 0.0

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is primarily defensive."""
        defensive_keywords = [
            'defend', 'block', 'iron wave', 'flame barrier', 'impervious',
            'entrench', 'shrug it off', 'sentinel', 'ghostly armor',
        ]

        card_id_lower = card.card_id.lower()

        for keyword in defensive_keywords:
            if keyword in card_id_lower:
                return True

        return False
