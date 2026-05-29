"""
Combat ending detection - can we kill all monsters this turn?

This module provides lethality detection to prevent over-defending when
combat could be ended this turn.
"""

import logging
import re
from dataclasses import dataclass, replace
from typing import List, Tuple, Optional
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Monster
from spirecomm.communication.action import PlayCardAction
from spirecomm.ai.intent_utils import intent_is_attack
from spirecomm.data.loader import game_data_loader
from ..decision.base import DecisionContext
from .card_names import canonical_card_name
from .card_costs import (
    effective_card_cost,
    energy_refund_for_card,
    playable_card_cost_after_refund,
    whirlwind_damage,
    x_effect_energy,
)

logger = logging.getLogger(__name__)

TARGETED_LETHAL_MAX_CARDS = 8
TARGETED_LETHAL_MAX_MONSTERS = 4


@dataclass(frozen=True)
class _TargetedLethalState:
    hp: Tuple[int, ...]
    vulnerable: Tuple[int, ...]
    artifact: Tuple[int, ...]
    strength: int
    player_hp: int
    corruption_active: bool
    double_tap_charges: int
    energy: int

    def seen_key(self, remaining_card_keys: Tuple[object, ...]):
        return (
            remaining_card_keys,
            self.hp,
            self.vulnerable,
            self.artifact,
            self.strength,
            self.player_hp,
            self.corruption_active,
            self.double_tap_charges,
            self.energy,
        )

    def after_spending(self, cost: int, **changes) -> "_TargetedLethalState":
        return replace(self, energy=self.energy - cost, **changes)


