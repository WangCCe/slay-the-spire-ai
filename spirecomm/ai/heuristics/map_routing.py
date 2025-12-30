"""
Adaptive map router with HP-aware decision making.

Implements expert strategies for map navigation:
- Act 1: Aggressive (take 2-3 elites, Ironclad is strongest early)
- Act 2+: Conservative (avoid elites unless high HP)
- Dynamic rest site priority based on HP
- Smart campfire choices
"""

import sys
from typing import List, Dict
from ..decision.base import DecisionContext
from spirecomm.spire.map import Node
from spirecomm.spire.screen import RestOption


class AdaptiveMapRouter:
    """
    HP-aware map routing for all character classes.

    Key principles:
    - Act 1: Take elites when HP is good (character-specific advantages)
    - Act 2+: Be more conservative with elites
    - Rest sites are critical when HP < 50%
    - Avoid ? events that might be risky when low HP
    """

    # Base node priorities (from SimpleAgent)
    BASE_NODE_PRIORITIES = {
        'M': 50,      # Monster
        'E': -10,     # Elite (risky by default)
        '$': 100,     # Shop
        '?': 75,      # Unknown
        'T': 75,      # Treasure
        'R': 25,      # Rest
    }

    def __init__(self, player_class='IRONCLAD'):
        """Initialize map router."""
        self.player_class = player_class

    def calculate_node_priority(self, node: Node, context: DecisionContext) -> int:
        """
        Calculate dynamic priority for a map node.

        Adjusts base priorities based on:
        - Current act number
        - HP percentage
        - Player class (Ironclad can be more aggressive in Act 1)
        """
        symbol = node.symbol
        base_priority = self.BASE_NODE_PRIORITIES.get(symbol, 0)
        hp_pct = context.player_hp_pct
        act = context.act

        # Act 1: Character-specific strategies
        if act == 1:
            floor = getattr(context, 'floor', 0) or 0
            base_priority = self._adjust_act_1_priority(symbol, base_priority, hp_pct, floor)

        # Act 2+: More conservative
        elif act >= 2:
            base_priority = self._adjust_act_2_plus_priority(symbol, base_priority, hp_pct)

        # Generic HP-based adjustments for all acts
        base_priority = self._adjust_for_hp(symbol, base_priority, hp_pct)

        return base_priority

    def _adjust_act_1_priority(self, symbol: str, base: int, hp_pct: float, floor: int) -> int:
        """Act 1 priorities - adjusted for A20 difficulty, less aggressive early on."""
        # Ironclad is strongest in Act 1 (Burning Blood healing), but adjusted for A20
        if self.player_class == 'IRONCLAD':
            if symbol == 'E':  # Elite
                # More cautious in early Act 1 (floors 1-5)
                if floor <= 5:
                    # Avoid elites entirely in first 5 floors
                    return base - 200  # Too risky early
                elif floor <= 10:
                    # Moderate caution for mid Act 1
                    if hp_pct > 0.8:
                        return base + 100  # Only take if very healthy
                    elif hp_pct > 0.6:
                        return base + 50  # Cautious
                    else:
                        return base - 100  # Too risky
                else:
                    # Late Act 1, can be more aggressive
                    if hp_pct > 0.7:
                        return base + 150  # Aggressive when healthy
                    elif hp_pct > 0.5:
                        return base + 50  # Moderate
                    else:
                        return base - 50  # Too risky

            elif symbol == 'R':  # Rest
                if hp_pct > 0.75:
                    return base - 50  # Don't need rest (reduced from -100)
                elif hp_pct < 0.4:
                    return base + 300  # Urgent
                else:
                    return base  # Neutral

        # Silent can also be aggressive with poison, adjusted for A20
        elif self.player_class == 'THE_SILENT':
            if symbol == 'E':
                if floor <= 7:
                    return base - 150  # Avoid early elites
                elif hp_pct > 0.6:
                    return base + 100  # More cautious than before

        # Defect is weakest early, more conservative
        elif self.player_class == 'THE_DEFECT':
            if symbol == 'E':
                return base - 100  # More cautious for Defect in A20

        return base

    def _adjust_act_2_plus_priority(self, symbol: str, base: int, hp_pct: float) -> int:
        """Act 2+ priorities - more conservative."""
        if symbol == 'E':  # Elite
            # Much more cautious in Act 2+
            if hp_pct < 0.6:
                return base - 200  # Avoid elites
            elif hp_pct < 0.75:
                return base - 50   # Cautious
            else:
                return base + 50   # Can take risk if very healthy

        elif symbol == 'R':  # Rest
            if hp_pct < 0.5:
                return base + 400  # Critical need
            elif hp_pct < 0.7:
                return base + 150  # Good to have
            else:
                return base - 50   # Can skip

        elif symbol == '?':  # Unknown
            if hp_pct < 0.4:
                return base - 50   # Risky events when low HP
            else:
                return base + 20   # Generally good

        return base

    def _adjust_for_hp(self, symbol: str, base: int, hp_pct: float) -> int:
        """Generic HP-based adjustments."""
        # Critical HP: prioritize survival
        if hp_pct < 0.25:
            if symbol == 'R':
                return base + 300
            elif symbol == 'E':
                return base - 300
            elif symbol == 'M':
                return base - 100  # Even normal fights are risky

        # Very healthy: can afford risks
        elif hp_pct > 0.85:
            if symbol == 'E':
                return base + 50
            elif symbol == 'R':
                return base - 150

        return base

    def choose_campfire_option(self, options: List[RestOption], context: DecisionContext) -> RestOption:
        """
        Choose best campfire option based on game state.

        Priority logic based on expert strategies:
        - REST: When HP < 50% or before boss
        - SMITH: When HP > 60% and have good upgrade targets
        - LIFT: When deck is small and lean
        - DIG: When need gold/cards and HP is good
        """
        if not options:
            return RestOption.REST

        scores = {}

        # Calculate scores for each available option
        if RestOption.REST in options:
            scores[RestOption.REST] = self._score_rest_option(context)

        if RestOption.SMITH in options:
            scores[RestOption.SMITH] = self._score_smith_option(context)

        if RestOption.LIFT in options:
            scores[RestOption.LIFT] = self._score_lift_option(context)

        if RestOption.DIG in options:
            scores[RestOption.DIG] = self._score_dig_option(context)

        # Return highest priority option
        best_option = max(scores.keys(), key=lambda k: scores[k])
        return best_option

    def _score_rest_option(self, context: DecisionContext) -> int:
        """Score REST option."""
        score = 50
        hp_pct = context.player_hp_pct
        floor = context.floor if hasattr(context, 'floor') else 0

        # Is this pre-boss?
        is_pre_boss = (floor % 17) in [15, 16]

        # Critical need
        if hp_pct < 0.3:
            score += 150
        elif hp_pct < 0.5:
            score += 80
        elif is_pre_boss and hp_pct < 0.8:
            score += 100  # Rest before boss
        elif is_pre_boss and hp_pct < 0.6:
            score += 150  # Definitely rest before boss

        return score

    def _score_smith_option(self, context: DecisionContext) -> int:
        """Score SMITH option."""
        score = 40
        hp_pct = context.player_hp_pct

        # Need HP to afford not healing
        if hp_pct > 0.6:
            score += 70
        elif hp_pct > 0.4:
            score += 30  # Risky but might be worth it
        else:
            score -= 50  # Too risky

        # Check for upgrade targets
        upgradeable_count = self._count_upgradeable_cards(context)
        score += upgradeable_count * 15

        return score

    def _score_lift_option(self, context: DecisionContext) -> int:
        """Score LIFT option."""
        score = 30

        if not hasattr(context.game, 'deck'):
            return score

        deck_size = len(context.game.deck)

        # Small decks benefit most
        if deck_size <= 12:
            score += 60
        elif deck_size <= 15:
            score += 40
        elif deck_size <= 18:
            score += 20
        elif deck_size >= 25:
            score -= 50  # Don't add to bloated deck
        elif deck_size >= 20:
            score -= 20

        # Check for card removal needs
        strike_count = sum(1 for c in context.game.deck if c.card_id == 'Strike_R')
        if strike_count >= 3:
            score += 30  # Need to remove cards

        return score

    def _score_dig_option(self, context: DecisionContext) -> int:
        """Score DIG option."""
        score = 20
        hp_pct = context.player_hp_pct

        # Need to be healthy to risk it
        if hp_pct < 0.5:
            score -= 30

        # Need gold for card removal?
        if hasattr(context.game, 'gold'):
            if context.game.gold < 300:
                score += 40  # Need gold
            elif context.game.gold < 500:
                score += 20

        # Need cards? (only if deck is small)
        if hasattr(context.game, 'deck'):
            deck_size = len(context.game.deck)
            if deck_size <= 15 and hp_pct > 0.7:
                score += 30  # Can afford to add card
            elif deck_size >= 20:
                score -= 30  # Don't want more cards

        return score

    def _count_upgradeable_cards(self, context: DecisionContext) -> int:
        """Count cards that would benefit from upgrading."""
        if not hasattr(context.game, 'deck'):
            return 0

        count = 0
        for card in context.game.deck:
            # Unupgraded cards
            if hasattr(card, 'upgrades') and card.upgrades == 0:
                # Skip strikes/defends (low priority)
                if card.card_id not in ['Strike_R', 'Defend_R']:
                    count += 1

        return count
