"""
Ironclad-specific combat planner with expert strategy integration.

Optimizes combat decisions for Ironclad's unique mechanics using beam search:
- Combat ending detection (can we kill all this turn?)
- Demon Form timing (play by turn 2-3)
- Limit Break logic (Strength >= 5)
- Corruption mode (all skills become 0 cost)
- Vulnerable optimization (Bash before big attacks)
- Reaper healing logic
- Body Slam optimization
- Smart targeting (Bash on high HP, kill low HP, etc.)
"""

import logging
import copy
import time
from typing import List, Tuple, Optional, Dict
from enum import Enum
from .simulation import (
    CombatPlanner,
    SimulationState,
    FastCombatSimulator,
    W_DEATHRISK,
)
from .card_costs import effective_card_cost, is_x_cost_card, whirlwind_damage, x_effect_energy
from .card_hits import (
    fiend_fire_exhaust_count,
    fixed_attack_hit_count,
    strike_card_count,
)
from .card_names import canonical_card_name
from .card_types import card_requires_target, card_type_name, is_attack_card
from .card_upgrades import (
    card_upgrade_count,
    heavy_blade_strength_multiplier,
    is_card_upgraded,
    known_damage_upgrade_bonus,
    perfected_strike_bonus_per_strike,
)
from .combat_state import is_card_played, mark_card_played, player_block_value
from .combat_ending import CombatEndingDetector
from .monster_database import evaluate_monster_threat, get_monster_info
from ..decision.base import DecisionContext
from spirecomm.ai.monster_names import canonical_live_monster_name
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action, PlayCardAction
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.ai.intent_utils import intent_is_attack, intent_tokens
from spirecomm.data.loader import game_data_loader
# === TIMING AWARENESS IMPORTS ===
from .timing import TurnTimingClassifier, CombatBalanceStrategy

logger = logging.getLogger(__name__)

POWER_BONUS_EARLY = 18
POWER_BONUS_MID = 12
POWER_BONUS_LATE = 6
AWAKENED_ONE_POWER_PENALTY = 90
AOE_ATTACK_CARDS = {'Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper'}


def _monster_matches_any_name(monster, candidate_names) -> bool:
    raw_name = str(getattr(monster, 'name', '') or '').lower()
    canonical_name = canonical_live_monster_name(monster).lower()
    for candidate in candidate_names:
        candidate_name = str(candidate or '').lower()
        if not candidate_name:
            continue
        if raw_name and (candidate_name in raw_name or raw_name in candidate_name):
            return True
        if canonical_name and (candidate_name in canonical_name or canonical_name in candidate_name):
            return True
    return False


def _format_card_for_log(card: Card) -> str:
    upgrades = getattr(card, 'upgrades', 0)
    name = getattr(card, 'name', '')
    card_id = getattr(card, 'card_id', None) or canonical_card_name(card)
    if name:
        return f"{card_id}({name},u{upgrades})"
    return f"{card_id}(u{upgrades})"


class EliteType(Enum):
    """Enumeration of Act 1 elite monsters for specialized strategy application."""
    GREMLIN_NOB = "Gremlin Nob"
    LAGAVULIN = "Lagavulin"
    THREE_SENTRIES = "3 Sentries"
    SLIME_BOSS = "Slime Boss"
    UNKNOWN = "Unknown"


