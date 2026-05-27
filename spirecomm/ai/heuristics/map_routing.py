"""
Adaptive map router with HP-aware decision making.

Implements expert strategies for map navigation:
- Act 1: Aggressive (take 2-3 elites, Ironclad is strongest early)
- Act 2+: Conservative (avoid elites unless high HP)
- Dynamic rest site priority based on HP
- Smart campfire choices
"""

import sys
import logging
from typing import List, Dict
from ..decision.base import DecisionContext
from spirecomm.ai.heuristics.card_names import canonical_card_name
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

    def __init__(self, player_class='IRONCLAD', elite_mode: str = None):
        """Initialize map router.

        Args:
            player_class: Character class (IRONCLAD, THE_SILENT, THE_DEFECT)
            elite_mode: Elite routing strategy ("conservative" or "aggressive", default: "aggressive")
        """
        self.player_class = player_class
        self.elite_mode = (elite_mode or "aggressive").lower()
        logging.getLogger(__name__).info(
            "[MAP_ROUTING] elite_mode=%s (player_class=%s)",
            self.elite_mode,
            self.player_class,
        )

    @staticmethod
    def _card_name(card) -> str:
        return canonical_card_name(card)

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
        floor = getattr(context, 'floor', 0) or 0

        # Act 1: Character-specific strategies
        if act == 1:
            base_priority = self._adjust_act_1_priority(symbol, base_priority, hp_pct, floor, context)

        # Act 2+: More conservative
        elif act >= 2:
            base_priority = self._adjust_act_2_plus_priority(symbol, base_priority, hp_pct)

        # Generic HP-based adjustments for all acts
        base_priority = self._adjust_for_hp(symbol, base_priority, hp_pct, act=act, floor=floor)

        return base_priority

    def _adjust_act_1_priority(self, symbol: str, base: int, hp_pct: float, floor: int, context: DecisionContext) -> int:
        """Act 1 priorities - Ironclad takes elites only after readiness checks."""
        # Ironclad prioritizes rest sites for card upgrades, avoids elites consistently
        if self.player_class == 'IRONCLAD':
            if symbol == 'E':  # Elite
                # Optional elite routing mode for experimentation.
                if self.elite_mode == "aggressive":
                    readiness = self._act_1_elite_readiness_score(context)
                    if readiness >= 5:
                        return base + 450 + readiness * 30
                    if readiness >= 3 and floor >= 8 and hp_pct >= 0.7:
                        return base + 80
                    logging.getLogger(__name__).info(
                        "[MAP_ROUTING] Act1 elite gated: floor=%s hp=%.1f%% readiness=%s",
                        floor,
                        hp_pct * 100,
                        readiness,
                    )
                    return base - 260
                # Conservative mode is for first-win validation: make elites a
                # route-blocking penalty unless every reachable path is forced.
                return base - 5000

            elif symbol == 'R':  # Rest
                # Prioritize rest sites for card upgrades even when healthy
                if hp_pct > 0.75:
                    return base + 50  # Worth it for upgrades (was -50)
                elif hp_pct < 0.4:
                    return base + 300  # Urgent healing
                else:
                    return base + 100  # Generally good for upgrades

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

    def _act_1_elite_readiness_score(self, context: DecisionContext) -> int:
        """Estimate if the deck is ready for Nob/Lagavulin/Sentries."""
        game = getattr(context, "game", None)
        deck = list(getattr(game, "deck", []) or [])
        potions = list(getattr(game, "potions", []) or [])
        relics = list(getattr(game, "relics", []) or [])

        card_names = [self._card_name(card) for card in deck]
        upgraded_ids = {
            self._card_name(card)
            for card in deck
            if int(getattr(card, "upgrades", 0) or 0) > 0
        }

        premium_attacks = {
            "Pommel Strike", "Anger", "Clothesline", "Uppercut",
            "Hemokinesis", "Carnage", "Cleave", "Headbutt",
            "Twin Strike", "Whirlwind", "Iron Wave", "Perfected Strike",
        }
        strong_blocks = {
            "Shrug It Off", "Flame Barrier", "Power Through",
            "Ghostly Armor", "Metallicize", "Impervious", "Disarm",
        }
        fight_potions = {
            "Fire Potion", "Attack Potion", "Strength Potion", "Flex Potion",
            "Dexterity Potion", "Skill Potion", "Power Potion", "Fear Potion",
            "Duplication Potion", "Distilled Chaos", "Explosive Potion",
            "Swift Potion", "Energy Potion", "Entropic Brew",
        }

        score = 0
        score += min(4, sum(1 for card_name in card_names if card_name in premium_attacks))
        score += min(2, sum(1 for card_name in card_names if card_name in strong_blocks))
        if "Bash" in upgraded_ids:
            score += 1
        score += min(
            2,
            sum(
                1
                for potion in potions
                if getattr(potion, "potion_id", "") in fight_potions
                and getattr(potion, "can_use", True)
            ),
        )
        score += min(2, max(0, len(relics) - 1))
        if context.player_hp_pct >= 0.85:
            score += 1
        elif context.player_hp_pct < 0.65:
            score -= 2

        floor = getattr(context, "floor", 0) or 0
        if floor <= 6:
            score -= 2
        elif floor >= 10:
            score += 1

        return score

    def _adjust_act_2_plus_priority(self, symbol: str, base: int, hp_pct: float) -> int:
        """Act 2+ priorities - first-win conservative mode avoids optional elites."""
        if symbol == 'E':  # Elite
            if self.elite_mode == "conservative":
                return base - 5000

            # Aggressive elite routing in Act 2
            if hp_pct < 0.2:
                return base - 100  # Avoid elites when very low HP
            elif hp_pct < 0.65:
                return base + 50   # Cautious but willing
            else:
                return base + 200  # Strongly prefer elites when healthy

        elif symbol == 'M':  # Monster
            # Avoid normal monsters in Act 2
            return base - 100

        elif symbol == 'R':  # Rest
            if hp_pct < 0.5:
                return base + 400  # Critical need
            elif hp_pct < 0.7:
                return base + 150  # Good to have
            else:
                return base - 50   # Can skip

        elif symbol == '?':  # Unknown
            # Favor events in Act 2
            if hp_pct < 0.2:
                return base - 50   # Risky events when low HP
            else:
                return base + 100  # Strongly prefer events

        return base

    def _adjust_for_hp(self, symbol: str, base: int, hp_pct: float, act: int = None, floor: int = None) -> int:
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
            if symbol == 'E' and not (act == 1 and floor is not None and floor <= 7):
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

        if RestOption.REST in options:
            force_rest, reason = self._should_force_rest(context)
            if force_rest:
                logging.getLogger(__name__).info(
                    "[REST_GUARD] Map router forcing REST reason=%s hp_pct=%.1f%% floor=%s",
                    reason,
                    context.player_hp_pct * 100,
                    getattr(context, "floor", 0),
                )
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
        if is_pre_boss and hp_pct < 0.6:
            score += 150  # Definitely rest before boss
        elif is_pre_boss and hp_pct < 0.8:
            score += 100  # Rest before boss

        return score

    def _should_force_rest(self, context: DecisionContext) -> tuple[bool, str]:
        hp_pct = context.player_hp_pct
        floor = getattr(context, 'floor', 0) or 0
        is_pre_boss = (floor % 17) in (15, 16)

        if hp_pct < 0.5:
            return True, "low_hp"
        if is_pre_boss and hp_pct < 0.8:
            return True, "pre_boss"
        return False, ""

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
        strike_count = sum(1 for c in context.game.deck if self._card_name(c) == 'Strike')
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
                if self._card_name(card) not in ['Strike', 'Defend']:
                    count += 1

        return count
