"""
Combat ending detection - can we kill all monsters this turn?

This module provides lethality detection to prevent over-defending when
combat could be ended this turn.
"""

import logging
from typing import List, Tuple, Optional
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Monster
from spirecomm.communication.action import PlayCardAction
from spirecomm.data.loader import game_data_loader
from ..decision.base import DecisionContext

logger = logging.getLogger(__name__)


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

        Improved detection with:
        - Energy constraint validation
        - Targeting feasibility check
        - HP safety threshold
        - Reduced margin (10% instead of 20%)

        Args:
            context: Current decision context

        Returns:
            True if lethal is possible
        """
        try:
            logger.info("[LETHAL_ENTRY] can_kill_all() called")

            if not context.monsters_alive:
                logger.info("[LETHAL_ENTRY] No monsters alive, returning True")
                return True

            logger.info(f"[LETHAL_ENTRY] {len(context.monsters_alive)} monsters, {len(context.playable_cards)} cards")

            # Step 1: Calculate affordable damage (respecting energy constraints)
            logger.info("[LETHAL_ENTRY] About to calculate affordable damage...")
            affordable_damage = self._calculate_affordable_damage(context)
            logger.info(f"[LETHAL_ENTRY] Affordable damage calculated: {affordable_damage}")

            # Step 2: Calculate total monster HP (including block)
            total_monster_hp = sum(m.current_hp + m.block for m in context.monsters_alive)

            # Step 3: Check with reduced margin (10% instead of 20%)
            margin_multiplier = 1.1
            has_damage_potential = affordable_damage >= total_monster_hp * margin_multiplier

            # Step 4: Validate targeting (single-target vs AOE constraints)
            targeting_feasible = self._can_target_all_monsters(context, affordable_damage)

            # Step 5: HP safety check (only go for lethal if not too risky)
            hp_safe = context.player_hp > 30 or context.player_hp_pct > 0.3

            # Log detection results
            logger.info(f"[LETHAL_DETECTION] affordable_damage={affordable_damage}, "
                       f"total_monster_hp={total_monster_hp}, margin_ok={has_damage_potential}, "
                       f"targeting_ok={targeting_feasible}, hp_safe={hp_safe}, "
                       f"player_hp={context.player_hp}, player_hp_pct={context.player_hp_pct:.2f}")

            # Final decision
            lethal_detected = has_damage_potential and targeting_feasible and hp_safe

            if lethal_detected:
                logger.info(f"[LETHAL_DETECTION] LETHAL DETECTED! All checks passed")
            else:
                reasons = []
                if not has_damage_potential:
                    reasons.append(f"Insufficient damage ({affordable_damage} < {int(total_monster_hp * margin_multiplier)} with 10% margin)")
                if not targeting_feasible:
                    reasons.append("Targeting constraints prevent lethal")
                if not hp_safe:
                    reasons.append(f"HP too low for risky lethal ({context.player_hp} HP, {context.player_hp_pct:.1%})")
                logger.info(f"[LETHAL_DETECTION] No lethal. Reason: {'; '.join(reasons)}")

            return lethal_detected

        except Exception as e:
            import traceback
            logger.error(f"[LETHAL_ERROR] Exception in can_kill_all: {e}")
            logger.error(f"[LETHAL_ERROR] Traceback: {traceback.format_exc()}")
            # On error, assume no lethal
            return False

    def find_lethal_sequence(self, context: DecisionContext) -> List[PlayCardAction]:
        """
        Find card sequence that kills all monsters.

        Uses greedy approach: play highest-damage cards on lowest-HP targets.

        Args:
            context: Current decision context

        Returns:
            List of actions to kill all monsters, or empty list if not possible
        """
        logger.info(f"[LETHAL_SEQUENCE] Attempting to construct lethal sequence")

        if not self.can_kill_all(context):
            logger.info(f"[LETHAL_SEQUENCE] Construction aborted: lethal not detected")
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

        if sequence:
            card_names = [action.card.card_id if hasattr(action, 'card') and hasattr(action.card, 'card_id') else 'Unknown' for action in sequence]
            logger.info(f"[LETHAL_SEQUENCE] Constructed sequence with {len(sequence)} cards: {', '.join(card_names)}")
        else:
            logger.warning(f"[LETHAL_SEQUENCE] Construction failed: greedy approach returned empty sequence")

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

    def _calculate_affordable_damage(self, context: DecisionContext) -> int:
        """
        Calculate total damage from cards that are affordable with available energy.

        This respects energy constraints, unlike _calculate_max_damage().

        Args:
            context: Current decision context

        Returns:
            Total damage that can be dealt with available energy
        """
        total_damage = 0
        energy_used = 0

        # Sort attack cards by damage efficiency (damage per energy)
        attack_cards = []
        for card in context.playable_cards:
            # FIX: Compare CardType enum directly, not string
            if hasattr(card, 'type') and card.type == CardType.ATTACK:
                cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
                damage = self._get_card_damage(card, context)
                logger.info(f"[LETHAL_CALC] {card.name}: cost={cost}, damage={damage}, eff={damage/cost if cost > 0 else 'inf'}")
                if cost > 0:
                    efficiency = damage / cost
                else:
                    efficiency = float('inf')  # Zero-cost cards are infinitely efficient
                attack_cards.append((card, cost, damage, efficiency))

        # Sort by efficiency (highest first), then by damage (highest first)
        attack_cards.sort(key=lambda x: (x[3], x[2]), reverse=True)

        # Greedily select cards until energy runs out
        selected = []
        for card, cost, damage, _ in attack_cards:
            if energy_used + cost <= context.energy_available:
                total_damage += damage
                energy_used += cost
                selected.append(card.name)
            elif cost == 0:
                # Zero-cost cards can always be played
                total_damage += damage
                selected.append(card.name)

        logger.info(f"[LETHAL_CALC] Selected: {selected}, total_damage={total_damage}, energy_used={energy_used}/{context.energy_available}")
        return total_damage

    def _can_target_all_monsters(self, context: DecisionContext, affordable_damage: int) -> bool:
        """
        Check if targeting constraints allow killing all monsters.

        Validates that single-target attacks can reach all monsters
        (i.e., we have enough attacks and energy to target each monster).

        Args:
            context: Current decision context
            affordable_damage: Total damage we can afford to deal

        Returns:
            True if targeting is feasible, False otherwise
        """
        num_monsters = len(context.monsters_alive)

        # Count AOE attacks
        aoe_count = 0
        single_target_count = 0

        for card in context.playable_cards:
            if hasattr(card, 'type') and str(card.type) == 'ATTACK':
                # Check if this is an AOE attack
                card_id = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ""
                is_aoe = card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper', 'Carnage']

                if is_aoe:
                    aoe_count += 1
                else:
                    single_target_count += 1

        # If we have AOE, targeting is always feasible
        if aoe_count > 0:
            return True

        # If we have enough single-target attacks for each monster, feasible
        if single_target_count >= num_monsters:
            return True

        # Otherwise, check if we have enough total damage to overcome targeting inefficiency
        # Apply a penalty for single-target vs multiple monsters
        if num_monsters == 1:
            return True  # Single monster, no targeting issue
        elif num_monsters == 2:
            # Need 30% more damage to overcome targeting inefficiency
            return affordable_damage >= sum(m.current_hp + m.block for m in context.monsters_alive) * 1.3
        else:
            # Need 50% more damage for 3+ monsters
            return affordable_damage >= sum(m.current_hp + m.block for m in context.monsters_alive) * 1.5

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

        # Get base damage from game data loader (Card objects don't have damage attribute)
        # Use card.name instead of card_id because:
        #   - card_id: "Strike_R" (Communication Mod internal ID)
        #   - card.name: "Strike+" (matches items.json)
        if hasattr(card, 'name'):
            card_data = game_data_loader.get_card_data(card.name)
            if card_data:
                # Use _parse_card_damage which handles metadata and regex parsing
                base_damage = game_data_loader._parse_card_damage(card_data) or 0

        # Add strength (for attacks)
        # FIX: Compare CardType enum directly, not string
        if hasattr(card, 'type') and card.type == CardType.ATTACK:
            base_damage += context.strength

        return max(0, base_damage)