class IroncladCombatPlanner(CombatPlanner):
    """
    Ironclad-specific combat planner with beam search and expert strategies.

    Key features:
    1. Combat ending detection - don't over-defend when lethal is possible
    2. Beam search - find optimal card sequences, not greedy single-card plays
    3. Smart targeting - Bash high HP, kill low HP, AOE optimization
    4. Ironclad-specific logic - Demon Form timing, Limit Break threshold, etc.
    """

    def __init__(self, card_evaluator=None, beam_width=10, max_depth=5, combat_mode=None):
        """
        Initialize Ironclad combat planner.

        Args:
            card_evaluator: Card evaluator for fallback
            beam_width: Number of candidates to keep in beam search
            max_depth: Maximum depth for beam search
            combat_mode: Optional combat mode (BALANCED/AGGRESSIVE/DEFENSIVE)
        """
        self.card_evaluator = card_evaluator or SynergyCardEvaluator()
        self.simulator = FastCombatSimulator(self.card_evaluator)
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.combat_ending_detector = CombatEndingDetector()
        self.combat_mode = combat_mode  # Store combat mode for reference

        # === TIMING AWARENESS INITIALIZATION ===
        self.timing_classifier = TurnTimingClassifier()
        self.balance_strategy = CombatBalanceStrategy()
        logger.info("[TIMING_INIT] IroncladCombatPlanner initialized with timing awareness")

    @staticmethod
    def _non_negative_int(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _non_negative_float(value) -> float:
        try:
            return max(0.0, float(value or 0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _is_aoe_attack(card: Card) -> bool:
        return canonical_card_name(card) in AOE_ATTACK_CARDS

    @staticmethod
    def _context_ascension_level(context: DecisionContext) -> int:
        game = getattr(context, 'game', None)
        if game is not None and hasattr(game, 'ascension_level'):
            return int(getattr(game, 'ascension_level') or 0)
        if hasattr(context, 'ascension_level'):
            return int(getattr(context, 'ascension_level') or 0)
        return int(getattr(context, 'ascension', 0) or 0)

    @staticmethod
    def _combat_hp_damage_so_far(context: DecisionContext) -> int:
        game = getattr(context, 'game', None)
        monsters = getattr(game, 'monsters', None) or getattr(context, 'monsters_alive', [])
        damage_so_far = 0
        for monster in monsters:
            max_hp = getattr(monster, 'max_hp', None)
            current_hp = getattr(monster, 'current_hp', None)
            if max_hp is None or current_hp is None:
                continue
            damage_so_far += max(0, int(max_hp) - max(0, int(current_hp)))
        return damage_so_far

    @staticmethod
    def _is_gremlin_nob(monster) -> bool:
        identifiers = (
            getattr(monster, 'monster_id', ''),
            getattr(monster, 'name', ''),
        )
        return any(
            ''.join(ch for ch in str(identifier).lower() if ch.isalnum()) == 'gremlinnob'
            for identifier in identifiers
        )

    def _is_single_target_attack(self, card: Card, target_idx: Optional[int]) -> bool:
        if target_idx is None:
            return False
        is_attack = is_attack_card(card)
        return is_attack and not self._is_aoe_attack(card)

    def plan_turn(self, context: DecisionContext) -> List[Action]:
        """
        Plan optimal turn using Ironclad-specific strategies.

        Returns:
            List of actions to execute in order
        """
        # Track decision start time for timeout protection
        self.decision_start = time.time()

        import sys
        playable_cards = context.playable_cards

        if not playable_cards:
            return []

        # Log turn start
        logger.info(f"[COMBAT] game_id={context.game_id} Turn {context.turn}, Floor {context.floor}, Act {context.act}")
        logger.info(f"[COMBAT] Playable cards: {len(playable_cards)}, Energy: {context.energy_available}")
        # Log card IDs for debugging
        card_ids = [_format_card_for_log(card) for card in playable_cards]
        logger.info(f"[COMBAT] Cards in hand: {', '.join(card_ids)}")
        logger.info(f"[COMBAT] Monsters: {len(context.monsters_alive)}, HP: {context.player_hp_pct:.1%}")

        # Log monster intents for debugging over-defense issues
        for i, monster in enumerate(context.monsters_alive):
            intent_str = str(monster.intent) if hasattr(monster, 'intent') else 'UNKNOWN'
            logger.info(
                f"[COMBAT] Monster {i+1}: {monster.name}({monster.monster_id}), move_id={monster.move_id}, "
                f"Intent: {intent_str}, HP: {monster.current_hp}/{monster.max_hp}"
            )

        # Step 1: Check for lethal (can we kill all monsters this turn?)
        logger.info("[COMBAT] About to check lethal...")
        if self.combat_ending_detector.can_kill_all(context):
            logger.info("[COMBAT] Lethal detected!")
            lethal_sequence = self.combat_ending_detector.find_lethal_sequence(context)
            if lethal_sequence:
                logger.info(f"[COMBAT] Lethal sequence: {len(lethal_sequence)} cards")
                return lethal_sequence
            logger.warning(f"[COMBAT] game_id={context.game_id} Lethal detected but sequence empty; falling back to beam search")
        logger.info("[COMBAT] No lethal, proceeding to beam search...")

        # === TIMING AWARENESS: Classify turn timing ===
        logger.info("[TIMING] About to classify turn timing...")
        timing_context = self.timing_classifier.classify_turn(context)
        logger.info(f"[TIMING_CLASSIFY] Turn {context.turn}: {timing_context.turn_timing.value}")
        logger.info(f"[TIMING_CLASSIFY] Current damage: {timing_context.current_damage:.1f}")
        if timing_context.future_damage_curve:
            logger.info(f"[TIMING_CLASSIFY] Future damage: {[f'{d:.1f}' for d in timing_context.future_damage_curve]}")
        if timing_context.safe_windows:
            logger.info(f"[TIMING_CLASSIFY] Safe windows: {len(timing_context.safe_windows)}")

        # Get optimal weights for this timing
        balance_weights = self.balance_strategy.get_balance_weights(
            timing_context.turn_timing,
            context,
            timing_context
        )
        timing_context.balance_weights = balance_weights
        logger.info(f"[TIMING_WEIGHTS] Using {timing_context.turn_timing.value} weights: "
                   f"damage={balance_weights.damage_weight:.2f}, block={balance_weights.block_weight:.2f}, "
                   f"kill_bonus={balance_weights.kill_bonus:.1f}")

        # Set timing context on simulator for dynamic weight usage
        self.simulator.set_timing_context(timing_context)

        # Store timing context in DecisionContext for reference
        context.timing_context = timing_context

        # Step 2: Determine adaptive parameters based on complexity
        logger.info("[COMBAT] About to get adaptive parameters...")
        beam_width, max_depth = self._get_adaptive_parameters(context, playable_cards)
        logger.info(f"[COMBAT] Beam search: width={beam_width}, depth={max_depth}")

        # Step 3: Use beam search to find optimal sequence
        sequence = self._beam_search_turn(context, playable_cards, beam_width, max_depth)
        if not sequence:
            logger.info(f"[COMBAT] game_id={context.game_id} End turn chosen (empty sequence)")
            return []
        logger.info(f"[COMBAT] game_id={context.game_id} Best sequence: {len(sequence)} cards")
        # Log card IDs in best sequence for debugging
        seq_card_ids = []
        for action in sequence:
            if hasattr(action, 'card') and action.card:
                seq_card_ids.append(_format_card_for_log(action.card))
        logger.info(f"[COMBAT] game_id={context.game_id} Sequence cards: {', '.join(seq_card_ids)}")
        return sequence

    def _get_adaptive_parameters(self, context: DecisionContext, playable_cards: List[Card]) -> Tuple[int, int]:
        """
        Determine adaptive beam width and depth based on game complexity.

        Args:
            context: Decision context
            playable_cards: List of playable cards

        Returns:
            (beam_width, max_depth) tuple
        """
        num_playable = len(playable_cards)
        num_monsters = len(context.monsters_alive)

        # Calculate complexity score
        complexity = num_playable * num_monsters

        # Simple局面 (1-3 cards, 1-2 monsters) - increased from 8,3 to 10,4
        if num_playable <= 3 and num_monsters <= 2:
            return 10, 4

        # Medium局面 (4-6 cards, 2-3 monsters) - increased from 12,4 to 15,5
        elif num_playable <= 6 and num_monsters <= 3:
            return 15, 5

        # Complex局面 (7+ cards or 4+ monsters) - deeper search, increased from 15,5 to 20,6
        else:
            return 20, 6

    def _beam_search_turn(self, context: DecisionContext,
                         playable_cards: List[Card],
                         beam_width: int, max_depth: int) -> List[Action]:
        """Use beam search to find best action sequence."""
        initial_state = SimulationState(context)

        # Initialize beam with empty sequence
        beam = [([], initial_state, 0, float('-inf'))]  # (actions, state, energy_spent, score)

        best_sequence = []
        # Treat ending the turn as the baseline so fallback does not force
        # negative-value nonlethal plays just because energy remains.
        best_score = self._score_sequence([], initial_state, initial_state, context)

        for depth in range(max_depth):
            new_candidates = []

            # === NEW: Check if target exploration should be enabled ===
            elapsed_ms = (time.time() - self.decision_start) * 1000 if hasattr(self, 'decision_start') else 0
            explore_targets = self._should_explore_targets(context, elapsed_ms)

            for sequence, state, energy_spent, score in beam:
                # Try each remaining card
                for card in playable_cards:
                    if is_card_played(state.played_card_uuids, card):
                        continue

                    # Check energy
                    cost = self._card_cost_for_state(card, state)
                    if self._is_zero_effect_x_attack(card, cost, context):
                        continue
                    if cost > state.player_energy:
                        continue

                    # === NEW: Target exploration ===
                    if card_requires_target(card, AOE_ATTACK_CARDS) and explore_targets:
                        # Get ranked targets
                        ranked_targets = self._rank_targets(card, context, state)

                        # Prune targets
                        pruned_targets = self._prune_targets(card, ranked_targets, context, state)

                        # Progressive target expansion: depth 0→2 targets, depth 1→1-2, depth 2+→1
                        M_targets = 2 if depth == 0 else (1 if depth >= 2 else 2)

                        if pruned_targets and len(pruned_targets) > 1:
                            # Explore multiple targets
                            targets_to_explore = pruned_targets[:M_targets]
                            card_name = canonical_card_name(card)
                            logger.info(f"[TARGET_EXPLORE] Depth {depth}: exploring {len(targets_to_explore)} targets for {card_name}")

                            for target, target_idx, threat in targets_to_explore:
                                # Simulate
                                new_state = self.simulator.simulate_card_play(
                                    state, card, target, target_idx, context=context
                                )
                                new_state_copy = copy.deepcopy(new_state)
                                mark_card_played(new_state_copy.played_card_uuids, card)

                                # Set primary target on first attack
                                if state.primary_target is None and target_idx is not None:
                                    if self._is_single_target_attack(card, target_idx):
                                        new_state_copy.primary_target = target_idx

                                # Create action
                                if target:
                                    action = PlayCardAction(card=card, target_monster=target)
                                else:
                                    action = PlayCardAction(card=card)

                                new_sequence = sequence + [action]

                                # Score
                                score_val = self._score_sequence(new_sequence, initial_state, new_state_copy, context)
                                if score_val > best_score:
                                    best_score = score_val
                                    best_sequence = new_sequence

                                new_candidates.append((new_sequence, new_state_copy, energy_spent + cost, score_val))
                        else:
                            # Fallback to deterministic
                            target, target_idx = self._choose_target_for_card(card, context, state)

                            # Simulate
                            new_state = self.simulator.simulate_card_play(
                                state, card, target, target_idx, context=context
                            )
                            mark_card_played(new_state.played_card_uuids, card)

                            # Set primary target on first attack
                            if state.primary_target is None and target_idx is not None:
                                if self._is_single_target_attack(card, target_idx):
                                    new_state.primary_target = target_idx

                            # Create action
                            if target:
                                action = PlayCardAction(card=card, target_monster=target)
                            else:
                                action = PlayCardAction(card=card)

                            new_sequence = sequence + [action]

                            # Score
                            score_val = self._score_sequence(new_sequence, initial_state, new_state, context)
                            if score_val > best_score:
                                best_score = score_val
                                best_sequence = new_sequence

                            new_candidates.append((new_sequence, new_state, energy_spent + cost, score_val))
                    else:
                        # Use deterministic targeting (either no target exploration needed, or card has no target)
                        # Select target
                        target, target_idx = self._choose_target_for_card(card, context, state)

                        # Simulate
                        new_state = self.simulator.simulate_card_play(
                            state, card, target, target_idx, context=context
                        )
                        mark_card_played(new_state.played_card_uuids, card)

                        # === NEW: Set primary target on first attack ===
                        # If this is the first attack (no primary target yet), set it
                        if state.primary_target is None and target_idx is not None:
                            # Check if this is an attack card (not AOE)
                            if self._is_single_target_attack(card, target_idx):
                                new_state.primary_target = target_idx

                        # Create action
                        if target:
                            action = PlayCardAction(card=card, target_monster=target)
                        else:
                            action = PlayCardAction(card=card)

                        new_sequence = sequence + [action]

                        # Score
                        score = self._score_sequence(new_sequence, initial_state, new_state, context)
                        if score > best_score:
                            best_score = score
                            best_sequence = new_sequence

                        new_candidates.append((new_sequence, new_state, energy_spent + cost, score))

            if not new_candidates:
                break

            # Keep top candidates
            new_candidates.sort(key=lambda x: x[3], reverse=True)
            beam = new_candidates[:beam_width]

        if beam:
            top_candidates = beam[:3]
            for rank, (seq, state, energy, score) in enumerate(top_candidates, start=1):
                seq_card_ids = []
                for action in seq:
                    if hasattr(action, 'card') and action.card:
                        seq_card_ids.append(_format_card_for_log(action.card))
                block_gained = state.turn_block() - initial_state.turn_block()
                logger.info(
                    "[COMBAT_CANDIDATE] game_id=%s rank=%s score=%.1f damage=%s kills=%s block=%s energy=%s cards=%s",
                    context.game_id,
                    rank,
                    score,
                    state.total_damage_dealt,
                    state.monsters_killed,
                    block_gained,
                    state.energy_spent,
                    ", ".join(seq_card_ids),
                )

        return best_sequence

    @staticmethod
    def _card_cost_for_state(card: Card, state: SimulationState) -> int:
        cost = effective_card_cost(card, getattr(state, 'player_energy', 0))
        if (
            card_type_name(card) == 'SKILL'
            and getattr(state, 'corruption_active', False)
        ):
            return 0
        return cost

    @staticmethod
    def _is_zero_effect_x_attack(card: Card, cost: int, context: DecisionContext) -> bool:
        return (
            x_effect_energy(card, cost, context) <= 0
            and is_x_cost_card(card)
            and is_attack_card(card)
        )

    @staticmethod
    def _is_live_monster_state(monster_state: dict) -> bool:
        return (
            not monster_state.get('is_gone', False)
            and monster_state.get('hp', monster_state.get('current_hp', 1)) > 0
        )

    def _choose_target_for_card(self, card: Card, context: DecisionContext,
                                state: SimulationState) -> Tuple[Optional[Monster], Optional[int]]:
        """
        Choose best target for card given current simulation state.

        Implements focused fire: prioritizes primary_target to concentrate damage
        and kill monsters faster, reducing total damage taken.
        """
        if not state.monsters:
            return None, None

        card_id = canonical_card_name(card)
        alive_monsters = [
            (i, m) for i, m in enumerate(state.monsters)
            if self._is_live_monster_state(m)
        ]
        if not alive_monsters:
            return None, None

        # AOE cards - no targeting needed
        # Reaper is AOE heal - prioritize when multiple monsters alive and we have Strength
        if card_id == 'Reaper':
            if len(state.monsters) >= 2 and context.strength >= 3:
                # Best case: multiple targets + good Strength
                return None, None  # AOE
            elif len(state.monsters) == 1:
                # Single target - less valuable but still use
                i, _ = alive_monsters[0]
                if i < len(context.monsters_alive):
                    return context.monsters_alive[i], i
                return None, None
            else:
                return None, None

        if card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap']:
            return None, None

        # === NEW: Focused Fire ===
        # If we have a primary target that's still alive, prioritize attacking it
        if state.primary_target is not None:
            primary_idx = state.primary_target
            # Check if primary target is still alive
            if primary_idx < len(state.monsters) and self._is_live_monster_state(state.monsters[primary_idx]):
                # Primary target still alive - focus fire on it
                if primary_idx < len(context.monsters_alive):
                    return context.monsters_alive[primary_idx], primary_idx
            else:
                # Primary target is dead - clear it
                state.primary_target = None

        # Prefer finishing a killable low-HP target in multi-monster fights to reduce incoming attacks.
        if is_attack_card(card) and len(alive_monsters) >= 2:
            killable_targets = []
            for i, monster_state in alive_monsters:
                if i >= len(context.monsters_alive):
                    continue
                effective_hp = monster_state.get('hp', 0) + monster_state.get('block', 0)
                damage = self._estimate_attack_damage_to_target(
                    card,
                    context,
                    state,
                    i,
                )
                if damage >= effective_hp:
                    real_monster = context.monsters_alive[i]
                    threat = evaluate_monster_threat(real_monster, context)
                    killable_targets.append((effective_hp, -threat, i))

            if killable_targets:
                killable_targets.sort()
                _, _, i = killable_targets[0]
                return context.monsters_alive[i], i

        # Calculate threat levels for all alive monsters
        monster_threats = []
        for i, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                real_monster = context.monsters_alive[i]
                threat = evaluate_monster_threat(real_monster, context)
                monster_threats.append((i, monster_state, threat))

        if not monster_threats:
            return None, None

        # Bash - highest HP with threat consideration (maximize vulnerable duration)
        if card_id == 'Bash':
            # Balance HP and threat for Bash targeting
            best_idx = max(monster_threats, 
                         key=lambda x: x[1]['hp'] * 0.7 + x[2] * 0.3)
            i, _, _ = best_idx
            if i < len(context.monsters_alive):
                return context.monsters_alive[i], i

        # Body Slam - lowest HP with threat consideration (finish off weakened enemies)
        if card_id == 'Body Slam':
            # Balance HP and threat for Body Slam targeting
            best_idx = min(monster_threats, 
                         key=lambda x: x[1]['hp'] * 0.5 + (10 - x[2]) * 0.5)
            i, _, _ = best_idx
            if i < len(context.monsters_alive):
                return context.monsters_alive[i], i

        # Standard attacks - prioritize high threat targets, then lowest HP
        if is_attack_card(card):
            # Prefer non-vulnerable high threat targets if available
            non_vulnerable = [(i, m, t) for i, m, t in monster_threats if m.get('vulnerable', 0) == 0]
            if non_vulnerable:
                # First sort by threat (descending), then by HP (ascending)
                non_vulnerable.sort(key=lambda x: (-x[2], x[1]['hp']))
                i, _, _ = non_vulnerable[0]
                if i < len(context.monsters_alive):
                    return context.monsters_alive[i], i

            # Otherwise prioritize high threat targets, then lowest HP
            monster_threats.sort(key=lambda x: (-x[2], x[1]['hp']))
            i, _, _ = monster_threats[0]
            if i < len(context.monsters_alive):
                return context.monsters_alive[i], i

        # Default - highest threat monster
        monster_threats.sort(key=lambda x: -x[2])
        i, _, _ = monster_threats[0]
        if i < len(context.monsters_alive):
            return context.monsters_alive[i], i

        return None, None

    def _choose_target_for_card_v2(self, card: Card, context: DecisionContext,
                                    state: SimulationState) -> Tuple[Optional[Monster], Optional[int]]:
        """
        Enhanced target selection using Wiki monster data for intelligent targeting.

        This enhanced version incorporates:
        - Special mechanics handling (summoner, hibernation, phase change, death split)
        - AOE optimization for minion swarms and death splits
        - Duo boss strategy (focus fire)
        - Threat-based targeting with future threat prediction

        Args:
            card: Card being played
            context: Decision context
            state: Simulation state

        Returns:
            Tuple of (target_monster, target_index) or (None, None) for AOE
        """
        if not state.monsters:
            return None, None

        card_id = canonical_card_name(card)
        alive_monsters = [
            (i, context.monsters_alive[i], m)
            for i, m in enumerate(state.monsters)
            if self._is_live_monster_state(m) and i < len(context.monsters_alive)
        ]
        if not alive_monsters:
            return None, None

        # === AOE Cards - Enhanced Logic ===
        if card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']:
            return None, None

        # === Special Mechanics Targeting ===

        # 1. Summoner handling - check for Reptomancer/Gremlin Leader/etc.
        summoner_targets = []
        for i, monster, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                monster_name = canonical_live_monster_name(monster)
                if game_data_loader.is_monster_summoner(monster_name):
                    # Get minions count
                    minions = game_data_loader.get_monster_minions(monster_name)
                    if minions:
                        summoner_targets.append((i, monster, monster_state, monster_name, minions))

        if summoner_targets:
            # Strategy depends on summoner type
            for i, monster, monster_state, monster_name, minions in summoner_targets:
                strategy = game_data_loader.get_monster_recommended_strategy(monster_name)
                if strategy:
                    primary = strategy.get('primary', '')
                    # If strategy says "kill_minions_first", check if we have minions to target
                    if 'kill_minions_first' in primary or 'minion' in primary.lower():
                        # Target minions instead of summoner
                        minion_indices = [j for j, m in enumerate(context.monsters_alive)
                                        if _monster_matches_any_name(m, minions)]
                        if minion_indices and card_id not in ['Bash']:  # Bash on summoner
                            # Target highest HP minion to clear them efficiently
                            minion_idx = max(minion_indices,
                                           key=lambda idx: context.monsters_alive[idx].current_hp)
                            if minion_idx < len(context.monsters_alive):
                                return context.monsters_alive[minion_idx], minion_idx

                    # Otherwise, kill summoner first
                    if 'kill_summoner' in primary or 'priority_target' in primary:
                        return monster, i

        # 2. Hibernation handling - ignore Lagavulin while sleeping
        hibernating_monsters = []
        awake_monsters = []
        for i, monster, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                monster_name = canonical_live_monster_name(monster)
                if game_data_loader.is_monster_hibernating(monster_name, context.turn):
                    hibernating_monsters.append((i, monster, monster_state))
                else:
                    awake_monsters.append((i, monster, monster_state))

        # If we have awake monsters, prioritize them over hibernating ones
        if awake_monsters and hibernating_monsters and len(awake_monsters) > 0:
            # Filter to only consider awake monsters
            alive_monsters = awake_monsters

        # 3. Death split handling - prioritize AOE or burst below threshold
        for i, monster, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                real_monster = context.monsters_alive[i]
                real_monster_name = canonical_live_monster_name(real_monster)
                if game_data_loader.does_monster_have_death_split(real_monster_name):
                    # Check if we're near split threshold
                    if hasattr(real_monster, 'current_hp') and hasattr(real_monster, 'max_hp'):
                        current_hp = monster_state.get(
                            'hp',
                            getattr(real_monster, 'current_hp', 0),
                        )
                        max_hp = monster_state.get(
                            'max_hp',
                            getattr(real_monster, 'max_hp', 1),
                        )
                        block = monster_state.get(
                            'block',
                            getattr(real_monster, 'block', 0),
                        )
                        hp_percent = current_hp / max(max_hp, 1)

                        # Get split threshold
                        monster_data = game_data_loader.get_enhanced_monster_data(real_monster_name)
                        if monster_data and 'special_mechanics' in monster_data:
                            split_threshold = monster_data['special_mechanics'].get('split_conditions', {}).get('hp_threshold', 50) / 100.0

                            # If below threshold and not using AOE, prioritize this monster to finish it
                            if hp_percent < split_threshold:
                                damage = self._estimate_attack_damage_to_target(
                                    card,
                                    context,
                                    state,
                                    i,
                                )
                                if damage >= current_hp + block:
                                    # Can kill before split - prioritize
                                    return real_monster, i

        # 4. Phase change handling - prioritize during burst windows
        for i, monster, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                real_monster = context.monsters_alive[i]
                real_monster_name = canonical_live_monster_name(real_monster)
                if game_data_loader.does_monster_have_phase_change(real_monster_name):
                    strategy = game_data_loader.get_monster_recommended_strategy(real_monster_name)
                    if strategy:
                        primary = strategy.get('primary', '')
                        # Check for burst windows
                        if 'burst' in primary.lower() and '50_percent' in primary:
                            # Burst phase active - prioritize this monster
                            if hasattr(real_monster, 'current_hp') and hasattr(real_monster, 'max_hp'):
                                max_hp = self._non_negative_float(real_monster.max_hp)
                                hp_pct = (
                                    self._non_negative_float(real_monster.current_hp) / max_hp
                                    if max_hp > 0
                                    else 1.0
                                )
                                if hp_pct < 0.6:
                                    # In burst window - prioritize
                                    return real_monster, i

        # 5. Duo boss handling - focus fire on one
        duo_bosses = []
        for i, monster, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                real_monster = context.monsters_alive[i]
                real_monster_name = canonical_live_monster_name(real_monster)
                if game_data_loader.is_monster_duo_boss(real_monster_name):
                    duo_bosses.append((i, real_monster, monster_state))

        if duo_bosses and len(duo_bosses) >= 2:
            # Focus fire on the weaker one (lower HP) or the one with higher threat
            # Calculate enhanced threat for each duo boss
            duo_with_threat = []
            for i, boss, monster_state in duo_bosses:
                threat = context.compute_threat_v2(boss)
                duo_with_threat.append((i, boss, threat, monster_state['hp']))

            # Prioritize by threat, then by HP (weaker first)
            duo_with_threat.sort(key=lambda x: (-x[2], x[3]))
            i, boss, _, _ = duo_with_threat[0]
            return boss, i

        # === Fallback to Enhanced Threat-Based Targeting ===
        # Calculate enhanced threat for all monsters
        monster_threats = []
        for i, real_monster, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                threat = context.compute_threat_v2(real_monster)
                monster_threats.append((i, monster_state, threat))

        if not monster_threats:
            return None, None

        # Bash - highest HP with enhanced threat consideration
        if card_id == 'Bash':
            # Balance HP and threat for Bash targeting
            best_idx = max(monster_threats,
                         key=lambda x: x[1]['hp'] * 0.6 + x[2] * 0.4)  # More weight on threat with v2
            i, _, _ = best_idx
            if i < len(context.monsters_alive):
                return context.monsters_alive[i], i

        # Body Slam - lowest HP (finish off weakened enemies)
        if card_id == 'Body Slam':
            best_idx = min(monster_threats,
                         key=lambda x: x[1]['hp'])
            i, _, _ = best_idx
            if i < len(context.monsters_alive):
                return context.monsters_alive[i], i

        # Standard attacks - prioritize high threat targets with enhanced threat
        if is_attack_card(card):
            # Prefer non-vulnerable high threat targets
            non_vulnerable = [(i, m, t) for i, m, t in monster_threats if m.get('vulnerable', 0) == 0]
            if non_vulnerable:
                non_vulnerable.sort(key=lambda x: (-x[2], x[1]['hp']))
                i, _, _ = non_vulnerable[0]
                if i < len(context.monsters_alive):
                    return context.monsters_alive[i], i

            # Otherwise prioritize high threat
            monster_threats.sort(key=lambda x: (-x[2], x[1]['hp']))
            i, _, _ = monster_threats[0]
            if i < len(context.monsters_alive):
                return context.monsters_alive[i], i

        # Default - highest threat monster (enhanced)
        monster_threats.sort(key=lambda x: -x[2])
        i, _, _ = monster_threats[0]
        if i < len(context.monsters_alive):
            return context.monsters_alive[i], i

        return None, None

    def _should_use_aoe(self, card_id: str, context: DecisionContext, state: SimulationState) -> bool:
        """
        Decide if AOE card should be used based on monster composition.

        AOE is optimal when:
        - 3+ monsters with similar HP (efficient multi-target damage)
        - Summoner with 2+ minions (clear minions efficiently)
        - Death split monster below threshold (kill all parts)
        - Duo boss (both bosses similar HP)

        Args:
            card_id: Card being considered
            context: Decision context
            state: Simulation state

        Returns:
            True if AOE should be used, False if single-target is better
        """
        if not state.monsters:
            return False

        alive_monsters = [
            (i, m) for i, m in enumerate(state.monsters)
            if self._is_live_monster_state(m)
        ]
        if len(alive_monsters) < 2:
            return False  # Single target - no AOE benefit

        # Check for death split monsters
        for i, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                monster = context.monsters_alive[i]
                monster_name = canonical_live_monster_name(monster)
                if game_data_loader.does_monster_have_death_split(monster_name):
                    # AOE is very effective against split monsters
                    return True

        # Check for summoner with minions
        summoner_with_minions = False
        for i, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                monster = context.monsters_alive[i]
                monster_name = canonical_live_monster_name(monster)
                if game_data_loader.is_monster_summoner(monster_name):
                    minions = game_data_loader.get_monster_minions(monster_name)
                    minion_count = len([m for m in context.monsters_alive
                                      if _monster_matches_any_name(m, minions)])
                    if minion_count >= 2:
                        summoner_with_minions = True
                        break

        if summoner_with_minions:
            return True

        # Check for 3+ monsters with similar HP
        if len(alive_monsters) >= 3:
            hp_values = [m['hp'] for _, m in alive_monsters]
            hp_std_dev = (max(hp_values) - min(hp_values)) / max(sum(hp_values), 1)

            # If HP values are within 30% of each other, AOE is efficient
            if hp_std_dev < 0.3:
                return True

        # Check for duo boss
        duo_count = 0
        for i, monster_state in alive_monsters:
            if i < len(context.monsters_alive):
                monster = context.monsters_alive[i]
                monster_name = canonical_live_monster_name(monster)
                if game_data_loader.is_monster_duo_boss(monster_name):
                    duo_count += 1

        if duo_count >= 2:
            return True

        # Special case: Reaper with good Strength
        if card_id == 'Reaper' and context.strength >= 3:
            return True

        # Default: use AOE if 3+ targets
        return len(alive_monsters) >= 3

    def _rank_targets(self, card: Card, context: DecisionContext, state: SimulationState) -> List[Tuple]:
        """
        Rank targets for a card using threat-based targeting.

        Returns a list of (monster, monster_idx, threat_score) tuples sorted by threat (highest first).

        Args:
            card: Card being played
            context: Decision context
            state: Simulation state

        Returns:
            List of (monster, monster_idx, threat_score) tuples sorted by threat descending
        """
        if not context.monsters_alive:
            return []

        # Rank all monsters by threat
        ranked_targets = []
        for i, monster_state in enumerate(state.monsters):
            if not self._is_live_monster_state(monster_state):
                continue

            if i < len(context.monsters_alive):
                monster = context.monsters_alive[i]
                threat = evaluate_monster_threat(monster, context)
                ranked_targets.append((monster, i, threat))

        # Sort by threat descending
        ranked_targets.sort(key=lambda x: x[2], reverse=True)

        return ranked_targets

    def _prune_targets(self, card: Card, ranked_targets: List[Tuple], context: DecisionContext, state: SimulationState) -> List[Tuple]:
        """
        Prune target space to limit beam search expansion.

        Pruning strategy:
        - For attack cards: Keep killable targets + highest threat fallback
        - For debuff cards: Keep top 2 threat targets
        - Skip if > 4 monsters (fallback to deterministic)

        Args:
            card: Card being played
            ranked_targets: List of (monster, monster_idx, threat_score) tuples from _rank_targets()
            context: Decision context
            state: Simulation state

        Returns:
            Pruned list of (monster, monster_idx, threat_score) tuples
        """
        if not ranked_targets:
            return []

        monster_count = len(context.monsters_alive)

        # Skip pruning if too many monsters (fallback to deterministic)
        if monster_count > 4:
            logger.info(f"[TARGET_PRUNING] Skipping - {monster_count} monsters > 4")
            return []

        # Check if cleanup phase (all monsters low HP)
        all_low_hp = all(m['hp'] < 8 for m in state.monsters if not m['is_gone'])
        if all_low_hp:
            logger.info("[TARGET_PRUNING] Cleanup phase detected - using greedy lowest-HP")
            # Use greedy lowest-HP targeting
            low_hp_targets = sorted(
                [(m, idx, threat) for m, idx, threat in ranked_targets],
                key=lambda x: x[0].current_hp
            )
            return low_hp_targets[:1]  # Just the lowest HP target

        is_attack = is_attack_card(card)

        if is_attack:
            # Separate killable and non-killable targets
            killable = []
            non_killable = []
            for monster, idx, threat in ranked_targets:
                if idx < len(state.monsters):
                    effective_hp = state.monsters[idx]['hp'] + state.monsters[idx]['block']
                    estimated_damage = self._estimate_attack_damage_to_target(
                        card,
                        context,
                        state,
                        idx,
                    )
                    if estimated_damage >= effective_hp:
                        killable.append((monster, idx, threat))
                    else:
                        non_killable.append((monster, idx, threat))

            if killable:
                # Keep only killable targets (max 3)
                result = killable[:3]
                logger.info(f"[TARGET_PRUNING] Attack: {len(result)} killable targets (from {len(ranked_targets)} total)")
                return result
            else:
                # No killable targets, keep highest threat only
                result = ranked_targets[:1]
                logger.info(f"[TARGET_PRUNING] Attack: 1 non-killable target (highest threat)")
                return result
        else:
            # For debuff cards, keep top 2 threat targets
            result = ranked_targets[:2]
            logger.info(f"[TARGET_PRUNING] Debuff: {len(result)} targets (top threat)")
            return result

    def _estimate_attack_damage_to_target(
        self,
        card: Card,
        context: DecisionContext,
        state: SimulationState,
        target_idx: int,
    ) -> int:
        """Estimate target-specific attack damage using the real simulator rules."""
        if target_idx < 0 or target_idx >= len(state.monsters):
            return 0

        before = state.monsters[target_idx]['hp'] + state.monsters[target_idx]['block']
        if before <= 0:
            return 0

        if not hasattr(state, 'clone'):
            return self._estimate_attack_damage_without_simulation(card, context)

        target = (
            context.monsters_alive[target_idx]
            if target_idx < len(context.monsters_alive)
            else None
        )
        result = self.simulator.simulate_card_play(
            state.clone(),
            card,
            target=target,
            target_index=target_idx,
            context=context,
        )
        if target_idx >= len(result.monsters):
            return 0

        after = result.monsters[target_idx]['hp'] + result.monsters[target_idx]['block']
        return max(0, before - after)

    def _estimate_attack_damage_without_simulation(
        self,
        card: Card,
        context: DecisionContext,
    ) -> int:
        card_name = canonical_card_name(card)
        if card_name == 'Body Slam':
            strength = getattr(context, 'strength', 0)
            return max(0, player_block_value(context) + strength)
        if card_name == 'Whirlwind':
            energy = x_effect_energy(card, getattr(context, 'energy_available', 0), context)
            return whirlwind_damage(card, energy, getattr(context, 'strength', 0))

        base_damage = self._non_negative_int(getattr(card, 'damage', 0))
        parsed_card_data_name = None

        if base_damage == 0 or not hasattr(card, 'damage'):
            try:
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    parsed_card_data_name = card_data.get('name', '')
                    parsed_damage = game_data_loader._parse_card_damage(card_data)
                    base_damage = parsed_damage if parsed_damage is not None else 0
            except Exception:
                base_damage = 0

        if base_damage == 0:
            base_damage = 6

        if (
            card_name == 'Searing Blow'
            and is_card_upgraded(card)
            and parsed_card_data_name is not None
            and '+' not in str(parsed_card_data_name or '')
        ):
            base_damage += known_damage_upgrade_bonus(card, card_name)

        strength = getattr(context, 'strength', 0)
        if card_name == 'Heavy Blade':
            return max(0, base_damage + strength * heavy_blade_strength_multiplier(card))
        if card_name == 'Perfected Strike':
            return max(
                0,
                base_damage + strike_card_count(context) * perfected_strike_bonus_per_strike(card) + strength,
            )

        hit_count = self._get_attack_hit_count(card, context)
        return max(0, base_damage + strength) * hit_count

    @staticmethod
    def _get_attack_hit_count(card: Card, context: Optional[DecisionContext] = None) -> int:
        card_name = canonical_card_name(card)
        fixed_hit_count = fixed_attack_hit_count(card)
        if fixed_hit_count is not None:
            return fixed_hit_count

        if card_name == 'Fiend Fire' and context is not None:
            return fiend_fire_exhaust_count(card, context)

        return 1

    def _known_attack_damage_for_bonus(self, card: Card) -> int:
        """Return known attack damage for strategic bonuses without generic fallback."""
        card_type = card_type_name(card)
        if card_type and card_type != 'ATTACK':
            return 0

        base_damage = self._non_negative_int(getattr(card, 'damage', 0))
        if base_damage > 0:
            return base_damage

        try:
            card_name = canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if not card_data:
                return 0

            parsed_damage = game_data_loader._parse_card_damage(card_data)
            if parsed_damage is None or parsed_damage <= 0:
                return 0
            return parsed_damage + known_damage_upgrade_bonus(card, card_name)
        except Exception:
            return 0

    def _should_explore_targets(self, context: DecisionContext, elapsed_time: float) -> bool:
        """
        Determine if target exploration should be enabled based on game state.

        Enable when ALL of:
        - 2-3 monsters alive (not overwhelming)
        - Hand size <= 5 cards (manageable complexity)
        - At least one single-target attack or debuff card in hand
        - Beam search time < 60ms (not approaching timeout)
        - NOT in cleanup phase (not all monsters < 8 HP)

        Args:
            context: Decision context
            elapsed_time: Time elapsed in beam search so far (ms)

        Returns:
            True if target exploration should be enabled, False otherwise
        """
        monster_count = len(context.monsters_alive)
        hand_size = len(context.hand) if hasattr(context, 'hand') else len(context.playable_cards)

        # Condition 1: Monster count
        if monster_count > 3:
            logger.info(f"[TARGET_EXPLORE] Disabled - {monster_count} monsters > 3")
            return False
        if monster_count < 2:
            logger.info(f"[TARGET_EXPLORE] Disabled - {monster_count} monster < 2")
            return False

        # Condition 2: Hand size
        if hand_size > 5:
            logger.info(f"[TARGET_EXPLORE] Disabled - hand size {hand_size} > 5")
            return False

        # Condition 3: Check for single-target cards
        has_single_target = False
        for card in context.playable_cards:
            if card_requires_target(card, AOE_ATTACK_CARDS):
                has_single_target = True
                break

        if not has_single_target:
            logger.info("[TARGET_EXPLORE] Disabled - no single-target cards")
            return False

        # Condition 4: Timeout protection
        if elapsed_time > 60:
            logger.info(f"[TARGET_EXPLORE] Disabled - timeout risk ({elapsed_time:.1f}ms > 60ms)")
            return False

        # Condition 5: Cleanup phase detection
        # Note: Can't access state.monsters here, so use context
        all_low_hp = all(
            self._non_negative_int(getattr(m, 'current_hp', 0)) < 8
            for m in context.monsters_alive
        )
        if all_low_hp:
            logger.info("[TARGET_EXPLORE] Disabled - cleanup phase (all monsters < 8 HP)")
            return False

        logger.info(f"[TARGET_EXPLORE] Enabled - {monster_count} monsters, {hand_size} cards, {elapsed_time:.1f}ms")
        return True

    def _score_sequence(self, sequence: List[Action], initial_state: SimulationState,
                       final_state: SimulationState, context: DecisionContext) -> float:
        """
        Score an action sequence.

        Priorities:
        1. Killing monsters (highest priority)
        2. Damage dealt
        3. Block gained (only when needed)
        4. Energy efficiency
        5. Strategic value (powers, draw cards)
        6. Elite-specific tactics (applied via unified framework)
        """
        score = 0.0
        final_state = self.simulator.project_end_turn_effects(final_state)

        # DEBUG: Log when _score_sequence is called
        if len(sequence) <= 1:
            logger.info("[SCORE_DEBUG] _score_sequence called - will call _detect_elite_type")

        # Detect elite type for specialized strategies (A20 elite framework)
        elite_type = self._detect_elite_type(context)

        # Special handling for monsters that require quick kills
        cultist_ritual = self._is_cultist_ritual_turn(context)
        has_cultist = self._has_cultist(context)
        has_gremlin_nob = self._has_gremlin_nob(context)
        has_awakened_one = self._has_awakened_one(context)
        lagavulin_hibernating = self._is_lagavulin_hibernating(context)
        has_lagavulin = self._has_lagavulin(context)
        
        # Determine if we should prioritize attack over defense
        # These monsters have scaling damage or dangerous mechanics
        if cultist_ritual:
            # Cultist is gaining Strength, will attack next turn with more damage
            damage_weight = 5.0
            block_penalty = True
        elif lagavulin_hibernating:
            # Lagavulin is hibernating: favor damage if available, but don't punish setup blocks/draw.
            damage_weight = 5.0
            block_penalty = False
        elif has_gremlin_nob or has_lagavulin or has_cultist:
            # These monsters have scaling damage or dangerous mechanics
            # Defense is not sustainable - always prioritize attacking
            damage_weight = 4.0
            block_penalty = True
        else:
            damage_weight = 3.0
            block_penalty = False

        # If no attack cards are playable, don't punish defensive sequences.
        if block_penalty:
            has_attack_playable = any(
                is_attack_card(card)
                for card in context.playable_cards
            )
            if not has_attack_playable:
                block_penalty = False

        # 1. Monsters killed (huge bonus)
        kills = final_state.monsters_killed
        score += kills * 200
        total_monsters = len(context.monsters_alive)
        all_killed = total_monsters > 0 and kills >= total_monsters

        # 2. Damage dealt (with multi-monster bonuses)
        damage = final_state.total_damage_dealt

        # Multi-monster detection and adaptive damage weighting
        num_monsters = len(context.monsters_alive)

        # Get floor for special Floor 6-7 handling
        current_floor = getattr(context, 'floor', 0)

        # Base damage multiplier based on monster count
        if num_monsters >= 3:
            damage_multiplier = 1.8
        elif num_monsters == 2:
            damage_multiplier = 1.3
        else:
            damage_multiplier = 1.0

        # Floor 6-7 special AOE priority (highest death floors)
        if current_floor in [6, 7] and num_monsters >= 2:
            floor_bonus = 0.4 if num_monsters >= 3 else 0.2
            damage_multiplier += floor_bonus
            logger.info(f"[FLOOR6_AOE] Enhanced priority on Floor {current_floor}: {damage_multiplier}×")

        logger.info(f"[OUTCOME_MONSTERS] Detected {num_monsters} alive monsters")
        logger.info(f"[OUTCOME_MULTIPLIER] Applied {damage_multiplier}× damage weight (base: {damage_weight})")

        score += damage * damage_weight * damage_multiplier

        # AOE card bonus in multi-monster scenarios
        if num_monsters >= 2:
            aoe_cards = ['Cleave', 'Whirlwind', 'Thunderclap', 'Immolate']

            for action in sequence:
                if isinstance(action, PlayCardAction) and getattr(action, 'card', None) is not None:
                    card_id = canonical_card_name(action.card)

                    if card_id in aoe_cards:
                        aoe_bonus = 40 if num_monsters >= 3 else 20
                        score += aoe_bonus
                        logger.info(f"[OUTCOME_AOE] +{aoe_bonus} for {card_id} in {num_monsters}-monster fight")

        # 3. Block (only valuable when taking damage, but less valuable than attacking)
        # Defense is temporary (blocks 1 turn), while killing monsters is permanent
        initial_turn_block = initial_state.turn_block()
        final_turn_block = final_state.turn_block()
        block_gained = final_turn_block - initial_turn_block
        incoming_damage = context.incoming_damage

        if block_penalty and block_gained > 0:
            # Heavily penalize block against monsters with scaling/dangerous mechanics
            # This prevents the AI from prolonging the battle
            score -= block_gained * 10
        elif incoming_damage > initial_turn_block:
            # Need block - value it, but less than damage
            # Defense is temporary (blocks 1 turn), attack is permanent (kills monsters)
            block_value = 3 if self._is_low_scaling_encounter(context) else 2
            score += min(block_gained, incoming_damage) * block_value
        else:
            # Already safe - minimal value
            score += block_gained * 0.5

        # 3.5. Future damage penalty (multi-turn enemy lookahead)
        try:
            lookahead_turns = self.simulator._get_enemy_lookahead_depth(final_state, context)
            future_damage = self.simulator.simulate_enemy_lookahead(final_state, context, look_ahead=lookahead_turns)
            if future_damage > 0:
                future_damage_penalty = future_damage * W_DEATHRISK * 0.5
                score -= future_damage_penalty
                logger.info(
                    "[FUTURE_DAMAGE_PENALTY] -%.1f score for %s predicted damage over next %s turns",
                    future_damage_penalty,
                    future_damage,
                    lookahead_turns
                )
        except Exception as e:
            logger.warning("[FUTURE_DAMAGE_PENALTY] Failed to apply future damage penalty: %s", e)

        # 4. Energy efficiency
        energy_used = final_state.energy_spent
        score += energy_used * 2
        # Draw/energy gains (Offering/Bloodletting/etc.)
        score += final_state.cards_drawn * 3
        score += final_state.energy_gained * 4

        # 5. Strategic bonus for card types
        for action in sequence:
            if isinstance(action, PlayCardAction):
                card = action.card
                card_id = canonical_card_name(card)
                raw_card_id = getattr(card, 'card_id', card_id)
                card_type = card_type_name(card)

                if card_type == "POWER":
                    if context.turn <= 2:
                        power_bonus = POWER_BONUS_EARLY
                    elif context.turn <= 4:
                        power_bonus = POWER_BONUS_MID
                    else:
                        power_bonus = POWER_BONUS_LATE
                    score += power_bonus
                    logger.debug(f"[POWER_BONUS] +{power_bonus} for {raw_card_id} on turn {context.turn}")

                    if has_awakened_one and not all_killed:
                        score -= AWAKENED_ONE_POWER_PENALTY
                        logger.info(
                            "[AWAKENED_POWER_PENALTY] -%s for %s against Awakened One",
                            AWAKENED_ONE_POWER_PENALTY,
                            card_id,
                        )

                # HP-cost cards: strong penalty at low HP unless the sequence kills everything
                hp_costs = {
                    'Offering': 6,
                    'Bloodletting': 3,
                    'Hemokinesis': 2,
                }
                if card_id in hp_costs and not all_killed:
                    hp_cost = hp_costs[card_id]
                    if context.player_hp <= hp_cost:
                        score -= 1000
                    else:
                        multiplier = 1.0
                        if context.player_hp_pct < 0.3:
                            multiplier = 3.0
                        elif context.player_hp_pct < 0.5:
                            multiplier = 2.0
                        penalty_per_hp = 12
                        penalty = hp_cost * penalty_per_hp * multiplier
                        score -= penalty

                # Gremlin Nob SKILL penalty: playing SKILL cards gives Nob +1 Strength
                # This heavily penalizes SKILL cards to discourage triggering Nob's passive
                if has_gremlin_nob and card_type == "SKILL":
                    score -= 50
                    logger.info(f"[SKILL_PENALTY] Applied -50 for {card_id} (SKILL) against Gremlin Nob")

                # Powers are valuable early
                if card_id == 'Demon Form' and context.turn <= 3:
                    score += 50

                # Draw cards help consistency
                if self._is_draw_card(card):
                    score += 15

                # Armaments: value upgrades proportional to available targets
                if card_id == 'Armaments':
                    upgradeable = self._count_upgradeable_cards(
                        context,
                        exclude_uuid=getattr(card, 'uuid', None),
                        exclude_card=card,
                    )
                    if upgradeable > 0:
                        per_card = 3 if is_card_upgraded(card) else 2
                        score += per_card * upgradeable

                # Limit Break with high strength
                if card_id == 'Limit Break' and context.strength >= 5:
                    score += 40

                # Reaper - huge heal potential with Strength
                if card_id == 'Reaper':
                    # Value scales with Strength and number of monsters
                    monster_count = len(context.monsters_alive)
                    if context.strength >= 3 and monster_count >= 2:
                        # Optimal Reaper usage
                        score += 60
                    elif context.strength >= 5 and monster_count >= 1:
                        # Still good with high Strength
                        score += 40
                    # Low strength/single target - minimal bonus

                # Bash before big attacks
                if card_id == 'Bash':
                    # Check if we have big attacks remaining
                    big_attack_pending = any(
                        self._is_big_attack_followup(c, context, current_card=card)
                        for c in context.playable_cards
                    )
                    if big_attack_pending:
                        score += 25

                # Hybrid cards (block + damage) - special handling
                if card_id in ['Iron Wave', 'Flame Barrier']:
                    # Value both the block and damage aspects
                    # Block values from game_data_loader since card.block is not set
                    if card_id == 'Iron Wave':
                        block_val = 7 if is_card_upgraded(card) else 5
                    elif card_id == 'Flame Barrier':
                        block_val = 16 if is_card_upgraded(card) else 12
                    else:
                        # Fallback: try to get from game data
                        block_val = 0

                    if block_val > 0:
                        score += block_val * 3  # Value block

                    damage_value = self._known_attack_damage_for_bonus(card)
                    if damage_value > 0:
                        score += damage_value * 1.5  # Value damage
                    # Bonus for hybrid nature
                    score += 15
                
                # High priority cards that need special handling
                elif card_id == 'Immolate':
                    # Immolate: high damage + card draw, despite self-damage
                    damage_value = self._known_attack_damage_for_bonus(card)
                    if damage_value > 0:
                        score += damage_value * 2.0  # Value damage highly
                    # Value card draw potential
                    score += 10
                    # Penalize for self-damage only if HP is low
                    if context.player_hp_pct < 0.3:
                        score -= 15
                
                elif card_id == 'Rage':
                    # Rage: provides scaling damage boost
                    score += 20  # Base bonus for scaling potential
                    # More valuable with high strength
                    if context.strength >= 5:
                        score += 15
                
                elif card_id == 'Whirlwind':
                    # Whirlwind: excellent AOE damage
                    monster_count = len(context.monsters_alive)
                    if monster_count >= 2:
                        score += 25  # Bonus for multiple monsters
                    damage_value = self._known_attack_damage_for_bonus(card)
                    if damage_value > 0:
                        score += damage_value * monster_count * 0.5  # Value per target
                
                elif card_id == 'Battle Trance':
                    # Battle Trance: critical card draw
                    score += 30  # High value for consistency
                    # More valuable with small decks
                    if hasattr(context, 'deck_size') and context.deck_size <= 20:
                        score += 15
                
                elif card_id == 'Double Tap':
                    # Double Tap: enables powerful combos
                    score += 25  # Base combo potential
                    # Check if we have high-damage cards to combo with
                    has_high_damage = any(
                        canonical_card_name(c) in ['Perfected Strike', 'Heavy Blade', 'Body Slam']
                        for c in context.playable_cards
                    )
                    if has_high_damage:
                        score += 20

        # Apply elite-specific strategy overrides (unified framework)
        score = self._apply_elite_strategy_override(
            elite_type, sequence, initial_state, final_state, context, score
        )

        return score

    def _is_low_scaling_encounter(self, context: DecisionContext) -> bool:
        """Return True for fights without meaningful scaling or time pressure."""
        try:
            monsters = getattr(context, 'monsters_alive', [])
            if not monsters:
                return False

            for monster in monsters:
                name = canonical_live_monster_name(monster)
                if not name:
                    return False

                if game_data_loader.is_monster_summoner(name):
                    return False
                if game_data_loader.does_monster_have_phase_change(name):
                    return False

                threat_profile = game_data_loader.get_monster_threat_profile(name) or {}
                scaling = threat_profile.get('scaling_threat', 0)
                if scaling > 2:
                    return False
                if 'time_pressure' in threat_profile or 'echoing_doom' in threat_profile:
                    return False

            return True
        except Exception:
            return False

    def _is_draw_card(self, card: Card) -> bool:
        """Check if card draws cards."""
        draw_keywords = ['draw', 'pommel strike', 'shrug it off', 'battle trance']
        card_lower = canonical_card_name(card).lower().replace('_', ' ')
        return any(kw in card_lower for kw in draw_keywords)

    def _count_upgradeable_cards(self, context: DecisionContext, exclude_uuid=None, exclude_card=None) -> int:
        """Count upgradeable cards in hand (excluding the Armaments card itself)."""
        hand = getattr(context, 'hand', None)
        if not hand:
            hand = getattr(context, 'playable_cards', [])
        count = 0
        for card in hand:
            if exclude_card is not None and card is exclude_card:
                continue
            if exclude_uuid is not None and getattr(card, 'uuid', None) == exclude_uuid:
                continue
            if card_upgrade_count(card) == 0:
                count += 1
        return count

    def _fallback_plan(self, context: DecisionContext,
                       playable_cards: List[Card]) -> List[Action]:
        """Fallback to priority-based selection if beam search fails."""
        # Score each card
        scored_cards = []
        for card in playable_cards:
            score = self._get_card_priority(card, context)
            scored_cards.append((card, score))

        # Sort and return best
        scored_cards.sort(key=lambda x: x[1], reverse=True)

        if scored_cards and scored_cards[0][1] > 0:
            best_card = scored_cards[0][0]
            if card_requires_target(best_card, AOE_ATTACK_CARDS) and context.monsters_alive:
                target, _ = self._choose_target_for_card(best_card, context, SimulationState(context))
                return [PlayCardAction(card=best_card, target_monster=target)]
            else:
                return [PlayCardAction(card=best_card)]

        return []

    def _get_card_priority(self, card: Card, context: DecisionContext) -> float:
        """Get priority score for a card (simplified version of existing logic)."""
        card_type = card_type_name(card)
        card_id = canonical_card_name(card)
        
        # Check if fighting Gremlins or other weak monsters that require aggressive play
        aggressive_mode = False
        for monster in context.monsters_alive:
            monster_info = self._get_monster_info(monster)
            strategy = monster_info.get("recommended_strategy", "balanced")
            if strategy in ["aggressive", "priority_aggressive", "kill_quickly", "focus_down"]:
                aggressive_mode = True
                break
        
        # Check if all monsters are weak (low threat)
        all_weak = all(self._get_monster_info(m).get("threat_level", 2) <= 1 for m in context.monsters_alive)
        if all_weak:
            aggressive_mode = True

        # Powers first
        if card_type == 'POWER':
            if self._has_awakened_one(context):
                return -200
            if card_id == 'Demon Form' and context.turn <= 3:
                return 1000
            return 600 if context.turn <= 3 else 400

        # Draw cards
        if self._is_draw_card(card):
            return 800

        # Bash before attacks
        if card_id == 'Bash':
            return 850 if self._should_bash_now(context) else 100

        # Special hybrid cards (block + damage) - Iron Wave
        if card_id == 'Iron Wave':
            # Iron Wave is excellent hybrid card - value it highly
            # Always good, but even better when we need block
            if context.incoming_damage > context.game.player.block:
                return 850  # High priority when we need block
            return 750  # Still good when we don't need block

        # Attacks - prioritize more in aggressive mode
        if card_type == 'ATTACK':
            base_attack_priority = 700
            
            # Increase attack priority for aggressive mode against Gremlins
            if aggressive_mode:
                base_attack_priority = 900
            
            if card_id == 'Reaper' and len(context.monsters_alive) >= 2:
                return 900 if context.strength >= 5 else base_attack_priority
            if card_id == 'Body Slam' and context.game.player.block >= 20:
                return 950
            return base_attack_priority

        # Other defense cards - decrease priority for aggressive mode
        if self._is_defensive_card(card):
            # In aggressive mode, only use defense cards if incoming damage is very high
            if aggressive_mode:
                # Only use defense if incoming damage is extremely high
                player_hp = self._non_negative_float(context.game.current_hp)
                if context.incoming_damage > player_hp * 0.8:
                    return 600
                # Otherwise, lower defense priority
                return 100
            # Normal mode - use defense when needed
            return 700 if context.incoming_damage > context.game.player.block else 200

        return 400
        
    def _get_monster_info(self, monster):
        """Get monster info from database."""
        from .monster_database import get_monster_info
        return get_monster_info(monster.monster_id)

    def _should_bash_now(self, context: DecisionContext) -> bool:
        """Check if Bash should be played now."""
        # Bash is good if we have big attacks to follow up
        return any(
            self._is_big_attack_followup(card, context)
            for card in context.playable_cards
        )

    def _is_big_attack_followup(
        self,
        candidate: Card,
        context: DecisionContext,
        current_card: Optional[Card] = None,
    ) -> bool:
        """Return whether candidate is a meaningful attack to amplify after Bash."""
        if candidate is current_card:
            return False

        current_uuid = getattr(current_card, 'uuid', None)
        if current_uuid and getattr(candidate, 'uuid', None) == current_uuid:
            return False

        card_name = canonical_card_name(candidate)
        if card_name in ['Bash', 'Strike', 'Defend']:
            return False

        if not is_attack_card(candidate):
            return False

        return self._estimate_attack_damage_without_simulation(candidate, context) > 10

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is defensive."""
        # Block values from game_data_loader since card.block is not set
        # So we check by card_id instead
        # Complete list of 47 defensive cards across all 4 characters (from items.json analysis)
        defensive_keywords = [
            'armaments', 'backflip', 'blur', 'boot sequence', 'charge battery',
            'cloak and dagger', 'dash', 'deceive reality', 'defend', 'deflect',
            'dodge and roll', 'empty body', 'entrench', 'equilibrium', 'evaluate',
            'finesse', 'flame barrier', 'force field', 'genetic algorithm', 'ghostly armor',
            'glacier', 'good instincts', 'halt', 'hologram', 'impervious', 'iron wave',
            'just lucky', 'leap', 'leg sweep', 'panic button', 'perseverance', 'power through',
            'prostrate', 'protect', 'reinforced body', 'safety', 'sanctity', 'second wind',
            'sentinel', 'shrug it off', 'spirit shield', 'steam barrier', 'survivor', 'swivel',
            'third eye', 'true grit', 'vigilance'
        ]
        card_lower = canonical_card_name(card).lower().replace('_', ' ')
        return any(keyword in card_lower for keyword in defensive_keywords)

    def _is_cultist_ritual_turn(self, context: DecisionContext) -> bool:
        """
        Check if any Cultist is using Ritual (non-attack turn).
        
        Cultist uses Ritual on first turn to gain Strength, which means:
        - No damage this turn (safe to attack)
        - Next turn will deal more damage (need to kill quickly)
        
        Args:
            context: Current decision context
            
        Returns:
            True if any Cultist is using Ritual this turn
        """
        for monster in context.monsters_alive:
            if monster.monster_id == "Cultist":
                if hasattr(monster, 'intent'):
                    if not intent_is_attack(monster.intent):
                        return True
        return False

    def _has_cultist(self, context: DecisionContext) -> bool:
        """
        Check if there are any Cultists alive.
        
        Cultist's damage scales with Strength each turn, so defense is not sustainable.
        We should always prioritize attacking over defending.
        
        Args:
            context: Current decision context
            
        Returns:
            True if any Cultist is alive
        """
        return any(monster.monster_id == "Cultist" for monster in context.monsters_alive)

    def _has_gremlin_nob(self, context: DecisionContext) -> bool:
        """
        Check if there are any Gremlin Nob alive.
        
        Gremlin Nob is an Act 1 elite that gains Strength when using Bash.
        Its damage scales with Strength, making defense unsustainable.
        We should always prioritize attacking over defending.
        
        Args:
            context: Current decision context
            
        Returns:
            True if any Gremlin Nob is alive
        """
        return any(self._is_gremlin_nob(monster) for monster in context.monsters_alive)

    def _has_awakened_one(self, context: DecisionContext) -> bool:
        """Return True if Awakened One is alive in the current combat."""
        for monster in getattr(context, "monsters_alive", []) or []:
            identifiers = [
                getattr(monster, "monster_id", ""),
                getattr(monster, "name", ""),
            ]
            for identifier in identifiers:
                normalized = "".join(
                    ch for ch in str(identifier).lower() if ch.isalnum()
                )
                if "awakenedone" in normalized:
                    return True
        return False

    def _is_lagavulin_hibernating(self, context: DecisionContext) -> bool:
        """
        Check if any Lagavulin is hibernating (charging up).
        
        Lagavulin hibernates for 3 turns, then deals massive damage (18-22).
        We should kill it before it wakes up, or at least minimize defense.
        
        Args:
            context: Current decision context
            
        Returns:
            True if any Lagavulin is hibernating
        """
        for monster in context.monsters_alive:
            if monster.monster_id == "Lagavulin":
                if hasattr(monster, 'intent'):
                    if "DEFEND" in intent_tokens(monster.intent):
                        return True
        return False

    def _has_lagavulin(self, context: DecisionContext) -> bool:
        """
        Check if there are any Lagavulin alive.

        Lagavulin is an Act 1 elite with hibernation mechanics.
        After hibernating, it deals massive damage.
        We should prioritize attacking over defending throughout the fight.

        Args:
            context: Current decision context

        Returns:
            True if any Lagavulin is alive
        """
        return any(monster.monster_id == "Lagavulin" for monster in context.monsters_alive)

    def _detect_elite_type(self, context: DecisionContext) -> EliteType:
        """
        Detect which Act 1 elite we're fighting to apply specialized strategy.

        This unified detection system enables elite-specific tactics:
        - Gremlin Nob: SKILL card penalty (-50)
        - Lagavulin: Progressive scaling based on Siphon Soul count
        - 3 Sentries: Single-target focus bonus
        - Slime Boss: AOE damage priority

        Args:
            context: Current decision context

        Returns:
            EliteType enum value indicating the elite type (or UNKNOWN)
        """
        logger.info("[ELITE_ENTRY] _detect_elite_type called")

        if not context.monsters_alive:
            logger.info("[ELITE_ENTRY] No monsters alive, returning UNKNOWN")
            return EliteType.UNKNOWN

        monster_ids = [m.monster_id for m in context.monsters_alive]
        monster_names = [m.name for m in context.monsters_alive]

        # DEBUG: Log monster IDs and names for debugging
        logger.info(f"[ELITE_DEBUG] monster_ids: {monster_ids}")
        logger.info(f"[ELITE_DEBUG] monster_names: {monster_names}")

        # Gremlin Nob: live ids may be "GremlinNob" while display names include a space.
        if any(self._is_gremlin_nob(monster) for monster in context.monsters_alive):
            logger.info("[ELITE_DETECTION] Gremlin Nob detected - SKILL penalty active")
            return EliteType.GREMLIN_NOB

        # Lagavulin: Single elite with specific name
        if "Lagavulin" in monster_ids:
            logger.info("[ELITE_DETECTION] Lagavulin detected - progressive scaling active")
            return EliteType.LAGAVULIN

        # 3 Sentries: Multiple monsters with "Sentry" in name
        sentry_count = sum(1 for name in monster_names if "Sentry" in name)
        if sentry_count >= 2:  # Usually 3, but might kill one already
            logger.info(f"[ELITE_DETECTION] 3 Sentries detected ({sentry_count} alive) - single-target focus active")
            return EliteType.THREE_SENTRIES

        # Slime Boss: Single monster with "Slime" in name
        if len(context.monsters_alive) == 1:
            monster = context.monsters_alive[0]
            monster_id = getattr(monster, 'monster_id', '')
            monster_name = getattr(monster, 'name', '')
            if monster_id == "Slime_Boss" or monster_name == "Slime Boss":
                logger.info("[ELITE_DETECTION] Slime Boss detected - AOE priority active")
                return EliteType.SLIME_BOSS

        return EliteType.UNKNOWN

    def _apply_elite_strategy_override(
        self,
        elite_type: EliteType,
        sequence: List[Action],
        initial_state: SimulationState,
        final_state: SimulationState,
        context: DecisionContext,
        base_score: float
    ) -> float:
        """
        Apply elite-specific strategy overrides using unified framework.

        This is the central integration point for all Act 1 elite tactics.
        Each elite type has specialized handling based on its unique mechanics.

        Args:
            elite_type: Type of elite detected (Gremlin Nob, Lagavulin, etc.)
            sequence: Action sequence being scored
            initial_state: Starting simulation state
            final_state: Ending simulation state after sequence
            context: Current decision context
            base_score: Pre-calculated score from base evaluation

        Returns:
            Final score after applying elite-specific modifiers
        """
        score = base_score

        # Apply elite-specific strategies
        if elite_type == EliteType.GREMLIN_NOB:
            # Gremlin Nob: SKILL penalty already applied in card loop (v3.3.1)
            # No additional modifiers needed here - existing logic handles it
            pass

        elif elite_type == EliteType.LAGAVULIN:
            # Lagavulin: Progressive scaling based on Siphon Soul count
            score = self._apply_lagavulin_strategy(sequence, initial_state, final_state, context, score)

        elif elite_type == EliteType.THREE_SENTRIES:
            # 3 Sentries: Single-target focus bonus
            score = self._apply_sentries_strategy(sequence, context, score)

        elif elite_type == EliteType.SLIME_BOSS:
            # Slime Boss: AOE damage priority
            score = self._apply_slime_boss_strategy(sequence, context, score)

        # A20 Early Aggression (applies to ALL elites at ascension >= 20)
        if elite_type != EliteType.UNKNOWN and self._context_ascension_level(context) >= 20:
            score = self._apply_a20_early_aggression(sequence, initial_state, final_state, context, score)

        return score

    def _apply_lagavulin_strategy(
        self,
        sequence: List[Action],
        initial_state: SimulationState,
        final_state: SimulationState,
        context: DecisionContext,
        score: float
    ) -> float:
        """
        Apply Lagavulin-specific strategy: progressive scaling based on Siphon Soul count.

        Lagavulin uses Siphon Soul every 3 turns (turns 6, 9, 12, ...) which reduces
        player Dexterity and Strength, making the fight progressively harder.

        Strategy: Exponentially increase damage_weight as Siphon Soul count increases.

        Formula: damage_weight = min(8.0, 4.0 + (siphon_count × 1.5))

        Args:
            sequence: Action sequence being scored
            initial_state: Starting simulation state
            final_state: Ending simulation state after sequence
            context: Current decision context
            score: Current score

        Returns:
            Adjusted score with Lagavulin-specific modifiers
        """
        if not hasattr(context, 'turn'):
            return score

        turn = context.turn

        # Calculate Siphon Soul count (starts turn 6, happens every 3 turns)
        if turn < 6:
            siphon_count = 0
            damage_weight = 5.0  # Early hibernation phase
        else:
            siphon_count = (turn - 6) // 3 + 1
            damage_weight = min(8.0, 4.0 + (siphon_count * 1.5))

        # Calculate damage dealt in this sequence
        damage_dealt = final_state.total_damage_dealt - initial_state.total_damage_dealt

        # Apply progressive damage bonus
        damage_bonus = damage_dealt * damage_weight
        score += damage_bonus

        # Low-damage penalty after first Siphon (turn 6+)
        if turn >= 6:
            min_damage_needed = 15 + (siphon_count * 5)
            if damage_dealt < min_damage_needed:
                penalty = 200
                score -= penalty
                logger.info(f"[LAGAVULIN_LOW_DAMAGE] -{penalty} for {damage_dealt} damage (need {min_damage_needed}+, siphon_count={siphon_count})")

        # Pre-Siphon Soul burst bonus (incentivize killing before next debuff)
        if turn >= 5:
            turns_until_siphon = 2 - (turn - 5) % 3
            if turns_until_siphon == 1 and damage_dealt > 30:
                bonus = 100
                score += bonus
                logger.info(f"[LAGAVULIN_BURST] +{bonus} for {damage_dealt} damage before Siphon Soul")

        logger.debug(f"[LAGAVULIN] Turn {turn}: Siphon count={siphon_count}, damage_weight={damage_weight:.1f}, damage_bonus={damage_bonus:.1f}")

        return score

    def _apply_sentries_strategy(
        self,
        sequence: List[Action],
        context: DecisionContext,
        score: float
    ) -> float:
        """
        Apply 3 Sentries strategy: reward concentrated damage on one elite.

        Principle: "Burst down one" is better than spreading damage evenly.
        When two Sentries both use Focus to gain Strength, the fight becomes much harder.
        We must eliminate one Sentry ASAP before both stack high Strength.

        Scoring:
        - 70%+ damage on one target → +50 bonus (concentrated fire)
        - <50% concentration → -30 penalty (spreading damage too evenly)

        Args:
            sequence: Action sequence being scored
            context: Current decision context
            score: Current score

        Returns:
            Adjusted score with Sentries-specific modifiers
        """
        if len(context.monsters_alive) < 2:
            # Only one Sentry left, normal priority
            return score

        # Calculate damage distribution
        damage_by_target = self._calculate_damage_distribution(sequence, context)

        if not damage_by_target or damage_by_target['total_damage'] == 0:
            # No damage dealt, no modifiers
            return score

        # Calculate concentration ratio
        concentration = damage_by_target['highest_damage'] / damage_by_target['total_damage']

        # Bonus: 70%+ damage on one target = +50 points
        if concentration >= 0.7:
            bonus = 50
            score += bonus
            logger.info(f"[SENTRIES_FOCUS] +{bonus} for concentrating {concentration:.1%} damage on one target")

        # Penalty: Evenly spread damage (<50% on any target) = -30 points
        elif concentration < 0.5 and damage_by_target['total_damage'] > 15:
            penalty = 30
            score -= penalty
            logger.info(f"[SENTRIES_SPREAD] -{penalty} for spreading damage too evenly ({concentration:.1%} concentration)")

        return score

    def _calculate_damage_distribution(self, sequence: List[Action], context: DecisionContext) -> Dict:
        """
        Calculate how damage is distributed across monsters.

        Used by 3 Sentries strategy to determine if damage is concentrated on one target.

        Args:
            sequence: Action sequence to analyze
            context: Current decision context

        Returns:
            Dict with 'highest_damage', 'total_damage', and optionally 'target_count'
        """
        damage_by_target = {}

        for action in sequence:
            if isinstance(action, PlayCardAction):
                card = action.card
                # Try to get target monster
                target = getattr(action, 'target_monster', None)
                target_idx = self.simulator._resolve_target_index(
                    target,
                    getattr(action, 'target_index', None),
                    context,
                )
                if target_idx is not None and 0 <= target_idx < len(context.monsters_alive):
                    target = context.monsters_alive[target_idx]
                elif target is None and card_requires_target(card, AOE_ATTACK_CARDS) and context.monsters_alive:
                    # Default to first monster if we can't determine target
                    target = context.monsters_alive[0]
                    target_idx = 0

                if target:
                    damage = (
                        self._estimate_attack_damage_to_target(
                            card,
                            context,
                            SimulationState(context),
                            target_idx,
                        )
                        if target_idx is not None
                        else self._estimate_attack_damage_without_simulation(card, context)
                    )
                    if damage <= 0:
                        continue

                    # Use monster id or index as key
                    target_key = id(target)
                    damage_by_target[target_key] = damage_by_target.get(target_key, 0) + damage

        if damage_by_target:
            return {
                'highest_damage': max(damage_by_target.values()),
                'total_damage': sum(damage_by_target.values()),
                'target_count': len(damage_by_target)
            }
        else:
            return {'highest_damage': 0, 'total_damage': 0, 'target_count': 0}

    def _apply_slime_boss_strategy(
        self,
        sequence: List[Action],
        context: DecisionContext,
        score: float
    ) -> float:
        """
        Apply Slime Boss strategy: prioritize AOE damage.

        Slime Boss splits into 3 monsters at 50% HP, making AOE attacks highly valuable.
        AOE cards damage the boss before split AND all spawned slimes after split.

        Strategy:
        - AOE cards (Cleave, Thunderclap, Whirlwind, Immolate) → ×1.5 damage multiplier
        - High damage (>12) near split threshold (40-60% HP) → +30 bonus

        Args:
            sequence: Action sequence being scored
            context: Current decision context
            score: Current score

        Returns:
            Adjusted score with Slime Boss-specific modifiers
        """
        if not context.monsters_alive:
            return score

        # Get Slime Boss HP percentage
        slime_boss = context.monsters_alive[0]
        if hasattr(slime_boss, 'current_hp') and hasattr(slime_boss, 'max_hp'):
            max_hp = self._non_negative_float(slime_boss.max_hp)
            hp_pct = (
                self._non_negative_float(slime_boss.current_hp) / max_hp
                if max_hp > 0
                else 1.0
            )
        else:
            hp_pct = 1.0  # Default to full HP if unknown

        # AOE cards list
        aoe_cards = ['Cleave', 'Thunderclap', 'Whirlwind', 'Immolate']

        for action in sequence:
            if isinstance(action, PlayCardAction):
                card = action.card
                card_id = canonical_card_name(card)
                damage = 0
                if is_attack_card(card):
                    damage = self._estimate_attack_damage_to_target(
                        card,
                        context,
                        SimulationState(context),
                        0,
                    )

                # AOE damage multiplier (×1.5)
                if card_id in aoe_cards:
                    monster_count = len(context.monsters_alive)
                    if damage > 0:
                        aoe_damage = damage * monster_count
                        bonus = aoe_damage * 1.5
                        score += bonus
                        logger.info(f"[SLIME_AOE] +{bonus:.1f} for {card_id} ({aoe_damage} damage × 1.5 to {monster_count} targets)")

                # Near split threshold (40-60% HP): Extra bonus for high damage
                if 0.4 < hp_pct < 0.6:
                    if damage > 12:
                        burst_bonus = 30
                        score += burst_bonus
                        logger.info(f"[SLIME_BURST] +{burst_bonus} for high damage ({damage}) near split threshold")

        return score

    def _apply_a20_early_aggression(
        self,
        sequence: List[Action],
        initial_state: SimulationState,
        final_state: SimulationState,
        context: DecisionContext,
        score: float
    ) -> float:
        """
        Apply A20 early aggression rules for elite fights.

        At A20, elites kill you if you wait. Must damage from turn 1.
        This prevents passive "preparation" turns where AI only plays Powers/defends.

        Thresholds:
        - Turn 1: Require 8+ damage (-50 penalty if not)
        - Turn 2: Require 15+ damage (-100 penalty if not)
        - Turn 3+: Require 12 HP damage per turn average (-150 penalty if behind)

        Args:
            sequence: Action sequence being scored
            initial_state: Starting simulation state
            final_state: Ending simulation state after sequence
            context: Current decision context
            score: Current score

        Returns:
            Adjusted score with A20 early aggression penalties
        """
        if not hasattr(context, 'turn'):
            return score

        turn = context.turn
        damage_dealt = final_state.total_damage_dealt - initial_state.total_damage_dealt

        # Turn 1: At least some damage (8+)
        if turn == 1 and damage_dealt < 8:
            penalty = 50
            score -= penalty
            logger.info(f"[A20_AGGRESSION_TURN1] -{penalty} for only {damage_dealt} damage (need 8+)")

        # Turn 2: Significant damage expected (15+)
        if turn == 2 and damage_dealt < 15:
            penalty = 100
            score -= penalty
            logger.info(f"[A20_AGGRESSION_TURN2] -{penalty} for only {damage_dealt} damage (need 15+)")

        # Turn 3+: Kill pressure - check if we're keeping up
        if turn >= 3:
            # Calculate expected damage (12 HP per turn average)
            expected_damage = turn * 12

            # Include killed monsters so finished Sentries still count as progress.
            damage_so_far = self._combat_hp_damage_so_far(context)

            if damage_so_far < expected_damage:
                penalty = 150
                score -= penalty
                logger.info(f"[A20_AGGRESSION_TURN{turn}] -{penalty} for falling behind ({damage_so_far} damage vs {expected_damage} expected)")

        return score

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

        # Higher with lethal detected
        if self.combat_ending_detector.can_kill_all(context):
            confidence += 0.2

        return max(0.0, min(1.0, confidence))