@dataclass(frozen=True)
class _TargetedLethalCandidate:
    priority: Tuple[int, int, int, int]
    card_pos: int
    monster_idx: Optional[int]
    next_state: _TargetedLethalState


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

    @staticmethod
    def _play_card_action(card: Card, target_monster: Optional[Monster] = None) -> PlayCardAction:
        if not getattr(card, 'has_target', False):
            target_monster = None
        return PlayCardAction(card=card, target_monster=target_monster)

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
            exact_single_target_kill = (
                len(context.monsters_alive) == 1
                and affordable_damage >= total_monster_hp
            )
            has_damage_potential = (
                exact_single_target_kill
                or affordable_damage >= total_monster_hp * margin_multiplier
            )

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

            attack_cards = [
                card for card in context.playable_cards
                if hasattr(card, 'type') and card.type == CardType.ATTACK
            ]
            proven_aoe_cleanup = bool(self._find_aoe_cleanup_sequence(
                context,
                attack_cards,
                context.energy_available,
            ))
            proven_targeted_sequence = bool(self._find_targeted_lethal_sequence(
                context,
                attack_cards,
                context.energy_available,
            ))
            exact_sequence_search_applicable = self._can_use_exact_lethal_sequence(
                context,
                attack_cards,
            )
            random_targeting_uncertain = self._has_uncertain_random_target_attack(
                context,
                attack_cards,
            )

            # Final decision
            lethal_detected = (
                proven_aoe_cleanup
                or proven_targeted_sequence
                or (
                    not exact_sequence_search_applicable
                    and not random_targeting_uncertain
                    and has_damage_potential
                    and targeting_feasible
                )
            )

            if lethal_detected:
                logger.info(f"[LETHAL_DETECTION] LETHAL DETECTED! All checks passed")
            else:
                reasons = []
                if not has_damage_potential:
                    reasons.append(f"Insufficient damage ({affordable_damage} < {int(total_monster_hp * margin_multiplier)} with 10% margin)")
                if not targeting_feasible:
                    reasons.append("Targeting constraints prevent lethal")
                if exact_sequence_search_applicable and not proven_targeted_sequence:
                    reasons.append("No exact lethal sequence found")
                if random_targeting_uncertain:
                    reasons.append("Random-target attacks cannot prove multi-target lethal")
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

        for card in attack_cards:
            cost = effective_card_cost(card, remaining_energy)
            if cost > remaining_energy:
                continue
            if self._is_aoe_attack(card) and self._aoe_card_kills_all(card, context, remaining_energy):
                return [PlayCardAction(card=card)]

        aoe_cleanup_sequence = self._find_aoe_cleanup_sequence(
            context,
            attack_cards,
            remaining_energy,
        )
        if aoe_cleanup_sequence:
            return aoe_cleanup_sequence

        targeted_sequence = self._find_targeted_lethal_sequence(
            context,
            attack_cards,
            remaining_energy,
        )
        if targeted_sequence:
            return targeted_sequence

        for monster, monster_idx in zip(remaining_monsters, remaining_monster_indices):
            damage_needed = monster.current_hp + monster.block
            while damage_needed > 0:
                best_card = None
                best_card_uuid = None
                best_cost = 0
                best_damage = 0
                best_priority = None

                for card in attack_cards:
                    card_uuid = getattr(card, 'uuid', None) or id(card)
                    if card_uuid in played_cards:
                        continue

                    cost = self._card_energy_cost_against_monster(
                        card,
                        context,
                        monster_idx,
                        remaining_energy,
                    )
                    if cost > remaining_energy:
                        continue

                    damage = self._card_damage_against_monster(
                        card,
                        context,
                        monster_idx,
                        remaining_energy,
                    )
                    if damage <= 0:
                        continue

                    refunds_energy = self._card_refunds_energy_against_monster(
                        card,
                        context,
                        monster_idx,
                    )
                    priority = (1 if refunds_energy else 0, damage, -cost)
                    if best_priority is None or priority > best_priority:
                        best_card = card
                        best_card_uuid = card_uuid
                        best_cost = cost
                        best_damage = damage
                        best_priority = priority

                if best_card is None:
                    break

                sequence.append(self._play_card_action(best_card, monster))
                played_cards.add(best_card_uuid)
                remaining_energy -= best_cost
                damage_needed -= best_damage

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

    def _is_aoe_attack(self, card: Card) -> bool:
        card_id = self._base_card_name(card)
        return card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']

    def _is_all_enemy_debuff_card(self, card: Card) -> bool:
        return self._base_card_name(card) == 'Shockwave'

    def _aoe_card_kills_all(
        self,
        card: Card,
        context: DecisionContext,
        available_energy: int,
    ) -> bool:
        base_damage = self._get_card_damage(
            card,
            context,
            available_energy=available_energy,
        )
        base_damage = self._apply_player_weak_to_card_damage(
            card,
            context,
            base_damage,
            available_energy,
        )
        for monster_idx, monster in enumerate(context.monsters_alive):
            damage = base_damage
            if context.vulnerable_stacks.get(monster_idx, 0) > 0:
                damage = self._apply_vulnerable_to_card_damage(
                    card,
                    context,
                    damage,
                    available_energy,
                )
            if damage < monster.current_hp + monster.block:
                return False
        return True

    @staticmethod
    def _card_play_key(card: Card):
        return getattr(card, 'uuid', None) or id(card)

    def _can_use_exact_lethal_sequence(
        self,
        context: DecisionContext,
        attack_cards: List[Card],
    ) -> bool:
        monsters = getattr(context, 'monsters_alive', []) or []
        if not monsters:
            return False

        sequence_cards = [
            card
            for card in attack_cards
            if self._is_aoe_attack(card) or getattr(card, 'has_target', False)
        ]
        return (
            bool(sequence_cards)
            and len(sequence_cards) == len(attack_cards)
            and len(sequence_cards) <= TARGETED_LETHAL_MAX_CARDS
            and len(monsters) <= TARGETED_LETHAL_MAX_MONSTERS
        )

    def _has_uncertain_random_target_attack(
        self,
        context: DecisionContext,
        attack_cards: List[Card],
    ) -> bool:
        monsters = getattr(context, 'monsters_alive', []) or []
        if len(monsters) <= 1:
            return False

        return any(
            not self._is_aoe_attack(card) and not getattr(card, 'has_target', False)
            for card in attack_cards
        )

    def _card_damage_against_monster(
        self,
        card: Card,
        context: DecisionContext,
        monster_idx: int,
        available_energy: int,
        fiend_fire_exhaust_count: Optional[int] = None,
        target_vulnerable_stacks: Optional[int] = None,
        strength: Optional[int] = None,
    ) -> int:
        damage = self._get_card_damage(
            card,
            context,
            monster_idx,
            available_energy,
            fiend_fire_exhaust_count,
            strength,
        )
        damage = self._apply_player_weak_to_card_damage(
            card,
            context,
            damage,
            available_energy,
            monster_idx,
            fiend_fire_exhaust_count,
        )
        vulnerable_stacks = (
            self._monster_vulnerable_stacks(context, monster_idx)
            if target_vulnerable_stacks is None
            else target_vulnerable_stacks
        )
        if vulnerable_stacks > 0:
            damage = self._apply_vulnerable_to_card_damage(
                card,
                context,
                damage,
                available_energy,
                monster_idx,
                fiend_fire_exhaust_count,
            )
        return max(0, damage)

    def _card_energy_cost_against_monster(
        self,
        card: Card,
        context: DecisionContext,
        monster_idx: int,
        available_energy: int,
        target_vulnerable_stacks: Optional[int] = None,
    ) -> int:
        return playable_card_cost_after_refund(
            card,
            available_energy,
            self._card_energy_refund_against_monster(
                card,
                context,
                monster_idx,
                target_vulnerable_stacks,
            ),
        )

    def _card_energy_refund_against_monster(
        self,
        card: Card,
        context: DecisionContext,
        monster_idx: int,
        target_vulnerable_stacks: Optional[int] = None,
    ) -> int:
        vulnerable_stacks = (
            self._monster_vulnerable_stacks(context, monster_idx)
            if target_vulnerable_stacks is None
            else target_vulnerable_stacks
        )
        return energy_refund_for_card(
            card,
            target_vulnerable=vulnerable_stacks > 0,
        )

    def _card_refunds_energy_against_monster(
        self,
        card: Card,
        context: DecisionContext,
        monster_idx: int,
        target_vulnerable_stacks: Optional[int] = None,
    ) -> bool:
        return (
            self._card_energy_refund_against_monster(
                card,
                context,
                monster_idx,
                target_vulnerable_stacks,
            )
            > 0
        )

    def _monster_vulnerable_stacks(self, context: DecisionContext, monster_idx: int) -> int:
        vulnerable_stacks = getattr(context, 'vulnerable_stacks', {}) or {}
        stacks = vulnerable_stacks.get(monster_idx, 0)
        if stacks:
            return stacks

        monsters = getattr(context, 'monsters_alive', []) or []
        if 0 <= monster_idx < len(monsters):
            return self._get_monster_power_amount(monsters[monster_idx], 'Vulnerable')
        return 0

    def _monster_poison_stacks(self, context: DecisionContext, monster_idx: int) -> int:
        monsters = getattr(context, 'monsters_alive', []) or []
        if 0 <= monster_idx < len(monsters):
            return self._get_monster_power_amount(monsters[monster_idx], 'Poison')
        return 0

    def _vulnerable_state_after_card(
        self,
        card: Card,
        context: DecisionContext,
        vulnerable_state: Tuple[int, ...],
        artifact_state: Tuple[int, ...],
        hp_state: Tuple[int, ...],
        monster_idx: Optional[int],
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
        debuff_effects = self._card_debuff_effects_applied(card)
        if not debuff_effects:
            return vulnerable_state, artifact_state

        if self._is_aoe_attack(card) or self._is_all_enemy_debuff_card(card):
            target_indices = range(len(vulnerable_state))
        elif monster_idx is not None:
            target_indices = (monster_idx,)
        else:
            return vulnerable_state, artifact_state

        next_vulnerable = list(vulnerable_state)
        next_artifact = list(artifact_state)
        for target_idx in target_indices:
            if target_idx >= len(next_vulnerable) or hp_state[target_idx] <= 0:
                continue
            artifact = max(0, next_artifact[target_idx])
            for debuff, stacks in debuff_effects:
                if stacks <= 0:
                    continue
                if artifact > 0:
                    artifact -= 1
                    continue
                if debuff == 'vulnerable':
                    next_vulnerable[target_idx] = max(0, next_vulnerable[target_idx]) + stacks
            next_artifact[target_idx] = artifact
        return tuple(next_vulnerable), tuple(next_artifact)

    def _card_debuff_effects_applied(self, card: Card) -> List[Tuple[str, int]]:
        text = self._card_effect_text(card)
        if not text:
            return []

        upgraded = getattr(card, 'upgrades', 0) > 0
        effects = []
        effect_text = text.replace('\\n', '\n').replace('#', '').lower()
        for clause in re.split(r'[\n.;]', effect_text):
            if 'apply' not in clause:
                continue

            for debuff in ('weak', 'vulnerable'):
                if debuff not in clause:
                    continue

                upgraded_match = re.search(
                    rf'\[(\d+)\|(\d+)\]\s+{debuff}\b',
                    clause,
                )
                if upgraded_match:
                    stacks = int(upgraded_match.group(2) if upgraded else upgraded_match.group(1))
                    effects.append((debuff, stacks))
                    continue

                stack_match = re.search(rf'\bapply\s+(\d+)\s+{debuff}\b', clause)
                if stack_match:
                    effects.append((debuff, int(stack_match.group(1))))

        if self._base_card_name(card) == 'Shockwave':
            stacks = 5 if upgraded else 3
            parsed_debuffs = {debuff for debuff, _stacks in effects}
            for debuff, marker in (
                ('weak', 'weak'),
                ('vulnerable', 'vulnerable'),
                ('strength_down', 'strength down'),
            ):
                if marker in effect_text and debuff not in parsed_debuffs:
                    effects.append((debuff, stacks))

        return effects

    def _card_effect_text(self, card: Card) -> str:
        card_name = self._base_card_name(card)

        try:
            wiki_data = getattr(game_data_loader, '_wiki_data', None)
            if wiki_data is None and hasattr(game_data_loader, '_load_wiki_data'):
                game_data_loader._load_wiki_data()
                wiki_data = getattr(game_data_loader, '_wiki_data', None)
            if wiki_data:
                wiki_entry = wiki_data.get(card_name.lower())
                if wiki_entry and wiki_entry.get('text'):
                    return str(wiki_entry['text'])
        except Exception:
            pass

        card_data = game_data_loader.get_card_data(card_name) or {}
        for key in ('description', 'text'):
            value = card_data.get(key)
            if value:
                return str(value)

        return ''

    def _is_lethal_strength_support_card(self, card: Card) -> bool:
        card_name = self._base_card_name(card)
        card_type = getattr(card, 'type', None)
        if card_type == CardType.SKILL:
            return card_name in {'Flex', 'Limit Break', 'Spot Weakness'}
        if card_type == CardType.POWER:
            return card_name == 'Inflame'
        return False

    def _strength_after_lethal_support_card(self, card: Card, strength: int) -> int:
        if self._base_card_name(card) == 'Flex':
            return strength + (4 if getattr(card, 'upgrades', 0) > 0 else 2)
        if self._base_card_name(card) == 'Limit Break':
            return strength * 2
        if self._base_card_name(card) == 'Spot Weakness':
            return strength + (4 if getattr(card, 'upgrades', 0) > 0 else 3)
        if self._base_card_name(card) == 'Inflame':
            return strength + (3 if getattr(card, 'upgrades', 0) > 0 else 2)
        return strength

    def _lethal_strength_support_targets(
        self,
        card: Card,
        context: DecisionContext,
        hp_state: Tuple[int, ...],
    ) -> Tuple[Optional[int], ...]:
        if self._base_card_name(card) != 'Spot Weakness':
            return (None,)

        return tuple(
            monster_idx
            for monster_idx, hp in enumerate(hp_state)
            if hp > 0
            and intent_is_attack(getattr(context.monsters_alive[monster_idx], 'intent', None))
        )

    def _is_lethal_energy_support_card(self, card: Card) -> bool:
        if getattr(card, 'type', None) != CardType.SKILL:
            return False
        return self._base_card_name(card) in {'Bloodletting', 'Offering', 'Seeing Red'}

    def _lethal_energy_gain(self, card: Card) -> int:
        card_name = self._base_card_name(card)
        if card_name == 'Bloodletting':
            return 3 if getattr(card, 'upgrades', 0) > 0 else 2
        if card_name in {'Offering', 'Seeing Red'}:
            return 2
        return 0

    def _lethal_energy_hp_loss(self, card: Card) -> int:
        card_name = self._base_card_name(card)
        if card_name == 'Bloodletting':
            return 3
        if card_name == 'Offering':
            return 6
        return 0

    def _context_player_hp(self, context: DecisionContext) -> int:
        hp = getattr(context, 'player_hp', None)
        if hp is None:
            hp = getattr(getattr(context, 'game', None), 'current_hp', 0)
        try:
            return int(hp)
        except (TypeError, ValueError):
            return 0

    def _context_corruption_active(self, context: DecisionContext) -> bool:
        return self._get_player_debuff_stacks(context, 'Corruption') > 0

    def _lethal_card_cost(
        self,
        card: Card,
        context: DecisionContext,
        available_energy: int,
        corruption_active: Optional[bool] = None,
    ) -> int:
        if corruption_active is None:
            corruption_active = self._context_corruption_active(context)
        if (
            getattr(card, 'type', None) == CardType.SKILL
            and corruption_active
        ):
            return 0
        return effective_card_cost(card, available_energy)

    def _is_lethal_corruption_support_card(self, card: Card) -> bool:
        if getattr(card, 'type', None) != CardType.POWER:
            return False
        return self._base_card_name(card) == 'Corruption'

    def _context_double_tap_charges(self, context: DecisionContext) -> int:
        try:
            return max(0, int(self._get_player_debuff_stacks(context, 'Double Tap') or 0))
        except (TypeError, ValueError):
            return 0

    def _is_lethal_double_tap_support_card(self, card: Card) -> bool:
        if getattr(card, 'type', None) != CardType.SKILL:
            return False
        return self._base_card_name(card) == 'Double Tap'

    def _lethal_double_tap_charges(self, card: Card) -> int:
        return 2 if getattr(card, 'upgrades', 0) > 0 else 1

    def _lethal_attack_repeats(self, card: Card, double_tap_charges: int) -> int:
        if double_tap_charges <= 0:
            return 1
        if self._base_card_name(card) == 'Fiend Fire':
            return 1
        return 2

    def _double_tap_charges_after_attack(self, double_tap_charges: int) -> int:
        return max(0, double_tap_charges - 1)

    def _is_lethal_vulnerable_support_card(self, card: Card) -> bool:
        if getattr(card, 'type', None) != CardType.SKILL:
            return False
        return self._is_all_enemy_debuff_card(card)

    def _find_targeted_lethal_sequence(
        self,
        context: DecisionContext,
        attack_cards: List[Card],
        available_energy: int,
    ) -> List[PlayCardAction]:
        """Prove a lethal line across attacks without relying on monster order."""
        sequence_cards = [
            card
            for card in attack_cards
            if self._is_aoe_attack(card) or getattr(card, 'has_target', False)
        ]
        support_cards = [
            card
            for card in getattr(context, 'playable_cards', []) or []
            if (
                self._is_lethal_strength_support_card(card)
                or self._is_lethal_energy_support_card(card)
                or self._is_lethal_corruption_support_card(card)
                or self._is_lethal_double_tap_support_card(card)
                or self._is_lethal_vulnerable_support_card(card)
            )
        ]
        sequence_cards = support_cards + sequence_cards
        if not sequence_cards or not getattr(context, 'monsters_alive', None):
            return []
        if (
            len(sequence_cards) > TARGETED_LETHAL_MAX_CARDS
            or len(context.monsters_alive) > TARGETED_LETHAL_MAX_MONSTERS
        ):
            return []

        sequence_card_keys = {self._card_play_key(card) for card in sequence_cards}
        starting_hp = tuple(
            max(0, monster.current_hp + monster.block)
            for monster in context.monsters_alive
        )
        starting_vulnerable = tuple(
            self._monster_vulnerable_stacks(context, monster_idx)
            for monster_idx, _monster in enumerate(context.monsters_alive)
        )
        starting_artifact = tuple(
            self._get_monster_power_amount(monster, 'Artifact')
            for monster in context.monsters_alive
        )
        starting_state = _TargetedLethalState(
            hp=starting_hp,
            vulnerable=starting_vulnerable,
            artifact=starting_artifact,
            strength=getattr(context, 'strength', 0),
            player_hp=self._context_player_hp(context),
            corruption_active=self._context_corruption_active(context),
            double_tap_charges=self._context_double_tap_charges(context),
            energy=available_energy,
        )
        seen = set()

        def search(remaining_cards, state: _TargetedLethalState):
            if all(hp <= 0 for hp in state.hp):
                return []

            remaining_card_keys = tuple(self._card_play_key(card) for card in remaining_cards)
            state_key = state.seen_key(remaining_card_keys)
            if state_key in seen:
                return None
            seen.add(state_key)

            candidates = []
            for card_pos, card in enumerate(remaining_cards):
                if self._is_lethal_strength_support_card(card):
                    cost = self._lethal_card_cost(
                        card,
                        context,
                        state.energy,
                        state.corruption_active,
                    )
                    if cost > state.energy:
                        continue

                    next_strength = self._strength_after_lethal_support_card(card, state.strength)
                    if next_strength <= state.strength:
                        continue

                    for target_idx in self._lethal_strength_support_targets(
                        card,
                        context,
                        state.hp,
                    ):
                        candidates.append(
                            _TargetedLethalCandidate(
                                priority=(0, 0, next_strength - state.strength, -cost),
                                card_pos=card_pos,
                                monster_idx=target_idx,
                                next_state=state.after_spending(
                                    cost,
                                    strength=next_strength,
                                ),
                            )
                        )
                    continue

                if self._is_lethal_energy_support_card(card):
                    cost = self._lethal_card_cost(
                        card,
                        context,
                        state.energy,
                        state.corruption_active,
                    )
                    if cost > state.energy:
                        continue

                    energy_gain = self._lethal_energy_gain(card)
                    hp_loss = self._lethal_energy_hp_loss(card)
                    if state.player_hp <= hp_loss:
                        continue

                    net_cost = cost - energy_gain
                    if net_cost >= 0:
                        continue
                    next_player_hp = state.player_hp - hp_loss

                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(0, 0, energy_gain - cost, -cost),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                net_cost,
                                player_hp=next_player_hp,
                            ),
                        )
                    )
                    continue

                if self._is_lethal_corruption_support_card(card):
                    if state.corruption_active:
                        continue

                    cost = effective_card_cost(card, state.energy)
                    if cost > state.energy:
                        continue

                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(0, 0, 0, -cost),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                corruption_active=True,
                            ),
                        )
                    )
                    continue

                if self._is_lethal_double_tap_support_card(card):
                    cost = self._lethal_card_cost(
                        card,
                        context,
                        state.energy,
                        state.corruption_active,
                    )
                    if cost > state.energy:
                        continue

                    next_double_tap_charges = (
                        state.double_tap_charges + self._lethal_double_tap_charges(card)
                    )
                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(0, 0, next_double_tap_charges, -cost),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                double_tap_charges=next_double_tap_charges,
                            ),
                        )
                    )
                    continue

                if self._is_lethal_vulnerable_support_card(card):
                    cost = self._lethal_card_cost(
                        card,
                        context,
                        state.energy,
                        state.corruption_active,
                    )
                    if cost > state.energy:
                        continue

                    next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                        card,
                        context,
                        state.vulnerable,
                        state.artifact,
                        state.hp,
                        None,
                    )
                    if next_vulnerable == state.vulnerable and next_artifact == state.artifact:
                        continue

                    vulnerable_gain = sum(next_vulnerable) - sum(state.vulnerable)
                    artifact_reduced = sum(state.artifact) - sum(next_artifact)
                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(0, 0, vulnerable_gain + artifact_reduced, -cost),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                vulnerable=next_vulnerable,
                                artifact=next_artifact,
                            ),
                        )
                    )
                    continue

                if self._is_aoe_attack(card):
                    cost = effective_card_cost(card, state.energy)
                    if cost > state.energy:
                        continue

                    attack_repeats = self._lethal_attack_repeats(
                        card,
                        state.double_tap_charges,
                    )
                    next_double_tap_charges = self._double_tap_charges_after_attack(
                        state.double_tap_charges
                    )
                    next_hp = tuple(state.hp)
                    next_vulnerable = state.vulnerable
                    next_artifact = state.artifact
                    total_damage = 0
                    for _repeat_idx in range(attack_repeats):
                        repeat_hp = list(next_hp)
                        repeat_damage = 0
                        for monster_idx, hp in enumerate(next_hp):
                            if hp <= 0:
                                continue

                            damage = self._card_damage_against_monster(
                                card,
                                context,
                                monster_idx,
                                state.energy,
                                target_vulnerable_stacks=next_vulnerable[monster_idx],
                                strength=state.strength,
                            )
                            if damage <= 0:
                                continue

                            repeat_damage += min(hp, damage)
                            repeat_hp[monster_idx] = max(0, hp - damage)

                        if repeat_damage <= 0:
                            break

                        total_damage += repeat_damage
                        next_hp = tuple(repeat_hp)
                        next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                            card,
                            context,
                            next_vulnerable,
                            next_artifact,
                            next_hp,
                            None,
                        )

                    if total_damage <= 0:
                        continue

                    kill_count = sum(
                        1
                        for before_hp, after_hp in zip(state.hp, next_hp)
                        if before_hp > 0 and after_hp <= 0
                    )
                    priority = (
                        kill_count,
                        0,
                        total_damage,
                        -cost,
                    )
                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=priority,
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                hp=next_hp,
                                vulnerable=next_vulnerable,
                                artifact=next_artifact,
                                double_tap_charges=next_double_tap_charges,
                            ),
                        )
                    )
                    continue

                if not getattr(card, 'has_target', False):
                    continue

                for monster_idx, hp in enumerate(state.hp):
                    if hp <= 0:
                        continue

                    attack_repeats = self._lethal_attack_repeats(
                        card,
                        state.double_tap_charges,
                    )
                    next_double_tap_charges = self._double_tap_charges_after_attack(
                        state.double_tap_charges
                    )
                    upfront_cost = effective_card_cost(card, state.energy)
                    if upfront_cost > state.energy:
                        continue

                    fiend_fire_exhaust_count = self._fiend_fire_exhaust_count_for_remaining_cards(
                        card,
                        context,
                        remaining_cards,
                        sequence_card_keys,
                    )
                    next_hp = list(state.hp)
                    next_vulnerable = state.vulnerable
                    next_artifact = state.artifact
                    total_damage = 0
                    total_energy_refund = 0
                    for _repeat_idx in range(attack_repeats):
                        current_hp = next_hp[monster_idx]
                        if current_hp <= 0:
                            break

                        total_energy_refund += self._card_energy_refund_against_monster(
                            card,
                            context,
                            monster_idx,
                            next_vulnerable[monster_idx],
                        )
                        damage = self._card_damage_against_monster(
                            card,
                            context,
                            monster_idx,
                            state.energy,
                            fiend_fire_exhaust_count,
                            next_vulnerable[monster_idx],
                            state.strength,
                        )
                        if damage <= 0:
                            continue

                        total_damage += min(current_hp, damage)
                        next_hp[monster_idx] = max(0, current_hp - damage)
                        next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                            card,
                            context,
                            next_vulnerable,
                            next_artifact,
                            tuple(next_hp),
                            monster_idx,
                        )

                    if total_damage <= 0:
                        continue

                    cost = upfront_cost - total_energy_refund
                    next_hp = tuple(next_hp)
                    refunds_energy = total_energy_refund > 0
                    priority = (
                        1 if next_hp[monster_idx] <= 0 else 0,
                        1 if refunds_energy else 0,
                        total_damage,
                        -cost,
                    )
                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=priority,
                            card_pos=card_pos,
                            monster_idx=monster_idx,
                            next_state=state.after_spending(
                                cost,
                                hp=next_hp,
                                vulnerable=next_vulnerable,
                                artifact=next_artifact,
                                double_tap_charges=next_double_tap_charges,
                            ),
                        )
                    )

            candidates.sort(key=lambda item: item.priority, reverse=True)

            for candidate in candidates:
                card = remaining_cards[candidate.card_pos]
                if self._base_card_name(card) == 'Fiend Fire':
                    next_cards = ()
                else:
                    next_cards = (
                        remaining_cards[:candidate.card_pos]
                        + remaining_cards[candidate.card_pos + 1:]
                    )
                tail = search(
                    next_cards,
                    candidate.next_state,
                )
                if tail is not None:
                    target_monster = (
                        None
                        if candidate.monster_idx is None
                        else context.monsters_alive[candidate.monster_idx]
                    )
                    return [
                        PlayCardAction(
                            card=card,
                            target_monster=target_monster,
                        )
                    ] + tail

            return None

        sequence = search(
            tuple(sequence_cards),
            starting_state,
        )
        return sequence or []

    def _fiend_fire_exhaust_count_for_remaining_cards(
        self,
        card: Card,
        context: DecisionContext,
        remaining_cards: Tuple[Card, ...],
        sequence_card_keys,
    ) -> Optional[int]:
        if self._base_card_name(card) != 'Fiend Fire':
            return None

        hand_cards = getattr(getattr(context, 'game', None), 'hand', None)
        if not hand_cards:
            hand_cards = getattr(context, 'playable_cards', []) or []

        remaining_card_keys = {
            self._card_play_key(remaining_card)
            for remaining_card in remaining_cards
        }
        played_card_key = self._card_play_key(card)
        count = 0
        for hand_card in hand_cards:
            hand_card_key = self._card_play_key(hand_card)
            if hand_card is card or hand_card_key == played_card_key:
                continue
            if (
                hand_card_key in sequence_card_keys
                and hand_card_key not in remaining_card_keys
            ):
                continue
            count += 1
        return max(0, count)

    def _find_aoe_cleanup_sequence(
        self,
        context: DecisionContext,
        attack_cards: List[Card],
        available_energy: int,
    ) -> List[PlayCardAction]:
        """Prove a lethal line where one AOE leaves single-target cleanup."""
        if len(context.monsters_alive) <= 1:
            return []

        aoe_cards = [card for card in attack_cards if self._is_aoe_attack(card)]
        aoe_cards.sort(key=lambda card: self._get_card_damage(card, context), reverse=True)
        sequence_card_keys = {self._card_play_key(card) for card in attack_cards}

        for aoe_card in aoe_cards:
            aoe_cost = effective_card_cost(aoe_card, available_energy)
            if aoe_cost > available_energy:
                continue

            survivors = []
            for monster_idx, monster in enumerate(context.monsters_alive):
                damage = self._card_damage_against_monster(
                    aoe_card,
                    context,
                    monster_idx,
                    available_energy,
                )
                hp_after_aoe = monster.current_hp + monster.block - damage
                if hp_after_aoe > 0:
                    survivors.append((hp_after_aoe, monster_idx, monster))

            if not survivors:
                return [PlayCardAction(card=aoe_card)]

            sequence = [PlayCardAction(card=aoe_card)]
            remaining_energy = available_energy - aoe_cost
            played_cards = {self._card_play_key(aoe_card)}
            survivors.sort(key=lambda item: item[0], reverse=True)

            for damage_needed, monster_idx, monster in survivors:
                while damage_needed > 0:
                    best_card = None
                    best_cost = 0
                    best_damage = 0
                    best_priority = None

                    for card in attack_cards:
                        card_key = self._card_play_key(card)
                        if card_key in played_cards or self._is_aoe_attack(card):
                            continue

                        cost = self._card_energy_cost_against_monster(
                            card,
                            context,
                            monster_idx,
                            remaining_energy,
                        )
                        if cost > remaining_energy:
                            continue

                        remaining_cards = tuple(
                            remaining_card
                            for remaining_card in attack_cards
                            if self._card_play_key(remaining_card) not in played_cards
                        )
                        fiend_fire_exhaust_count = self._fiend_fire_exhaust_count_for_remaining_cards(
                            card,
                            context,
                            remaining_cards,
                            sequence_card_keys,
                        )
                        damage = self._card_damage_against_monster(
                            card,
                            context,
                            monster_idx,
                            remaining_energy,
                            fiend_fire_exhaust_count,
                        )
                        refunds_energy = self._card_refunds_energy_against_monster(
                            card,
                            context,
                            monster_idx,
                        )
                        priority = (
                            1 if damage >= damage_needed else 0,
                            1 if refunds_energy else 0,
                            damage,
                            -cost,
                        )
                        if best_priority is None or priority > best_priority:
                            best_card = card
                            best_cost = cost
                            best_damage = damage
                            best_priority = priority

                    if best_card is None or best_damage <= 0:
                        sequence = []
                        break

                    sequence.append(self._play_card_action(best_card, monster))
                    if self._base_card_name(best_card) == 'Fiend Fire':
                        played_cards.update(sequence_card_keys)
                    else:
                        played_cards.add(self._card_play_key(best_card))
                    remaining_energy -= best_cost
                    damage_needed -= best_damage

                if damage_needed > 0:
                    break
            else:
                return sequence

        return []

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
                if len(context.monsters_alive) == 1:
                    cost = self._card_energy_cost_against_monster(
                        card,
                        context,
                        0,
                        context.energy_available,
                    )
                else:
                    cost = effective_card_cost(card, context.energy_available)
                damage = self._get_card_damage(
                    card,
                    context,
                    available_energy=context.energy_available,
                )
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
                elif self._is_aoe_attack(card):
                    damage = self._aoe_damage_potential(
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

        def greedy_total(candidates):
            selected_damage = 0
            selected_energy = 0
            selected_cards = []
            for card, cost, damage, _ in candidates:
                if selected_energy + cost <= context.energy_available:
                    selected_damage += damage
                    selected_energy += cost
                    selected_cards.append(card.name)
                elif cost == 0:
                    selected_damage += damage
                    selected_cards.append(card.name)
            return selected_damage, selected_energy, selected_cards

        # Sort by efficiency (highest first), then by damage (highest first)
        attack_cards.sort(key=lambda x: (x[3], x[2]), reverse=True)

        fiend_fire_cards = [
            item for item in attack_cards if self._base_card_name(item[0]) == 'Fiend Fire'
        ]
        if fiend_fire_cards:
            regular_damage, regular_energy, regular_selected = greedy_total(
                [item for item in attack_cards if self._base_card_name(item[0]) != 'Fiend Fire']
            )
            fiend_damage, fiend_energy, fiend_selected = greedy_total(fiend_fire_cards)
            if fiend_damage > regular_damage:
                total_damage = fiend_damage
                energy_used = fiend_energy
                selected = fiend_selected
            else:
                total_damage = regular_damage
                energy_used = regular_energy
                selected = regular_selected
        else:
            total_damage, energy_used, selected = greedy_total(attack_cards)

        logger.info(f"[LETHAL_CALC] Selected: {selected}, total_damage={total_damage}, energy_used={energy_used}/{context.energy_available}")
        return total_damage

    def _aoe_damage_potential(
        self,
        card: Card,
        context: DecisionContext,
        base_damage: int,
        available_energy: int,
    ) -> int:
        total = 0
        for monster_idx, _monster in enumerate(context.monsters_alive):
            damage = base_damage
            if context.vulnerable_stacks.get(monster_idx, 0) > 0:
                damage = self._apply_vulnerable_to_card_damage(
                    card,
                    context,
                    damage,
                    available_energy,
                )
            total += damage
        return total

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

        # Count attacks by targeting behavior
        attack_cards = []
        aoe_cards = []
        single_target_count = 0

        for card in context.playable_cards:
            if hasattr(card, 'type') and card.type == CardType.ATTACK:
                attack_cards.append(card)
                if self._is_aoe_attack(card):
                    aoe_cards.append(card)
                elif getattr(card, 'has_target', False):
                    single_target_count += 1

        for card in aoe_cards:
            cost = effective_card_cost(card, getattr(context, 'energy_available', 0))
            if cost <= getattr(context, 'energy_available', 0) and self._aoe_card_kills_all(
                card,
                context,
                getattr(context, 'energy_available', 0),
            ):
                return True

        if aoe_cards and self._find_aoe_cleanup_sequence(
            context,
            attack_cards,
            getattr(context, 'energy_available', 0),
        ):
            return True

        if aoe_cards and single_target_count == 0:
            return False

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

    def _get_card_damage(
        self,
        card: Card,
        context: DecisionContext,
        monster_idx: Optional[int] = None,
        available_energy: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
        strength_override: Optional[int] = None,
    ) -> int:
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

        if card_name == 'Body Slam':
            base_damage = self._get_player_block(context)

        if card_name == 'Whirlwind':
            energy = x_effect_energy(
                card,
                context.energy_available if available_energy is None else available_energy,
                context,
            )
            strength = getattr(context, 'strength', 0) if strength_override is None else strength_override
            return whirlwind_damage(card, energy, strength)

        if hasattr(card, 'type') and card.type == CardType.ATTACK:
            strength = getattr(context, 'strength', 0) if strength_override is None else strength_override
            upgrades = getattr(card, 'upgrades', 0)

            if card_name == 'Heavy Blade':
                multiplier = 5 if upgrades > 0 else 3
                base_damage += strength * multiplier
            elif card_name == 'Perfected Strike':
                per_strike_bonus = 3 if upgrades > 0 else 2
                base_damage += self._count_strike_cards(context) * per_strike_bonus + strength
            else:
                base_damage += strength

            base_damage *= self._get_attack_hit_count(
                card,
                context,
                monster_idx,
                available_energy,
                fiend_fire_exhaust_count,
            )

        return max(0, base_damage)

    def _apply_player_weak_to_card_damage(
        self,
        card: Card,
        context: DecisionContext,
        total_damage: int,
        available_energy: int,
        monster_idx: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
    ) -> int:
        """Apply player Weak using the game's per-hit rounding."""
        if self._get_player_debuff_stacks(context, 'Weak') <= 0:
            return total_damage

        hit_count = self._get_vulnerable_damage_instance_count(
            card,
            context,
            available_energy,
            monster_idx,
            fiend_fire_exhaust_count,
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
        monster_idx: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
    ) -> int:
        """Apply Vulnerable using the game's per-hit rounding."""
        hit_count = self._get_vulnerable_damage_instance_count(
            card,
            context,
            available_energy,
            monster_idx,
            fiend_fire_exhaust_count,
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
        monster_idx: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
    ) -> int:
        card_name = self._base_card_name(card)

        if card_name == 'Whirlwind':
            return max(1, x_effect_energy(card, available_energy, context))

        return self._get_attack_hit_count(
            card,
            context,
            monster_idx,
            available_energy,
            fiend_fire_exhaust_count,
        )

    def _get_player_debuff_stacks(self, context: DecisionContext, power_name: str) -> int:
        player = getattr(getattr(context, 'game', None), 'player', None)
        powers = getattr(player, 'powers', []) if player is not None else []
        for power in powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 1
        return 0

    def _get_player_block(self, context: DecisionContext) -> int:
        block = getattr(context, 'player_block', None)
        if block is None:
            player = getattr(getattr(context, 'game', None), 'player', None)
            block = getattr(player, 'block', 0)

        try:
            return max(0, int(block or 0))
        except (TypeError, ValueError):
            return 0

    def _all_alive_targets_poisoned(self, context: DecisionContext) -> bool:
        monsters = getattr(context, 'monsters_alive', []) or []
        alive_monsters = [
            monster for monster in monsters
            if getattr(monster, 'current_hp', 0) > 0
        ]
        if not alive_monsters:
            return False

        return all(
            self._get_monster_power_amount(monster, 'Poison') > 0
            for monster in alive_monsters
        )

    def _get_monster_power_amount(self, monster, power_name: str) -> int:
        direct_attr = power_name.lower()
        direct_amount = getattr(monster, direct_attr, None)
        if direct_amount is not None:
            try:
                return max(0, int(direct_amount))
            except (TypeError, ValueError):
                return 0

        powers = getattr(monster, 'powers', []) or []
        for power in powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 1

        return 0

    def _power_name(self, power):
        return (
            getattr(power, 'name', None)
            or getattr(power, 'power_name', None)
            or getattr(power, 'power_id', None)
        )

    def _get_attack_hit_count(
        self,
        card: Card,
        context: DecisionContext,
        monster_idx: Optional[int] = None,
        available_energy: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
    ) -> int:
        """Return known hit counts for repeated-hit attacks."""
        card_name = self._base_card_name(card)
        upgrades = getattr(card, 'upgrades', 0)

        if card_name == 'Twin Strike':
            return 2
        if card_name == 'Bane' and context is not None:
            if monster_idx is not None:
                return 2 if self._monster_poison_stacks(context, monster_idx) > 0 else 1
            return 2 if self._all_alive_targets_poisoned(context) else 1
        if card_name == 'Skewer':
            energy = (
                getattr(context, 'energy_available', 0)
                if available_energy is None
                else available_energy
            )
            return x_effect_energy(card, energy, context)
        if card_name == 'Sword Boomerang':
            return 4 if upgrades > 0 else 3
        if card_name == 'Pummel':
            return 5 if upgrades > 0 else 4
        if card_name == 'Fiend Fire':
            if fiend_fire_exhaust_count is not None:
                return fiend_fire_exhaust_count
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
