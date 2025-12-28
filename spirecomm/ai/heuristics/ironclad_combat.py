"""
Ironclad-specific combat planner with expert strategy integration.

Optimizes combat decisions for Ironclad's unique mechanics:
- Demon Form timing (play by turn 2-3)
- Limit Break logic (Strength >= 5)
- Corruption mode (all skills become 0 cost)
- Vulnerable optimization (Bash before big attacks)
- Reaper healing logic
- Body Slam optimization
- HP conservation in easy fights
"""

import sys
from typing import List
from .simulation import CombatPlanner
from ..decision.base import DecisionContext
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action


class IroncladCombatPlanner(CombatPlanner):
    """
    Ironclad-specific combat planner based on expert strategies.

    Key combat optimizations:
    1. Powers first (Demon Form by turn 2-3)
    2. Corruption mode: All skills priority
    3. Vulnerable timing (Bash before big attacks)
    4. Reaper healing in multi-enemy fights
    5. Body Slam when block >= 20
    6. HP conservation when safe
    """

    def __init__(self, card_evaluator=None):
        """Initialize Ironclad combat planner."""
        self.card_evaluator = card_evaluator

    def plan_turn(self, context: DecisionContext, playable_cards: List[Card]) -> List[Action]:
        """
        Plan optimal turn for Ironclad.

        Returns ordered list of actions to execute.
        """
        if not playable_cards:
            return []

        # Score each card for current situation
        scored_cards = []
        for card in playable_cards:
            score = self._get_combat_priority(card, context)
            scored_cards.append((card, score))

        # Sort by score (highest first)
        scored_cards.sort(key=lambda x: x[1], reverse=True)

        # Build action sequence
        actions = []
        for card, score in scored_cards:
            if score > 0:  # Only play positive-score cards
                target = self._choose_target(card, context)
                # Create play card action
                # (This will be converted to actual action by coordinator)
                actions.append((card, target, score))

        return actions

    def _get_combat_priority(self, card: Card, context: DecisionContext) -> float:
        """
        Get combat priority score for a card.

        Priority hierarchy:
        1. Powers (Demon Form highest early, Limit Break at high strength)
        2. Corruption mode: All skills max priority
        3. Draw cards (to find combo pieces)
        4. Vulnerable application (Bash before big attacks)
        5. Defensive cards (only when needed)
        6. Offensive cards (Body Slam, Reaper, etc.)
        """
        # Check if card is power, skill, or attack
        card_type = str(card.type) if hasattr(card, 'type') else 'UNKNOWN'

        # 1. POWERS - Highest priority (need time to pay off)
        if card_type == 'POWER':
            return self._get_power_priority(card, context)

        # 2. Check for Corruption mode
        if self._is_corruption_active(context):
            if card_type == 'SKILL':
                # All skills are 0 cost with Corruption
                return 900 + self._get_skill_base_value(card, context)

        # 3. DRAW CARDS - High priority to find combo pieces
        if self._is_draw_card(card):
            return 800

        # 4. VULNERABLE APPLICATION - Before big attacks
        if card.card_id == 'Bash':
            if self._should_bash_now(context):
                return 850
            else:
                return 50  # Save Bash for better timing

        # 5. DEFENSIVE CARDS - Only when needed
        if self._is_defensive_card(card):
            if self._needs_block(context):
                return self._get_defensive_priority(card, context)
            else:
                return 50  # Skip if safe

        # 6. OFFENSIVE CARDS
        if card_type == 'ATTACK':
            return self._get_attack_priority(card, context)

        # 7. OTHER SKILLS
        if card_type == 'SKILL':
            return self._get_skill_priority(card, context)

        return 100  # Default low priority

    def _get_power_priority(self, card: Card, context: DecisionContext) -> float:
        """Get priority for power cards."""
        card_id = card.card_id

        # Demon Form - highest priority, must play early
        if card_id == 'Demon Form':
            turn = context.turn if hasattr(context, 'turn') else 1
            if turn <= 3:
                return 1000  # Must play immediately
            # Check if already have one
            demon_count = sum(1 for c in context.game.deck if c.card_id == 'Demon Form')
            if demon_count == 0:
                return 950
            return 200  # Second Demon Form is low priority

        # Limit Break - only when strength is high
        if card_id == 'Limit Break':
            strength = self._estimate_strength(context)
            if strength >= 7:  # Upgraded Limit Break threshold
                return 950
            elif strength >= 5:  # Normal Limit Break threshold
                return 800
            else:
                return 100  # Wait for more strength

        # Corruption - very high priority
        if card_id == 'Corruption':
            return 950

        # Spot Weakness - high if enemy intends to attack
        if card_id == 'Spot Weakness':
            if self._enemy_intends_to_attack(context):
                return 850
            return 200

        # Other powers - moderate priority
        return 600

    def _get_attack_priority(self, card: Card, context: DecisionContext) -> float:
        """Get priority for attack cards."""
        card_id = card.card_id

        # Reaper - amazing in multi-enemy fights with strength
        if card_id == 'Reaper':
            num_monsters = len(context.monsters_alive) if context.monsters_alive else 0
            strength = self._estimate_strength(context)
            if num_monsters >= 2 and strength >= 5:
                return 950  # Perfect situation
            elif num_monsters >= 2:
                return 600  # Still good for healing
            else:
                return 200  # Not ideal for single enemy

        # Body Slam - insane with high block
        if card_id == 'Body Slam':
            current_block = context.game.player.block if hasattr(context.game.player, 'block') else 0
            if current_block >= 25:
                return 950  # One-shot territory
            elif current_block >= 15:
                return 800  # Very good
            elif current_block >= 10:
                return 500  # Decent
            else:
                return 100  # Wait for more block

        # Pommel Strike - draw + damage
        if card_id == 'Pommel Strike':
            return 750

        # Other attacks - baseline
        return 500

    def _get_skill_priority(self, card: Card, context: DecisionContext) -> float:
        """Get priority for skill cards."""
        # Shrug It Off - excellent (block + draw)
        if card.card_id == 'Shrug It Off':
            return 850

        # Disarm - powerful single-target defense
        if card.card_id == 'Disarm':
            if self._needs_defense(context):
                return 800
            return 200

        # Metallicize - good in Act 1-2
        if card.card_id == 'Metallicize':
            if context.act <= 2:
                return 700
            return 300

        return 400

    def _get_defensive_priority(self, card: Card, context: DecisionContext) -> float:
        """Get priority for defensive cards."""
        incoming = context.incoming_damage if hasattr(context, 'incoming_damage') else 0
        current_block = context.game.player.block if hasattr(context.game.player, 'block') else 0

        # Iron Wave - attack + block
        if card.card_id == 'Iron Wave':
            return 750

        # Entrench - double block (amazing with high block)
        if card.card_id == 'Entrench':
            if current_block >= 10:
                return 900
            return 400

        # Pure defense cards
        if incoming > current_block + 5:
            return 700  # Need block badly
        elif incoming > current_block:
            return 500  # Need some block
        else:
            return 200  # Already safe

    def _should_bash_now(self, context: DecisionContext) -> bool:
        """Determine if Bash should be played now."""
        # Check if we have follow-up attacks
        if not hasattr(context.game, 'hand'):
            return False

        attack_cards = [c for c in context.game.hand
                       if hasattr(c, 'type') and str(c.type) == 'ATTACK'
                       and c.card_id != 'Bash']

        if not attack_cards:
            return False  # No point in Bash without attacks

        # Find best target
        target = self._find_highest_hp_monster(context)

        if target:
            # Check if target will survive to benefit from vulnerable
            # (2 turns of vulnerable = full benefit)
            estimated_damage = sum(self._estimate_card_damage(c, context) for c in attack_cards)
            if estimated_damage < target.current_hp * 0.7:
                return True  # Target won't die too fast

        return False

    def _needs_block(self, context: DecisionContext) -> bool:
        """Check if player needs block."""
        incoming = context.incoming_damage if hasattr(context, 'incoming_damage') else 0
        current_block = context.game.player.block if hasattr(context.game.player, 'block') else 0

        return incoming > current_block + 5

    def _needs_defense(self, context: DecisionContext) -> bool:
        """Check if player needs defensive measures."""
        incoming = context.incoming_damage if hasattr(context, 'incoming_damage') else 0
        current_block = context.game.player.block if hasattr(context.game.player, 'block') else 0
        hp_pct = context.player_hp_pct

        # Need defense if: high incoming damage OR low HP
        return (incoming > current_block) or (hp_pct < 0.4)

    def _is_corruption_active(self, context: DecisionContext) -> bool:
        """Check if Corruption power is active."""
        if not hasattr(context.game, 'player') or not hasattr(context.game.player, 'powers'):
            return False

        for power in context.game.player.powers:
            if power.power_id == 'Corruption':
                return True

        return False

    def _is_draw_card(self, card: Card) -> bool:
        """Check if card draws other cards."""
        draw_keywords = ['draw', 'battle trance', 'pommel strike', 'shrug it off']
        card_id_lower = card.card_id.lower()

        for keyword in draw_keywords:
            if keyword in card_id_lower:
                return True

        # Check card description for "draw"
        if hasattr(card, 'description'):
            desc_lower = card.description.lower()
            if 'draw' in desc_lower:
                return True

        return False

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is primarily defensive."""
        defensive_keywords = [
            'defend', 'block', 'iron wave', 'flame barrier', 'impervious',
            'entrench', 'sentinel', 'ghostly armor', 'shrug it off',
        ]

        card_id_lower = card.card_id.lower()

        for keyword in defensive_keywords:
            if keyword in card_id_lower:
                return True

        return False

    def _get_skill_base_value(self, card: Card, context: DecisionContext) -> float:
        """Get base value of skill (for Corruption mode)."""
        # Shrug It Off is best
        if card.card_id == 'Shrug It Off':
            return 50

        # Block cards
        if self._is_defensive_card(card):
            return 40

        # Draw cards
        if self._is_draw_card(card):
            return 45

        return 30

    def _choose_target(self, card: Card, context: DecisionContext):
        """Choose target for card."""
        if not context.monsters_alive:
            return None

        # Bash: highest HP (maximize vulnerable duration)
        if card.card_id == 'Bash':
            return self._find_highest_hp_monster(context)

        # Body Slam: lowest HP (efficient kills)
        if card.card_id == 'Body Slam':
            return self._find_lowest_hp_monster(context)

        # Reaper: highest HP (most healing)
        if card.card_id == 'Reaper':
            return self._find_highest_hp_monster(context)

        # AOE: doesn't matter
        if card.card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap']:
            return None  # AOE doesn't need targeting

        # Standard attacks: lowest HP
        if hasattr(card, 'type') and str(card.type) == 'ATTACK':
            return self._find_lowest_hp_monster(context)

        # Debuffs: highest HP
        return self._find_highest_hp_monster(context)

    def _find_lowest_hp_monster(self, context: DecisionContext) -> Monster:
        """Find monster with lowest HP."""
        if not context.monsters_alive:
            return None

        return min(context.monsters_alive, key=lambda m: m.current_hp)

    def _find_highest_hp_monster(self, context: DecisionContext) -> Monster:
        """Find monster with highest HP."""
        if not context.monsters_alive:
            return None

        return max(context.monsters_alive, key=lambda m: m.current_hp)

    def _estimate_strength(self, context: DecisionContext) -> int:
        """Estimate current strength."""
        if not hasattr(context.game, 'player'):
            return 0

        # Base strength from powers
        strength = 0

        if hasattr(context.game.player, 'powers'):
            for power in context.game.player.powers:
                if power.amount:
                    strength += power.amount

        return strength

    def _estimate_card_damage(self, card: Card, context: DecisionContext) -> int:
        """Estimate damage of a card."""
        if hasattr(card, 'damage'):
            return card.damage
        return 0

    def _enemy_intends_to_attack(self, context: DecisionContext) -> bool:
        """Check if any enemy intends to attack (for Spot Weakness)."""
        if not context.monsters_alive:
            return False

        for monster in context.monsters_alive:
            if hasattr(monster, 'intent') and hasattr(monster.intent, '__str__'):
                intent_str = str(monster.intent).upper()
                if 'ATTACK' in intent_str or 'ATTACK_' in intent_str:
                    return True

        return False

    def get_confidence(self, context: DecisionContext) -> float:
        """
        Return confidence in combat plan (0-1).

        Higher confidence when:
        - Clear archetype detected
        - Good energy available
        - Playable cards match strategy
        """
        # Base confidence
        confidence = 0.7

        # Higher with more energy (more options)
        if context.energy_available >= 3:
            confidence += 0.1
        elif context.energy_available == 1:
            confidence -= 0.2

        # Higher with HP safety
        if context.player_hp_pct > 0.7:
            confidence += 0.1
        elif context.player_hp_pct < 0.3:
            confidence -= 0.2

        # Higher in Act 1 (more familiar)
        if context.act == 1:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

