"""
Combat ending detection - can we kill all monsters this turn?

This module provides lethality detection to prevent over-defending when
combat could be ended this turn.
"""

import logging
import re
from dataclasses import dataclass, replace
from typing import List, Optional, Sequence, Tuple
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.spire.numeric import coerce_float, coerce_int
from spirecomm.communication.action import PlayCardAction
from spirecomm.ai.intent_utils import intent_is_attack
from spirecomm.data.loader import game_data_loader
from ..decision.base import DecisionContext
from .combat_state import (
    card_play_key,
    draw_pile_count,
    is_card_played,
    mark_card_played,
    monster_power_amount,
    player_block_value,
    player_debuff_stacks,
    player_has_power,
    player_hp_values,
    player_power_amount,
)
from .card_names import canonical_card_name
from .card_costs import (
    effective_card_cost,
    energy_refund_for_card,
    is_x_cost_card,
    playable_card_cost_after_refund,
    whirlwind_damage,
    x_effect_energy,
)
from .card_types import card_requires_target, card_type_name, is_attack_card
from .card_hits import (
    fiend_fire_exhaust_count as context_fiend_fire_exhaust_count,
    fixed_attack_hit_count,
    strike_card_count,
)
from .card_upgrades import (
    card_upgrade_count,
    heavy_blade_strength_multiplier,
    is_card_upgraded,
    known_block_upgrade_bonus,
    known_damage_upgrade_bonus,
    perfected_strike_bonus_per_strike,
)

logger = logging.getLogger(__name__)

TARGETED_LETHAL_MAX_CARDS = 8
TARGETED_LETHAL_MAX_MONSTERS = 4
AOE_ATTACK_NAMES = frozenset(['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper'])
PANACHE_DAMAGE = 10
PANACHE_RESET_COUNT = 5
LETTER_OPENER_DAMAGE = 5
CHARONS_ASHES_DAMAGE = 3
THE_BOOT_MINIMUM_DAMAGE = 5


