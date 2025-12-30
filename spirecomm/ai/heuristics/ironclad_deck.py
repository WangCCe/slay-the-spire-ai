"""
Ironclad deck building strategy based on expert player principles.

Key principles:
- Keep deck small (<20 cards, ideally 15-17)
- Remove Strikes first, then Defends
- Act 1: Focus on damage (take 2-3 elites)
- Don't take curses (except Necronomicurse)
- Upgrade priority: Whirlwind > Powers > Utility > Attacks
- Stick to archetype once established
"""

from typing import List, Tuple
from ..decision.base import DecisionContext
from .ironclad_archetype import IroncladArchetypeManager
from spirecomm.spire.card import Card

# For Python 3.8 compatibility
if tuple:  # Just to check type exists
    pass


class IroncladDeckStrategy:
    """
    Manages Ironclad deck building decisions.

    Implements expert strategies for:
    - Card acceptance/rejection
    - Deck size management
    - Upgrade priorities
    - Act-based strategy (Act 1 aggressive, Act 2+ conservative)
    """

    # Tier 0/1 cards (always acceptable)
    TIER_0_1_CARDS = {
        # Tier 0 (Game-winning)
        'Limit Break', 'Demon Form', 'Corruption', 'Barricade',

        # Tier 1 (Excellent)
        'Reaper', 'Shrug It Off', 'Feel No Pain', 'Spot Weakness',
        'Disarm', 'Headbutt', 'Uppercut', 'Pommel Strike',
        'Whirlwind', 'True Grit', 'Body Slam', 'Inflame',
    }

    # Act 1 damage priorities
    ACT_1_DAMAGE_PRIORITY = {
        'Whirlwind', 'Pommel Strike', 'Cleave', 'Fiend Fire',
        'Inflame', 'Body Slam', 'Rampage', 'Heavy Blade', 'Headbutt',
        'Uppercut', 'Spot Weakness', 'Twin Strike', 'Reaper',
    }

    # HP-cost cards (spend HP to play, avoid at low HP)
    HP_COST_CARDS = {
        'Offering', 'Bloodletting', 'Hemokinesis',
    }

    # Cards to avoid (bloat deck without enough payoff)
    AVOID_CARDS = {
        'Searing Blow',  # Needs too many upgrades
        'Wild Strike',   # Adds random cards
    }

    # Upgrade priorities based on expert input
    UPGRADE_PRIORITIES = {
        # Tier 0: Highest (game-changing when upgraded)
        'Whirlwind': 10,
        'Demon Form': 10,
        'Limit Break': 10,
        'Corruption': 10,
        'Barricade': 10,

        # Tier 1: High priority
        'Reaper': 9,
        'True Grit': 9,
        'Body Slam': 9,
        'Feel No Pain': 9,
        'Shrug It Off': 8,
        'Spot Weakness': 8,
        'Disarm': 8,
        'Inflame': 8,

        # Tier 2: Medium priority
        'Pommel Strike': 7,
        'Uppercut': 7,
        'Iron Wave': 6,
        'Cleave': 6,
        'Flame Barrier': 6,
        'Heavy Blade': 6,

        # Tier 3: Low priority
        'Bash': 5,
        'Strike_R': 3,
        'Defend_R': 2,
        'Clash': 2,
    }

    def __init__(self):
        """Initialize deck strategy manager."""
        self.archetype_manager = IroncladArchetypeManager()

    def should_pick_card(self, card: Card, context: DecisionContext) -> Tuple[bool, str]:
        """
        Decide if we should pick a card.

        Returns:
            (should_pick, reason)
        """
        # Get deck info
        deck_size = len(context.game.deck) if hasattr(context.game, 'deck') else 10
        archetype = self.archetype_manager.detect_archetype(context)

        # Rule 1: Deck size limit
        if deck_size >= 20:
            # Only accept tier 0/1 cards
            if card.card_id not in self.TIER_0_1_CARDS:
                return (False, f"Deck too large ({deck_size} cards), only taking top-tier cards")

        # Rule 2: Avoid clearly bad cards
        if card.card_id in self.AVOID_CARDS:
            return (False, f"Card '{card.card_id}' is suboptimal")

        # Rule 3: HP risk assessment
        if context.player_hp_pct < 0.4:
            if card.card_id in self.HP_COST_CARDS:
                return (False, f"Too risky at {context.player_hp_pct*100:.0f}% HP")

        # Rule 4: Archetype consistency
        if archetype not in ['unknown', 'flexible']:
            archetype_ok, reason = self.archetype_manager.should_accept_card(card, context)
            if not archetype_ok:
                return (False, reason)

        # Rule 5: Act 1 aggression
        if context.act == 1 and deck_size <= 12:
            # Prioritize damage in Act 1
            if card.card_id in self.ACT_1_DAMAGE_PRIORITY:
                return (True, f"Act 1 damage priority (deck size: {deck_size})")

        # Rule 6: Win condition cards always good
        if card.card_id in ['Demon Form', 'Limit Break', 'Corruption', 'Barricade']:
            # But limit to 1 copy except特殊情况
            if deck_size > 0:
                current_count = sum(1 for c in context.game.deck if c.card_id == card.card_id)
                if card.card_id == 'Limit Break' and current_count >= 1:
                    return (False, "Already have Limit Break (doesn't exhaust when upgraded)")
                if card.card_id == 'Demon Form' and current_count >= 1:
                    # Second Demon Form is okay but low priority
                    return (True, "Second Demon Form (low priority)")
            return (True, f"Win condition card: {card.card_id}")

        # Rule 7: Defend/Strike removal consideration
        if deck_size >= 15:
            # In late Act 1/Act 2, be very selective
            if card.card_id in ['Strike_R', 'Defend_R']:
                return (False, "Need card removal, not basics")

        # Default: accept good cards
        baseline_score = self._get_card_baseline_score(card.card_id)
        if baseline_score >= 60:
            return (True, f"Good card (score: {baseline_score})")
        elif baseline_score >= 40:
            return (True, f"Acceptable card (score: {baseline_score})")
        else:
            return (False, f"Weak card (score: {baseline_score})")

    def get_upgrade_priority(self, card: Card, context: DecisionContext) -> int:
        """
        Get upgrade priority for a card (1-10).

        Higher is more important to upgrade.
        """
        base_priority = self.UPGRADE_PRIORITIES.get(card.card_id, 5)

        # Adjust based on archetype
        archetype = self.archetype_manager.detect_archetype(context)

        if archetype == 'strength':
            # Prioritize strength cards
            if card.card_id in ['Demon Form', 'Limit Break', 'Spot Weakness', 'Inflame']:
                base_priority = min(10, base_priority + 2)
            elif card.card_id in ['Reaper', 'Disarm']:
                base_priority = min(10, base_priority + 1)

        elif archetype == 'exhaust':
            # Prioritize exhaust cards
            if card.card_id in ['Corruption', 'Feel No Pain', 'Dark Embrace']:
                base_priority = min(10, base_priority + 2)

        elif archetype == 'body_slam':
            # Prioritize block/body slam cards
            if card.card_id in ['Barricade', 'Body Slam', 'Entrench']:
                base_priority = min(10, base_priority + 2)
            elif card.card_id in ['Iron Wave', 'Impervious', 'Flame Barrier']:
                base_priority = min(10, base_priority + 1)

        # Adjust based on game act
        if context.act == 1:
            # Prioritize consistency in Act 1
            if card.card_id in ['Bash', 'Iron Wave', 'Pommel Strike']:
                base_priority = min(10, base_priority + 1)

        return base_priority

    def should_remove_card(self, card: Card, context: DecisionContext) -> Tuple[bool, str]:
        """
        Decide if a card should be removed (at shop/event).

        Returns:
            (should_remove, reason)
        """
        card_id = card.card_id

        # Priority 1: Strikes (always remove first)
        if card_id == 'Strike_R':
            return (True, "Strike removal is highest priority")

        # Priority 2: Basic defends (after strikes)
        if card_id == 'Defend_R':
            # Check if we have enough strike removals
            strike_count = sum(1 for c in context.game.deck if c.card_id == 'Strike_R')
            if strike_count <= 2:
                return (False, "Remove Strikes first")
            return (True, "Defend removal (after Strikes)")

        # Priority 3: Bad cards
        if card_id in self.AVOID_CARDS:
            return (True, f"Remove suboptimal card: {card_id}")

        # Priority 4: Cards that don't fit archetype
        archetype = self.archetype_manager.detect_archetype(context)
        if archetype not in ['unknown', 'flexible']:
            fits, _ = self.archetype_manager.should_accept_card(card, context)
            if not fits:
                return (True, f"Doesn't fit {archetype} archetype")

        # Priority 5: Duplicate core cards (case by case)
        if card_id in ['Demon Form', 'Barricade', 'Corruption']:
            count = sum(1 for c in context.game.deck if c.card_id == card_id)
            if count >= 2:
                return (True, f"Duplicate power card: {card_id}")

        # Don't remove good cards
        if card_id in self.TIER_0_1_CARDS:
            return (False, f"Keep top-tier card: {card_id}")

        return (False, "Keep this card")

    def get_deck_health_score(self, context: DecisionContext) -> float:
        """
        Evaluate overall deck health (0.0 to 1.0).

        Considers:
        - Deck size (smaller is better)
        - Strike/Defend count (fewer is better)
        - Archetype clarity
        - Upgrade count
        """
        if not hasattr(context.game, 'deck'):
            return 0.5

        deck = context.game.deck
        deck_size = len(deck)

        score = 0.5

        # 1. Deck size (optimal: 15-17)
        if deck_size <= 12:
            score += 0.15
        elif deck_size <= 17:
            score += 0.10
        elif deck_size <= 20:
            score += 0.05
        elif deck_size >= 25:
            score -= 0.15

        # 2. Strike/Defend count (fewer is better)
        strike_count = sum(1 for c in deck if c.card_id == 'Strike_R')
        defend_count = sum(1 for c in deck if c.card_id == 'Defend_R')
        basic_count = strike_count + defend_count

        if basic_count <= 2:
            score += 0.15
        elif basic_count <= 4:
            score += 0.10
        elif basic_count >= 6:
            score -= 0.10

        # 3. Archetype clarity
        archetype = self.archetype_manager.detect_archetype(context)
        if archetype in ['strength', 'exhaust', 'body_slam']:
            score += 0.10
        elif archetype == 'flexible':
            score += 0.05

        # 4. Upgrade count
        upgrade_count = sum(1 for c in deck if hasattr(c, 'upgrades') and c.upgrades > 0)
        upgrade_rate = upgrade_count / deck_size if deck_size > 0 else 0

        if upgrade_rate >= 0.4:
            score += 0.10
        elif upgrade_rate >= 0.3:
            score += 0.05

        return max(0.0, min(1.0, score))

    def _get_card_baseline_score(self, card_id: str) -> int:
        """Get baseline score for card from expert priorities."""
        # Import from evaluator to avoid duplication
        from .ironclad_evaluator import IroncladCardEvaluator

        evaluator = IroncladCardEvaluator()
        return evaluator.baseline_scores.get(card_id, 50)
