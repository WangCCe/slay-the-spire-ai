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
from .card_names import canonical_card_name
from .card_costs import effective_card_cost, whirlwind_damage, x_effect_energy

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

    @staticmethod
    def _base_card_name(card: Card) -> str:
        return canonical_card_name(card)

    def can_kill_all(self, context: DecisionContext) -> bool:
        """
        Check if all monsters can be killed this turn.

        Improved detection with:
        - Energy constraint validation
        - Targeting feasibility check
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

            # Log vulnerable-related intermediate values for verification
            vulnerable_targets = []
            for i, monster in enumerate(context.monsters_alive):
                stacks = context.vulnerable_stacks.get(i, 0)
                if stacks > 0:
                    vulnerable_targets.append(
                        f"idx={i}, stacks={stacks}, hp={monster.current_hp}, block={monster.block}"
                    )
            logger.info(
                "[LETHAL_VULNERABLE] targets=%s, multiplier=1.5",
                vulnerable_targets if vulnerable_targets else "none",
            )

            # Step 3: Check with reduced margin (10% instead of 20%)
            margin_multiplier = 1.1
            has_damage_potential = affordable_damage >= total_monster_hp * margin_multiplier

            # Step 4: Validate targeting (single-target vs AOE constraints)
            targeting_feasible = self._can_target_all_monsters(context, affordable_damage)

            # Low HP must not suppress a deterministic kill. The margin and
            # targeting checks already keep this detector conservative.
            low_hp = context.player_hp <= 30 and context.player_hp_pct <= 0.3

            # Log detection results
            logger.info(f"[LETHAL_DETECTION] affordable_damage={affordable_damage}, "
                       f"total_monster_hp={total_monster_hp}, margin_ok={has_damage_potential}, "
                       f"targeting_ok={targeting_feasible}, low_hp={low_hp}, "
                       f"player_hp={context.player_hp}, player_hp_pct={context.player_hp_pct:.2f}")

            # Final decision
            lethal_detected = has_damage_potential and targeting_feasible

            if lethal_detected:
                logger.info(f"[LETHAL_DETECTION] LETHAL DETECTED! All checks passed")
            else:
                reasons = []
                if not has_damage_potential:
                    reasons.append(f"Insufficient damage ({affordable_damage} < {int(total_monster_hp * margin_multiplier)} with 10% margin)")
                if not targeting_feasible:
                    reasons.append("Targeting constraints prevent lethal")
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
        remaining_monster_indices = list(range(len(remaining_monsters)))
        played_cards = set()
        remaining_energy = context.energy_available

        # Sort monsters by HP (kill weakest first)
        combined = list(zip(remaining_monsters, remaining_monster_indices))
        combined.sort(key=lambda pair: pair[0].current_hp)
        remaining_monsters = [m for m, _ in combined]
        remaining_monster_indices = [i for _, i in combined]

        # Get attack cards sorted by damage
        attack_cards = [c for c in context.playable_cards
                       if hasattr(c, 'type') and c.type == CardType.ATTACK]
        attack_cards.sort(key=lambda c: self._get_card_damage(c, context), reverse=True)

        for monster, monster_idx in zip(remaining_monsters, remaining_monster_indices):
            damage_needed = monster.current_hp + monster.block
            for card in attack_cards:
                card_uuid = getattr(card, 'uuid', None) or id(card)
                if card_uuid in played_cards:
                    continue

                cost = effective_card_cost(card, remaining_energy)
                if cost > remaining_energy:
                    continue

                # Check vulnerable status
                vulnerable = context.vulnerable_stacks.get(monster_idx, 0)
                damage = self._get_card_damage(card, context)
                damage = self._apply_player_weak_to_card_damage(
                    card,
                    context,
                    damage,
                    remaining_energy,
                )
                if vulnerable > 0:
                    damage = self._apply_vulnerable_to_card_damage(
                        card,
                        context,
                        damage,
                        remaining_energy,
                    )

                sequence.append(PlayCardAction(card=card, target_monster=monster))
                played_cards.add(card_uuid)
                remaining_energy -= cost
                damage_needed -= damage
                if damage_needed <= 0:
                    break

            if damage_needed > 0:
                logger.warning(
                    "[LETHAL_SEQUENCE] Construction failed: %s still has %s HP/block remaining",
                    getattr(monster, 'name', 'monster'),
                    damage_needed,
                )
                return []

        if sequence:
            card_names = [action.card.card_id if hasattr(action, 'card') and hasattr(action.card, 'card_id') else 'Unknown' for action in sequence]
            logger.info(f"[LETHAL_SEQUENCE] Constructed sequence with {len(sequence)} cards: {', '.join(card_names)}")
        else:
            logger.warning(f"[LETHAL_SEQUENCE] Construction failed: greedy approach returned empty sequence")
            logger.warning(f"[LETHAL_SEQUENCE] Debug: attacks={len(attack_cards)}, energy={context.energy_available}")

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
                cost = effective_card_cost(card, context.energy_available)
                damage = self._get_card_damage(card, context)
                damage = self._apply_player_weak_to_card_damage(
                    card,
                    context,
                    damage,
                    context.energy_available,
                )
                if len(context.monsters_alive) == 1 and context.vulnerable_stacks.get(0, 0) > 0:
                    damage = self._apply_vulnerable_to_card_damage(
                        card,
                        context,
                        damage,
                        context.energy_available,
                    )
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
            if hasattr(card, 'type') and card.type == CardType.ATTACK:
                # Check if this is an AOE attack
                card_id = self._base_card_name(card)
                is_aoe = card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']

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
            if hasattr(card, 'type') and card.type == CardType.ATTACK:
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
        card_name = self._base_card_name(card)
        upgrades = getattr(card, 'upgrades', 0)
        display_name = getattr(card, 'name', None) or card_name
        if upgrades > 0 and '+' not in display_name:
            upgrade_suffix = f"+{upgrades}" if card_name == 'Searing Blow' and upgrades > 1 else '+'
            display_name = f"{card_name}{upgrade_suffix}"
        base_damage = 0

        card_data = game_data_loader.get_card_data(card_name)
        if card_data:
            damage_data = dict(card_data)
            damage_data['name'] = display_name
            base_damage = game_data_loader._parse_card_damage(damage_data) or 0

        if card_name == 'Whirlwind':
            energy = x_effect_energy(card, context.energy_available, context)
            return whirlwind_damage(card, energy, getattr(context, 'strength', 0))

        if hasattr(card, 'type') and card.type == CardType.ATTACK:
            strength = getattr(context, 'strength', 0)
            upgrades = getattr(card, 'upgrades', 0)

            if card_name == 'Heavy Blade':
                multiplier = 5 if upgrades > 0 else 3
                base_damage += strength * multiplier
            elif card_name == 'Perfected Strike':
                per_strike_bonus = 3 if upgrades > 0 else 2
                base_damage += self._count_strike_cards(context) * per_strike_bonus + strength
            else:
                base_damage += strength

            base_damage *= self._get_attack_hit_count(card, context)

        return max(0, base_damage)

    def _apply_player_weak_to_card_damage(
        self,
        card: Card,
        context: DecisionContext,
        total_damage: int,
        available_energy: int,
    ) -> int:
        """Apply player Weak using the game's per-hit rounding."""
        if self._get_player_debuff_stacks(context, 'Weak') <= 0:
            return total_damage

        hit_count = self._get_vulnerable_damage_instance_count(
            card,
            context,
            available_energy,
        )
        if hit_count <= 1:
            return int(total_damage * 0.75)

        per_hit_damage, remainder = divmod(total_damage, hit_count)
        if remainder != 0:
            return int(total_damage * 0.75)

        return int(per_hit_damage * 0.75) * hit_count

    def _apply_vulnerable_to_card_damage(
        self,
        card: Card,
        context: DecisionContext,
        total_damage: int,
        available_energy: int,
    ) -> int:
        """Apply Vulnerable using the game's per-hit rounding."""
        hit_count = self._get_vulnerable_damage_instance_count(
            card,
            context,
            available_energy,
        )
        if hit_count <= 1:
            return int(total_damage * 1.5)

        per_hit_damage, remainder = divmod(total_damage, hit_count)
        if remainder != 0:
            return int(total_damage * 1.5)

        return int(per_hit_damage * 1.5) * hit_count

    def _get_vulnerable_damage_instance_count(
        self,
        card: Card,
        context: DecisionContext,
        available_energy: int,
    ) -> int:
        card_name = self._base_card_name(card)

        if card_name == 'Whirlwind':
            return max(1, x_effect_energy(card, available_energy, context))

        return self._get_attack_hit_count(card, context)

    def _get_player_debuff_stacks(self, context: DecisionContext, power_name: str) -> int:
        player = getattr(getattr(context, 'game', None), 'player', None)
        powers = getattr(player, 'powers', []) if player is not None else []
        for power in powers:
            current_name = (
                getattr(power, 'name', None)
                or getattr(power, 'power_name', None)
                or getattr(power, 'power_id', None)
            )
            if current_name == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 1
        return 0

    def _get_attack_hit_count(self, card: Card, context: DecisionContext) -> int:
        """Return known hit counts for repeated-hit attacks."""
        card_name = self._base_card_name(card)
        upgrades = getattr(card, 'upgrades', 0)

        if card_name == 'Twin Strike':
            return 2
        if card_name == 'Sword Boomerang':
            return 4 if upgrades > 0 else 3
        if card_name == 'Pummel':
            return 5 if upgrades > 0 else 4
        if card_name == 'Fiend Fire':
            return self._count_fiend_fire_exhausted_cards(card, context)

        return 1

    def _count_fiend_fire_exhausted_cards(self, card: Card, context: DecisionContext) -> int:
        """Count cards Fiend Fire will exhaust after the played card leaves hand."""
        hand_cards = getattr(getattr(context, 'game', None), 'hand', None)
        if not hand_cards:
            hand_cards = getattr(context, 'playable_cards', []) or []

        played_uuid = getattr(card, 'uuid', None)
        count = 0
        for hand_card in hand_cards:
            if hand_card is card:
                continue
            if played_uuid and getattr(hand_card, 'uuid', None) == played_uuid:
                continue
            count += 1
        return max(0, count)

    def _count_strike_cards(self, context: DecisionContext) -> int:
        """Count deck cards whose displayed name or id contains Strike."""
        deck = getattr(getattr(context, 'game', None), 'deck', None)
        if not deck:
            return 0

        count = 0
        for deck_card in deck:
            card_name = getattr(deck_card, 'name', '') or ''
            card_id = getattr(deck_card, 'card_id', '') or ''
            if 'strike' in card_name.lower() or 'strike' in card_id.lower():
                count += 1
        return count
