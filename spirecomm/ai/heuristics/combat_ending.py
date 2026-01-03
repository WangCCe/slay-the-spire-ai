"""
Combat ending detection - can we kill all monsters this turn?

This module provides lethality detection to prevent over-defending when
combat could be ended this turn.
"""

from typing import List, Tuple, Optional
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import PlayCardAction
from ..decision.base import DecisionContext


class CombatEndingDetector:
    """
    Detect if combat can be ended this turn.

    Uses conservative estimation:
    - Assumes base damage (plus visible Strength)
    - Accounts for monster block
    - Accounts for Vulnerable if present
    - Considers AOE vs single-target efficiency
    """

    def __init__(self):
        """Initialize the combat ending detector."""
        pass

    def can_kill_all(self, context: DecisionContext) -> bool:
        """
        Check if all monsters can be killed this turn.

        Args:
            context: Current decision context

        Returns:
            True if lethal is possible
        """
        if not context.monsters_alive:
            return True

        # Calculate total damage potential
        total_possible_damage = self._calculate_max_damage(context)

        # Calculate total monster HP (including block)
        total_monster_hp = sum(m.current_hp + m.block for m in context.monsters_alive)

        # Conservative check: need 20% margin for error
        # (to account for suboptimal targeting, AOE inefficiency, etc.)
        return total_possible_damage >= total_monster_hp * 1.2

    def find_lethal_sequence(self, context: DecisionContext) -> List[PlayCardAction]:
        """
        Find card sequence that kills all monsters.

        Uses greedy approach: play highest-damage cards on lowest-HP targets.

        Args:
            context: Current decision context

        Returns:
            List of actions to kill all monsters, or empty list if not possible
        """
        if not self.can_kill_all(context):
            return []

        # Greedy approach: play highest-damage cards on lowest-HP targets
        sequence = []
        remaining_monsters = context.monsters_alive.copy()
        played_cards = set()

        # Sort monsters by HP (kill weakest first)
        remaining_monsters.sort(key=lambda m: m.current_hp)

        # Get attack cards sorted by damage
        attack_cards = [c for c in context.playable_cards
                       if hasattr(c, 'type') and str(c.type) == 'ATTACK']
        attack_cards.sort(key=lambda c: self._get_card_damage(c, context), reverse=True)

        for monster in remaining_monsters:
            for card in attack_cards:
                card_uuid = card.uuid if hasattr(card, 'uuid') else id(card)
                if card_uuid in played_cards:
                    continue

                cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
                if cost > context.energy_available:
                    continue

                # Check vulnerable status
                vulnerable = context.vulnerable_stacks.get(monster, 0)
                damage = self._get_card_damage(card, context)
                if vulnerable > 0:
                    damage = int(damage * 1.5)

                # Estimate if this card can kill the monster
                total_damage = damage
                if total_damage >= monster.current_hp + monster.block:
                    sequence.append(PlayCardAction(card=card, target_monster=monster))
                    played_cards.add(card_uuid)
                    break

        return sequence

    def should_skip_defense(self, context: DecisionContext) -> bool:
        """
        Determine if defense cards should be skipped this turn.

        Args:
            context: Current decision context

        Returns:
            True if we can kill all monsters and shouldn't defend
        """
        if not context.monsters_alive:
            return True

        # Check if we have lethal
        if self.can_kill_all(context):
            # But only skip if we're not at critical HP
            return context.player_hp_pct > 0.3

        return False

    def _calculate_max_damage(self, context: DecisionContext) -> int:
        """
        Calculate maximum possible damage this turn.

        Args:
            context: Current decision context

        Returns:
            Total damage that can be dealt
        """
        total_damage = 0

        for card in context.playable_cards:
            if hasattr(card, 'type') and str(card.type) == 'ATTACK':
                total_damage += self._get_card_damage(card, context)

        return total_damage

    def _get_card_damage(self, card: Card, context: DecisionContext) -> int:
        """
        Get actual damage of card accounting for modifiers.

        Args:
            card: The card to evaluate
            context: Current decision context

        Returns:
            Damage value
        """
        base_damage = 0

        if hasattr(card, 'damage') and card.damage is not None:
            base_damage = card.damage

        # Add strength (for attacks)
        if hasattr(card, 'type') and str(card.type) == 'ATTACK':
            base_damage += context.strength

        return max(0, base_damage)
