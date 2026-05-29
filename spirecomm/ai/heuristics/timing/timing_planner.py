"""
Timing-Aware Combat Planner - Integrates timing analysis with beam search.

This module bridges the timing strategy layer with the existing combat simulation,
enabling dynamic weight adjustment based on turn timing classification.
"""

import logging
from typing import List, Optional

from .models import TimingContext, TurnTiming, BalanceWeights
from .turn_classifier import TurnTimingClassifier
from .balance_strategy import CombatBalanceStrategy
from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_costs import (
    effective_card_cost,
    energy_refund_for_card,
    playable_card_cost_after_refund,
    whirlwind_damage,
    x_effect_energy,
)
from spirecomm.ai.heuristics.simulation import BLOCK_UPGRADE_BONUS, _known_damage_upgrade_bonus
from spirecomm.data.loader import game_data_loader
from spirecomm.spire.card import CardType

logger = logging.getLogger(__name__)

TARGETED_LETHAL_MAX_CARDS = 8
TARGETED_LETHAL_MAX_MONSTERS = 4


class TimingAwareCombatPlanner:
    """
    Integrates timing analysis into combat planning.

    This planner:
    1. Classifies turn timing using TurnTimingClassifier
    2. Gets appropriate balance weights from CombatBalanceStrategy
    3. Applies dynamic weights to beam search scoring
    4. Implements opportunistic lethal detection

    The planner wraps the existing FastCombatSimulator and enhances it
    with timing-aware decision making.
    """

    def __init__(
        self,
        base_planner=None,
        classifier: Optional[TurnTimingClassifier] = None,
        strategy: Optional[CombatBalanceStrategy] = None
    ):
        """
        Initialize timing-aware planner.

        Args:
            base_planner: Existing FastCombatSimulator to enhance (None = standalone)
            classifier: Turn timing classifier (default: create new)
            strategy: Balance strategy (default: create new)
        """
        self.base_planner = base_planner
        self.classifier = classifier or TurnTimingClassifier()
        self.strategy = strategy or CombatBalanceStrategy()

        # Cache for timing analysis (per turn)
        self._timing_cache = {}
        self._current_turn = 0

    def plan_with_timing(self, context) -> List:
        """
        Plan combat actions with timing awareness.

        This is the main entry point that replaces the standard plan_turn() call.

        Args:
            context: Decision context with game state

        Returns:
            List of actions to execute
        """
        # Check cache first
        current_turn = getattr(context, 'turn', 1)
        if current_turn == self._current_turn and hasattr(self, '_cached_actions'):
            return self._cached_actions

        # Step 1: Classify turn timing
        timing_ctx = self.classifier.classify_turn(context)

        # Log timing classification
        logger.info(
            f"[TIMING_PLANNER] Turn {current_turn}: {timing_ctx.turn_timing.value}, "
            f"current_damage={timing_ctx.current_damage}, "
            f"weights=(damage={timing_ctx.balance_weights.damage_weight:.2f}, "
            f"block={timing_ctx.balance_weights.block_weight:.2f})"
        )

        # Step 2: Check for lethal first (opportunistic philosophy)
        if self._can_kill_all_this_turn(context, timing_ctx):
            logger.info("[TIMING_PLANNER] Lethal detected - all-in attack sequence")
            actions = self._generate_lethal_sequence(context)
            self._cached_actions = actions
            self._current_turn = current_turn
            return actions

        # Step 3: Use base planner with timing weights
        if self.base_planner:
            # Store timing context for use in scoring
            if hasattr(self.base_planner, 'set_timing_context'):
                self.base_planner.set_timing_context(timing_ctx)

            # Plan with timing-aware scoring
            actions = self.base_planner.plan_turn(context)
        else:
            # Fallback: simple greedy plan
            actions = self._fallback_plan(context, timing_ctx)

        # Cache and return
        self._cached_actions = actions
        self._current_turn = current_turn
        return actions

    def get_timing_context(self, context) -> TimingContext:
        """
        Get timing classification for current context.

        Useful for debugging and logging.

        Args:
            context: Decision context

        Returns:
            TimingContext with full timing analysis
        """
        return self.classifier.classify_turn(context)

    def _can_kill_all_this_turn(self, context, timing_ctx: TimingContext) -> bool:
        """
        Check if we can kill all monsters this turn.

        Implements opportunistic philosophy: always check for lethal.

        Args:
            context: Decision context
            timing_ctx: Timing context

        Returns:
            True if lethal is possible
        """
        try:
            monsters = getattr(context, 'monsters_alive', [])
            if not monsters:
                return True  # No monsters = already lethal

            # Get playable cards
            playable_cards = getattr(context, 'playable_cards', [])
            if not playable_cards:
                return False

            targeted_sequence = self._find_targeted_lethal_sequence(
                context,
                playable_cards,
                monsters,
                getattr(context, 'energy_available', 3),
            )
            if targeted_sequence:
                return True

            # Calculate damage options, then choose a lethal affordable subset.
            damage_options = []
            energy = getattr(context, 'energy_available', 3)

            for card in playable_cards:
                # Simple estimate: use card's base damage
                card_damage = self._estimate_card_damage(card, context)
                if card_damage > 0:
                    if not self._can_use_scalar_damage_option(card, monsters):
                        continue
                    cost = self._card_energy_cost_for_targets(
                        card,
                        context,
                        monsters,
                        energy,
                    )
                    if cost > energy:
                        continue

                    effect_type = 'aoe' if self._is_card_aoe(card) else 'single'
                    card_damage = self._apply_attack_status_modifiers(
                        card,
                        context,
                        card_damage,
                        energy,
                        monsters,
                    )
                    damage_options.append((effect_type, card_damage, cost))

            monster_hp = [
                m.current_hp + getattr(m, 'block', 0)
                for m in monsters
                if hasattr(m, 'current_hp')
            ]

            can_kill = self._affordable_damage_effects_can_kill_all(
                damage_options,
                monster_hp,
                energy,
            )

            if can_kill:
                logger.debug(
                    f"[LETHAL_CHECK] Possible! options={damage_options}, hp={sum(monster_hp)}"
                )

            return can_kill

        except Exception as e:
            logger.warning(f"[LETHAL_CHECK] Failed: {e}")
            return False

    def _generate_lethal_sequence(self, context) -> List:
        """
        Generate all-in attack sequence for lethal.

        Args:
            context: Decision context

        Returns:
            List of attack actions
        """
        try:
            from spirecomm.communication.action import PlayCardAction

            playable_cards = getattr(context, 'playable_cards', [])
            monsters = getattr(context, 'monsters_alive', [])

            if not playable_cards or not monsters:
                return []

            targeted_sequence = self._find_targeted_lethal_sequence(
                context,
                playable_cards,
                monsters,
                getattr(context, 'energy_available', 3),
            )
            if targeted_sequence:
                return targeted_sequence

            attack_options = []
            for card in playable_cards:
                damage = self._estimate_card_damage(card, context)
                if damage > 0:
                    if not self._can_use_scalar_damage_option(card, monsters):
                        continue
                    energy_available = getattr(context, 'energy_available', 3)
                    cost = self._card_energy_cost_for_targets(
                        card,
                        context,
                        monsters,
                        energy_available,
                    )
                    effect_type = 'aoe' if self._is_card_aoe(card) else 'single'
                    damage = self._apply_attack_status_modifiers(
                        card,
                        context,
                        damage,
                        energy_available,
                        monsters,
                    )
                    attack_options.append((card, effect_type, damage, cost))

            monster_hp = [
                max(0, getattr(monster, 'current_hp', 0) + getattr(monster, 'block', 0))
                for monster in monsters
            ]
            selected_options = self._find_affordable_lethal_card_options(
                attack_options,
                monster_hp,
                getattr(context, 'energy_available', 3),
            )
            if not selected_options:
                return []

            # Generate actions from the proven lethal subset when one exists.
            actions = []
            energy = getattr(context, 'energy_available', 3)
            remaining_hp = list(monster_hp)

            for card, _effect_type, damage, _planned_cost in selected_options:
                cost = self._card_energy_cost_for_targets(
                    card,
                    context,
                    monsters,
                    energy,
                )

                if energy >= cost:
                    action_target = None
                    if self._is_card_aoe(card):
                        remaining_hp = [
                            max(0, hp - damage)
                            for hp in remaining_hp
                        ]
                    elif getattr(card, 'has_target', False):
                        live_targets = [
                            (hp, idx)
                            for idx, hp in enumerate(remaining_hp)
                            if hp > 0
                        ]
                        if not live_targets:
                            break
                        _hp, target_idx = max(
                            live_targets,
                            key=lambda item: (item[0], -item[1]),
                        )
                        action_target = monsters[target_idx]
                        remaining_hp[target_idx] = max(0, remaining_hp[target_idx] - damage)
                    actions.append(PlayCardAction(card=card, target_monster=action_target))
                    energy -= cost

                if energy <= 0:
                    break

            logger.info(f"[LETHAL_SEQUENCE] Generated {len(actions)} attack actions")
            return actions

        except Exception as e:
            logger.warning(f"[LETHAL_SEQUENCE] Failed: {e}")
            return []

    def _fallback_plan(self, context, timing_ctx: TimingContext) -> List:
        """
        Fallback simple plan when base planner is unavailable.

        Uses timing weights to make greedy card choices.

        Args:
            context: Decision context
            timing_ctx: Timing context

        Returns:
            List of actions
        """
        try:
            from spirecomm.communication.action import PlayCardAction

            playable_cards = getattr(context, 'playable_cards', [])
            if not playable_cards:
                return []

            # Score cards based on timing weights
            weights = timing_ctx.balance_weights
            best_card = None
            best_score = float('-inf')
            energy = getattr(context, 'energy_available', 3)
            monsters = getattr(context, 'monsters_alive', [])

            for card in playable_cards:
                score = 0

                # Check if card deals damage
                damage = self._estimate_card_damage(card, context)
                if damage > 0:
                    damage = self._apply_attack_status_modifiers(
                        card,
                        context,
                        damage,
                        energy,
                        monsters,
                    )
                score += damage * weights.damage_weight

                # Check if card provides block
                block = self._estimate_card_block(card, context)
                score += block * weights.block_weight

                if score > best_score:
                    best_score = score
                    best_card = card

            if best_card:
                # Find target if needed
                target = None
                if getattr(best_card, 'has_target', False) and not self._is_card_aoe(best_card):
                    target = monsters[0] if monsters else None

                return [PlayCardAction(card=best_card, target_monster=target)]

            return []

        except Exception as e:
            logger.warning(f"[FALLBACK_PLAN] Failed: {e}")
            return []

    def _damage_effects_can_kill_all(self, damage_effects, monster_hp) -> bool:
        """Check whether single-target and AOE damage can cover each monster HP pool."""
        remaining = tuple(sorted((hp for hp in monster_hp if hp > 0), reverse=True))
        effects = tuple(
            (effect_type, int(damage))
            for effect_type, damage in damage_effects
            if damage > 0
        )

        if not remaining:
            return True
        total_potential = sum(
            damage * len(remaining) if effect_type == 'aoe' else damage
            for effect_type, damage in effects
        )
        if total_potential < sum(remaining):
            return False

        seen = set()

        def search(effect_index, hp_state):
            if not hp_state:
                return True
            if effect_index >= len(effects):
                return False

            key = (effect_index, hp_state)
            if key in seen:
                return False
            seen.add(key)

            effect_type, damage = effects[effect_index]

            # It can be correct to leave a high-overkill hit unused.
            if search(effect_index + 1, hp_state):
                return True

            if effect_type == 'aoe':
                next_hp = [max(0, hp - damage) for hp in hp_state]
                next_state = tuple(sorted((hp for hp in next_hp if hp > 0), reverse=True))
                return search(effect_index + 1, next_state)

            tried_hp = set()
            for idx, hp in enumerate(hp_state):
                if hp in tried_hp:
                    continue
                tried_hp.add(hp)

                next_hp = list(hp_state)
                next_hp[idx] = max(0, next_hp[idx] - damage)
                next_state = tuple(sorted((value for value in next_hp if value > 0), reverse=True))
                if search(effect_index + 1, next_state):
                    return True

            return False

        return search(0, remaining)

    def _find_affordable_lethal_card_options(self, card_options, monster_hp, energy):
        """Return an affordable card subset whose damage effects kill all monsters."""
        starting_energy = max(0, int(energy))
        def option_sort_key(option):
            card, _effect_type, damage, cost = option
            upfront_cost = effective_card_cost(card, starting_energy)
            refunds_energy = cost < upfront_cost
            return (0 if refunds_energy else 1, cost, -damage)

        options = tuple(sorted(
            (
                (card, effect_type, int(damage), max(0, int(cost)))
                for card, effect_type, damage, cost in card_options
                if damage > 0
            ),
            key=option_sort_key,
        ))
        seen = set()

        def selected_effects(selected_options):
            return tuple(
                (effect_type, damage)
                for _card, effect_type, damage, _cost in selected_options
            )

        def search(option_index, remaining_energy, selected_options):
            if self._damage_effects_can_kill_all(selected_effects(selected_options), monster_hp):
                return selected_options
            if option_index >= len(options):
                return None

            key = (option_index, remaining_energy, selected_effects(selected_options))
            if key in seen:
                return None
            seen.add(key)

            card, effect_type, damage, cost = options[option_index]
            if cost <= remaining_energy:
                with_card = selected_options + ((card, effect_type, damage, cost),)
                result = search(option_index + 1, remaining_energy - cost, with_card)
                if result is not None:
                    return result

            return search(option_index + 1, remaining_energy, selected_options)

        return search(0, starting_energy, ())

    def _card_energy_cost_for_targets(self, card, context, monsters, available_energy: int) -> int:
        return playable_card_cost_after_refund(
            card,
            available_energy,
            self._card_energy_refund_for_targets(card, context, monsters),
        )

    def _card_energy_refund_for_targets(self, card, context, monsters) -> int:
        return energy_refund_for_card(
            card,
            target_vulnerable=self._all_alive_targets_vulnerable(context, monsters),
        )

    def _can_use_scalar_damage_option(self, card, monsters) -> bool:
        if len(monsters) <= 1:
            return True
        return self._is_card_aoe(card) or getattr(card, 'has_target', False)

    def _affordable_damage_effects_can_kill_all(self, damage_options, monster_hp, energy) -> bool:
        """Check whether any affordable subset of damage effects can kill all monsters."""
        options = tuple(
            (effect_type, int(damage), max(0, int(cost)))
            for effect_type, damage, cost in damage_options
            if damage > 0
        )
        starting_energy = max(0, int(energy))
        seen = set()

        def search(option_index, remaining_energy, selected_effects):
            if self._damage_effects_can_kill_all(selected_effects, monster_hp):
                return True
            if option_index >= len(options):
                return False

            key = (option_index, remaining_energy, selected_effects)
            if key in seen:
                return False
            seen.add(key)

            if search(option_index + 1, remaining_energy, selected_effects):
                return True

            effect_type, damage, cost = options[option_index]
            if cost <= remaining_energy:
                next_effects = selected_effects + ((effect_type, damage),)
                if search(option_index + 1, remaining_energy - cost, next_effects):
                    return True

            return False

        return search(0, starting_energy, ())

    def _find_targeted_lethal_sequence(
        self,
        context,
        playable_cards,
        monsters,
        available_energy: int,
    ) -> List:
        """Prove a lethal line with target-specific status effects."""
        from spirecomm.communication.action import PlayCardAction

        attack_cards = [
            card
            for card in playable_cards
            if self._estimate_card_damage(card, context, available_energy) > 0
        ]
        if not attack_cards or not monsters:
            return []
        if (
            len(attack_cards) > TARGETED_LETHAL_MAX_CARDS
            or len(monsters) > TARGETED_LETHAL_MAX_MONSTERS
        ):
            return []

        starting_hp = tuple(
            max(0, getattr(monster, 'current_hp', 0) + getattr(monster, 'block', 0))
            for monster in monsters
        )
        seen = set()

        def search(remaining_cards, hp_state, remaining_energy):
            if all(hp <= 0 for hp in hp_state):
                return []

            state_key = (
                tuple(self._card_play_key(card) for card in remaining_cards),
                hp_state,
                remaining_energy,
            )
            if state_key in seen:
                return None
            seen.add(state_key)

            candidates = []
            for card_pos, card in enumerate(remaining_cards):
                if self._is_card_aoe(card):
                    cost = effective_card_cost(card, remaining_energy)
                    if cost > remaining_energy:
                        continue

                    next_hp = list(hp_state)
                    total_damage = 0
                    kill_count = 0
                    for monster_idx, hp in enumerate(hp_state):
                        if hp <= 0:
                            continue

                        damage = self._card_damage_against_monster(
                            card,
                            context,
                            monsters,
                            monster_idx,
                            remaining_energy,
                        )
                        if damage <= 0:
                            continue

                        total_damage += min(hp, damage)
                        if damage >= hp:
                            kill_count += 1
                        next_hp[monster_idx] = max(0, hp - damage)

                    if total_damage <= 0:
                        continue

                    priority = (
                        kill_count,
                        0,
                        total_damage,
                        -cost,
                    )
                    candidates.append((
                        priority,
                        card_pos,
                        None,
                        cost,
                        tuple(next_hp),
                    ))
                    continue

                if not getattr(card, 'has_target', False):
                    continue

                for monster_idx, hp in enumerate(hp_state):
                    if hp <= 0:
                        continue

                    cost = self._card_energy_cost_against_monster(
                        card,
                        context,
                        monsters,
                        monster_idx,
                        remaining_energy,
                    )
                    if cost > remaining_energy:
                        continue

                    damage = self._card_damage_against_monster(
                        card,
                        context,
                        monsters,
                        monster_idx,
                        remaining_energy,
                    )
                    if damage <= 0:
                        continue

                    next_hp = list(hp_state)
                    next_hp[monster_idx] = max(0, hp - damage)
                    refunds_energy = self._card_energy_refund_against_monster(
                        card,
                        context,
                        monsters,
                        monster_idx,
                    ) > 0
                    priority = (
                        1 if damage >= hp else 0,
                        1 if refunds_energy else 0,
                        damage,
                        -cost,
                    )
                    candidates.append((
                        priority,
                        card_pos,
                        monster_idx,
                        cost,
                        tuple(next_hp),
                    ))

            candidates.sort(key=lambda item: item[0], reverse=True)

            for _priority, card_pos, monster_idx, cost, next_hp in candidates:
                card = remaining_cards[card_pos]
                next_cards = remaining_cards[:card_pos] + remaining_cards[card_pos + 1:]
                tail = search(next_cards, next_hp, remaining_energy - cost)
                if tail is not None:
                    target_monster = (
                        None
                        if monster_idx is None
                        else monsters[monster_idx]
                    )
                    return [
                        PlayCardAction(
                            card=card,
                            target_monster=target_monster,
                        )
                    ] + tail

            return None

        sequence = search(tuple(attack_cards), starting_hp, max(0, int(available_energy)))
        return sequence or []

    @staticmethod
    def _card_play_key(card):
        return getattr(card, 'uuid', None) or id(card)

    def _card_damage_against_monster(
        self,
        card,
        context,
        monsters,
        monster_idx: int,
        available_energy: int,
    ) -> int:
        damage = self._estimate_card_damage(card, context, available_energy)
        if self._get_player_debuff_stacks(context, 'Weak') > 0:
            damage = self._apply_per_hit_damage_multiplier(
                card,
                context,
                damage,
                available_energy,
                0.75,
            )

        if self._monster_vulnerable_stacks(context, monsters, monster_idx) > 0:
            damage = self._apply_per_hit_damage_multiplier(
                card,
                context,
                damage,
                available_energy,
                1.5,
            )

        return max(0, int(damage))

    def _card_energy_cost_against_monster(
        self,
        card,
        context,
        monsters,
        monster_idx: int,
        available_energy: int,
    ) -> int:
        return playable_card_cost_after_refund(
            card,
            available_energy,
            self._card_energy_refund_against_monster(card, context, monsters, monster_idx),
        )

    def _card_energy_refund_against_monster(
        self,
        card,
        context,
        monsters,
        monster_idx: int,
    ) -> int:
        return energy_refund_for_card(
            card,
            target_vulnerable=self._monster_vulnerable_stacks(
                context,
                monsters,
                monster_idx,
            ) > 0,
        )

    def _single_target_damage_can_kill_all(self, damage_instances, monster_hp) -> bool:
        """Check whether single-target damage instances can cover each monster HP pool."""
        effects = [('single', damage) for damage in damage_instances]
        return self._damage_effects_can_kill_all(effects, monster_hp)

    def _is_card_aoe(self, card) -> bool:
        """Check card data for damage that applies to every monster."""
        try:
            card_name = canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                return game_data_loader._is_card_aoe(card_data)
        except Exception:
            pass

        return False

    def _estimate_card_damage(self, card, context, available_energy=None) -> int:
        """Estimate card damage for timing decisions from methods or parsed data."""
        if getattr(card, 'type', None) not in (None, CardType.ATTACK):
            return 0

        if hasattr(card, 'damage_for'):
            try:
                strength = getattr(context, 'strength', 0)
                return max(0, int(card.damage_for(getattr(context, 'turn', 1), strength)))
            except Exception:
                pass

        card_name = canonical_card_name(card)
        strength = getattr(context, 'strength', 0)
        energy_for_x = (
            getattr(context, 'energy_available', 0)
            if available_energy is None
            else available_energy
        )

        if card_name == 'Whirlwind':
            energy = x_effect_energy(card, energy_for_x, context)
            return whirlwind_damage(card, energy, strength)
        if card_name == 'Body Slam':
            return max(0, self._get_player_block(context) + strength)

        base_damage = getattr(card, 'damage', 0) or 0
        if base_damage <= 0:
            try:
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    parsed_damage = game_data_loader._parse_card_damage(card_data)
                    if parsed_damage is not None:
                        base_damage = parsed_damage + _known_damage_upgrade_bonus(card, card_name)
            except Exception:
                base_damage = 0

        if base_damage <= 0:
            return 0

        scaled_damage = self._apply_attack_damage_scaling(card, base_damage, strength, context)
        hit_count = self._get_attack_hit_count(card, context, energy_for_x)
        return max(0, int(scaled_damage * hit_count))

    def _apply_attack_status_modifiers(
        self,
        card,
        context,
        total_damage: int,
        available_energy: int,
        monsters,
    ) -> int:
        """Apply combat status modifiers that are safe for scalar damage estimates."""
        damage = max(0, int(total_damage))
        if self._get_player_debuff_stacks(context, 'Weak') > 0:
            damage = self._apply_per_hit_damage_multiplier(
                card,
                context,
                damage,
                available_energy,
                0.75,
            )

        if self._all_alive_targets_vulnerable(context, monsters):
            damage = self._apply_per_hit_damage_multiplier(
                card,
                context,
                damage,
                available_energy,
                1.5,
            )

        return max(0, int(damage))

    def _apply_per_hit_damage_multiplier(
        self,
        card,
        context,
        total_damage: int,
        available_energy: int,
        multiplier: float,
    ) -> int:
        hit_count = self._get_damage_instance_count(card, context, available_energy)
        if hit_count <= 1:
            return int(total_damage * multiplier)

        per_hit_damage, remainder = divmod(total_damage, hit_count)
        if remainder != 0:
            return int(total_damage * multiplier)

        return int(per_hit_damage * multiplier) * hit_count

    def _get_damage_instance_count(self, card, context, available_energy: int) -> int:
        card_name = canonical_card_name(card)
        if card_name in {'Skewer', 'Whirlwind'}:
            return max(1, x_effect_energy(card, available_energy, context))

        return max(1, self._get_attack_hit_count(card, context))

    def _get_player_debuff_stacks(self, context, power_name: str) -> int:
        player = getattr(getattr(context, 'game', None), 'player', None)
        powers = getattr(player, 'powers', []) if player is not None else []
        for power in powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 1
        return 0

    def _get_player_power_amount(self, context, power_name: str) -> int:
        player = getattr(getattr(context, 'game', None), 'player', None)
        powers = getattr(player, 'powers', []) if player is not None else []
        for power in powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 0
        return 0

    def _power_name(self, power):
        return (
            getattr(power, 'name', None)
            or getattr(power, 'power_name', None)
            or getattr(power, 'power_id', None)
        )

    def _all_alive_targets_vulnerable(self, context, monsters) -> bool:
        alive_targets = [
            index for index, monster in enumerate(monsters)
            if getattr(monster, 'current_hp', 0) > 0
        ]
        if not alive_targets:
            return False

        return all(
            self._monster_vulnerable_stacks(context, monsters, index) > 0
            for index in alive_targets
        )

    def _monster_vulnerable_stacks(self, context, monsters, monster_idx: int) -> int:
        vulnerable_stacks = getattr(context, 'vulnerable_stacks', {}) or {}
        stacks = vulnerable_stacks.get(monster_idx, 0)
        if stacks:
            return stacks

        if 0 <= monster_idx < len(monsters):
            return self._get_monster_power_amount(monsters[monster_idx], 'Vulnerable')

        return 0

    def _all_alive_targets_poisoned(self, context) -> bool:
        """Return True only when every live target is known to have Poison."""
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

    def _apply_attack_damage_scaling(self, card, base_damage: int, strength: int, context) -> int:
        """Apply non-standard attack damage scaling for timing estimates."""
        card_name = canonical_card_name(card)

        if card_name == 'Heavy Blade':
            multiplier = 5 if getattr(card, 'upgrades', 0) > 0 else 3
            return base_damage + strength * multiplier
        if card_name == 'Perfected Strike':
            per_strike_bonus = 3 if getattr(card, 'upgrades', 0) > 0 else 2
            return base_damage + self._count_strike_cards(context) * per_strike_bonus + strength

        return base_damage + strength

    def _count_strike_cards(self, context) -> int:
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

        return max(0, count)

    def _get_player_block(self, context) -> int:
        """Return current player block from common decision-context shapes."""
        block = getattr(context, 'player_block', None)
        if block is None:
            player = getattr(getattr(context, 'game', None), 'player', None)
            block = getattr(player, 'block', 0)

        try:
            return max(0, int(block or 0))
        except (TypeError, ValueError):
            return 0

    def _get_attack_hit_count(self, card, context=None, available_energy=None) -> int:
        """Return known deterministic hit counts for attack damage estimates."""
        card_name = canonical_card_name(card)
        upgrades = getattr(card, 'upgrades', 0)

        if card_name == 'Twin Strike':
            return 2
        if card_name == 'Bane' and context is not None:
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
        if card_name == 'Fiend Fire' and context is not None:
            return self._count_fiend_fire_exhausted_cards(card, context)

        return 1

    def _count_fiend_fire_exhausted_cards(self, card, context) -> int:
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

    def _estimate_card_block(self, card, context=None) -> int:
        """Estimate card block for timing decisions from methods or parsed data."""
        if hasattr(card, 'block_for'):
            try:
                block = max(0, int(card.block_for()))
                return self._apply_block_status_modifiers(block, context)
            except Exception:
                pass

        block = getattr(card, 'block', 0) or 0
        if block <= 0:
            try:
                card_name = canonical_card_name(card)
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    parsed_block = game_data_loader._parse_card_block(card_data)
                    if parsed_block is not None:
                        block = parsed_block
                        if getattr(card, 'upgrades', 0) > 0:
                            block += BLOCK_UPGRADE_BONUS.get(card_name, 0)
            except Exception:
                block = 0

        return self._apply_block_status_modifiers(block, context)

    def _apply_block_status_modifiers(self, block: int, context=None) -> int:
        block = max(0, int(block))
        if block <= 0:
            return 0
        if context is None:
            return block

        block = max(0, block + self._get_player_power_amount(context, 'Dexterity'))
        if self._get_player_debuff_stacks(context, 'Frail') > 0:
            block = int(block * 0.75)

        return max(0, int(block))