@dataclass(frozen=True)
class _TargetedLethalState:
    hp: Tuple[int, ...]
    block: Tuple[int, ...]
    curl_up: Tuple[int, ...]
    malleable: Tuple[int, ...]
    vulnerable: Tuple[int, ...]
    artifact: Tuple[int, ...]
    flight: Tuple[int, ...]
    thorns: Tuple[int, ...]
    strength: int
    player_hp: int
    player_block: int
    corruption_active: bool
    duplication_charges: int
    double_tap_charges: int
    necronomicon_available: bool
    nunchaku_counter: Optional[int]
    panache_counter: int
    panache_damage: int
    letter_opener_counter: Optional[int]
    energy: int
    havoc_cards_consumed: int = 0

    def seen_key(self, remaining_card_keys: Tuple[object, ...]):
        return (
            remaining_card_keys,
            self.hp,
            self.block,
            self.curl_up,
            self.malleable,
            self.vulnerable,
            self.artifact,
            self.flight,
            self.thorns,
            self.strength,
            self.player_hp,
            self.player_block,
            self.corruption_active,
            self.duplication_charges,
            self.double_tap_charges,
            self.necronomicon_available,
            self.nunchaku_counter,
            self.panache_counter,
            self.panache_damage,
            self.letter_opener_counter,
            self.energy,
            self.havoc_cards_consumed,
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

    def __init__(self, data_loader=None):
        """Initialize the combat ending detector."""
        self.game_data_loader = data_loader or game_data_loader

    @staticmethod
    def _base_card_name(card: Card) -> str:
        return canonical_card_name(card)

    @staticmethod
    def _positive_card_misc(card: Card) -> int:
        try:
            return max(0, int(getattr(card, 'misc', 0) or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _monster_current_hp(monster: Monster) -> int:
        return max(
            0,
            CombatEndingDetector._safe_int(getattr(monster, 'current_hp', 0), default=0),
        )

    @staticmethod
    def _monster_hp_with_block(monster: Monster) -> int:
        return max(
            0,
            CombatEndingDetector._monster_current_hp(monster)
            + CombatEndingDetector._safe_int(getattr(monster, 'block', 0), default=0),
        )

    @staticmethod
    def _card_requires_target(card: Card) -> bool:
        return card_requires_target(card, AOE_ATTACK_NAMES)

    @staticmethod
    def _play_card_action(card: Card, target_monster: Optional[Monster] = None) -> PlayCardAction:
        if not CombatEndingDetector._card_requires_target(card):
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
            available_energy = max(
                0,
                self._safe_int(getattr(context, 'energy_available', 0), default=0),
            )

            if not context.monsters_alive:
                logger.info("[LETHAL_ENTRY] No monsters alive, returning True")
                return True

            logger.info(f"[LETHAL_ENTRY] {len(context.monsters_alive)} monsters, {len(context.playable_cards)} cards")

            # Step 1: Calculate affordable damage (respecting energy constraints)
            logger.info("[LETHAL_ENTRY] About to calculate affordable damage...")
            affordable_damage = self._calculate_affordable_damage(context)
            logger.info(f"[LETHAL_ENTRY] Affordable damage calculated: {affordable_damage}")

            # Step 2: Calculate total monster HP (including block)
            total_monster_hp = sum(
                self._monster_hp_with_block(monster)
                for monster in context.monsters_alive
            )

            # Log vulnerable-related intermediate values for verification
            vulnerable_targets = []
            for i, monster in enumerate(context.monsters_alive):
                stacks = self._monster_vulnerable_stacks(context, i)
                if stacks > 0:
                    vulnerable_targets.append(
                        f"idx={i}, stacks={stacks}, hp={monster.current_hp}, block={monster.block}"
                    )
            logger.info(
                "[LETHAL_VULNERABLE] targets=%s, multiplier=1.5/1.75",
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
            targeting_feasible = self._can_target_all_monsters(
                context,
                affordable_damage,
                available_energy,
            )

            # Low HP must not suppress a deterministic kill. The margin and
            # targeting checks already keep this detector conservative.
            player_hp = self._context_player_hp(context)
            player_hp_pct = self._context_player_hp_pct(context)
            low_hp = player_hp <= 30 and player_hp_pct <= 0.3

            # Log detection results
            logger.info(f"[LETHAL_DETECTION] affordable_damage={affordable_damage}, "
                       f"total_monster_hp={total_monster_hp}, margin_ok={has_damage_potential}, "
                       f"targeting_ok={targeting_feasible}, low_hp={low_hp}, "
                       f"player_hp={player_hp}, player_hp_pct={player_hp_pct:.2f}")

            attack_cards = [
                card for card in context.playable_cards
                if (
                    is_attack_card(card)
                    or self._havoc_top_attack_card(card, context) is not None
                    or self._havoc_top_exhaust_juggernaut_damage_potential(
                        card,
                        context,
                        available_energy,
                    ) > 0
                )
            ]
            proven_aoe_cleanup = bool(self._find_aoe_cleanup_sequence(
                context,
                attack_cards,
                available_energy,
            ))
            proven_targeted_sequence = bool(self._find_targeted_lethal_sequence(
                context,
                attack_cards,
                available_energy,
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
        remaining_energy = max(
            0,
            self._safe_int(getattr(context, 'energy_available', 0), default=0),
        )

        # Sort monsters by HP (kill weakest first)
        combined = list(zip(remaining_monsters, remaining_monster_indices))
        combined.sort(key=lambda pair: self._monster_hp_with_block(pair[0]))
        remaining_monsters = [m for m, _ in combined]
        remaining_monster_indices = [i for _, i in combined]

        # Get attack cards sorted by damage
        attack_cards = [c for c in context.playable_cards
                       if (
                           is_attack_card(c)
                           or self._havoc_top_attack_card(c, context) is not None
                           or self._havoc_top_exhaust_juggernaut_damage_potential(
                               c,
                               context,
                               remaining_energy,
                           ) > 0
                       )]
        attack_cards.sort(
            key=lambda c: self._get_card_damage(
                c,
                context,
                available_energy=remaining_energy,
            ),
            reverse=True,
        )

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
            damage_needed = self._monster_hp_with_block(monster)
            while damage_needed > 0:
                best_card = None
                best_cost = 0
                best_damage = 0
                best_priority = None

                for card in attack_cards:
                    if is_card_played(played_cards, card):
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
                        best_cost = cost
                        best_damage = damage
                        best_priority = priority

                if best_card is None:
                    break

                sequence.append(self._play_card_action(best_card, monster))
                mark_card_played(played_cards, best_card)
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
            logger.warning(f"[LETHAL_SEQUENCE] Debug: attacks={len(attack_cards)}, energy={remaining_energy}")

        return sequence

    def _is_aoe_attack(self, card: Card) -> bool:
        card_id = self._base_card_name(card)
        return card_id in AOE_ATTACK_NAMES

    def _is_all_enemy_debuff_card(self, card: Card) -> bool:
        if self._base_card_name(card) == 'Shockwave':
            return True
        if not any(
            debuff == 'vulnerable' and stacks > 0
            for debuff, stacks in self._card_debuff_effects_applied(card)
        ):
            return False

        try:
            return bool(
                self.game_data_loader._is_card_aoe(
                    {
                        'name': getattr(card, 'name', self._base_card_name(card)),
                        'description': self._card_effect_text(card),
                    }
                )
            )
        except Exception:
            effect_text = (
                self._card_effect_text(card)
                .replace('\\n', '\n')
                .replace('#', '')
                .lower()
            )
            return any(
                keyword in effect_text
                for keyword in ('all enemies', 'every enemy', 'each enemy')
            )

    def _aoe_card_kills_all(
        self,
        card: Card,
        context: DecisionContext,
        available_energy: int,
    ) -> bool:
        for monster_idx, monster in enumerate(context.monsters_alive):
            damage = self._card_damage_against_monster(
                card,
                context,
                monster_idx,
                available_energy,
            )
            if damage < self._monster_hp_with_block(monster):
                return False
        return True

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
            if (
                self._is_aoe_attack(card)
                or self._card_requires_target(card)
                or self._havoc_top_attack_card(card, context) is not None
                or self._havoc_top_exhaust_juggernaut_ready(card, context)
            )
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
            not self._is_aoe_attack(card) and not self._card_requires_target(card)
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
        base_damage_bonus: int = 0,
    ) -> int:
        damage = self._get_card_damage(
            card,
            context,
            monster_idx,
            available_energy,
            fiend_fire_exhaust_count,
            strength,
            base_damage_bonus,
        )
        damage_before_weak = damage
        vulnerable_stacks = (
            self._monster_vulnerable_stacks(context, monster_idx)
            if target_vulnerable_stacks is None
            else target_vulnerable_stacks
        )
        player_weak = self._player_is_weak(context)
        if vulnerable_stacks > 0 and player_weak:
            damage = self._apply_weak_and_vulnerable_to_card_damage(
                card,
                context,
                damage_before_weak,
                available_energy,
                monster_idx,
                fiend_fire_exhaust_count,
            )
        else:
            damage = self._apply_player_weak_to_card_damage(
                card,
                context,
                damage,
                available_energy,
                monster_idx,
                fiend_fire_exhaust_count,
            )
        if vulnerable_stacks > 0 and not player_weak:
            damage = self._apply_vulnerable_to_card_damage(
                card,
                context,
                damage,
                available_energy,
                monster_idx,
                fiend_fire_exhaust_count,
            )
        damage = self._apply_the_boot_minimum_attack_damage(
            context,
            damage,
            self._get_vulnerable_damage_instance_count(
                card,
                context,
                available_energy,
                monster_idx,
                fiend_fire_exhaust_count,
            ),
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
        stacks = self._safe_int(vulnerable_stacks.get(monster_idx, 0), default=0)
        if stacks > 0:
            return stacks

        monsters = getattr(context, 'monsters_alive', []) or []
        if 0 <= monster_idx < len(monsters):
            return self._safe_int(
                self._get_monster_power_amount(monsters[monster_idx], 'Vulnerable'),
                default=0,
            )
        return 0

    def _monster_thorns_stacks(self, context: DecisionContext, monster_idx: int) -> int:
        thorns_stacks = getattr(context, 'thorns_stacks', {}) or {}
        stacks = self._safe_int(thorns_stacks.get(monster_idx, 0), default=0)
        if stacks > 0:
            return stacks

        monsters = getattr(context, 'monsters_alive', []) or []
        if 0 <= monster_idx < len(monsters):
            return max(
                0,
                self._safe_int(
                    self._get_monster_power_amount(monsters[monster_idx], 'Thorns'),
                    default=0,
                ),
            )
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

        upgraded = is_card_upgraded(card)
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
            wiki_data = getattr(self.game_data_loader, '_wiki_data', None)
            if wiki_data is None and hasattr(self.game_data_loader, '_load_wiki_data'):
                self.game_data_loader._load_wiki_data()
                wiki_data = getattr(self.game_data_loader, '_wiki_data', None)
            if wiki_data:
                wiki_entry = wiki_data.get(card_name.lower())
                if wiki_entry and wiki_entry.get('text'):
                    return str(wiki_entry['text'])
        except Exception:
            pass

        card_data = self.game_data_loader.get_card_data(card_name) or {}
        for key in ('description', 'text'):
            value = card_data.get(key)
            if value:
                return str(value)

        return ''

    def _draw_pile_top_card_for_havoc(
        self,
        context: DecisionContext,
        consumed: int = 0,
    ) -> Optional[Card]:
        game = getattr(context, 'game', None)
        for owner in (game, context):
            draw_pile = getattr(owner, 'draw_pile', None)
            if isinstance(draw_pile, list) and draw_pile:
                skipped = 0
                for top_card in reversed(draw_pile):
                    if not isinstance(top_card, Card):
                        continue
                    if skipped < consumed:
                        skipped += 1
                        continue
                    return top_card
        return None

    def _havoc_top_attack_card(
        self,
        card: Card,
        context: DecisionContext,
        consumed: int = 0,
    ) -> Optional[Card]:
        if self._base_card_name(card) != 'Havoc':
            return None
        if self._player_is_entangled(context):
            return None

        top_card = self._draw_pile_top_card_for_havoc(context, consumed)
        if top_card is None or not is_attack_card(top_card):
            return None
        return top_card

    def _havoc_top_energy_support_card(
        self,
        card: Card,
        context: DecisionContext,
        consumed: int = 0,
    ) -> Optional[Card]:
        if self._base_card_name(card) != 'Havoc':
            return None

        top_card = self._draw_pile_top_card_for_havoc(context, consumed)
        if top_card is None or not self._is_lethal_energy_support_card(top_card):
            return None
        return top_card

    def _havoc_top_attack_damage_potential(
        self,
        havoc_card: Card,
        context: DecisionContext,
        available_energy: int,
    ) -> int:
        top_attack = self._havoc_top_attack_card(havoc_card, context)
        if top_attack is None:
            return 0

        havoc_cost = self._lethal_card_cost(havoc_card, context, available_energy)
        if havoc_cost > available_energy:
            return 0

        monsters = getattr(context, 'monsters_alive', []) or []
        if not monsters:
            return 0

        havoc_top_card_energy = self._havoc_top_attack_effect_energy(
            top_attack,
            available_energy - havoc_cost,
        )
        if self._is_aoe_attack(top_attack):
            damage = self._get_card_damage(
                top_attack,
                context,
                available_energy=havoc_top_card_energy,
            )
            return self._aoe_damage_potential(
                top_attack,
                context,
                damage,
                havoc_top_card_energy,
            )

        if len(monsters) == 1:
            return self._card_damage_against_monster(
                top_attack,
                context,
                0,
                havoc_top_card_energy,
            )

        return 0

    def _havoc_top_attack_effect_energy(
        self,
        top_attack: Card,
        remaining_energy: int,
    ) -> int:
        if not is_x_cost_card(top_attack):
            return 0
        return max(0, self._safe_int(remaining_energy, default=0))

    def _player_feel_no_pain_block_per_exhaust(self, context: DecisionContext) -> int:
        block = max(0, self._get_player_debuff_stacks(context, 'Feel No Pain'))
        if block <= 0 and player_has_power(context, 'Feel No Pain'):
            return 3
        return block

    def _havoc_top_exhaust_juggernaut_ready(
        self,
        havoc_card: Card,
        context: DecisionContext,
        consumed: int = 0,
    ) -> bool:
        if self._base_card_name(havoc_card) != 'Havoc':
            return False
        if self._draw_pile_top_card_for_havoc(context, consumed) is None:
            return False
        return (
            self._player_feel_no_pain_block_per_exhaust(context) > 0
            and self._player_juggernaut_damage(context) > 0
        )

    def _apply_havoc_top_exhaust_juggernaut_damage(
        self,
        havoc_card: Card,
        context: DecisionContext,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        consumed: int = 0,
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
        if not self._havoc_top_exhaust_juggernaut_ready(
            havoc_card,
            context,
            consumed,
        ):
            return hp_state, block_state, 0

        target_idx = self._single_alive_monster_index(hp_state)
        if target_idx is None:
            return hp_state, block_state, 0

        return self._apply_lethal_direct_damage_to_target(
            hp_state,
            block_state,
            target_idx,
            self._player_juggernaut_damage(context),
        )

    def _havoc_top_exhaust_juggernaut_damage_potential(
        self,
        havoc_card: Card,
        context: DecisionContext,
        available_energy: int,
    ) -> int:
        if self._lethal_card_cost(havoc_card, context, available_energy) > available_energy:
            return 0

        hp_state = tuple(
            self._monster_current_hp(monster)
            for monster in getattr(context, 'monsters_alive', []) or []
        )
        block_state = tuple(
            max(0, self._safe_int(getattr(monster, 'block', 0), default=0))
            for monster in getattr(context, 'monsters_alive', []) or []
        )
        _next_hp, _next_block, damage = self._apply_havoc_top_exhaust_juggernaut_damage(
            havoc_card,
            context,
            hp_state,
            block_state,
        )
        return damage

    def _is_lethal_strength_support_card(self, card: Card) -> bool:
        card_name = self._base_card_name(card)
        card_type = card_type_name(card)
        if card_type == 'SKILL':
            return card_name in {'Flex', 'Limit Break', 'Spot Weakness'}
        if card_type == 'POWER':
            return card_name == 'Inflame'
        return False

    def _strength_after_lethal_support_card(self, card: Card, strength: int) -> int:
        if self._base_card_name(card) == 'Flex':
            return strength + (4 if is_card_upgraded(card) else 2)
        if self._base_card_name(card) == 'Limit Break':
            return strength * 2
        if self._base_card_name(card) == 'Spot Weakness':
            return strength + (4 if is_card_upgraded(card) else 3)
        if self._base_card_name(card) == 'Inflame':
            return strength + (3 if is_card_upgraded(card) else 2)
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

    @staticmethod
    def _single_alive_monster_index(hp_state: Tuple[int, ...]) -> Optional[int]:
        alive_indices = [
            monster_idx
            for monster_idx, hp in enumerate(hp_state)
            if hp > 0
        ]
        if len(alive_indices) != 1:
            return None
        return alive_indices[0]

    def _player_juggernaut_damage(self, context: DecisionContext) -> int:
        damage = max(0, self._get_player_debuff_stacks(context, 'Juggernaut'))
        if damage <= 1 and player_has_power(context, 'Juggernaut'):
            return 5
        return damage

    def _player_blocks_card_block(self, context: DecisionContext) -> bool:
        return any(
            self._get_player_debuff_stacks(context, power_name) > 0
            for power_name in ('No Block', 'NoBlock', 'NoBlockPower')
        )

    def _card_block_gain(self, card: Card, context: DecisionContext) -> int:
        card_name = self._base_card_name(card)
        if card_name == 'Entrench':
            return max(0, player_block_value(context))

        if self._player_blocks_card_block(context):
            return 0

        block_gain = max(0, self._safe_int(getattr(card, 'block', 0), default=0))
        if block_gain <= 0:
            card_data = self.game_data_loader.get_card_data(card_name) or {}
            if card_data:
                block_data = dict(card_data)
                upgrades = card_upgrade_count(card)
                block_data['name'] = f"{card_name}+" if upgrades > 0 else card_name
                parsed_block = self.game_data_loader._parse_card_block(block_data)
                block_gain = max(0, self._safe_int(parsed_block, default=0))
                if block_gain > 0 and upgrades > 0:
                    base_data = dict(card_data)
                    base_data['name'] = card_name
                    unupgraded_block = self.game_data_loader._parse_card_block(base_data)
                    if unupgraded_block is not None and block_gain == unupgraded_block:
                        block_gain += known_block_upgrade_bonus(card, card_name)

        if block_gain <= 0:
            return 0

        dexterity = self._get_player_debuff_stacks(context, 'Dexterity')
        block_gain = max(0, block_gain + dexterity)
        if self._get_player_debuff_stacks(context, 'Frail') > 0:
            block_gain = int(block_gain * 0.75)
        return max(0, block_gain)

    def _juggernaut_damage_for_block_card(
        self,
        card: Card,
        context: DecisionContext,
        hp_state: Tuple[int, ...],
    ) -> int:
        if self._single_alive_monster_index(hp_state) is None:
            return 0
        if not self._is_juggernaut_block_card(card, context):
            return 0
        return self._player_juggernaut_damage(context)

    def _is_juggernaut_block_card(
        self,
        card: Card,
        context: DecisionContext,
    ) -> bool:
        return (
            self._player_juggernaut_damage(context) > 0
            and self._card_block_gain(card, context) > 0
        )

    def _is_lethal_energy_support_card(self, card: Card) -> bool:
        if card_type_name(card) != 'SKILL':
            return False
        return self._base_card_name(card) in {'Bloodletting', 'Offering', 'Seeing Red'}

    def _lethal_energy_gain(self, card: Card) -> int:
        card_name = self._base_card_name(card)
        if card_name == 'Bloodletting':
            return 3 if is_card_upgraded(card) else 2
        if card_name in {'Offering', 'Seeing Red'}:
            return 2
        return 0

    def _is_lethal_hand_exhaust_energy_support_card(
        self,
        card: Card,
        context: DecisionContext,
    ) -> bool:
        if is_attack_card(card):
            return False
        if self._base_card_name(card) != 'Second Wind':
            return False

        cards = list(getattr(context, 'playable_cards', []) or [])
        card_pos = self._card_position_in_sequence(card, cards)
        if card_pos is None:
            return False
        return self._lethal_hand_exhaust_sentinel_energy_gain(card_pos, card, cards) > 0

    def _is_lethal_hand_exhaust_energy_resource_card(
        self,
        card: Card,
        context: DecisionContext,
    ) -> bool:
        if self._base_card_name(card) != 'Sentinel':
            return False

        cards = list(getattr(context, 'playable_cards', []) or [])
        for index, candidate in enumerate(cards):
            if candidate is card:
                continue
            if card in self._lethal_hand_exhausted_cards(index, candidate, cards):
                return True
        return False

    @staticmethod
    def _card_position_in_sequence(
        card: Card,
        cards: Sequence[Card],
    ) -> Optional[int]:
        for index, candidate in enumerate(cards):
            if candidate is card:
                return index
        return None

    def _lethal_hand_exhaust_sentinel_energy_gain(
        self,
        card_pos: int,
        card: Card,
        remaining_cards: Sequence[Card],
    ) -> int:
        energy_gain = 0
        for exhausted_card in self._lethal_hand_exhausted_cards(
            card_pos,
            card,
            remaining_cards,
        ):
            if self._base_card_name(exhausted_card) != 'Sentinel':
                continue
            energy_gain += 3 if is_card_upgraded(exhausted_card) else 2
        return energy_gain

    def _lethal_hand_exhausted_cards(
        self,
        card_pos: int,
        card: Card,
        remaining_cards: Sequence[Card],
    ) -> Tuple[Card, ...]:
        card_name = self._base_card_name(card)
        if card_name not in {'Fiend Fire', 'Second Wind', 'Sever Soul'}:
            return ()

        exhausted_cards = []
        for index, candidate in enumerate(remaining_cards):
            if index == card_pos:
                continue
            if card_name == 'Fiend Fire' or not is_attack_card(candidate):
                exhausted_cards.append(candidate)
        return tuple(exhausted_cards)

    def _remaining_cards_after_lethal_play(
        self,
        card_pos: int,
        card: Card,
        remaining_cards: Tuple[Card, ...],
    ) -> Tuple[Card, ...]:
        if self._base_card_name(card) == 'Fiend Fire':
            return ()

        exhausted_cards = self._lethal_hand_exhausted_cards(
            card_pos,
            card,
            remaining_cards,
        )
        exhausted_ids = {id(exhausted_card) for exhausted_card in exhausted_cards}
        return tuple(
            candidate
            for index, candidate in enumerate(remaining_cards)
            if index != card_pos and id(candidate) not in exhausted_ids
        )

    def _hand_exhaust_energy_lethal_candidate(
        self,
        card_pos: int,
        card: Card,
        remaining_cards: Tuple[Card, ...],
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        if is_attack_card(card):
            return None
        if self._base_card_name(card) != 'Second Wind':
            return None

        cost = self._lethal_card_cost(
            card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        energy_gain = self._lethal_hand_exhaust_sentinel_energy_gain(
            card_pos,
            card,
            remaining_cards,
        )
        if energy_gain <= cost:
            return None

        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        net_cost = cost - energy_gain
        return _TargetedLethalCandidate(
            priority=(0, 1, energy_gain - cost, -cost),
            card_pos=card_pos,
            monster_idx=None,
            next_state=state.after_spending(
                net_cost,
                duplication_charges=next_duplication_charges,
            ),
        )

    def _lethal_energy_hp_loss(self, card: Card) -> int:
        card_name = self._base_card_name(card)
        if card_name == 'Bloodletting':
            return 3
        if card_name == 'Offering':
            return 6
        return 0

    def _effective_player_hp_loss(self, context: DecisionContext, amount: int) -> int:
        hp_loss = max(0, self._safe_int(amount, default=0))
        if hp_loss > 0 and self._context_has_relic(context, 'Tungsten Rod'):
            hp_loss = max(0, hp_loss - 1)
        return hp_loss

    def _apply_lethal_player_damage(
        self,
        context: DecisionContext,
        player_hp: int,
        player_block: int,
        amount: int,
    ) -> Tuple[int, int, int]:
        damage = max(0, self._safe_int(amount, default=0))
        block = max(0, self._safe_int(player_block, default=0))
        blocked = min(block, damage)
        remaining = damage - blocked
        next_block = block - blocked
        hp_loss = self._effective_player_hp_loss(context, remaining)
        next_hp = max(0, self._safe_int(player_hp, default=0) - hp_loss)
        return next_hp, next_block, hp_loss

    def _lethal_energy_hp_loss_for_repeats(
        self,
        card: Card,
        context: DecisionContext,
        repeats: int,
    ) -> int:
        per_play_loss = self._effective_player_hp_loss(
            context,
            self._lethal_energy_hp_loss(card),
        )
        return per_play_loss * max(1, repeats)

    def _context_player_hp(self, context: DecisionContext) -> int:
        hp, _ = player_hp_values(context)
        return hp

    def _context_player_block(self, context: DecisionContext) -> int:
        return max(0, self._safe_int(player_block_value(context), default=0))

    def _context_player_hp_pct(self, context: DecisionContext) -> float:
        hp, max_hp = player_hp_values(context)
        return max(0.0, hp / max_hp) if max_hp > 0 else 0.0

    def _context_corruption_active(self, context: DecisionContext) -> bool:
        return (
            self._get_player_debuff_stacks(context, 'Corruption') > 0
            or player_has_power(context, 'Corruption')
        )

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
            card_type_name(card) == 'SKILL'
            and corruption_active
        ):
            return 0
        return effective_card_cost(card, available_energy)

    def _is_lethal_corruption_support_card(self, card: Card) -> bool:
        if card_type_name(card) != 'POWER':
            return False
        return self._base_card_name(card) == 'Corruption'

    def _context_double_tap_charges(self, context: DecisionContext) -> int:
        try:
            return max(0, int(self._get_player_debuff_stacks(context, 'Double Tap') or 0))
        except (TypeError, ValueError):
            return 0

    def _context_duplication_charges(self, context: DecisionContext) -> int:
        try:
            return max(
                0,
                player_power_amount(context, 'DuplicationPower'),
                player_power_amount(context, 'Duplication'),
            )
        except (TypeError, ValueError):
            return 0

    def _context_panache_counter(self, context: DecisionContext) -> int:
        try:
            counter = max(0, player_power_amount(context, 'Panache'))
        except (TypeError, ValueError):
            counter = 0
        if counter > 0:
            return counter
        return PANACHE_RESET_COUNT if player_has_power(context, 'Panache') else 0

    def _context_panache_damage(self, context: DecisionContext) -> int:
        return PANACHE_DAMAGE if self._context_panache_counter(context) > 0 else 0

    def _context_letter_opener_counter(
        self,
        context: DecisionContext,
    ) -> Optional[int]:
        counter = self._context_relic_counter(context, 'Letter Opener')
        if counter is None:
            return None
        return max(0, self._safe_int(counter, default=0))

    @staticmethod
    def _lethal_card_play_repeats(duplication_charges: int) -> int:
        return 2 if duplication_charges > 0 else 1

    @staticmethod
    def _duplication_charges_after_card(duplication_charges: int) -> int:
        return max(0, duplication_charges - 1)

    def _is_lethal_double_tap_support_card(self, card: Card) -> bool:
        if card_type_name(card) != 'SKILL':
            return False
        return self._base_card_name(card) == 'Double Tap'

    def _lethal_double_tap_charges(self, card: Card) -> int:
        return 2 if is_card_upgraded(card) else 1

    def _lethal_attack_repeats(self, card: Card, double_tap_charges: int) -> int:
        if double_tap_charges <= 0:
            return 1
        if self._base_card_name(card) == 'Fiend Fire':
            return 1
        return 2

    def _double_tap_charges_after_attack(self, double_tap_charges: int) -> int:
        return max(0, double_tap_charges - 1)

    def _lethal_necronomicon_replays_attack(
        self,
        card: Card,
        card_cost: int,
        necronomicon_available: bool,
    ) -> bool:
        return (
            necronomicon_available
            and is_attack_card(card)
            and card_cost >= 2
        )

    def _rampage_scaling_per_play(self, card: Card) -> int:
        if self._base_card_name(card) != 'Rampage':
            return 0
        return 8 if is_card_upgraded(card) else 5

    @staticmethod
    def _damage_instances(total_damage: int, hit_count: int) -> List[int]:
        total_damage = max(0, int(total_damage))
        hit_count = max(1, int(hit_count or 1))
        if hit_count <= 1:
            return [total_damage]

        per_hit, remainder = divmod(total_damage, hit_count)
        instances = [per_hit] * hit_count
        if remainder:
            instances[-1] += remainder
        return instances

    def _apply_lethal_attack_damage_to_target(
        self,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        curl_up_state: Tuple[int, ...],
        malleable_state: Tuple[int, ...],
        flight_state: Tuple[int, ...],
        monster_idx: int,
        total_damage: int,
        hit_count: int,
        apply_the_boot: bool = False,
    ) -> Tuple[
        Tuple[int, ...],
        Tuple[int, ...],
        Tuple[int, ...],
        Tuple[int, ...],
        Tuple[int, ...],
        int,
    ]:
        next_hp = list(hp_state)
        next_block = list(block_state)
        next_curl_up = list(curl_up_state)
        next_malleable = list(malleable_state)
        next_flight = list(flight_state)
        if monster_idx < 0 or monster_idx >= len(next_hp):
            return hp_state, block_state, curl_up_state, malleable_state, flight_state, 0

        damage_progress = 0
        deferred_curl_up_block = 0
        deferred_malleable_block = 0
        curl_up_amount = max(0, next_curl_up[monster_idx])
        malleable_amount = max(0, next_malleable[monster_idx])
        flight_amount = max(0, next_flight[monster_idx])
        flight_hit_pending = False

        for damage_instance in self._damage_instances(total_damage, hit_count):
            if next_hp[monster_idx] <= 0:
                break

            remaining_damage = max(0, damage_instance)
            if remaining_damage <= 0:
                continue

            if flight_amount > 0:
                remaining_damage //= 2

            block_before = max(0, next_block[monster_idx])
            if block_before > 0:
                blocked = min(block_before, remaining_damage)
                next_block[monster_idx] = block_before - blocked
                remaining_damage -= blocked
                damage_progress += blocked

            if apply_the_boot and 0 < remaining_damage < THE_BOOT_MINIMUM_DAMAGE:
                remaining_damage = THE_BOOT_MINIMUM_DAMAGE

            hp_before = max(0, next_hp[monster_idx])
            next_hp[monster_idx] = max(0, hp_before - remaining_damage)
            hp_loss = max(0, hp_before - next_hp[monster_idx])
            damage_progress += hp_loss

            if next_hp[monster_idx] <= 0:
                next_block[monster_idx] = 0
                break

            if hp_loss > 0 and curl_up_amount > 0:
                deferred_curl_up_block += curl_up_amount
                curl_up_amount = 0

            if hp_loss > 0 and malleable_amount > 0:
                deferred_malleable_block += malleable_amount
                malleable_amount += 1

            if hp_loss > 0:
                flight_hit_pending = True

        next_curl_up[monster_idx] = curl_up_amount
        next_malleable[monster_idx] = malleable_amount
        if flight_hit_pending and next_hp[monster_idx] > 0 and flight_amount > 0:
            flight_amount = max(0, flight_amount - 1)
        next_flight[monster_idx] = flight_amount
        if (
            (deferred_curl_up_block > 0 or deferred_malleable_block > 0)
            and next_hp[monster_idx] > 0
        ):
            next_block[monster_idx] = (
                max(0, next_block[monster_idx])
                + deferred_curl_up_block
                + deferred_malleable_block
            )

        return (
            tuple(next_hp),
            tuple(max(0, block) for block in next_block),
            tuple(max(0, amount) for amount in next_curl_up),
            tuple(max(0, amount) for amount in next_malleable),
            tuple(max(0, amount) for amount in next_flight),
            damage_progress,
        )

    def _apply_lethal_direct_damage_to_target(
        self,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        monster_idx: int,
        damage: int,
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
        next_hp = list(hp_state)
        next_block = list(block_state)
        if monster_idx < 0 or monster_idx >= len(next_hp):
            return hp_state, block_state, 0

        remaining_damage = max(0, int(damage))
        if remaining_damage <= 0 or next_hp[monster_idx] <= 0:
            return hp_state, block_state, 0

        damage_progress = 0
        block_before = max(0, next_block[monster_idx])
        if block_before > 0:
            blocked = min(block_before, remaining_damage)
            next_block[monster_idx] = block_before - blocked
            remaining_damage -= blocked
            damage_progress += blocked

        hp_before = max(0, next_hp[monster_idx])
        next_hp[monster_idx] = max(0, hp_before - remaining_damage)
        hp_loss = max(0, hp_before - next_hp[monster_idx])
        damage_progress += hp_loss
        if next_hp[monster_idx] <= 0:
            next_block[monster_idx] = 0

        return (
            tuple(next_hp),
            tuple(max(0, block) for block in next_block),
            damage_progress,
        )

    def _apply_lethal_panache_card_play(
        self,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        panache_counter: int,
        panache_damage: int,
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], int, int]:
        counter = max(0, self._safe_int(panache_counter, default=0))
        damage = max(0, self._safe_int(panache_damage, default=0))
        if counter <= 0 or damage <= 0:
            return hp_state, block_state, counter, 0

        if counter > 1:
            return hp_state, block_state, counter - 1, 0

        next_hp = tuple(hp_state)
        next_block = tuple(block_state)
        damage_progress = 0
        for monster_idx, hp in enumerate(next_hp):
            if hp <= 0:
                continue
            next_hp, next_block, dealt = self._apply_lethal_direct_damage_to_target(
                next_hp,
                next_block,
                monster_idx,
                damage,
            )
            damage_progress += dealt
        return next_hp, next_block, PANACHE_RESET_COUNT, damage_progress

    def _apply_lethal_panache_card_plays(
        self,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        panache_counter: int,
        panache_damage: int,
        repeats: int,
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], int, int]:
        next_hp = tuple(hp_state)
        next_block = tuple(block_state)
        next_counter = max(0, self._safe_int(panache_counter, default=0))
        total_damage = 0
        for _ in range(max(1, repeats)):
            next_hp, next_block, next_counter, damage = (
                self._apply_lethal_panache_card_play(
                    next_hp,
                    next_block,
                    next_counter,
                    panache_damage,
                )
            )
            total_damage += damage
        return next_hp, next_block, next_counter, total_damage

    def _apply_lethal_letter_opener_skill_play(
        self,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        letter_opener_counter: Optional[int],
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], Optional[int], int]:
        if letter_opener_counter is None:
            return hp_state, block_state, None, 0

        counter = max(0, self._safe_int(letter_opener_counter, default=0))
        if counter < 2:
            return hp_state, block_state, counter + 1, 0

        next_hp = tuple(hp_state)
        next_block = tuple(block_state)
        damage_progress = 0
        for monster_idx, hp in enumerate(next_hp):
            if hp <= 0:
                continue
            next_hp, next_block, dealt = self._apply_lethal_direct_damage_to_target(
                next_hp,
                next_block,
                monster_idx,
                LETTER_OPENER_DAMAGE,
            )
            damage_progress += dealt
        return next_hp, next_block, 0, damage_progress

    def _apply_lethal_letter_opener_skill_plays(
        self,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        letter_opener_counter: Optional[int],
        repeats: int,
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], Optional[int], int]:
        next_hp = tuple(hp_state)
        next_block = tuple(block_state)
        next_counter = letter_opener_counter
        total_damage = 0
        for _ in range(max(1, repeats)):
            next_hp, next_block, next_counter, damage = (
                self._apply_lethal_letter_opener_skill_play(
                    next_hp,
                    next_block,
                    next_counter,
                )
            )
            total_damage += damage
        return next_hp, next_block, next_counter, total_damage

    def _apply_lethal_juggernaut_block_damage(
        self,
        card: Card,
        context: DecisionContext,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
        target_idx = self._single_alive_monster_index(hp_state)
        if target_idx is None:
            return hp_state, block_state, 0

        damage = self._juggernaut_damage_for_block_card(card, context, hp_state)
        if damage <= 0:
            return hp_state, block_state, 0

        return self._apply_lethal_direct_damage_to_target(
            hp_state,
            block_state,
            target_idx,
            damage,
        )

    def _player_charons_ashes_damage_per_exhaust(self, context: DecisionContext) -> int:
        return (
            CHARONS_ASHES_DAMAGE
            if self._context_has_relic(context, "Charon's Ashes")
            else 0
        )

    def _charons_ashes_card_exhaust_events(
        self,
        card_pos: int,
        card: Card,
        remaining_cards: Sequence[Card],
        context: DecisionContext,
        corruption_active: bool,
    ) -> int:
        if self._player_charons_ashes_damage_per_exhaust(context) <= 0:
            return 0

        exhaust_events = len(
            self._lethal_hand_exhausted_cards(
                card_pos,
                card,
                remaining_cards,
            )
        )
        if card_type_name(card) == 'SKILL' and corruption_active:
            exhaust_events += 1
        return max(0, exhaust_events)

    def _apply_lethal_charons_ashes_damage(
        self,
        context: DecisionContext,
        hp_state: Tuple[int, ...],
        block_state: Tuple[int, ...],
        exhaust_events: int,
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
        damage = self._player_charons_ashes_damage_per_exhaust(context)
        if damage <= 0 or exhaust_events <= 0:
            return hp_state, block_state, 0

        next_hp = tuple(hp_state)
        next_block = tuple(block_state)
        total_damage = 0
        for _ in range(exhaust_events):
            for monster_idx, hp in enumerate(next_hp):
                if hp <= 0:
                    continue
                next_hp, next_block, damage_progress = (
                    self._apply_lethal_direct_damage_to_target(
                        next_hp,
                        next_block,
                        monster_idx,
                        damage,
                    )
                )
                total_damage += damage_progress
        return next_hp, next_block, total_damage

    def _is_lethal_charons_ashes_support_card(
        self,
        card: Card,
        context: DecisionContext,
    ) -> bool:
        if is_attack_card(card):
            return False
        if self._player_charons_ashes_damage_per_exhaust(context) <= 0:
            return False
        return (
            card_type_name(card) == 'SKILL'
            or self._base_card_name(card) in {'Second Wind', 'Sever Soul'}
        )

    def _charons_ashes_damage_potential(
        self,
        card: Card,
        context: DecisionContext,
        available_energy: int,
    ) -> int:
        if not self._is_lethal_charons_ashes_support_card(card, context):
            return 0

        cost = self._lethal_card_cost(
            card,
            context,
            available_energy,
            self._context_corruption_active(context),
        )
        if cost > available_energy:
            return 0

        cards = tuple(getattr(context, 'playable_cards', []) or [])
        card_pos = self._card_position_in_sequence(card, cards)
        if card_pos is None:
            return 0

        exhaust_events = self._charons_ashes_card_exhaust_events(
            card_pos,
            card,
            cards,
            context,
            self._context_corruption_active(context),
        )
        hp_state = tuple(
            self._monster_current_hp(monster)
            for monster in getattr(context, 'monsters_alive', []) or []
        )
        block_state = tuple(
            max(0, self._safe_int(getattr(monster, 'block', 0), default=0))
            for monster in getattr(context, 'monsters_alive', []) or []
        )
        _next_hp, _next_block, damage = self._apply_lethal_charons_ashes_damage(
            context,
            hp_state,
            block_state,
            exhaust_events,
        )
        return damage

    def _is_lethal_vulnerable_support_card(self, card: Card) -> bool:
        if card_type_name(card) != 'SKILL':
            return False
        return any(
            debuff == 'vulnerable' and stacks > 0
            for debuff, stacks in self._card_debuff_effects_applied(card)
        )

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
            if (
                self._is_aoe_attack(card)
                or self._card_requires_target(card)
                or self._havoc_top_attack_card(card, context) is not None
                or self._havoc_top_exhaust_juggernaut_ready(card, context)
            )
        ]
        support_cards = [
            card
            for card in getattr(context, 'playable_cards', []) or []
            if (
                self._is_lethal_strength_support_card(card)
                or self._is_lethal_energy_support_card(card)
                or self._is_lethal_hand_exhaust_energy_support_card(card, context)
                or self._is_lethal_hand_exhaust_energy_resource_card(card, context)
                or self._is_lethal_corruption_support_card(card)
                or self._is_lethal_double_tap_support_card(card)
                or self._is_lethal_vulnerable_support_card(card)
                or self._is_lethal_charons_ashes_support_card(card, context)
                or self._havoc_top_energy_support_card(card, context) is not None
                or (
                    not is_attack_card(card)
                    and self._is_juggernaut_block_card(card, context)
                )
                or (
                    not is_attack_card(card)
                    and not self._card_requires_target(card)
                    and 0 < self._context_panache_counter(context) <= 1
                )
                or (
                    card_type_name(card) == 'SKILL'
                    and self._context_letter_opener_counter(context) is not None
                )
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

        sequence_card_keys = {card_play_key(card) for card in sequence_cards}
        starting_hp = tuple(
            self._monster_current_hp(monster)
            for monster in context.monsters_alive
        )
        starting_block = tuple(
            max(0, self._safe_int(getattr(monster, 'block', 0), default=0))
            for monster in context.monsters_alive
        )
        starting_malleable = tuple(
            self._get_monster_power_amount(monster, 'Malleable')
            for monster in context.monsters_alive
        )
        starting_curl_up = tuple(
            self._get_monster_power_amount(monster, 'Curl Up')
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
        starting_flight = tuple(
            self._get_monster_power_amount(monster, 'Flight')
            for monster in context.monsters_alive
        )
        starting_thorns = tuple(
            self._monster_thorns_stacks(context, monster_idx)
            for monster_idx, _monster in enumerate(context.monsters_alive)
        )
        starting_state = _TargetedLethalState(
            hp=starting_hp,
            block=starting_block,
            curl_up=starting_curl_up,
            malleable=starting_malleable,
            vulnerable=starting_vulnerable,
            artifact=starting_artifact,
            flight=starting_flight,
            thorns=starting_thorns,
            strength=getattr(context, 'strength', 0),
            player_hp=self._context_player_hp(context),
            player_block=self._context_player_block(context),
            corruption_active=self._context_corruption_active(context),
            duplication_charges=self._context_duplication_charges(context),
            double_tap_charges=self._context_double_tap_charges(context),
            necronomicon_available=self._context_has_relic(context, 'Necronomicon'),
            nunchaku_counter=self._context_relic_counter(context, 'Nunchaku'),
            panache_counter=self._context_panache_counter(context),
            panache_damage=self._context_panache_damage(context),
            letter_opener_counter=self._context_letter_opener_counter(context),
            energy=available_energy,
        )
        seen = set()

        def search(remaining_cards, state: _TargetedLethalState):
            if all(hp <= 0 for hp in state.hp):
                return []

            remaining_card_keys = tuple(card_play_key(card) for card in remaining_cards)
            state_key = state.seen_key(remaining_card_keys)
            if state_key in seen:
                return None
            seen.add(state_key)

            candidates = []
            for card_pos, card in enumerate(remaining_cards):
                panache_candidate = self._panache_card_play_lethal_candidate(
                    card_pos,
                    card,
                    context,
                    state,
                )
                if panache_candidate is not None:
                    candidates.append(panache_candidate)

                letter_opener_candidate = self._letter_opener_skill_lethal_candidate(
                    card_pos,
                    card,
                    context,
                    state,
                )
                if letter_opener_candidate is not None:
                    candidates.append(letter_opener_candidate)

                charons_ashes_candidate = self._charons_ashes_lethal_candidate(
                    card_pos,
                    card,
                    remaining_cards,
                    context,
                    state,
                )
                if charons_ashes_candidate is not None:
                    candidates.append(charons_ashes_candidate)

                if self._is_juggernaut_block_card(card, context) and not is_attack_card(card):
                    cost = self._lethal_card_cost(
                        card,
                        context,
                        state.energy,
                        state.corruption_active,
                    )
                    if cost > state.energy:
                        continue

                    target_idx = self._single_alive_monster_index(state.hp)
                    if target_idx is None:
                        continue

                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    next_hp = state.hp
                    next_block = state.block
                    damage_progress = 0
                    for _card_play_idx in range(card_play_repeats):
                        next_hp, next_block, repeat_damage = (
                            self._apply_lethal_juggernaut_block_damage(
                                card,
                                context,
                                next_hp,
                                next_block,
                            )
                        )
                        damage_progress += repeat_damage
                    if damage_progress <= 0:
                        continue

                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(
                                1 if next_hp[target_idx] <= 0 else 0,
                                0,
                                damage_progress,
                                -cost,
                            ),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                hp=next_hp,
                                block=next_block,
                                duplication_charges=next_duplication_charges,
                            ),
                        )
                    )
                    continue

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
                    strength_gain = next_strength - state.strength
                    if strength_gain <= 0:
                        continue
                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    next_strength = state.strength + strength_gain * card_play_repeats

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
                                    duplication_charges=next_duplication_charges,
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

                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    energy_gain = self._lethal_energy_gain(card) * card_play_repeats
                    hp_loss = self._lethal_energy_hp_loss_for_repeats(
                        card,
                        context,
                        card_play_repeats,
                    )
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
                                duplication_charges=next_duplication_charges,
                            ),
                        )
                    )
                    continue

                hand_exhaust_energy_candidate = (
                    self._hand_exhaust_energy_lethal_candidate(
                        card_pos,
                        card,
                        remaining_cards,
                        context,
                        state,
                    )
                )
                if hand_exhaust_energy_candidate is not None:
                    candidates.append(hand_exhaust_energy_candidate)
                    continue

                if self._is_lethal_corruption_support_card(card):
                    if state.corruption_active:
                        continue

                    cost = effective_card_cost(card, state.energy)
                    if cost > state.energy:
                        continue

                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(0, 0, 0, -cost),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                corruption_active=True,
                                duplication_charges=next_duplication_charges,
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

                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    next_double_tap_charges = (
                        state.double_tap_charges
                        + self._lethal_double_tap_charges(card) * card_play_repeats
                    )
                    candidates.append(
                        _TargetedLethalCandidate(
                            priority=(0, 0, next_double_tap_charges, -cost),
                            card_pos=card_pos,
                            monster_idx=None,
                            next_state=state.after_spending(
                                cost,
                                duplication_charges=next_duplication_charges,
                                double_tap_charges=next_double_tap_charges,
                            ),
                        )
                    )
                    continue

                havoc_energy_candidate = self._havoc_top_energy_lethal_candidate(
                    card_pos,
                    card,
                    context,
                    state,
                )
                if havoc_energy_candidate is not None:
                    candidates.append(havoc_energy_candidate)
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

                    if self._is_all_enemy_debuff_card(card):
                        support_targets = (None,)
                    elif self._card_requires_target(card):
                        support_targets = tuple(
                            monster_idx
                            for monster_idx, hp in enumerate(state.hp)
                            if hp > 0
                        )
                    else:
                        support_targets = (None,)

                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    for target_idx in support_targets:
                        next_vulnerable = state.vulnerable
                        next_artifact = state.artifact
                        for _card_play_idx in range(card_play_repeats):
                            next_vulnerable, next_artifact = (
                                self._vulnerable_state_after_card(
                                    card,
                                    context,
                                    next_vulnerable,
                                    next_artifact,
                                    state.hp,
                                    target_idx,
                                )
                            )
                        if next_vulnerable == state.vulnerable and next_artifact == state.artifact:
                            continue

                        vulnerable_gain = sum(next_vulnerable) - sum(state.vulnerable)
                        artifact_reduced = sum(state.artifact) - sum(next_artifact)
                        candidates.append(
                            _TargetedLethalCandidate(
                                priority=(0, 0, vulnerable_gain + artifact_reduced, -cost),
                                card_pos=card_pos,
                                monster_idx=target_idx,
                                next_state=state.after_spending(
                                    cost,
                                    vulnerable=next_vulnerable,
                                    artifact=next_artifact,
                                    duplication_charges=next_duplication_charges,
                                ),
                            )
                        )
                    continue

                havoc_candidate = self._havoc_top_attack_lethal_candidate(
                    card_pos,
                    card,
                    context,
                    state,
                )
                if havoc_candidate is not None:
                    candidates.append(havoc_candidate)
                    continue

                havoc_exhaust_candidate = self._havoc_top_exhaust_juggernaut_lethal_candidate(
                    card_pos,
                    card,
                    context,
                    state,
                )
                if havoc_exhaust_candidate is not None:
                    candidates.append(havoc_exhaust_candidate)
                    continue

                if self._is_aoe_attack(card):
                    cost = effective_card_cost(card, state.energy)
                    if cost > state.energy:
                        continue

                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    next_double_tap_charges = state.double_tap_charges
                    next_necronomicon_available = state.necronomicon_available
                    next_hp = tuple(state.hp)
                    next_block = tuple(state.block)
                    next_curl_up = tuple(state.curl_up)
                    next_malleable = tuple(state.malleable)
                    next_flight = tuple(state.flight)
                    next_vulnerable = state.vulnerable
                    next_artifact = state.artifact
                    next_panache_counter = state.panache_counter
                    next_player_hp = state.player_hp
                    next_player_block = state.player_block
                    total_damage = 0
                    attack_plays_resolved = 0
                    rampage_bonus = 0
                    player_dead = False
                    for _card_play_idx in range(card_play_repeats):
                        attack_repeats = self._lethal_attack_repeats(
                            card,
                            next_double_tap_charges,
                        )
                        next_double_tap_charges = self._double_tap_charges_after_attack(
                            next_double_tap_charges
                        )
                        if self._lethal_necronomicon_replays_attack(
                            card,
                            cost,
                            next_necronomicon_available,
                        ):
                            attack_repeats *= 2
                            next_necronomicon_available = False
                        for _repeat_idx in range(attack_repeats):
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
                                    base_damage_bonus=rampage_bonus,
                                )
                                if damage <= 0:
                                    continue

                                hit_count = self._get_vulnerable_damage_instance_count(
                                    card,
                                    context,
                                    state.energy,
                                    monster_idx,
                                )
                                next_hp, next_block, next_curl_up, next_malleable, next_flight, damage_progress = (
                                    self._apply_lethal_attack_damage_to_target(
                                        next_hp,
                                        next_block,
                                        next_curl_up,
                                        next_malleable,
                                        next_flight,
                                        monster_idx,
                                        damage,
                                        hit_count,
                                        apply_the_boot=self._context_has_the_boot(context),
                                    )
                                )
                                repeat_damage += damage_progress
                                thorns_damage = max(0, state.thorns[monster_idx]) * max(1, hit_count)
                                if thorns_damage > 0:
                                    next_player_hp, next_player_block, _hp_loss = (
                                        self._apply_lethal_player_damage(
                                            context,
                                            next_player_hp,
                                            next_player_block,
                                            thorns_damage,
                                        )
                                    )
                                    if next_player_hp <= 0:
                                        player_dead = True
                                        break

                            if player_dead or repeat_damage <= 0:
                                break

                            attack_plays_resolved += 1
                            next_hp, next_block, juggernaut_damage = (
                                self._apply_lethal_juggernaut_block_damage(
                                    card,
                                    context,
                                    next_hp,
                                    next_block,
                                )
                            )
                            repeat_damage += juggernaut_damage
                            total_damage += repeat_damage
                            next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                                card,
                                context,
                                next_vulnerable,
                                next_artifact,
                                next_hp,
                                None,
                            )
                            rampage_bonus += self._rampage_scaling_per_play(card)
                        if player_dead:
                            break
                        next_hp, next_block, next_panache_counter, panache_damage = (
                            self._apply_lethal_panache_card_play(
                                next_hp,
                                next_block,
                                next_panache_counter,
                                state.panache_damage,
                            )
                        )
                        total_damage += panache_damage

                    if player_dead or total_damage <= 0:
                        continue

                    nunchaku_energy_gain, next_nunchaku_counter = (
                        self._nunchaku_energy_after_attack_plays(
                            state.nunchaku_counter,
                            attack_plays_resolved,
                        )
                    )
                    cost = cost - nunchaku_energy_gain
                    kill_count = sum(
                        1
                        for before_hp, after_hp in zip(state.hp, next_hp)
                        if before_hp > 0 and after_hp <= 0
                    )
                    priority = (
                        kill_count,
                        1 if nunchaku_energy_gain > 0 else 0,
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
                                block=next_block,
                                curl_up=next_curl_up,
                                malleable=next_malleable,
                                flight=next_flight,
                                vulnerable=next_vulnerable,
                                artifact=next_artifact,
                                player_hp=next_player_hp,
                                player_block=next_player_block,
                                duplication_charges=next_duplication_charges,
                                double_tap_charges=next_double_tap_charges,
                                necronomicon_available=next_necronomicon_available,
                                nunchaku_counter=next_nunchaku_counter,
                                panache_counter=next_panache_counter,
                            ),
                        )
                    )
                    continue

                if not self._card_requires_target(card):
                    continue

                for monster_idx, hp in enumerate(state.hp):
                    if hp <= 0:
                        continue

                    card_play_repeats = self._lethal_card_play_repeats(
                        state.duplication_charges
                    )
                    next_duplication_charges = self._duplication_charges_after_card(
                        state.duplication_charges
                    )
                    next_double_tap_charges = state.double_tap_charges
                    upfront_cost = effective_card_cost(card, state.energy)
                    if upfront_cost > state.energy:
                        continue
                    next_necronomicon_available = state.necronomicon_available

                    fiend_fire_exhaust_count = self._fiend_fire_exhaust_count_for_remaining_cards(
                        card,
                        context,
                        remaining_cards,
                        sequence_card_keys,
                    )
                    next_hp = tuple(state.hp)
                    next_block = tuple(state.block)
                    next_curl_up = tuple(state.curl_up)
                    next_malleable = tuple(state.malleable)
                    next_flight = tuple(state.flight)
                    next_vulnerable = state.vulnerable
                    next_artifact = state.artifact
                    next_panache_counter = state.panache_counter
                    next_player_hp = state.player_hp
                    next_player_block = state.player_block
                    total_damage = 0
                    total_energy_refund = 0
                    attack_plays_resolved = 0
                    rampage_bonus = 0
                    player_dead = False
                    for _card_play_idx in range(card_play_repeats):
                        attack_repeats = self._lethal_attack_repeats(
                            card,
                            next_double_tap_charges,
                        )
                        next_double_tap_charges = self._double_tap_charges_after_attack(
                            next_double_tap_charges
                        )
                        if self._lethal_necronomicon_replays_attack(
                            card,
                            upfront_cost,
                            next_necronomicon_available,
                        ):
                            attack_repeats *= 2
                            next_necronomicon_available = False
                        for _repeat_idx in range(attack_repeats):
                            current_hp = next_hp[monster_idx]
                            if current_hp <= 0:
                                break
                            if self._base_card_name(card) == 'Melter':
                                next_block_list = list(next_block)
                                next_block_list[monster_idx] = 0
                                next_block = tuple(next_block_list)

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
                                base_damage_bonus=rampage_bonus,
                            )
                            if damage <= 0:
                                continue

                            attack_plays_resolved += 1
                            hit_count = self._get_vulnerable_damage_instance_count(
                                card,
                                context,
                                state.energy,
                                monster_idx,
                                fiend_fire_exhaust_count,
                            )
                            next_hp, next_block, next_curl_up, next_malleable, next_flight, damage_progress = (
                                self._apply_lethal_attack_damage_to_target(
                                    next_hp,
                                    next_block,
                                    next_curl_up,
                                    next_malleable,
                                    next_flight,
                                    monster_idx,
                                    damage,
                                    hit_count,
                                    apply_the_boot=self._context_has_the_boot(context),
                                )
                            )
                            total_damage += damage_progress
                            thorns_damage = max(0, state.thorns[monster_idx]) * max(1, hit_count)
                            if thorns_damage > 0:
                                next_player_hp, next_player_block, _hp_loss = (
                                    self._apply_lethal_player_damage(
                                        context,
                                        next_player_hp,
                                        next_player_block,
                                        thorns_damage,
                                    )
                                )
                                if next_player_hp <= 0:
                                    player_dead = True
                                    break
                            next_hp, next_block, juggernaut_damage = (
                                self._apply_lethal_juggernaut_block_damage(
                                    card,
                                    context,
                                    next_hp,
                                    next_block,
                                )
                            )
                            total_damage += juggernaut_damage
                            next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                                card,
                                context,
                                next_vulnerable,
                                next_artifact,
                                next_hp,
                                monster_idx,
                            )
                            rampage_bonus += self._rampage_scaling_per_play(card)
                        if player_dead:
                            break
                        next_hp, next_block, next_panache_counter, panache_damage = (
                            self._apply_lethal_panache_card_play(
                                next_hp,
                                next_block,
                                next_panache_counter,
                                state.panache_damage,
                            )
                        )
                        total_damage += panache_damage
                        if player_dead:
                            break

                    if player_dead or total_damage <= 0:
                        continue

                    nunchaku_energy_gain, next_nunchaku_counter = (
                        self._nunchaku_energy_after_attack_plays(
                            state.nunchaku_counter,
                            attack_plays_resolved,
                        )
                    )
                    hand_exhaust_energy_gain = (
                        self._lethal_hand_exhaust_sentinel_energy_gain(
                            card_pos,
                            card,
                            remaining_cards,
                        )
                    )
                    cost = (
                        upfront_cost
                        - total_energy_refund
                        - nunchaku_energy_gain
                        - hand_exhaust_energy_gain
                    )
                    refunds_energy = (
                        total_energy_refund > 0
                        or nunchaku_energy_gain > 0
                        or hand_exhaust_energy_gain > 0
                    )
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
                                block=next_block,
                                curl_up=next_curl_up,
                                malleable=next_malleable,
                                flight=next_flight,
                                vulnerable=next_vulnerable,
                                artifact=next_artifact,
                                player_hp=next_player_hp,
                                player_block=next_player_block,
                                duplication_charges=next_duplication_charges,
                                double_tap_charges=next_double_tap_charges,
                                necronomicon_available=next_necronomicon_available,
                                nunchaku_counter=next_nunchaku_counter,
                                panache_counter=next_panache_counter,
                            ),
                        )
                    )

            candidates.sort(key=lambda item: item.priority, reverse=True)

            for candidate in candidates:
                card = remaining_cards[candidate.card_pos]
                next_cards = self._remaining_cards_after_lethal_play(
                    candidate.card_pos,
                    card,
                    remaining_cards,
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

    def _panache_card_play_lethal_candidate(
        self,
        card_pos: int,
        card: Card,
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        if (
            state.panache_damage <= 0
            or is_attack_card(card)
            or self._card_requires_target(card)
        ):
            return None

        cost = self._lethal_card_cost(
            card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        card_play_repeats = self._lethal_card_play_repeats(
            state.duplication_charges
        )
        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        next_hp, next_block, next_panache_counter, damage_progress = (
            self._apply_lethal_panache_card_plays(
                state.hp,
                state.block,
                state.panache_counter,
                state.panache_damage,
                card_play_repeats,
            )
        )
        if damage_progress <= 0 and next_panache_counter == state.panache_counter:
            return None

        kill_count = sum(
            1
            for before_hp, after_hp in zip(state.hp, next_hp)
            if before_hp > 0 and after_hp <= 0
        )
        return _TargetedLethalCandidate(
            priority=(kill_count, 0, damage_progress, -cost),
            card_pos=card_pos,
            monster_idx=None,
            next_state=state.after_spending(
                cost,
                hp=next_hp,
                block=next_block,
                duplication_charges=next_duplication_charges,
                panache_counter=next_panache_counter,
            ),
        )

    def _letter_opener_skill_lethal_candidate(
        self,
        card_pos: int,
        card: Card,
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        if state.letter_opener_counter is None or card_type_name(card) != 'SKILL':
            return None

        cost = self._lethal_card_cost(
            card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        monster_idx = None
        if self._card_requires_target(card):
            monster_idx = self._single_alive_monster_index(state.hp)
            if monster_idx is None:
                return None

        card_play_repeats = self._lethal_card_play_repeats(
            state.duplication_charges
        )
        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        next_hp, next_block, next_counter, damage_progress = (
            self._apply_lethal_letter_opener_skill_plays(
                state.hp,
                state.block,
                state.letter_opener_counter,
                card_play_repeats,
            )
        )
        if (
            damage_progress <= 0
            and next_counter == state.letter_opener_counter
        ):
            return None

        kill_count = sum(
            1
            for before_hp, after_hp in zip(state.hp, next_hp)
            if before_hp > 0 and after_hp <= 0
        )
        return _TargetedLethalCandidate(
            priority=(kill_count, 0, damage_progress, -cost),
            card_pos=card_pos,
            monster_idx=monster_idx,
            next_state=state.after_spending(
                cost,
                hp=next_hp,
                block=next_block,
                duplication_charges=next_duplication_charges,
                letter_opener_counter=next_counter,
            ),
        )

    def _charons_ashes_lethal_candidate(
        self,
        card_pos: int,
        card: Card,
        remaining_cards: Tuple[Card, ...],
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        if not self._is_lethal_charons_ashes_support_card(card, context):
            return None

        cost = self._lethal_card_cost(
            card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        exhaust_events = self._charons_ashes_card_exhaust_events(
            card_pos,
            card,
            remaining_cards,
            context,
            state.corruption_active,
        )
        if exhaust_events <= 0:
            return None

        card_play_repeats = self._lethal_card_play_repeats(
            state.duplication_charges
        )
        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        next_hp = state.hp
        next_block = state.block
        total_damage = 0
        for _ in range(card_play_repeats):
            next_hp, next_block, damage_progress = (
                self._apply_lethal_charons_ashes_damage(
                    context,
                    next_hp,
                    next_block,
                    exhaust_events,
                )
            )
            total_damage += damage_progress

        if total_damage <= 0:
            return None

        kill_count = sum(
            1
            for before_hp, after_hp in zip(state.hp, next_hp)
            if before_hp > 0 and after_hp <= 0
        )
        return _TargetedLethalCandidate(
            priority=(kill_count, 0, total_damage, -cost),
            card_pos=card_pos,
            monster_idx=None,
            next_state=state.after_spending(
                cost,
                hp=next_hp,
                block=next_block,
                duplication_charges=next_duplication_charges,
            ),
        )

    def _havoc_top_energy_lethal_candidate(
        self,
        card_pos: int,
        havoc_card: Card,
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        top_energy_card = self._havoc_top_energy_support_card(
            havoc_card,
            context,
            state.havoc_cards_consumed,
        )
        if top_energy_card is None:
            return None

        cost = self._lethal_card_cost(
            havoc_card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        energy_gain = self._lethal_energy_gain(top_energy_card)
        hp_loss = self._effective_player_hp_loss(
            context,
            self._lethal_energy_hp_loss(top_energy_card),
        )
        if energy_gain <= 0 or state.player_hp <= hp_loss:
            return None

        next_hp, next_block, exhaust_damage = (
            self._apply_havoc_top_exhaust_juggernaut_damage(
                havoc_card,
                context,
                state.hp,
                state.block,
                state.havoc_cards_consumed,
            )
        )
        kill_count = sum(
            1
            for before_hp, after_hp in zip(state.hp, next_hp)
            if before_hp > 0 and after_hp <= 0
        )
        net_cost = cost - energy_gain
        return _TargetedLethalCandidate(
            priority=(
                kill_count,
                1,
                energy_gain - cost + exhaust_damage,
                -cost,
            ),
            card_pos=card_pos,
            monster_idx=None,
            next_state=state.after_spending(
                net_cost,
                hp=next_hp,
                block=next_block,
                player_hp=state.player_hp - hp_loss,
                duplication_charges=next_duplication_charges,
                havoc_cards_consumed=state.havoc_cards_consumed + 1,
            ),
        )

    def _havoc_top_attack_lethal_candidate(
        self,
        card_pos: int,
        havoc_card: Card,
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        top_attack = self._havoc_top_attack_card(
            havoc_card,
            context,
            state.havoc_cards_consumed,
        )
        if top_attack is None:
            return None

        cost = self._lethal_card_cost(
            havoc_card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        top_attack_energy = self._havoc_top_attack_effect_energy(
            top_attack,
            state.energy - cost,
        )
        next_hp = tuple(state.hp)
        next_block = tuple(state.block)
        next_curl_up = tuple(state.curl_up)
        next_malleable = tuple(state.malleable)
        next_flight = tuple(state.flight)
        next_vulnerable = state.vulnerable
        next_artifact = state.artifact
        total_damage = 0
        attack_plays_resolved = 0

        if self._is_aoe_attack(top_attack):
            attack_repeats = self._lethal_attack_repeats(
                top_attack,
                state.double_tap_charges,
            )
            next_double_tap_charges = self._double_tap_charges_after_attack(
                state.double_tap_charges
            )
            rampage_bonus = 0
            for _repeat_idx in range(attack_repeats):
                repeat_damage = 0
                for monster_idx, hp in enumerate(next_hp):
                    if hp <= 0:
                        continue

                    damage = self._card_damage_against_monster(
                        top_attack,
                        context,
                        monster_idx,
                        top_attack_energy,
                        target_vulnerable_stacks=next_vulnerable[monster_idx],
                        strength=state.strength,
                        base_damage_bonus=rampage_bonus,
                    )
                    if damage <= 0:
                        continue

                    hit_count = self._get_vulnerable_damage_instance_count(
                        top_attack,
                        context,
                        top_attack_energy,
                        monster_idx,
                    )
                    next_hp, next_block, next_curl_up, next_malleable, next_flight, damage_progress = (
                        self._apply_lethal_attack_damage_to_target(
                            next_hp,
                            next_block,
                            next_curl_up,
                            next_malleable,
                            next_flight,
                            monster_idx,
                            damage,
                            hit_count,
                            apply_the_boot=self._context_has_the_boot(context),
                        )
                    )
                    repeat_damage += damage_progress

                if repeat_damage <= 0:
                    break

                attack_plays_resolved += 1
                next_hp, next_block, juggernaut_damage = (
                    self._apply_lethal_juggernaut_block_damage(
                        top_attack,
                        context,
                        next_hp,
                        next_block,
                    )
                )
                repeat_damage += juggernaut_damage
                total_damage += repeat_damage
                next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                    top_attack,
                    context,
                    next_vulnerable,
                    next_artifact,
                    next_hp,
                    None,
                )
                rampage_bonus += self._rampage_scaling_per_play(top_attack)
        else:
            alive_targets = [
                monster_idx
                for monster_idx, hp in enumerate(next_hp)
                if hp > 0
            ]
            if len(alive_targets) != 1:
                return None

            monster_idx = alive_targets[0]
            attack_repeats = self._lethal_attack_repeats(
                top_attack,
                state.double_tap_charges,
            )
            next_double_tap_charges = self._double_tap_charges_after_attack(
                state.double_tap_charges
            )
            total_energy_refund = 0
            rampage_bonus = 0
            for _repeat_idx in range(attack_repeats):
                if next_hp[monster_idx] <= 0:
                    break

                if self._base_card_name(top_attack) == 'Melter':
                    next_block_list = list(next_block)
                    next_block_list[monster_idx] = 0
                    next_block = tuple(next_block_list)

                total_energy_refund += self._card_energy_refund_against_monster(
                    top_attack,
                    context,
                    monster_idx,
                    next_vulnerable[monster_idx],
                )
                damage = self._card_damage_against_monster(
                    top_attack,
                    context,
                    monster_idx,
                    top_attack_energy,
                    target_vulnerable_stacks=next_vulnerable[monster_idx],
                    strength=state.strength,
                    base_damage_bonus=rampage_bonus,
                )
                if damage <= 0:
                    continue

                attack_plays_resolved += 1
                hit_count = self._get_vulnerable_damage_instance_count(
                    top_attack,
                    context,
                    top_attack_energy,
                    monster_idx,
                )
                next_hp, next_block, next_curl_up, next_malleable, next_flight, damage_progress = (
                    self._apply_lethal_attack_damage_to_target(
                        next_hp,
                        next_block,
                        next_curl_up,
                        next_malleable,
                        next_flight,
                        monster_idx,
                        damage,
                        hit_count,
                        apply_the_boot=self._context_has_the_boot(context),
                    )
                )
                total_damage += damage_progress
                next_hp, next_block, juggernaut_damage = (
                    self._apply_lethal_juggernaut_block_damage(
                        top_attack,
                        context,
                        next_hp,
                        next_block,
                    )
                )
                total_damage += juggernaut_damage
                next_vulnerable, next_artifact = self._vulnerable_state_after_card(
                    top_attack,
                    context,
                    next_vulnerable,
                    next_artifact,
                    tuple(next_hp),
                    monster_idx,
                )
                rampage_bonus += self._rampage_scaling_per_play(top_attack)

            cost -= total_energy_refund

        next_hp, next_block, exhaust_damage = (
            self._apply_havoc_top_exhaust_juggernaut_damage(
                havoc_card,
                context,
                next_hp,
                next_block,
                state.havoc_cards_consumed,
            )
        )
        total_damage += exhaust_damage

        if total_damage <= 0:
            return None

        nunchaku_energy_gain, next_nunchaku_counter = (
            self._nunchaku_energy_after_attack_plays(
                state.nunchaku_counter,
                attack_plays_resolved,
            )
        )
        cost -= nunchaku_energy_gain
        kill_count = sum(
            1
            for before_hp, after_hp in zip(state.hp, next_hp)
            if before_hp > 0 and after_hp <= 0
        )
        return _TargetedLethalCandidate(
            priority=(
                kill_count,
                1 if nunchaku_energy_gain > 0 else 0,
                total_damage,
                -cost,
            ),
            card_pos=card_pos,
            monster_idx=None,
            next_state=state.after_spending(
                cost,
                hp=next_hp,
                block=next_block,
                curl_up=next_curl_up,
                malleable=next_malleable,
                flight=next_flight,
                vulnerable=next_vulnerable,
                artifact=next_artifact,
                duplication_charges=next_duplication_charges,
                double_tap_charges=next_double_tap_charges,
                nunchaku_counter=next_nunchaku_counter,
                havoc_cards_consumed=state.havoc_cards_consumed + 1,
            ),
        )

    def _havoc_top_exhaust_juggernaut_lethal_candidate(
        self,
        card_pos: int,
        havoc_card: Card,
        context: DecisionContext,
        state: _TargetedLethalState,
    ) -> Optional[_TargetedLethalCandidate]:
        cost = self._lethal_card_cost(
            havoc_card,
            context,
            state.energy,
            state.corruption_active,
        )
        if cost > state.energy:
            return None

        next_duplication_charges = self._duplication_charges_after_card(
            state.duplication_charges
        )
        next_hp, next_block, damage_progress = (
            self._apply_havoc_top_exhaust_juggernaut_damage(
                havoc_card,
                context,
                state.hp,
                state.block,
                state.havoc_cards_consumed,
            )
        )
        if damage_progress <= 0:
            return None

        kill_count = sum(
            1
            for before_hp, after_hp in zip(state.hp, next_hp)
            if before_hp > 0 and after_hp <= 0
        )
        return _TargetedLethalCandidate(
            priority=(
                kill_count,
                0,
                damage_progress,
                -cost,
            ),
            card_pos=card_pos,
            monster_idx=None,
            next_state=state.after_spending(
                cost,
                hp=next_hp,
                block=next_block,
                duplication_charges=next_duplication_charges,
                havoc_cards_consumed=state.havoc_cards_consumed + 1,
            ),
        )

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
            card_play_key(remaining_card)
            for remaining_card in remaining_cards
        }
        played_card_key = card_play_key(card)
        count = 0
        for hand_card in hand_cards:
            hand_card_key = card_play_key(hand_card)
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
        sequence_card_keys = {card_play_key(card) for card in attack_cards}

        for aoe_card in aoe_cards:
            aoe_cost = effective_card_cost(aoe_card, available_energy)
            if aoe_cost > available_energy:
                continue

            hp_state = tuple(
                self._monster_current_hp(monster)
                for monster in context.monsters_alive
            )
            block_state = tuple(
                max(0, self._safe_int(getattr(monster, 'block', 0), default=0))
                for monster in context.monsters_alive
            )
            malleable_state = tuple(
                self._get_monster_power_amount(monster, 'Malleable')
                for monster in context.monsters_alive
            )
            curl_up_state = tuple(
                self._get_monster_power_amount(monster, 'Curl Up')
                for monster in context.monsters_alive
            )
            flight_state = tuple(
                self._get_monster_power_amount(monster, 'Flight')
                for monster in context.monsters_alive
            )
            thorns_state = tuple(
                self._monster_thorns_stacks(context, monster_idx)
                for monster_idx, _monster in enumerate(context.monsters_alive)
            )
            player_hp = self._context_player_hp(context)
            player_block = self._context_player_block(context)
            player_dead = False
            survivors = []
            for monster_idx, monster in enumerate(context.monsters_alive):
                damage = self._card_damage_against_monster(
                    aoe_card,
                    context,
                    monster_idx,
                    available_energy,
                )
                if damage <= 0:
                    if hp_state[monster_idx] > 0:
                        survivors.append(
                            (
                                hp_state[monster_idx] + block_state[monster_idx],
                                monster_idx,
                                monster,
                            )
                        )
                    continue
                hit_count = self._get_vulnerable_damage_instance_count(
                    aoe_card,
                    context,
                    available_energy,
                    monster_idx,
                )
                hp_state, block_state, curl_up_state, malleable_state, flight_state, _damage_progress = (
                    self._apply_lethal_attack_damage_to_target(
                        hp_state,
                        block_state,
                        curl_up_state,
                        malleable_state,
                        flight_state,
                        monster_idx,
                        damage,
                        hit_count,
                        apply_the_boot=self._context_has_the_boot(context),
                    )
                )
                thorns_damage = max(0, thorns_state[monster_idx]) * max(1, hit_count)
                if thorns_damage > 0:
                    player_hp, player_block, _hp_loss = self._apply_lethal_player_damage(
                        context,
                        player_hp,
                        player_block,
                        thorns_damage,
                    )
                    if player_hp <= 0:
                        player_dead = True
                        break
                if hp_state[monster_idx] > 0:
                    survivors.append(
                        (
                            hp_state[monster_idx] + block_state[monster_idx],
                            monster_idx,
                            monster,
                        )
                    )

            if player_dead:
                continue

            if not survivors:
                return [PlayCardAction(card=aoe_card)]

            sequence = [PlayCardAction(card=aoe_card)]
            remaining_energy = available_energy - aoe_cost
            played_cards = set()
            mark_card_played(played_cards, aoe_card)
            survivors.sort(key=lambda item: item[0], reverse=True)

            for damage_needed, monster_idx, monster in survivors:
                while hp_state[monster_idx] > 0:
                    best_card = None
                    best_cost = 0
                    best_damage = 0
                    best_next_state = None
                    best_priority = None

                    for card in attack_cards:
                        if is_card_played(played_cards, card) or self._is_aoe_attack(card):
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
                            if not is_card_played(played_cards, remaining_card)
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
                        if damage <= 0:
                            continue
                        hit_count = self._get_vulnerable_damage_instance_count(
                            card,
                            context,
                            remaining_energy,
                            monster_idx,
                            fiend_fire_exhaust_count,
                        )
                        candidate_block_state = block_state
                        if self._base_card_name(card) == 'Melter':
                            candidate_block_list = list(candidate_block_state)
                            candidate_block_list[monster_idx] = 0
                            candidate_block_state = tuple(candidate_block_list)
                        candidate_hp, candidate_block, candidate_curl_up, candidate_malleable, candidate_flight, damage_progress = (
                            self._apply_lethal_attack_damage_to_target(
                                hp_state,
                                candidate_block_state,
                                curl_up_state,
                                malleable_state,
                                flight_state,
                                monster_idx,
                                damage,
                                hit_count,
                                apply_the_boot=self._context_has_the_boot(context),
                            )
                        )
                        candidate_player_hp = player_hp
                        candidate_player_block = player_block
                        thorns_damage = max(0, thorns_state[monster_idx]) * max(1, hit_count)
                        if thorns_damage > 0:
                            candidate_player_hp, candidate_player_block, _hp_loss = (
                                self._apply_lethal_player_damage(
                                    context,
                                    candidate_player_hp,
                                    candidate_player_block,
                                    thorns_damage,
                                )
                            )
                            if candidate_player_hp <= 0:
                                continue
                        refunds_energy = self._card_refunds_energy_against_monster(
                            card,
                            context,
                            monster_idx,
                        )
                        priority = (
                            1 if candidate_hp[monster_idx] <= 0 else 0,
                            1 if refunds_energy else 0,
                            damage_progress,
                            -cost,
                        )
                        if best_priority is None or priority > best_priority:
                            best_card = card
                            best_cost = cost
                            best_damage = damage_progress
                            best_next_state = (
                                candidate_hp,
                                candidate_block,
                                candidate_curl_up,
                                candidate_malleable,
                                candidate_flight,
                                candidate_player_hp,
                                candidate_player_block,
                            )
                            best_priority = priority

                    if best_card is None or best_damage <= 0:
                        sequence = []
                        break

                    sequence.append(self._play_card_action(best_card, monster))
                    (
                        hp_state,
                        block_state,
                        curl_up_state,
                        malleable_state,
                        flight_state,
                        player_hp,
                        player_block,
                    ) = best_next_state
                    if self._base_card_name(best_card) == 'Fiend Fire':
                        played_cards.update(sequence_card_keys)
                    else:
                        mark_card_played(played_cards, best_card)
                    remaining_energy -= best_cost
                    damage_needed = hp_state[monster_idx] + block_state[monster_idx]

                if hp_state[monster_idx] > 0:
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
            return self._context_player_hp_pct(context) > 0.3

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
        available_energy = max(
            0,
            self._safe_int(getattr(context, 'energy_available', 0), default=0),
        )
        hp_state = tuple(
            self._monster_current_hp(monster)
            for monster in getattr(context, 'monsters_alive', []) or []
        )

        # Sort attack cards by damage efficiency (damage per energy)
        attack_cards = []
        for card in context.playable_cards:
            juggernaut_damage = self._juggernaut_damage_for_block_card(
                card,
                context,
                hp_state,
            )
            if is_attack_card(card):
                if len(context.monsters_alive) == 1:
                    cost = self._card_energy_cost_against_monster(
                        card,
                        context,
                        0,
                        available_energy,
                    )
                else:
                    cost = effective_card_cost(card, available_energy)
                damage = self._get_card_damage(
                    card,
                    context,
                    available_energy=available_energy,
                )
                if len(context.monsters_alive) == 1:
                    damage = self._card_damage_against_monster(
                        card,
                        context,
                        0,
                        available_energy,
                    )
                elif self._is_aoe_attack(card):
                    damage = self._aoe_damage_potential(
                        card,
                        context,
                        damage,
                        available_energy,
                    )
                else:
                    damage = self._apply_player_weak_to_card_damage(
                        card,
                        context,
                        damage,
                        available_energy,
                    )
                damage += juggernaut_damage
                logger.info(f"[LETHAL_CALC] {card.name}: cost={cost}, damage={damage}, eff={damage/cost if cost > 0 else 'inf'}")
                if cost > 0:
                    efficiency = damage / cost
                else:
                    efficiency = float('inf')  # Zero-cost cards are infinitely efficient
                attack_cards.append((card, cost, damage, efficiency))
            elif (
                havoc_damage := self._havoc_top_attack_damage_potential(
                    card,
                    context,
                    available_energy,
                )
            ) > 0:
                havoc_damage += self._havoc_top_exhaust_juggernaut_damage_potential(
                    card,
                    context,
                    available_energy,
                )
                cost = self._lethal_card_cost(card, context, available_energy)
                logger.info(f"[LETHAL_CALC] {card.name}: cost={cost}, havoc_top_damage={havoc_damage}, eff={havoc_damage/cost if cost > 0 else 'inf'}")
                if cost > 0:
                    efficiency = havoc_damage / cost
                else:
                    efficiency = float('inf')
                attack_cards.append((card, cost, havoc_damage, efficiency))
            elif (
                havoc_exhaust_damage := self._havoc_top_exhaust_juggernaut_damage_potential(
                    card,
                    context,
                    available_energy,
                )
            ) > 0:
                cost = self._lethal_card_cost(card, context, available_energy)
                logger.info(f"[LETHAL_CALC] {card.name}: cost={cost}, havoc_top_exhaust_juggernaut_damage={havoc_exhaust_damage}, eff={havoc_exhaust_damage/cost if cost > 0 else 'inf'}")
                if cost > 0:
                    efficiency = havoc_exhaust_damage / cost
                else:
                    efficiency = float('inf')
                attack_cards.append((card, cost, havoc_exhaust_damage, efficiency))
            elif (
                charons_ashes_damage := self._charons_ashes_damage_potential(
                    card,
                    context,
                    available_energy,
                )
            ) > 0:
                cost = self._lethal_card_cost(
                    card,
                    context,
                    available_energy,
                    self._context_corruption_active(context),
                )
                logger.info(f"[LETHAL_CALC] {card.name}: cost={cost}, charons_ashes_damage={charons_ashes_damage}, eff={charons_ashes_damage/cost if cost > 0 else 'inf'}")
                if cost > 0:
                    efficiency = charons_ashes_damage / cost
                else:
                    efficiency = float('inf')
                attack_cards.append((card, cost, charons_ashes_damage, efficiency))
            elif juggernaut_damage > 0:
                cost = self._lethal_card_cost(card, context, available_energy)
                damage = juggernaut_damage
                logger.info(f"[LETHAL_CALC] {card.name}: cost={cost}, juggernaut_damage={damage}, eff={damage/cost if cost > 0 else 'inf'}")
                if cost > 0:
                    efficiency = damage / cost
                else:
                    efficiency = float('inf')
                attack_cards.append((card, cost, damage, efficiency))

        def greedy_total(candidates):
            selected_damage = 0
            remaining_energy = available_energy
            nunchaku_counter = self._context_relic_counter(context, 'Nunchaku')
            duplication_charges = self._context_duplication_charges(context)
            selected_cards = []
            for card, cost, damage, _ in candidates:
                if cost <= remaining_energy:
                    card_play_repeats = self._lethal_card_play_repeats(
                        duplication_charges
                    )
                    damage_repeats = card_play_repeats if is_attack_card(card) else 1
                    selected_damage += damage * damage_repeats
                    remaining_energy -= cost
                    selected_cards.append(card.name)
                    if is_attack_card(card) or self._havoc_top_attack_card(card, context) is not None:
                        attack_plays = damage_repeats if is_attack_card(card) else 1
                        nunchaku_energy_gain, nunchaku_counter = (
                            self._nunchaku_energy_after_attack_plays(
                                nunchaku_counter,
                                attack_plays,
                            )
                        )
                        remaining_energy += nunchaku_energy_gain
                    duplication_charges = self._duplication_charges_after_card(
                        duplication_charges
                    )
                elif cost == 0:
                    selected_damage += damage
                    selected_cards.append(card.name)
            return selected_damage, available_energy - remaining_energy, selected_cards

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

        logger.info(f"[LETHAL_CALC] Selected: {selected}, total_damage={total_damage}, energy_used={energy_used}/{available_energy}")
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
            vulnerable = self._monster_vulnerable_stacks(context, monster_idx) > 0
            player_weak = self._player_is_weak(context)
            if vulnerable and player_weak:
                damage = self._apply_weak_and_vulnerable_to_card_damage(
                    card,
                    context,
                    base_damage,
                    available_energy,
                    monster_idx,
                )
            else:
                damage = self._apply_player_weak_to_card_damage(
                    card,
                    context,
                    damage,
                    available_energy,
                    monster_idx,
                )
            if vulnerable and not player_weak:
                damage = self._apply_vulnerable_to_card_damage(
                    card,
                    context,
                    damage,
                    available_energy,
                    monster_idx,
                )
            total += damage
        return total

    def _can_target_all_monsters(
        self,
        context: DecisionContext,
        affordable_damage: int,
        available_energy: Optional[int] = None,
    ) -> bool:
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
        available_energy = (
            max(0, self._safe_int(getattr(context, 'energy_available', 0), default=0))
            if available_energy is None
            else max(0, self._safe_int(available_energy, default=0))
        )

        # Count attacks by targeting behavior
        attack_cards = []
        aoe_cards = []
        single_target_count = 0

        for card in context.playable_cards:
            if is_attack_card(card):
                attack_cards.append(card)
                if self._is_aoe_attack(card):
                    aoe_cards.append(card)
                elif self._card_requires_target(card):
                    single_target_count += 1

        for card in aoe_cards:
            cost = effective_card_cost(card, available_energy)
            if cost <= available_energy and self._aoe_card_kills_all(
                card,
                context,
                available_energy,
            ):
                return True

        if aoe_cards and self._find_aoe_cleanup_sequence(
            context,
            attack_cards,
            available_energy,
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
            total_monster_hp = sum(
                self._monster_hp_with_block(monster)
                for monster in context.monsters_alive
            )
            return affordable_damage >= total_monster_hp * 1.3
        else:
            # Need 50% more damage for 3+ monsters
            total_monster_hp = sum(
                self._monster_hp_with_block(monster)
                for monster in context.monsters_alive
            )
            return affordable_damage >= total_monster_hp * 1.5

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
            if is_attack_card(card):
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
        base_damage_bonus: int = 0,
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
        upgrades = card_upgrade_count(card)
        display_name = getattr(card, 'name', None) or card_name
        if upgrades > 0 and '+' not in display_name:
            upgrade_suffix = f"+{upgrades}" if card_name == 'Searing Blow' and upgrades > 1 else '+'
            display_name = f"{card_name}{upgrade_suffix}"
        base_damage = 0

        card_data = self.game_data_loader.get_card_data(card_name)
        if card_data:
            damage_data = dict(card_data)
            damage_data['name'] = display_name
            base_damage = self.game_data_loader._parse_card_damage(damage_data) or 0
            base_damage = self._apply_known_damage_upgrade_fallback(
                card,
                card_name,
                card_data,
                base_damage,
            )

        if card_name == 'Body Slam':
            base_damage = player_block_value(context)

        if card_name == 'Mind Blast':
            base_damage = draw_pile_count(context)

        if card_name == 'Ritual Dagger':
            base_damage += self._positive_card_misc(card)

        if card_name == 'Whirlwind':
            energy = x_effect_energy(
                card,
                context.energy_available if available_energy is None else available_energy,
                context,
            )
            strength = getattr(context, 'strength', 0) if strength_override is None else strength_override
            return whirlwind_damage(card, energy, strength)

        if is_attack_card(card):
            strength = getattr(context, 'strength', 0) if strength_override is None else strength_override
            if card_name == 'Heavy Blade':
                base_damage += strength * heavy_blade_strength_multiplier(card)
            elif card_name == 'Perfected Strike':
                base_damage += strike_card_count(context) * perfected_strike_bonus_per_strike(card) + strength
            else:
                base_damage += strength
            base_damage += base_damage_bonus

            base_damage *= self._get_attack_hit_count(
                card,
                context,
                monster_idx,
                available_energy,
                fiend_fire_exhaust_count,
            )

        return max(0, base_damage)

    def _apply_known_damage_upgrade_fallback(
        self,
        card: Card,
        card_name: str,
        card_data: dict,
        parsed_damage: int,
    ) -> int:
        upgrade_bonus = known_damage_upgrade_bonus(card, card_name)
        if upgrade_bonus <= 0:
            return parsed_damage

        base_damage_data = dict(card_data)
        base_damage_data['name'] = card_name
        base_damage = self.game_data_loader._parse_card_damage(base_damage_data) or 0
        if parsed_damage > 0 and parsed_damage == base_damage:
            return parsed_damage + upgrade_bonus
        return parsed_damage

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
        if not self._player_is_weak(context):
            return total_damage

        return self._apply_damage_multiplier_per_hit(
            card,
            context,
            total_damage,
            available_energy,
            numerator=3,
            denominator=4,
            monster_idx=monster_idx,
            fiend_fire_exhaust_count=fiend_fire_exhaust_count,
        )

    def _apply_weak_and_vulnerable_to_card_damage(
        self,
        card: Card,
        context: DecisionContext,
        total_damage: int,
        available_energy: int,
        monster_idx: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
    ) -> int:
        """Apply combined Weak+Vulnerable before final integer truncation."""
        numerator, denominator = (
            (21, 16)
            if self._context_has_relic(context, 'Paper Phrog')
            else (9, 8)
        )
        return self._apply_damage_multiplier_per_hit(
            card,
            context,
            total_damage,
            available_energy,
            numerator=numerator,
            denominator=denominator,
            monster_idx=monster_idx,
            fiend_fire_exhaust_count=fiend_fire_exhaust_count,
        )

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
        numerator, denominator = (
            (7, 4)
            if self._context_has_relic(context, 'Paper Phrog')
            else (3, 2)
        )
        return self._apply_damage_multiplier_per_hit(
            card,
            context,
            total_damage,
            available_energy,
            numerator=numerator,
            denominator=denominator,
            monster_idx=monster_idx,
            fiend_fire_exhaust_count=fiend_fire_exhaust_count,
        )

    def _apply_damage_multiplier_per_hit(
        self,
        card: Card,
        context: DecisionContext,
        total_damage: int,
        available_energy: int,
        numerator: int,
        denominator: int,
        monster_idx: Optional[int] = None,
        fiend_fire_exhaust_count: Optional[int] = None,
    ) -> int:
        hit_count = self._get_vulnerable_damage_instance_count(
            card,
            context,
            available_energy,
            monster_idx,
            fiend_fire_exhaust_count,
        )
        if hit_count <= 1:
            return total_damage * numerator // denominator

        per_hit_damage, remainder = divmod(total_damage, hit_count)
        if remainder != 0:
            return total_damage * numerator // denominator

        return per_hit_damage * numerator // denominator * hit_count

    def _player_is_weak(self, context: DecisionContext) -> bool:
        return self._get_player_debuff_stacks(context, 'Weak') > 0

    def _player_is_entangled(self, context: DecisionContext) -> bool:
        return (
            self._get_player_debuff_stacks(context, 'Entangled') > 0
            or player_has_power(context, 'Entangled')
        )

    def _nunchaku_energy_after_attack_plays(
        self,
        counter: Optional[int],
        attack_plays: int,
    ) -> Tuple[int, Optional[int]]:
        if counter is None or attack_plays <= 0:
            return 0, counter

        energy_gain = 0
        next_counter = max(0, self._safe_int(counter, default=0))
        for _ in range(attack_plays):
            if next_counter >= 9:
                energy_gain += 1
                next_counter = 0
            else:
                next_counter = min(9, next_counter + 1)
        return energy_gain, next_counter

    @staticmethod
    def _context_relic_counter(context: DecisionContext, relic_name: str) -> Optional[int]:
        target = ''.join(ch for ch in relic_name.lower() if ch.isalnum())
        if not target:
            return None

        relics = []
        for source in (getattr(context, 'game', None), context):
            relics.extend(getattr(source, 'relics', []) or [])

        for relic in relics:
            for attr in ('name', 'relic_id', 'id'):
                value = getattr(relic, attr, None)
                if value is None:
                    continue
                normalized = ''.join(ch for ch in str(value).lower() if ch.isalnum())
                if normalized == target:
                    return coerce_int(getattr(relic, 'counter', 0), 0)
        return None

    @staticmethod
    def _context_has_relic(context: DecisionContext, relic_name: str) -> bool:
        target = ''.join(ch for ch in relic_name.lower() if ch.isalnum())
        if not target:
            return False

        relics = []
        for source in (getattr(context, 'game', None), context):
            relics.extend(getattr(source, 'relics', []) or [])

        for relic in relics:
            for attr in ('name', 'relic_id', 'id'):
                value = getattr(relic, attr, None)
                if value is None:
                    continue
                normalized = ''.join(ch for ch in str(value).lower() if ch.isalnum())
                if normalized == target:
                    return True
        return False

    @staticmethod
    def _context_has_the_boot(context: DecisionContext) -> bool:
        return (
            CombatEndingDetector._context_has_relic(context, 'The Boot')
            or CombatEndingDetector._context_has_relic(context, 'Boot')
        )

    def _apply_the_boot_minimum_attack_damage(
        self,
        context: DecisionContext,
        total_damage: int,
        hit_count: int,
    ) -> int:
        if not self._context_has_the_boot(context):
            return max(0, total_damage)

        return sum(
            THE_BOOT_MINIMUM_DAMAGE
            if 0 < damage_instance < THE_BOOT_MINIMUM_DAMAGE
            else max(0, damage_instance)
            for damage_instance in self._damage_instances(total_damage, hit_count)
        )

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
        return player_debuff_stacks(context, power_name)

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        return coerce_float(value, default)

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        return coerce_int(value, default)

    def _all_alive_targets_poisoned(self, context: DecisionContext) -> bool:
        monsters = getattr(context, 'monsters_alive', []) or []
        alive_monsters = [
            monster for monster in monsters
            if self._safe_int(getattr(monster, 'current_hp', 0), default=0) > 0
        ]
        if not alive_monsters:
            return False

        return all(
            self._get_monster_power_amount(monster, 'Poison') > 0
            for monster in alive_monsters
        )

    def _get_monster_power_amount(self, monster, power_name: str) -> int:
        return monster_power_amount(monster, power_name)

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
        fixed_hit_count = fixed_attack_hit_count(card)
        if fixed_hit_count is not None:
            return fixed_hit_count

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
        if card_name == 'Fiend Fire':
            if fiend_fire_exhaust_count is not None:
                return fiend_fire_exhaust_count
            return context_fiend_fire_exhaust_count(card, context)

        return 1
