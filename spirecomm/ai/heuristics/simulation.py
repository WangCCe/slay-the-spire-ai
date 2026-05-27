"""
Fast combat simulation and action planning.

This module implements a combat simulator that can lookahead multiple actions
to find optimal play sequences using beam search.
"""

import copy
import logging
import re
import time
from typing import List, Dict, Tuple, Optional, Any
from spirecomm.spire.card import Card, CardType
from spirecomm.spire.character import Monster, Intent
from spirecomm.communication.action import Action, PlayCardAction, EndTurnAction
from spirecomm.ai.decision.base import DecisionContext, CombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.ai.heuristics.card_costs import (
    effective_card_cost,
    is_x_cost_card,
    raw_card_cost,
)
from spirecomm.data.loader import game_data_loader

# Configure logging for combat decisions
logger = logging.getLogger(__name__)


# =============================================================================
# SCORING WEIGHTS CONFIGURATION (Tune these based on testing results)
# =============================================================================

# Survival weights
W_DEATHRISK = 8.0  # Penalty per HP expected to be lost next turn
                   # Increase (→10-12) for more defensive play
                   # Decrease (→5-6) for more aggressive play
                   # Target: 15-25 HP loss per act

# Combat outcome weights
KILL_BONUS = 100  # Points per monster killed
                 # Increase if AI doesn't prioritize kills enough
                 # Decrease if AI overkills excessively

ALL_LETHAL_BONUS = 500  # Exponential bonus for killing ALL monsters
                       # This creates strong incentive to close out games
                       # Should be much higher than KILL_BONUS to prioritize all-kill over partial kill

DAMAGE_WEIGHT = 2.0  # Points per damage dealt
                    # Increase (→3-4) for more aggressive damage
                    # Decrease if AI ignores defense

BLOCK_WEIGHT = 1.5  # Points per block gained
                   # Increase (→2-3) for more defensive play
                   # Decrease if AI over-defends

ENERGY_EFFICIENCY_WEIGHT = 3.0  # Points per energy spent
                               # Reward for using available energy

HP_LOSS_PENALTY = 10.0  # Penalty per HP lost this turn
                       # Increase for more conservative play

# Danger threshold penalty
DANGER_PENALTY = 50.0  # Extra penalty when below danger threshold
                      # Threshold = 15 + (act * 5) → Act 1: 20, Act 2: 25, Act 3: 30

# Engine event synergy weights
EXHAULT_SYNERGY_VALUE = 3.0  # Points per exhaust event (Feel No Pain)
DRAW_SYNERGY_VALUE = 3.0  # Points per card drawn
ENERGY_SYNERGY_VALUE = 4.0  # Points per energy gained/saved (Corruption, Bloodletting)

# Debuff application bonuses
VULNERABLE_APPLY_BONUS = 6.0
WEAK_APPLY_BONUS = 3.0

# Lookahead risk adjustments for player debuffs
LOOKAHEAD_WEAK_RISK_PER_STACK = 0.05
LOOKAHEAD_FRAIL_RISK_PER_STACK = 0.07
LOOKAHEAD_DEBUFF_RISK_CAP = 0.2
LOOKAHEAD_DAMAGE_DISCOUNT = 0.8

# Adaptive search parameters
BEAM_WIDTH_ACT1 = 20  # Beam width for Act 1 (simple enemies) - increased from 12 (+67%)
BEAM_WIDTH_ACT2 = 30  # Beam width for Act 2 (moderate complexity) - increased from 18 (+67%)
BEAM_WIDTH_ACT3 = 40  # Beam width for Act 3 (high complexity, elites/bosses) - increased from 25 (+60%)
MAX_DEPTH_CAP = 5  # Maximum search depth (hard cap for timeout protection)

# FastScore weights (Stage 1 of two-stage expansion)
FASTSCORE_ZERO_COST_BONUS = 20  # Bonus for zero-cost cards
FASTSCORE_ATTACK_BONUS = 10  # Bonus for attacks when monsters alive
FASTSCORE_LOWHP_BLOCK_BONUS = 15  # Bonus for block when low HP
FASTSCORE_DAMAGE_MULTIPLIER = 2.0  # Points per damage point in FastScore
FASTSCORE_POWER_BONUS = 8  # Baseline bonus for power cards
FASTSCORE_POWER_EARLY_BONUS = 6  # Extra bonus for early-turn powers

# Progressive widening M values (Stage 2 of two-stage expansion)
M_VALUES = [20, 18, 15, 12, 10]  # Number of actions to full-simulate at each depth
                                  # Decreases with depth: 20→18→15→12→10 (increased from 12→10→7→5→4)

# =============================================================================
# CARD UPGRADE MAPPINGS
# =============================================================================

# Attack card upgrade damage bonuses (Ironclad)
# Maps card name to damage increase when upgraded (upgrades=1)
DAMAGE_UPGRADE_BONUS = {
    # +0 damage (upgrades don't increase base damage)
    'Pummel': 0,
    'Sword Boomerang': 0,
    'Perfected Strike': 0,
    'Heavy Blade': 0,  # Complex: depends on Strength
    'Uppercut': 0,
    'Rampage': 0,  # Has separate scaling mechanism

    # +1 damage
    'Pommel Strike': 1,
    'Reaper': 1,

    # +2 damage
    'Anger': 2,
    'Bash': 2,
    'Iron Wave': 2,
    'Clothesline': 2,
    'Twin Strike': 2,

    # +3 damage
    'Dropkick': 3,
    'Fiend Fire': 3,
    'Reckless Charge': 3,
    'Strike': 3,
    'Thunderclap': 3,
    'Headbutt': 3,
    'Cleave': 3,

    # +4 damage
    'Clash': 4,
    'Blood for Blood': 4,
    'Searing Blow': 4,

    # +5 damage
    'Wild Strike': 5,
    'Hemokinesis': 5,

    # +6 damage
    'Sever Soul': 6,

    # +7 damage
    'Immolate': 7,

    # +8 damage
    'Carnage': 8,

    # +10 damage
    'Bludgeon': 10,
}

# Block card upgrade block bonuses (All characters)
# Maps card name to block increase when upgraded (upgrades=1)
BLOCK_UPGRADE_BONUS = {
    # Ironclad
    'Defend': 3,        # 5 → 8
    'Iron Wave': 2,     # 5 → 7
    'Flame Barrier': 4, # 12 → 16
    'Impervious': 10,   # 30 → 40

    # Silent
    'Survivor': 3,      # 8 → 11
    'Backflip': 3,      # 5 → 8
    'Deflect': 3,       # 4 → 7
    'Dodge and Roll': 2, # 4 → 6
    'Blur': 3,          # 5 → 8
    'Leg Sweep': 3,     # 11 → 14

    # Defect
    'Charge Battery': 3,  # 7 → 10
    'Hologram': 2,        # 3 → 5
    'Leap': 3,            # 9 → 12
    'Steam Barrier': 2,   # 6 → 8
    'Boot Sequence': 3,   # 10 → 13
    'Equilibrium': 3,     # 13 → 16
    'Force Field': 4,     # 12 → 16
    'Glacier': 3,         # 7 → 10
    'Reinforced Body': 2, # 7 → 9
}

# Timeout protection
TIMEOUT_BUDGET = 0.15  # Seconds (150ms budget for beam search) - increased from 80ms


# =============================================================================
# COMBAT MODE CONFIGURATION
# =============================================================================

from enum import Enum


class CombatMode(Enum):
    """
    Combat mode determines the aggression level of the AI.

    Each mode has different weight profiles for scoring combat actions.
    """
    BALANCED = 0          # Standard balanced play (original weights)
    AGGRESSIVE = 1        # Elite/scaling fights (maximize damage)
    SEMI_AGGRESSIVE = 2   # Boss fights (damage-focused but balanced)


# Combat mode weight profiles
COMBAT_MODE_WEIGHTS = {
    CombatMode.BALANCED: {
        'DAMAGE_WEIGHT': 2.0,
        'BLOCK_WEIGHT': 1.5,
        'W_DEATHRISK': 8.0,
        'KILL_BONUS': 100,
        'ENERGY_EFFICIENCY_WEIGHT': 3.0,
    },
    CombatMode.AGGRESSIVE: {
        'DAMAGE_WEIGHT': 5.0,        # +150% damage priority
        'BLOCK_WEIGHT': 0.5,         # -67% block priority
        'W_DEATHRISK': 4.0,          # -50% survival penalty
        'KILL_BONUS': 200,           # +100% kill bonus
        'ENERGY_EFFICIENCY_WEIGHT': 5.0,  # +67% energy efficiency
    },
    CombatMode.SEMI_AGGRESSIVE: {
        'DAMAGE_WEIGHT': 3.5,        # +75% damage priority
        'BLOCK_WEIGHT': 1.0,         # -33% block priority
        'W_DEATHRISK': 6.0,          # -25% survival penalty
        'KILL_BONUS': 150,           # +50% kill bonus
        'ENERGY_EFFICIENCY_WEIGHT': 4.0,  # +33% energy efficiency
    },
}


def get_combat_mode_weights(mode: CombatMode) -> dict:
    """
    Get weight profile for a combat mode.

    Args:
        mode: The combat mode

    Returns:
        Dictionary of weight names to values
    """
    return COMBAT_MODE_WEIGHTS.get(mode, COMBAT_MODE_WEIGHTS[CombatMode.BALANCED]).copy()


def select_combat_mode(threat_category) -> CombatMode:
    """
    Select appropriate combat mode based on enemy threat category.

    Args:
        threat_category: ThreatCategory from EnemyThreatProfiler

    Returns:
        CombatMode to use for this fight
    """
    # Import here to avoid circular dependency
    from spirecomm.ai.decision.base import ThreatCategory

    if threat_category in [ThreatCategory.ELITE, ThreatCategory.SCALING]:
        return CombatMode.AGGRESSIVE
    elif threat_category == ThreatCategory.BOSS:
        return CombatMode.SEMI_AGGRESSIVE
    else:
        return CombatMode.BALANCED


def select_combat_mode_with_monster_data(context) -> CombatMode:
    """
    Enhanced combat mode selection using Wiki monster data for intelligent mode selection.

    This enhanced version analyzes monster composition and special mechanics to select
    the optimal combat mode (AGGRESSIVE/SEMI_AGGRESSIVE/BALANCED).

    Combat Mode Strategy:
    - AGGRESSIVE: Summoners, phase-change bosses, high scaling, time pressure
    - SEMI_AGGRESSIVE: Elites, hibernating monsters, high HP single targets
    - BALANCED: Normal monsters, low threat encounters

    Args:
        context: Decision context with game state and monsters

    Returns:
        CombatMode to use for this fight
    """
    if not context.monsters_alive:
        return CombatMode.BALANCED

    # Analyze monster composition
    has_summoner = False
    has_phase_change = False
    has_hibernating = False
    has_high_scaling = False
    has_time_pressure = False
    has_duo_boss = False
    has_death_split = False

    elite_count = 0
    boss_count = 0
    total_scaling_threat = 0

    for monster in context.monsters_alive:
        # Check for summoners
        if game_data_loader.is_monster_summoner(monster.name):
            has_summoner = True

        # Check for phase change
        if game_data_loader.does_monster_have_phase_change(monster.name):
            has_phase_change = True

        # Check for hibernation
        if game_data_loader.is_monster_hibernating(monster.name, context.turn):
            has_hibernating = True

        # Check for death split
        if game_data_loader.does_monster_have_death_split(monster.name):
            has_death_split = True

        # Check for duo boss
        if game_data_loader.is_monster_duo_boss(monster.name):
            has_duo_boss = True

        # Get threat profile
        threat_profile = game_data_loader.get_monster_threat_profile(monster.name)
        if threat_profile:
            # Accumulate scaling threat
            scaling_threat = threat_profile.get('scaling_threat', 0)
            if scaling_threat > 0:
                total_scaling_threat += scaling_threat
                has_high_scaling = total_scaling_threat > 8  # Threshold for high scaling

            # Check for time pressure mechanics
            if 'time_pressure' in threat_profile or 'echoing_doom' in threat_profile:
                has_time_pressure = True

        # Count elites and bosses
        monster_type = game_data_loader.get_monster_type(monster.name)
        if monster_type == 'elite':
            elite_count += 1
        elif monster_type == 'boss':
            boss_count += 1

    # === Combat Mode Decision Logic ===

    # Priority 1: Summoners and phase changes (AGGRESSIVE)
    # Summoners need to be killed quickly before they snowball
    # Phase-change bosses need burst during specific windows
    if has_summoner or (has_phase_change and boss_count > 0):
        return CombatMode.AGGRESSIVE

    # Priority 2: Time pressure mechanics (AGGRESSIVE)
    # Monsters like Time Eater with Echoing Doom require aggressive play
    if has_time_pressure:
        return CombatMode.AGGRESSIVE

    # Priority 3: High scaling threats (AGGRESSIVE)
    # Monsters that scale quickly need to be burst down
    if has_high_scaling:
        return CombatMode.AGGRESSIVE

    # Priority 4: Duo boss (SEMI_AGGRESSIVE)
    # Two bosses require sustained damage but balanced approach
    if has_duo_boss:
        return CombatMode.SEMI_AGGRESSIVE

    # Priority 5: Death split with AOE (SEMI_AGGRESSIVE)
    # Need to burst below threshold efficiently
    if has_death_split:
        return CombatMode.SEMI_AGGRESSIVE

    # Priority 6: Hibernating monsters (SEMI_AGGRESSIVE)
    # Can be aggressive once they wake up, but balanced while sleeping
    if has_hibernating:
        return CombatMode.SEMI_AGGRESSIVE

    # Priority 7: Elites (SEMI_AGGRESSIVE)
    if elite_count >= 1:
        return CombatMode.SEMI_AGGRESSIVE

    # Priority 8: Bosses (SEMI_AGGRESSIVE to AGGRESSIVE based on type)
    if boss_count >= 1:
        # Check if boss has phase change or time pressure
        if has_phase_change or has_time_pressure:
            return CombatMode.AGGRESSIVE
        return CombatMode.SEMI_AGGRESSIVE

    # Priority 9: High monster count (AGGRESSIVE for AOE efficiency)
    if len(context.monsters_alive) >= 3:
        # Multiple monsters benefit from aggressive AOE
        return CombatMode.AGGRESSIVE

    # Default: BALANCED for normal fights
    return CombatMode.BALANCED


# =============================================================================
# END CONFIGURATION
# =============================================================================


class SimulationState:
    """
    Enhanced simulation state with complete combat tracking.

    This is a lightweight version of game state that can be quickly copied
    and modified during simulation, with accurate tracking of combat modifiers.
    """

    def __init__(self, context: DecisionContext):
        """Initialize simulation state from decision context."""
        # Player state
        self.player_hp = context.game.current_hp
        self.player_max_hp = context.game.max_hp
        self.player_block = context.game.player.block if hasattr(context.game.player, 'block') else 0
        self.player_energy = context.energy_available
        self.player_strength = context.strength

        # Player debuffs (binary: >0 means debuffed)
        self.player_vulnerable = self._get_player_debuff_stacks(context, 'Vulnerable')
        self.player_weak = self._get_player_debuff_stacks(context, 'Weak')
        self.player_frail = self._get_player_debuff_stacks(context, 'Frail')
        # Rage power: block gained per attack played.
        self.rage_block_per_attack = self._get_player_power_amount(context, 'Rage')

        # Monster state (each monster tracked independently)
        self.monsters = []
        for i, monster in enumerate(context.monsters_alive):
            monster_state = {
                'name': monster.name,
                'hp': monster.current_hp,
                'max_hp': monster.max_hp,
                'block': monster.block if hasattr(monster, 'block') else 0,
                'intent': monster.intent if hasattr(monster, 'intent') else None,
                'is_gone': monster.is_gone,
                'half_dead': monster.half_dead,
                'vulnerable': context.vulnerable_stacks.get(i, 0),  # Vulnerable stacks (by index)
                'weak': context.weak_stacks.get(i, 0),  # Weak stacks (by index)
                'frail': context.frail_stacks.get(i, 0),  # Frail stacks (by index)
                'thorns': context.thorns_stacks.get(i, 0),  # Thorns/反伤 stacks (by index)
                'move_base_damage': monster.move_base_damage if hasattr(monster, 'move_base_damage') else 0,
                'move_adjusted_damage': monster.move_adjusted_damage if hasattr(monster, 'move_adjusted_damage') else 0,
                'strength': monster.strength if hasattr(monster, 'strength') else 0,
            }
            self.monsters.append(monster_state)

        # Track what we've played
        self.played_card_uuids = set()
        self.energy_spent = 0
        self.total_damage_dealt = 0
        self.monsters_killed = 0

        # Primary target for focused fire (monster index or None)
        # Set on first attack, maintained until target dies
        self.primary_target = None

        # Engine event tracking (for synergy evaluation)
        self.exhaust_events = 0  # Cards exhausted
        self.cards_drawn = 0  # Cards drawn
        self.skills_played = 0  # Skill cards played
        self.attacks_played = 0  # Attack cards played
        self.damage_instances = 0  # Individual damage instances
        self.energy_gained = 0  # Energy gained (e.g., Bloodletting)
        self.energy_saved = 0  # Energy saved (e.g., Corruption free skills)

    def _get_player_debuff_stacks(self, context: DecisionContext, power_name: str) -> int:
        """Get debuff stacks on the player from powers."""
        if not hasattr(context.game, 'player') or not hasattr(context.game.player, 'powers'):
            return 0

        for power in context.game.player.powers:
            if hasattr(power, 'name') and power.name == power_name:
                return hasattr(power, 'amount') and power.amount or 1
        return 0

    def _get_player_power_amount(self, context: DecisionContext, power_name: str) -> int:
        """Get power amount on the player from powers."""
        if not hasattr(context.game, 'player') or not hasattr(context.game.player, 'powers'):
            return 0

        for power in context.game.player.powers:
            if hasattr(power, 'name') and power.name == power_name:
                return hasattr(power, 'amount') and power.amount or 0
        return 0

    def clone(self) -> 'SimulationState':
        """Create a deep copy of this state."""
        new_state = SimulationState.__new__(SimulationState)
        new_state.player_hp = self.player_hp
        new_state.player_max_hp = self.player_max_hp
        new_state.player_block = self.player_block
        new_state.player_energy = self.player_energy
        new_state.player_strength = self.player_strength
        new_state.player_vulnerable = self.player_vulnerable
        new_state.player_weak = self.player_weak
        new_state.player_frail = self.player_frail
        new_state.rage_block_per_attack = self.rage_block_per_attack
        new_state.monsters = [m.copy() for m in self.monsters]
        new_state.played_card_uuids = self.played_card_uuids.copy()
        new_state.energy_spent = self.energy_spent
        new_state.total_damage_dealt = self.total_damage_dealt
        new_state.monsters_killed = self.monsters_killed
        new_state.primary_target = self.primary_target
        new_state.exhaust_events = self.exhaust_events
        new_state.cards_drawn = self.cards_drawn
        new_state.skills_played = self.skills_played
        new_state.attacks_played = self.attacks_played
        new_state.damage_instances = self.damage_instances
        new_state.energy_gained = self.energy_gained
        new_state.energy_saved = self.energy_saved
        return new_state

    def state_key(self, playable_cards):
        """
        Create a hashable key for state deduplication in transposition table.

        The key includes all game-relevant fields that affect the value of a state.
        Different action sequences that lead to identical states will have the same key.

        Args:
            playable_cards: List of cards currently playable (not yet played)

        Returns:
            Tuple containing (player_key, monster_key, hand_key)
        """
        # Player state (what matters for future decisions)
        player_key = (
            self.player_hp,
            self.player_block,
            self.player_energy,
            self.player_strength,
            self.player_vulnerable,
            self.player_weak,
            self.player_frail,
            self.rage_block_per_attack
        )

        # Monster states (sorted for consistent hashing)
        # Use tuple for immutability and sorting to ensure consistent ordering
        monster_key = tuple(sorted(
            (
                m['hp'],
                m['block'],
                m['vulnerable'],
                m['weak'],
                m['frail'],
                str(m['intent']) if m['intent'] else None,  # Convert intent to string
                m['is_gone'],
                m['name']  # Include name for elite/boss identification
            )
            for m in self.monsters
            if not m['is_gone']  # Only include alive monsters
        ))

        # Hand cards (multi-set - sorted list of card IDs)
        # This represents what cards are available to play
        hand_key = tuple(sorted(
            c.card_id for c in playable_cards
            if id(c) not in self.played_card_uuids  # Only cards not yet played
        ))

        return (player_key, monster_key, hand_key)


class FastCombatSimulator:
    """
    Fast forward combat simulator.

    Simulates card plays and combat outcomes to evaluate action sequences
    and find optimal plays.
    """

    def __init__(self, card_evaluator: SynergyCardEvaluator):
        """
        Initialize the simulator.

        Args:
            card_evaluator: Card evaluator for value calculations
        """
        self.card_evaluator = card_evaluator
        self.timing_context = None  # TimingContext for dynamic weights (set externally)

    def set_timing_context(self, timing_context):
        """
        Set timing context for dynamic weight adjustment.

        Args:
            timing_context: TimingContext with turn classification and weights
        """
        self.timing_context = timing_context

    def simulate_card_play(self, state: SimulationState, card: Card,
                          target: Optional[Monster] = None,
                          target_index: Optional[int] = None,
                          context: Optional[DecisionContext] = None) -> SimulationState:
        """
        Simulate playing a single card with accurate damage calculation.

        This simulation accounts for:
        - Actual card costs (cost_for_turn for Snecko Eye, etc.)
        - Strength power bonus
        - Vulnerable debuff (1.5x damage)
        - Monster block
        - AOE vs single-target
        - Power effects (Demon Form, Inflame, etc.)
        - X-damage and X-block cards (Body Slam, etc.)
        - Special monster abilities (death split, summoner, phase change, hibernation)

        Args:
            state: Current simulation state
            card: Card to play
            target: Target monster (if applicable)
            target_index: Index of target in monsters list
            context: Decision context (needed for X-card calculations)

        Returns:
            New simulation state after playing the card
        """
        new_state = state.clone()

        # Use actual cost (for Snecko Eye and other cost modifiers). X-cost
        # cards arrive as -1, but planning should spend all current energy.
        raw_cost = raw_card_cost(card)
        cost = effective_card_cost(card, new_state.player_energy)
        base_cost = raw_cost if raw_cost >= 0 else cost
        x_energy_spent = cost if is_x_cost_card(card) else None

        # Track energy saved (for Corruption, etc.)
        energy_saved = base_cost - cost
        if energy_saved > 0:
            new_state.energy_saved += energy_saved

        new_state.player_energy -= cost
        new_state.energy_spent += cost

        # Check special monster abilities before applying card effects
        for i, monster in enumerate(new_state.monsters):
            if not monster['is_gone']:
                self._handle_death_split(new_state, monster, i)
                self._handle_summoner(new_state, monster)
                self._handle_phase_change(new_state, monster)
                self._handle_hibernation(new_state, monster)

        # Apply card effects based on type
        card_type = card.type if hasattr(card, 'type') else None
        resolved_target_index = self._resolve_target_index(target, target_index, context)

        if card_type == CardType.ATTACK:
            new_state.attacks_played += 1
            self._apply_attack(
                new_state,
                card,
                target,
                resolved_target_index,
                context,
                x_energy_spent=x_energy_spent,
            )
            self._apply_rage_block(new_state)
        elif card_type == CardType.SKILL:
            new_state.skills_played += 1
            self._apply_skill(new_state, card, context, resolved_target_index)
        elif card_type == CardType.POWER:
            self._apply_power(new_state, card)

        self._apply_self_damage(new_state, card)

        return new_state

    def _resolve_target_index(
        self,
        target: Optional[Monster],
        target_index: Optional[int],
        context: Optional[DecisionContext],
    ) -> Optional[int]:
        """Resolve a target object back to its live-monster index."""
        if target_index is not None:
            return target_index
        if target is None or context is None:
            return None

        monsters = getattr(context, 'monsters_alive', []) or []
        for idx, monster in enumerate(monsters):
            if monster is target:
                return idx

        target_id = getattr(target, 'monster_id', None)
        target_name = getattr(target, 'name', None)
        target_hp = getattr(target, 'current_hp', None)
        for idx, monster in enumerate(monsters):
            if (
                getattr(monster, 'monster_id', None) == target_id
                and getattr(monster, 'name', None) == target_name
                and getattr(monster, 'current_hp', None) == target_hp
            ):
                return idx

        return None

    def _apply_attack(
        self,
        state: SimulationState,
        card: Card,
        target: Optional[Monster],
        target_index: Optional[int],
        context: DecisionContext = None,
        x_energy_spent: Optional[int] = None,
    ):
        """Apply attack card effects with proper damage calculation."""
        base_damage = getattr(card, 'damage', 0)
        if base_damage is None:
            base_damage = 0
        if base_damage == 0 or not hasattr(card, 'damage'):
            # Use game data for more accurate damage estimation
            card_name = card.card_id.replace('+', '').replace('+', '')  # Remove upgrade suffix
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                parsed_damage = game_data_loader._parse_card_damage(card_data)
                base_damage = parsed_damage if parsed_damage is not None else 0

                # Apply upgrade bonus if card is upgraded
                upgrades = getattr(card, 'upgrades', 0)
                if upgrades > 0 and base_damage:
                    # Check if we have a known upgrade bonus for this card
                    upgrade_bonus = DAMAGE_UPGRADE_BONUS.get(card_name)
                    if upgrade_bonus is not None:
                        # Use known bonus
                        base_damage += upgrade_bonus
                        logger.debug(f"[DAMAGE_UPGRADE] {card.card_id} (upgrades={upgrades}): {base_damage} damage (+{upgrade_bonus})")
                    else:
                        # Unknown card - apply generic +3 bonus (most common pattern)
                        base_damage += 3
                        logger.debug(f"[DAMAGE_UPGRADE_GENERIC] {card.card_id} (upgrades={upgrades}): {base_damage} damage (+3 generic)")

            # Check for X-damage cards and calculate dynamically
            if base_damage == 0 and context is not None:
                if x_energy_spent is not None:
                    setattr(state, '_current_x_energy_spent', x_energy_spent)
                try:
                    base_damage = self._calculate_x_damage(card, state, context)
                finally:
                    if x_energy_spent is not None and hasattr(state, '_current_x_energy_spent'):
                        delattr(state, '_current_x_energy_spent')
                if base_damage is None:
                    base_damage = 0

            if base_damage == 0:
                base_damage = 6  # Fallback estimate for truly unknown cards

        # Handle AOE attacks
        card_name = card.card_id.replace('+', '')
        card_data = game_data_loader.get_card_data(card_name)
        is_aoe = False
        if card_data:
            is_aoe = game_data_loader._is_card_aoe(card_data)
        # Also check known AOE cards by name
        if card.card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']:
            is_aoe = True
        hit_count = self._get_attack_hit_count(card, state, context)
        starting_total_damage = state.total_damage_dealt

        if is_aoe:
            # AOE - apply to all monsters
            for monster in state.monsters:
                if monster['is_gone']:
                    continue
                for _ in range(hit_count):
                    if monster['is_gone']:
                        break
                    damage = self._calculate_attack_damage(card, base_damage, state, context)
                    damage = self._apply_vulnerable_damage(damage, monster)
                    damage = self._apply_weak_damage(damage, monster.get('weak', 0))
                    self._deal_damage_to_monster(state, monster, damage)
                    state.damage_instances += 1  # Track each damage instance
        elif self._is_random_target_attack(card) and target_index is None:
            for hit_index in range(hit_count):
                alive_monsters = [monster for monster in state.monsters if not monster['is_gone']]
                if not alive_monsters:
                    break
                monster = alive_monsters[hit_index % len(alive_monsters)]
                damage = self._calculate_attack_damage(card, base_damage, state, context)
                damage = self._apply_vulnerable_damage(damage, monster)
                damage = self._apply_weak_damage(damage, monster.get('weak', 0))
                self._deal_damage_to_monster(state, monster, damage)
                state.damage_instances += 1
        else:
            # Single-target attack
            if target_index is not None and 0 <= target_index < len(state.monsters):
                monster = state.monsters[target_index]
                if not monster['is_gone']:
                    for _ in range(hit_count):
                        if monster['is_gone']:
                            break
                        damage = self._calculate_attack_damage(card, base_damage, state, context)
                        damage = self._apply_vulnerable_damage(damage, monster)
                        damage = self._apply_weak_damage(damage, monster.get('weak', 0))
                        self._deal_damage_to_monster(state, monster, damage)
                        state.damage_instances += 1  # Track damage instance

                    # Check for card effects using game data
                    if card_data:
                        description = self._get_card_effect_text(card_name, card_data)
                        upgraded = getattr(card, 'upgrades', 0) > 0
                        if 'vulnerable' in description:
                            vulnerable_stacks = self._extract_debuff_stacks(description, 'vulnerable', upgraded)
                            if vulnerable_stacks:
                                monster['vulnerable'] += vulnerable_stacks
                        if 'weak' in description:
                            weak_stacks = self._extract_debuff_stacks(description, 'weak', upgraded)
                            if weak_stacks:
                                monster['weak'] += weak_stacks

        self._apply_attack_healing(state, card, starting_total_damage)
        self._apply_attack_resource_effects(state, card, target_index)

    def _get_attack_hit_count(
        self,
        card: Card,
        state: SimulationState,
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Return known static hit counts for repeated-hit Ironclad attacks."""
        card_name = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        upgrades = getattr(card, 'upgrades', 0)

        if card_name == 'Twin Strike':
            return 2
        if card_name == 'Sword Boomerang':
            return 4 if upgrades > 0 else 3
        if card_name == 'Pummel':
            return 5 if upgrades > 0 else 4
        if card_name == 'Fiend Fire' and context is not None:
            return max(
                0,
                sum(
                    1
                    for hand_card in getattr(context, 'playable_cards', [])
                    if hand_card is not card and id(hand_card) not in state.played_card_uuids
                ),
            )

        return 1

    def _is_random_target_attack(self, card: Card) -> bool:
        card_name = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        return card_name in {'Sword Boomerang'}

    def _apply_attack_healing(self, state: SimulationState, card: Card, starting_total_damage: int):
        card_name = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        if card_name != 'Reaper':
            return

        unblocked_damage = max(0, state.total_damage_dealt - starting_total_damage)
        if unblocked_damage <= 0:
            return
        state.player_hp = min(state.player_max_hp, state.player_hp + unblocked_damage)

    def _apply_attack_resource_effects(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int],
    ):
        card_name = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        if card_name != 'Dropkick':
            return
        if target_index is None or not (0 <= target_index < len(state.monsters)):
            return
        if state.monsters[target_index].get('vulnerable', 0) <= 0:
            return

        state.player_energy += 1
        state.energy_gained += 1
        state.cards_drawn += 1

    def _calculate_attack_damage(
        self,
        card: Card,
        base_damage: int,
        state: SimulationState,
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Apply Strength, including cards with non-standard Strength scaling."""
        card_name = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''

        if card_name == 'Heavy Blade':
            multiplier = 5 if getattr(card, 'upgrades', 0) > 0 else 3
            return base_damage + state.player_strength * multiplier

        if card_name == 'Perfected Strike':
            per_strike_bonus = 3 if getattr(card, 'upgrades', 0) > 0 else 2
            return base_damage + self._count_strike_cards(context) * per_strike_bonus + state.player_strength

        return base_damage + state.player_strength

    def _count_strike_cards(self, context: Optional[DecisionContext]) -> int:
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

    def _apply_vulnerable_damage(self, damage: int, monster: dict) -> int:
        """Apply vulnerable multiplier (1.5x). Binary: any vulnerable stacks = 1.5x damage."""
        if monster.get('vulnerable', 0) > 0:
            return int(damage * 1.5)
        return damage

    def _apply_player_vulnerable_damage(self, damage: int, player_vulnerable: int) -> int:
        """Apply vulnerable multiplier (1.5x) to damage taken by the player."""
        if player_vulnerable > 0:
            return int(damage * 1.5)
        return damage

    def _apply_weak_damage(self, damage: int, player_weak: int) -> int:
        """Apply weak multiplier (0.75x). Binary: any weak stacks = 0.75x damage."""
        if player_weak > 0:
            return int(damage * 0.75)
        return damage

    def _get_card_effect_text(self, card_name: str, card_data: Dict[str, Any]) -> str:
        """Prefer wiki text for effect values because items.json stores base text only."""
        base_card_name = card_name.lower().rstrip('+')
        try:
            if getattr(game_data_loader, '_wiki_data', None) is None:
                game_data_loader._load_wiki_data()
            wiki_entry = getattr(game_data_loader, '_wiki_data', {}).get(base_card_name)
            if wiki_entry and wiki_entry.get('text'):
                return wiki_entry['text'].lower()
        except Exception:
            pass

        return card_data.get('description', '').lower()

    def _extract_debuff_stacks(self, description: str, keyword: str, upgraded: bool) -> Optional[int]:
        """Extract debuff stacks from card description for a keyword."""
        # Prefer [base|upgraded] notation when available.
        bracket_match = re.search(rf'\[(\d+)\|(\d+)\]\s*#?{keyword}', description)
        if bracket_match:
            return int(bracket_match.group(2 if upgraded else 1))

        patterns = [
            rf'{keyword}\s*(\d+)',
            rf'(\d+)\s*#?{keyword}',
            rf'apply\s*(\d+)\s*#?{keyword}',
        ]
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return int(match.group(1))

        return None

    def _apply_frail_block(self, block: int, player_frail: int) -> int:
        """Apply frail multiplier (0.75x). Binary: any frail stacks = 0.75x block gained."""
        if player_frail > 0:
            return int(block * 0.75)
        return block

    def _apply_debuff_risk_multiplier(self, damage: int, player_weak: int, player_frail: int) -> int:
        """Adjust expected damage based on player Weak/Frail stacks."""
        risk_multiplier = 1.0
        if player_weak > 0:
            risk_multiplier += min(LOOKAHEAD_WEAK_RISK_PER_STACK * player_weak, LOOKAHEAD_DEBUFF_RISK_CAP)
        if player_frail > 0:
            risk_multiplier += min(LOOKAHEAD_FRAIL_RISK_PER_STACK * player_frail, LOOKAHEAD_DEBUFF_RISK_CAP)
        return int(damage * risk_multiplier)

    def _extract_move_debuffs(self, move: Dict[str, Any]) -> Dict[str, int]:
        """Extract debuff stacks applied to the player from a monster move."""
        def _get_stack(key: str) -> int:
            value = move.get(key, 0)
            if isinstance(value, bool):
                return 1 if value else 0
            if isinstance(value, (int, float)):
                return int(value)
            return 0

        return {
            'weak': _get_stack('weak') or _get_stack('weak_applied') or _get_stack('weak_amount'),
            'frail': _get_stack('frail') or _get_stack('frail_applied') or _get_stack('frail_amount'),
            'vulnerable': _get_stack('vulnerable') or _get_stack('vulnerable_applied') or _get_stack('vulnerable_amount'),
        }

    def _calculate_x_damage(
        self,
        card: Card,
        state: SimulationState,
        context: DecisionContext,
        x_energy_spent: Optional[int] = None,
    ) -> int:
        """
        Calculate dynamic damage for X-damage cards.

        X-damage cards have variable damage based on game state:
        - Body Slam: damage = player_block
        - Whirlwind: damage = max_energy (applies AOE multiplier automatically)

        Args:
            card: The card being played
            state: Current simulation state
            context: Decision context

        Returns:
            Calculated damage value, or 0 if not an X-damage card

        Examples:
            >>> # Body Slam with 20 block
            >>> _calculate_x_damage(Card('Body Slam'), state, context)
            20
        """
        # Normalize card name by removing '+' suffix (handles upgraded cards)
        card_name = card.card_id.replace('+', '')

        if card_name == 'Body Slam':
            # Body Slam deals damage equal to your current block
            return state.player_block

        elif card_name == 'Whirlwind':
            # Whirlwind: 5/8 damage to all enemies X times, where X is
            # current energy. _apply_attack adds Strength once after this
            # helper, so include the remaining Strength hits here.
            energy = x_energy_spent
            if energy is None:
                energy = getattr(state, '_current_x_energy_spent', None)
            if energy is None:
                fallback_energy = getattr(state, 'player_energy', 0)
                energy = effective_card_cost(card, fallback_energy)
            energy = max(0, energy)
            per_hit = 8 if getattr(card, 'upgrades', 0) > 0 else 5
            strength = getattr(state, 'player_strength', 0)
            return per_hit * energy + max(0, energy - 1) * strength

        # Fallback: not an X-damage card
        return 0

    def _calculate_x_block(self, card: Card, state: SimulationState, context: DecisionContext) -> int:
        """
        Calculate dynamic block gain for X-block cards.

        X-block cards have variable block based on game state.

        Args:
            card: The card being played
            state: Current simulation state
            context: Decision context

        Returns:
            Calculated block value, or 0 if not an X-block card

        """
        # Fallback: not an X-block card
        return 0

    def _deal_damage_to_monster(self, state: SimulationState, monster: dict, damage: int):
        """Deal damage to monster, accounting for block and thorns."""
        # Damage block first
        block_damage = min(damage, monster['block'])
        monster['block'] -= block_damage

        # Remaining damage to HP
        hp_damage = damage - block_damage
        monster['hp'] -= hp_damage
        state.total_damage_dealt += hp_damage

        # Check if killed
        if monster['hp'] <= 0:
            monster['is_gone'] = True
            state.monsters_killed += 1
        else:
            # Apply thorns/反伤: take damage when attacking enemies with thorns
            thorns = monster.get('thorns', 0)
            if thorns > 0:
                # Calculate thorns damage (typically 1 damage per thorns stack)
                # But we'll use a more conservative approach based on damage dealt
                # because thorns damage is usually proportional to attack damage
                thorns_damage = min(int(hp_damage * 0.3), thorns)  # Conservative estimate
                if thorns_damage > 0:
                    state.player_hp -= thorns_damage
                    state.player_hp = max(0, state.player_hp)  # Ensure HP doesn't go negative

    def _apply_skill(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext] = None,
        target_index: Optional[int] = None,
    ):
        """Apply skill card effects."""
        # Block skills - apply frail multiplier if player has frail
        if hasattr(card, 'block') and card.block is not None:
            block_gain = card.block
            logger.debug(f"[BLOCK_SKILL] Using card.block attribute: {block_gain} for {card.card_id}")
            block_gain = self._apply_frail_block(block_gain, state.player_frail)
            state.player_block += block_gain
        else:
            # Check for X-block cards first
            if context is not None:
                block_gain = self._calculate_x_block(card, state, context)
                if block_gain > 0:
                    logger.debug(f"[BLOCK_X] X-block calculated: {block_gain} for {card.card_id}")
                    # Apply frail multiplier
                    block_gain = self._apply_frail_block(block_gain, state.player_frail)
                    state.player_block += block_gain
                else:
                    # Not an X-block card - try to get block from game data
                    # (needed because Card objects don't have block attribute set)
                    card_name = (getattr(card, 'name', None) or card.card_id).replace('+', '')
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        base_block = game_data_loader._parse_card_block(card_data)
                        if base_block and base_block > 0:
                            # Apply upgrade bonus if card is upgraded
                            upgrades = getattr(card, 'upgrades', 0)
                            if upgrades > 0:
                                # Check if we have a known upgrade bonus for this card
                                upgrade_bonus = BLOCK_UPGRADE_BONUS.get(card_name)
                                if upgrade_bonus is not None:
                                    # Use known bonus
                                    base_block += upgrade_bonus
                                    logger.debug(f"[BLOCK_UPGRADE] {card.card_id} (upgrades={upgrades}): {base_block} block (+{upgrade_bonus})")
                                else:
                                    # Unknown card - apply generic +3 bonus
                                    base_block += 3
                                    logger.debug(f"[BLOCK_UPGRADE_GENERIC] {card.card_id} (upgrades={upgrades}): {base_block} block (+3 generic)")
                            else:
                                logger.debug(f"[BLOCK_BASE] {card.card_id} (upgrades={upgrades}): {base_block} block")

                            block_gain = self._apply_frail_block(base_block, state.player_frail)
                            state.player_block += block_gain
                        else:
                            logger.debug(f"[BLOCK_NONE] No block found for {card.card_id}")
                    else:
                        logger.debug(f"[BLOCK_NODATA] No card data found for {card_name}")
        if card.card_id == 'Rage':
            rage_gain = 5 if getattr(card, 'upgrades', 0) > 0 else 3
            state.rage_block_per_attack += rage_gain

        self._apply_strength_skill(state, card, target_index)
        self._apply_energy_gain_skill(state, card)

        # Apply enemy debuffs from skill cards (e.g., Shockwave).
        try:
            card_name = (getattr(card, 'name', None) or card.card_id).replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = card_data.get('description', '').lower()
                has_debuff = 'vulnerable' in description or 'weak' in description
                if has_debuff:
                    upgrades = getattr(card, 'upgrades', 0) > 0
                    is_aoe = game_data_loader._is_card_aoe(card_data) or 'all enemies' in description
                    if is_aoe:
                        vuln_stacks = self._extract_debuff_stacks(description, 'vulnerable', upgrades)
                        weak_stacks = self._extract_debuff_stacks(description, 'weak', upgrades)
                        if vuln_stacks is None and card_name == 'Shockwave':
                            vuln_stacks = 5 if upgrades else 3
                        if weak_stacks is None and card_name == 'Shockwave':
                            weak_stacks = 5 if upgrades else 3

                        if vuln_stacks or weak_stacks:
                            for monster in state.monsters:
                                if monster['is_gone']:
                                    continue
                                if vuln_stacks:
                                    monster['vulnerable'] += vuln_stacks
                                if weak_stacks:
                                    monster['weak'] += weak_stacks
        except Exception:
            pass

        # Track exhaust events (for Feel No Pain, etc.)
        try:
            card_name = (getattr(card, 'name', None) or card.card_id).replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = card_data.get('description', '').lower()
                # Check if card exhausts
                if 'exhaust' in description or card.card_id in ['Pommel Strike', 'Offering', 'Reaper']:
                    state.exhaust_events += 1
                # Track draw events
                if 'draw' in description:
                    draw_match = re.search(r'draw (\d+)', description)
                    if draw_match:
                        state.cards_drawn += int(draw_match.group(1))
                # Track energy gain on skills (Offering, Bloodletting, etc.)
                if 'gain' in description and 'energy' in description:
                    energy_match = re.search(r'gain (\d+) energy', description)
                    if energy_match:
                        state.energy_gained += int(energy_match.group(1))
        except:
            pass

    def _apply_power(self, state: SimulationState, card: Card):
        """Apply power card effects."""
        card_id = card.card_id.replace('+', '')

        # Demon Form starts gaining Strength on future turns, not immediately.
        if card_id == 'Demon Form':
            pass

        # Inflame - adds strength
        elif card_id == 'Inflame':
            state.player_strength += 3 if card.upgrades > 0 else 2

        # Corruption - skills cost 0 (track for synergy evaluation)
        elif card_id == 'Corruption':
            # This is tracked implicitly via energy_saved when skills are played
            pass

        # Feel No Pain - gain block when cards exhaust
        elif card_id == 'Feel No Pain':
            # Track as exhaust synergy
            pass

        # Draw power
        elif card_id == 'Draw':
            state.cards_drawn += 1 if card.upgrades == 0 else 2

        # Energy gain (Bloodletting, etc.)
        elif 'energy' in card_id.lower() or card_id in ['Demon Form', 'Combust']:
            # Track energy gained
            try:
                card_name = card.card_id.replace('+', '')
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    description = card_data.get('description', '').lower()
                    energy_match = re.search(r'gain (\d+) energy', description)
                    if energy_match:
                        state.energy_gained += int(energy_match.group(1))
            except:
                pass

        # Other powers can be added as needed

    def _apply_strength_skill(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int] = None,
    ):
        """Apply immediate Strength-changing Ironclad skills."""
        card_id = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        upgrades = getattr(card, 'upgrades', 0)

        if card_id == 'Flex':
            state.player_strength += 4 if upgrades > 0 else 2
        elif card_id == 'Limit Break':
            state.player_strength *= 2
        elif card_id == 'Spot Weakness' and self._spot_weakness_condition_met(state, target_index):
            state.player_strength += 4 if upgrades > 0 else 3

    def _spot_weakness_condition_met(
        self,
        state: SimulationState,
        target_index: Optional[int],
    ) -> bool:
        """Return whether Spot Weakness has a valid attacking target."""
        if target_index is not None and 0 <= target_index < len(state.monsters):
            monster = state.monsters[target_index]
            return not monster['is_gone'] and self._monster_intends_attack(monster)

        return any(
            not monster['is_gone'] and self._monster_intends_attack(monster)
            for monster in state.monsters
        )

    def _monster_intends_attack(self, monster: dict) -> bool:
        intent = monster.get('intent')
        if intent is None:
            return False
        intent_name = getattr(intent, 'name', str(intent))
        return 'ATTACK' in intent_name.upper()

    def _apply_energy_gain_skill(self, state: SimulationState, card: Card):
        card_id = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        upgrades = getattr(card, 'upgrades', 0)
        energy_gain = 0

        if card_id == 'Bloodletting':
            energy_gain = 3 if upgrades > 0 else 2
        elif card_id in {'Offering', 'Seeing Red'}:
            energy_gain = 2

        if energy_gain <= 0:
            return

        state.player_energy += energy_gain
        state.energy_gained += energy_gain

    def _apply_rage_block(self, state: SimulationState):
        """Apply Rage block trigger after playing an attack."""
        if state.rage_block_per_attack <= 0:
            return
        block_gain = self._apply_frail_block(state.rage_block_per_attack, state.player_frail)
        state.player_block += block_gain

    def _apply_self_damage(self, state: SimulationState, card: Card):
        """Apply HP costs for cards that damage the player to fuel effects."""
        try:
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if not card_data:
                return

            description = card_data.get('description', '') or ''
            match = re.search(r'lose (\d+) hp', description.lower())
            if not match:
                return

            hp_loss = int(match.group(1))
            if hp_loss <= 0:
                return

            state.player_hp = max(0, state.player_hp - hp_loss)
        except Exception:
            pass

    def _estimate_incoming_damage(self, monsters_state: list) -> int:
        """
        Estimate expected incoming damage from monsters next turn.

        Args:
            monsters_state: List of monster state dictionaries

        Returns:
            Expected total damage
        """
        total_damage = 0
        debug_entries = []
        intent_present = False
        attack_intent_present = False

        for monster in monsters_state:
            if monster['is_gone']:
                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    "skip=gone"
                )
                continue

            intent = monster.get('intent')
            if intent is None:
                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    "skip=intent=None"
                )
                continue

            # Import Intent enum if available
            try:
                from spirecomm.spire.character import Intent
                # Check if intent is an Intent enum or string
                if isinstance(intent, str):
                    intent_str = intent
                else:
                    intent_str = str(intent).split('.')[-1] if hasattr(intent, 'name') else str(intent)
            except:
                intent_str = str(intent)

            # Estimate damage based on intent
            intent_present = True
            if 'ATTACK' in intent_str.upper() or 'ATTACK_BUFF' in intent_str.upper() or 'ATTACK_DEBUFF' in intent_str.upper() or 'ATTACK_DEFEND' in intent_str.upper():
                attack_intent_present = True
                # Use actual monster damage data from game state
                damage = monster.get('move_adjusted_damage', 0)
                hits = monster.get('move_hits', 1) or 1
                damage_source = "adjusted"

                # Fallback to base_damage if adjusted_damage not available
                if damage == 0:
                    damage = monster.get('move_base_damage', 0)
                    if damage > 0:
                        damage_source = "base"
                        logger.debug(f"[DAMAGE_FALLBACK] Monster '{monster.get('name', 'Unknown')}' using base_damage={damage}")

                # If still no damage data, use conservative estimate based on monster
                if damage == 0:
                    # Conservative estimate by monster name/type (can be improved)
                    monster_name = monster.get('name', '')
                    if 'elite' in monster_name.lower() or 'boss' in monster_name.lower():
                        damage = 15  # Elite/boss hit harder
                        damage_source = "fallback_elite"
                        logger.warning(f"[DAMAGE_FALLBACK] Monster '{monster_name}' using ELITE fallback damage={damage} (no damage data available)")
                    else:
                        damage = 8  # Normal monster
                        damage_source = "fallback_normal"
                        logger.warning(f"[DAMAGE_FALLBACK] Monster '{monster_name}' using NORMAL fallback damage={damage} (no damage data available)")

                # Adjust for monster strength
                strength = monster.get('strength', 0)
                if strength > 0:
                    logger.debug(f"[DAMAGE_FALLBACK] Monster '{monster.get('name', 'Unknown')}' has Strength {strength}, damage: {damage} → {damage + strength}")
                    damage += strength

                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    f"intent={intent_str} damage={damage} hits={hits} source={damage_source}"
                )
                total_damage += damage
            else:
                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    f"skip=intent={intent_str}"
                )

        if total_damage > 0:
            logger.debug(f"[INCOMING_DAMAGE] Estimated total incoming damage: {total_damage}")
        elif debug_entries and (attack_intent_present or intent_present):
            logger.info("[INCOMING_DAMAGE_ZERO] " + " | ".join(debug_entries))

        return total_damage

    def _get_enemy_lookahead_depth(self, state: SimulationState, context: DecisionContext, max_depth: int = 2) -> int:
        """Gate lookahead depth based on combat complexity and data availability."""
        try:
            monsters_alive = sum(1 for monster in state.monsters if not monster['is_gone'])
            playable_cards = len(getattr(context, 'playable_cards', []))

            if monsters_alive <= 1 and playable_cards <= 3:
                return 1

            return max_depth
        except Exception:
            return max_depth

    def simulate_enemy_lookahead(self, state: SimulationState, context: DecisionContext, look_ahead: int = 2) -> int:
        """
        Simulate enemy-only lookahead for the next N turns, applying debuffs to the player.

        Args:
            state: Current simulation state
            context: Decision context for accessing game data
            look_ahead: Number of turns to predict (default: 2)

        Returns:
            Total predicted damage over next N turns (discounted for uncertainty)
        """
        try:
            logger.info(
                "[LOOKAHEAD_ENTRY] turns=%s monsters=%s hp=%s/%s",
                look_ahead,
                len([m for m in state.monsters if not m['is_gone']]),
                state.player_hp,
                state.player_max_hp
            )
            total_future_damage = 0
            current_turn = getattr(context, 'turn', 1)

            predicted_by_monster: Dict[int, List[Dict[str, Any]]] = {}
            any_predictions = False

            for idx, monster in enumerate(state.monsters):
                if monster['is_gone']:
                    continue

                monster_name = monster.get('name', '')
                if not monster_name:
                    continue

                max_hp = monster.get('max_hp', monster['hp'])
                hp_percent = monster['hp'] / max_hp if max_hp > 0 else 1.0

                predicted_moves = game_data_loader.predict_monster_moves(
                    monster_name, current_turn, hp_percent
                )
                predicted_by_monster[idx] = predicted_moves
                if predicted_moves:
                    any_predictions = True

            if not any_predictions:
                look_ahead = 1

            player_vulnerable = state.player_vulnerable
            player_weak = state.player_weak
            player_frail = state.player_frail

            for step in range(look_ahead):
                turn_damage = 0
                pending_debuffs = {'weak': 0, 'frail': 0, 'vulnerable': 0}

                for idx, monster in enumerate(state.monsters):
                    if monster['is_gone']:
                        continue

                    predicted_moves = predicted_by_monster.get(idx, [])
                    move = None
                    if predicted_moves and step < len(predicted_moves):
                        move = predicted_moves[step].get('move', None)

                    if move:
                        move_intent = move.get('intent', '').upper()
                        move_damage = move.get('damage', 0)
                        move_hits = move.get('hits', 1)

                        if 'ATTACK' in move_intent and move_damage:
                            damage = move_damage * move_hits
                            current_strength = monster.get('strength', 0)
                            if current_strength > 0:
                                damage += current_strength * move_hits
                            damage = self._apply_player_vulnerable_damage(damage, player_vulnerable)
                            damage = self._apply_debuff_risk_multiplier(damage, player_weak, player_frail)
                            discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                            turn_damage += int(damage * discount)

                        move_debuffs = self._extract_move_debuffs(move)
                        pending_debuffs['weak'] += move_debuffs['weak']
                        pending_debuffs['frail'] += move_debuffs['frail']
                        pending_debuffs['vulnerable'] += move_debuffs['vulnerable']
                    else:
                        fallback_damage = monster.get('move_adjusted_damage', 0) or monster.get('move_base_damage', 0)
                        if fallback_damage > 0:
                            move_hits = monster.get('move_hits', 1)
                            damage = fallback_damage * move_hits
                            current_strength = monster.get('strength', 0)
                            if current_strength > 0:
                                damage += current_strength * move_hits
                            damage = self._apply_player_vulnerable_damage(damage, player_vulnerable)
                            damage = self._apply_debuff_risk_multiplier(damage, player_weak, player_frail)
                            discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                            turn_damage += int(damage * discount)

                total_future_damage += turn_damage

                player_vulnerable = max(0, player_vulnerable + pending_debuffs['vulnerable'] - 1)
                player_weak = max(0, player_weak + pending_debuffs['weak'] - 1)
                player_frail = max(0, player_frail + pending_debuffs['frail'] - 1)

                logger.debug(
                    f"[LOOKAHEAD_TURN] step={step + 1} damage={turn_damage} "
                    f"debuffs=V{player_vulnerable}/W{player_weak}/F{player_frail}"
                )

            if total_future_damage > 0:
                logger.info(f"[LOOKAHEAD] Predicted damage over next {look_ahead} turns: {total_future_damage}")

            return total_future_damage

        except Exception as e:
            logger.warning(f"[LOOKAHEAD] Failed to simulate enemy lookahead: {e}")
            return 0

    def calculate_future_monster_damage(self, state: SimulationState, context: DecisionContext, look_ahead: int = 2) -> int:
        """Compatibility wrapper for future damage prediction."""
        return self.simulate_enemy_lookahead(state, context, look_ahead)

    def _handle_death_split(self, state: SimulationState, monster: dict, monster_index: int):
        """
        Handle monster death split mechanics (e.g., Slime Boss splitting at low HP).

        Args:
            state: Current simulation state
            monster: Monster state dictionary
            monster_index: Index of monster in state.monsters list
        """
        try:
            from spirecomm.data.loader import game_data_loader

            monster_name = monster.get('name', '')
            if not monster_name:
                return

            # Check if monster has death split mechanic
            if not game_data_loader.does_monster_have_death_split(monster_name):
                return

            # Get death split threshold from Wiki data
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
            if not monster_data:
                return

            special_mechanics = monster_data.get('special_mechanics', {})
            split_threshold = special_mechanics.get('split_threshold_percent', 50)
            split_count = special_mechanics.get('split_count', 2)

            # Check if HP is below threshold
            max_hp = monster.get('max_hp', monster['hp'])
            hp_percent = (monster['hp'] / max_hp * 100) if max_hp > 0 else 0

            if hp_percent <= split_threshold and not monster.get('has_split', False):
                logger.info(f"[DEATH_SPLIT] {monster_name} at {hp_percent:.1f}% HP (threshold: {split_threshold}%) - splitting into {split_count} monsters")

                # Mark monster as having split (avoid re-splitting)
                monster['has_split'] = True

                # Create split monsters (simplified: add to monster list)
                # In a full implementation, you would add new monster entries
                # For now, just mark the original to handle it differently
                monster['is_split_form'] = True
                monster['split_count'] = split_count

        except Exception as e:
            logger.warning(f"[DEATH_SPLIT] Failed to handle death split for {monster.get('name', 'Unknown')}: {e}")

    def _handle_summoner(self, state: SimulationState, monster: dict):
        """
        Handle summoner mechanics (e.g., Reptomancer spawning Daggers).

        Args:
            state: Current simulation state
            monster: Monster state dictionary
        """
        try:
            from spirecomm.data.loader import game_data_loader

            monster_name = monster.get('name', '')
            if not monster_name:
                return

            # Check if monster is a summoner
            if not game_data_loader.is_monster_summoner(monster_name):
                return

            # Get summoning data from Wiki
            minions = game_data_loader.get_monster_minions(monster_name)
            if not minions:
                return

            # Track that this monster can summon
            monster['is_summoner'] = True
            monster['minions'] = minions

            logger.debug(f"[SUMMONER] {monster_name} can summon: {', '.join(minions)}")

        except Exception as e:
            logger.warning(f"[SUMMONER] Failed to handle summoner for {monster.get('name', 'Unknown')}: {e}")

    def _handle_phase_change(self, state: SimulationState, monster: dict):
        """
        Handle phase change mechanics (e.g., Hexaghost changing behavior at HP thresholds).

        Args:
            state: Current simulation state
            monster: Monster state dictionary
        """
        try:
            from spirecomm.data.loader import game_data_loader

            monster_name = monster.get('name', '')
            if not monster_name:
                return

            # Check if monster has phase change mechanic
            if not game_data_loader.does_monster_have_phase_change(monster_name):
                return

            # Get phase change data from Wiki
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
            if not monster_data:
                return

            special_mechanics = monster_data.get('special_mechanics', {})
            phases = special_mechanics.get('phases', [])

            # Calculate current HP percentage
            max_hp = monster.get('max_hp', monster['hp'])
            hp_percent = (monster['hp'] / max_hp * 100) if max_hp > 0 else 100

            # Determine current phase
            current_phase = None
            for phase in sorted(phases, key=lambda p: p.get('threshold_percent', 0)):
                threshold = phase.get('threshold_percent', 0)
                if hp_percent <= threshold:
                    current_phase = phase
                    break

            if current_phase:
                phase_name = current_phase.get('name', 'Unknown')
                logger.info(f"[PHASE_CHANGE] {monster_name} at {hp_percent:.1f}% HP - entered {phase_name} phase")
                monster['current_phase'] = phase_name
                monster['phase_burst_window'] = current_phase.get('burst_window', False)

        except Exception as e:
            logger.warning(f"[PHASE_CHANGE] Failed to handle phase change for {monster.get('name', 'Unknown')}: {e}")

    def _handle_hibernation(self, state: SimulationState, monster: dict):
        """
        Handle hibernation mechanics (e.g., Lagavulin sleeping vs awakened states).

        Args:
            state: Current simulation state
            monster: Monster state dictionary
        """
        try:
            from spirecomm.data.loader import game_data_loader

            monster_name = monster.get('name', '')
            if not monster_name:
                return

            # Only process if monster actually has hibernation mechanics
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
            if not monster_data:
                return

            special_mechanics = monster_data.get('special_mechanics', {})
            if special_mechanics.get('type') != 'hibernation':
                return  # Not a hibernating monster

            # Check if monster is hibernating
            current_turn = getattr(state, 'turn', 1)
            is_hibernating = game_data_loader.is_monster_hibernating(monster_name, current_turn)

            if is_hibernating:
                monster['is_hibernating'] = True
                logger.debug(f"[HIBERNATION] {monster_name} is hibernating (reduced threat)")
            else:
                monster['is_awakened'] = True
                logger.debug(f"[HIBERNATION] {monster_name} is awakened (full threat)")

        except Exception as e:
            logger.warning(f"[HIBERNATION] Failed to handle hibernation for {monster.get('name', 'Unknown')}: {e}")

    def _calculate_timing_bonus(self, final_state: SimulationState) -> float:
        """
        Calculate timing-specific bonuses based on turn classification.

        Adds bonuses for:
        - Attacking on safe turns (monster buffing)
        - Blocking properly on threat spike turns
        - Building block before big attacks

        Args:
            final_state: Final simulation state

        Returns:
            Timing bonus score (positive = good)
        """
        if self.timing_context is None:
            return 0.0

        bonus = 0.0
        timing = self.timing_context.turn_timing

        # Safe turn bonus: reward attacking when monsters are buffing
        if timing.value == "SAFE":
            damage_dealt = sum(
                m['hp'] for m in final_state.monsters if not m['is_gone']
            )  # Note: This is rough estimate
            bonus += damage_dealt * 0.5  # Extra reward for attacking on safe turns
            logger.debug(f"[TIMING_BONUS] Safe turn: +{damage_dealt * 0.5:.1f} for attacking")

        # Threat spike bonus: reward proper blocking
        elif timing.value == "THREAT_SPIKE":
            expected_damage = self.timing_context.current_damage
            if final_state.player_block >= expected_damage * 0.8:
                # Good blocking - sufficient block for incoming damage
                bonus += 50.0
                logger.debug(f"[TIMING_BONUS] Threat spike: +50.0 for proper blocking")
            else:
                # Under-blocking - penalty
                bonus -= 30.0
                logger.debug(f"[TIMING_BONUS] Threat spike: -30.0 for under-blocking (block={final_state.player_block}, damage={expected_damage})")

        # Preparation bonus: reward building block for future spike
        elif timing.value == "PREPARATION":
            if self.timing_context.future_damage_curve:
                future_damage = self.timing_context.future_damage_curve[0]
                if final_state.player_block >= future_damage * 0.6:
                    bonus += 30.0
                    logger.debug(f"[TIMING_BONUS] Preparation: +30.0 for building block (future_damage={future_damage})")

        # Burst window bonus: reward aggressive damage
        elif timing.value == "BURST_WINDOW":
            damage_dealt = getattr(final_state, 'damage_dealt', 0)
            bonus += damage_dealt * 0.8  # High bonus for damage
            logger.debug(f"[TIMING_BONUS] Burst window: +{damage_dealt * 0.8:.1f} for aggressive damage")

        return bonus

    def calculate_outcome_score(self, initial_state: SimulationState, final_state: SimulationState,
                               current_act: int = 1, weights: dict = None, context=None, sequence=None) -> float:
        """
        Calculate the quality of a combat outcome.

        Higher is better. Considers:
        - Monsters killed
        - Damage dealt
        - Block gained
        - Energy efficiency
        - HP preserved

        Args:
            initial_state: State before actions
            final_state: State after actions
            current_act: Current act number (1, 2, 3)
            weights: Combat mode weight profile (uses defaults if None)
            context: DecisionContext for floor-aware scoring (optional)
            sequence: Card action sequence for AOE bonuses (optional)

        Returns:
            Outcome score
        """
        # Use default weights if none provided (backward compatibility)
        if weights is None:
            # === TIMING-AWARE WEIGHT SELECTION ===
            # If timing context is available, use dynamic weights
            if self.timing_context is not None:
                timing_weights = self.timing_context.balance_weights
                weights = {
                    'KILL_BONUS': timing_weights.kill_bonus,
                    'DAMAGE_WEIGHT': timing_weights.damage_weight,
                    'BLOCK_WEIGHT': timing_weights.block_weight,
                    'ENERGY_EFFICIENCY_WEIGHT': ENERGY_EFFICIENCY_WEIGHT,  # Keep constant
                    'W_DEATHRISK': W_DEATHRISK,  # Keep constant for now
                }
                logger.debug(
                    f"[TIMING_WEIGHTS] Using {self.timing_context.turn_timing.value} weights: "
                    f"damage={timing_weights.damage_weight:.2f}, "
                    f"block={timing_weights.block_weight:.2f}, "
                    f"kill_bonus={timing_weights.kill_bonus:.0f}"
                )
            else:
                # Default static weights
                weights = {
                    'KILL_BONUS': KILL_BONUS,
                    'DAMAGE_WEIGHT': DAMAGE_WEIGHT,
                    'BLOCK_WEIGHT': BLOCK_WEIGHT,
                    'ENERGY_EFFICIENCY_WEIGHT': ENERGY_EFFICIENCY_WEIGHT,
                    'W_DEATHRISK': W_DEATHRISK,
                }

        score = 0.0

        # 1. Monsters killed (high priority)
        initial_alive = sum(1 for m in initial_state.monsters if not m['is_gone'])
        final_alive = sum(1 for m in final_state.monsters if not m['is_gone'])
        kills = initial_alive - final_alive
        score += kills * weights['KILL_BONUS']

        # ALL_LETHAL_BONUS: Exponential bonus for killing all monsters
        if final_alive == 0 and initial_alive > 0:
            score += ALL_LETHAL_BONUS
            logger.debug(f"[ALL_LETHAL_BONUS] +{ALL_LETHAL_BONUS} score for killing all {initial_alive} monsters")

        # 2. Damage dealt (with multi-monster bonuses)
        total_damage = sum(m['hp'] for m in initial_state.monsters) - \
                      sum(m['hp'] for m in final_state.monsters)

        # Multi-monster detection and adaptive damage weighting
        num_monsters = len([m for m in initial_state.monsters if not m['is_gone']])

        # Get floor for special Floor 6-7 handling
        current_floor = getattr(context, 'floor', 0) if context else 0

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
        logger.info(f"[OUTCOME_MULTIPLIER] Applied {damage_multiplier}× damage weight (base: {weights['DAMAGE_WEIGHT']})")

        score += total_damage * weights['DAMAGE_WEIGHT'] * damage_multiplier

        # Debuff application bonus (reward setting up future damage).
        debuff_bonus = 0.0
        for before, after in zip(initial_state.monsters, final_state.monsters):
            if before['is_gone'] or after['is_gone']:
                continue
            vuln_delta = max(0, after.get('vulnerable', 0) - before.get('vulnerable', 0))
            weak_delta = max(0, after.get('weak', 0) - before.get('weak', 0))
            debuff_bonus += vuln_delta * VULNERABLE_APPLY_BONUS
            debuff_bonus += weak_delta * WEAK_APPLY_BONUS
        score += debuff_bonus

        # AOE card bonus in multi-monster scenarios
        if sequence and num_monsters >= 2:
            aoe_cards = ['Cleave', 'Whirlwind', 'Thunderclap', 'Immolate']

            for action in sequence:
                if hasattr(action, 'card') and hasattr(action.card, 'card_id'):
                    card_id = action.card.card_id.replace('+', '')  # Handle upgraded cards

                    if card_id in aoe_cards:
                        aoe_bonus = 40 if num_monsters >= 3 else 20
                        score += aoe_bonus
                        logger.info(f"[OUTCOME_AOE] +{aoe_bonus} for {card_id} in {num_monsters}-monster fight")

        # 3. Block gained (defensive value)
        block_gained = final_state.player_block - initial_state.player_block

        # Log block cards used in this sequence for debugging
        if block_gained > 0 and sequence:
            block_cards = []
            for action in sequence:
                if hasattr(action, 'card') and hasattr(action.card, 'card_id'):
                    card_id = action.card.card_id
                    # Check if this is a block card by looking at known block cards
                    card_name = card_id.replace('+', '')
                    if any(bc in card_name for bc in ['Defend', 'Iron Wave', 'Flame Barrier', 'Impervious', 'Entrench', 'Rage', 'Body Slam']):
                        upgrades = getattr(action.card, 'upgrades', 0)
                        block_cards.append(f"{card_id}({upgrades}u)" if upgrades > 0 else card_id)
            if block_cards:
                logger.info(f"[BLOCK_CARDS] Block cards in sequence: {', '.join(block_cards)} → {block_gained} block gained")

        # Apply block penalty when lethal is available (all monsters could be killed)
        # Calculate if lethal is possible by checking if total damage could kill all
        total_monster_hp = sum(m['hp'] + m['block'] for m in initial_state.monsters if not m['is_gone'])
        if final_alive > 0 and total_damage >= total_monster_hp * 1.1:
            # Lethal is available but we chose defense - penalize heavily
            score += block_gained * weights['BLOCK_WEIGHT'] * 0.3  # 70% reduction
            logger.debug(f"[LETHAL_BLOCK_PENALTY] Block score reduced by 70% because lethal was available")
        else:
            # Normal scoring
            score += block_gained * weights['BLOCK_WEIGHT']
            if block_gained > 0:
                logger.debug(f"[BLOCK_SCORE] +{block_gained} block × {weights['BLOCK_WEIGHT']} = +{block_gained * weights['BLOCK_WEIGHT']:.1f} score")

        # 4. Energy efficiency (prefer using most energy)
        energy_used = initial_state.player_energy - final_state.player_energy
        score += energy_used * weights['ENERGY_EFFICIENCY_WEIGHT']

        # 5. HP preserved (very important)
        hp_lost = initial_state.player_hp - final_state.player_hp
        score -= hp_lost * HP_LOSS_PENALTY

        # 6. Survival-first scoring (estimate next turn incoming damage)
        expected_incoming = self._estimate_incoming_damage(final_state.monsters)
        hp_loss_next_turn = max(0, expected_incoming - final_state.player_block)

        # Log defensive analysis for debugging
        if block_gained > 0 or final_state.player_block > 0:
            logger.debug(f"[DEFENSE_ANALYSIS] block_gained={block_gained}, final_block={final_state.player_block}, "
                        f"expected_incoming={expected_incoming}, hp_loss_next_turn={hp_loss_next_turn}, "
                        f"player_hp={final_state.player_hp}")

        # Detect over-defense (block significantly exceeds incoming damage)
        if final_state.player_block > expected_incoming * 1.5 and expected_incoming > 0:
            logger.warning(f"[OVER_DEFENSE] Block ({final_state.player_block}) is {final_state.player_block / max(expected_incoming, 1):.1f}x incoming damage ({expected_incoming}) - wasting resources!")

        # Detect useless defense (block when no incoming damage)
        if expected_incoming == 0 and final_state.player_block > 0:
            logger.warning(f"[USELESS_DEFENSE] Gained {block_gained} block when no incoming damage expected - completely wasted!")

        # Penalty for useless defense (block when monsters aren't attacking)
        # Disabled: expected_incoming can be 0 when intent/attack data is missing,
        # which incorrectly punishes defensive plays.
        # if expected_incoming == 0 and block_gained > 0:
        #     # Heavy penalty: block cards are completely wasted this turn
        #     score -= block_gained * 10.0  # 10 points per block wasted
        #     logger.debug(f"[USELESS_DEFENSE_PENALTY] -{block_gained * 10.0:.1f} score for {block_gained} wasted block")

        # Death penalty (infinite score = avoid at all costs)
        if hp_loss_next_turn >= final_state.player_hp:
            return float('-inf')

        # Survival penalty (weighted heavily)
        score -= hp_loss_next_turn * weights['W_DEATHRISK']

        # === FUTURE DAMAGE PENALTY (proactive AI using Wiki move predictions) ===
        if context is not None:
            try:
                lookahead_turns = self._get_enemy_lookahead_depth(final_state, context)
                future_damage = self.simulate_enemy_lookahead(final_state, context, look_ahead=lookahead_turns)

                if future_damage > 0:
                    # Apply future damage penalty at 50% weight (uncertainty discount)
                    # This makes the AI proactive about preventing future threats
                    future_damage_penalty = future_damage * weights['W_DEATHRISK'] * 0.5
                    score -= future_damage_penalty
                    logger.info(
                        f"[FUTURE_DAMAGE_PENALTY] -{future_damage_penalty:.1f} score for "
                        f"{future_damage} predicted damage over next {lookahead_turns} turns"
                    )
            except Exception as e:
                logger.warning(f"[FUTURE_DAMAGE_PENALTY] Failed to apply future damage penalty: {e}")

        # Danger threshold penalty (act-dependent)
        danger_threshold = 15 + (current_act * 5)  # Act 1: 20, Act 2: 25, Act 3: 30
        if final_state.player_hp - hp_loss_next_turn < danger_threshold:
            score -= DANGER_PENALTY

        # 7. Engine event tracking (synergy bonuses)
        # Feel No Pain value: exhaust events generate block
        score += final_state.exhaust_events * EXHAULT_SYNERGY_VALUE

        # Draw Engine value: card draw provides options
        score += final_state.cards_drawn * DRAW_SYNERGY_VALUE

        # Energy value: gained/saved energy is valuable
        score += final_state.energy_gained * ENERGY_SYNERGY_VALUE
        score += final_state.energy_saved * ENERGY_SYNERGY_VALUE

        # === TIMING-AWARE SCORING BONUS ===
        # Add timing-specific bonuses based on turn classification
        timing_bonus = self._calculate_timing_bonus(final_state)
        score += timing_bonus

        return score


class HeuristicCombatPlanner(CombatPlanner):
    """
    Combat planner using heuristic evaluation and beam search.

    This planner uses beam search to find good action sequences without
    exhaustively searching all possibilities.
    """

    def __init__(self, card_evaluator: SynergyCardEvaluator = None,
                 beam_width: int = 10, max_depth: int = 4, player_class: str = None, act: int = 1,
                 combat_mode: CombatMode = CombatMode.BALANCED):
        """
        Initialize the combat planner.

        Args:
            card_evaluator: Card evaluator for value calculations
            beam_width: Number of candidates to keep at each depth (optional, adaptive if act provided)
            max_depth: Maximum number of cards to lookahead
            player_class: Player class for class-specific logic
            act: Current act number (1, 2, 3) for adaptive beam width
            combat_mode: Combat mode (BALANCED, AGGRESSIVE, SEMI_AGGRESSIVE)
        """
        self.card_evaluator = card_evaluator or SynergyCardEvaluator()
        self.simulator = FastCombatSimulator(self.card_evaluator)

        # Store combat mode and get weight profile
        self.combat_mode = combat_mode
        self.weights = get_combat_mode_weights(combat_mode)

        # Log mode selection for debugging
        logger.info(f"[COMBAT_MODE] Using {combat_mode.name} mode - DAMAGE={self.weights['DAMAGE_WEIGHT']}, BLOCK={self.weights['BLOCK_WEIGHT']}")

        # Adaptive beam width by act (if act provided)
        if act and beam_width == 10:  # Use adaptive if default and act known
            # Act 1: 12 (simple enemies, less search needed)
            # Act 2: 18 (moderate complexity)
            # Act 3: 25 (high complexity, elites/bosses)
            adaptive_width = [BEAM_WIDTH_ACT1, BEAM_WIDTH_ACT2, BEAM_WIDTH_ACT3]
            self.beam_width = adaptive_width[min(act - 1, 2)] if act <= 3 else BEAM_WIDTH_ACT3
        else:
            self.beam_width = beam_width

        self.max_depth = max_depth
        self.player_class = player_class
        self.act = act  # Store act for reference

    def plan_turn(self, context: DecisionContext) -> List[Action]:
        """
        Plan optimal action sequence for this turn.

        Uses beam search to find good sequences efficiently.

        Args:
            context: Current decision context

        Returns:
            List of actions to execute (may be empty)
        """
        # Track decision time
        decision_start = time.time()

        # Log input state
        logger.debug(f"=== Beam Search Planning ===")
        logger.debug(f"Act: {context.act if hasattr(context, 'act') else 1}")
        logger.debug(f"Turn: {context.turn if hasattr(context, 'turn') else 1}")
        logger.debug(f"Playable cards: {len(context.playable_cards)}")
        logger.debug(f"Energy available: {context.energy_available if hasattr(context, 'energy_available') else 3}")

        # === Adaptive beam width by act ===
        # Act 1: 12 (simple enemies, less search needed)
        # Act 2: 18 (moderate complexity)
        # Act 3: 25 (high complexity, elites/bosses)
        if hasattr(context, 'act'):
            adaptive_width = [BEAM_WIDTH_ACT1, BEAM_WIDTH_ACT2, BEAM_WIDTH_ACT3]
            self.beam_width = adaptive_width[min(context.act - 1, 2)] if context.act <= 3 else BEAM_WIDTH_ACT3

        # === Adaptive max_depth by hand size and energy ===
        playable_count = len(context.playable_cards)

        # Count zero-cost cards (they enable deeper chains)
        extra_zero_cost = sum(1 for c in context.playable_cards
                             if hasattr(c, 'cost_for_turn') and c.cost_for_turn == 0)

        # Extra energy beyond base 3
        extra_energy = context.energy_available - 3 if hasattr(context, 'energy_available') else 0

        # Calculate adaptive depth: base 3 + bonuses
        # More cards, zero-cost cards, or extra energy → deeper search
        adaptive_depth = 3 + extra_energy + (extra_zero_cost // 2)

        # Cap at playable card count (can't play more than you have)
        adaptive_depth = min(adaptive_depth, playable_count)

        # Hard cap at MAX_DEPTH_CAP to avoid excessive search (timeout protection)
        self.max_depth = min(adaptive_depth, MAX_DEPTH_CAP)

        # Log adaptive parameters
        logger.debug(f"Beam width: {self.beam_width}")
        logger.debug(f"Max depth: {self.max_depth}")
        logger.debug(f"Zero-cost cards: {extra_zero_cost}")
        logger.debug(f"Extra energy: {extra_energy}")

        if not context.playable_cards:
            decision_time = (time.time() - decision_start) * 1000
            logger.debug(f"No playable cards. Decision time: {decision_time:.1f}ms")
            return []  # No playable cards, end turn

        # If only 1-2 cards, simple evaluation is sufficient
        if len(context.playable_cards) <= 2:
            result = self._simple_plan(context)
            decision_time = (time.time() - decision_start) * 1000
            logger.debug(f"Simple plan ({len(result)} actions). Decision time: {decision_time:.1f}ms")
            return result

        # Use beam search for complex situations
        result = self._beam_search_plan(context)
        decision_time = (time.time() - decision_start) * 1000
        logger.debug(f"Beam search complete ({len(result)} actions). Decision time: {decision_time:.1f}ms")
        return result

    def _simple_plan(self, context: DecisionContext) -> List[Action]:
        """Simple planning for trivial situations."""
        if not context.playable_cards:
            return []

        # Rank cards by evaluator
        best_card = self.card_evaluator.get_best_card(context.playable_cards, context)

        if best_card.has_target:
            # Find best target
            target = self._find_best_target(best_card, context)
            return [PlayCardAction(card=best_card, target_monster=target)]
        else:
            return [PlayCardAction(card=best_card)]

    def _beam_search_plan(self, context: DecisionContext) -> List[Action]:
        """Use beam search to find optimal action sequence with transposition table."""
        initial_state = SimulationState(context)

        # === Timeout protection: Track start time ===
        start_time = time.time()
        timeout_budget = TIMEOUT_BUDGET  # Configurable timeout budget

        # Initialize beam with empty sequence
        beam = [([], initial_state, 0)]  # (actions, state, energy_spent)

        best_sequence = []
        best_score = float('-inf')

        # Transposition table: maps state_key → (sequence, state, energy_spent, score)
        seen_states = {}

        for depth in range(self.max_depth):
            # === Timeout check: Return best found so far ===
            elapsed_ms = (time.time() - start_time) * 1000
            if time.time() - start_time > timeout_budget:
                # Timeout! Return best sequence found (may be empty → use simple plan)
                logger.warning(f"Beam search timeout at depth {depth}! Time: {elapsed_ms:.1f}ms (budget: {timeout_budget * 1000:.1f}ms)")
                break

            # === Check if target exploration should be enabled ===
            explore_targets = self._should_explore_targets(context, elapsed_ms)
            new_candidates = []

            for sequence, state, energy_spent in beam:
                # === Two-stage action expansion ===
                # Collect playable cards
                playable_actions = []
                for card in context.playable_cards:
                    card_idx = id(card)
                    if card_idx not in state.played_card_uuids:
                        cost = effective_card_cost(card, state.player_energy)
                        if energy_spent + cost <= context.energy_available:
                            playable_actions.append((card, card_idx, cost))

                # Collect potion actions (only at depth 0 to limit search complexity)
                potion_actions = []
                if depth == 0:
                    potion_actions = self._get_potion_actions(context, state)
                    # Limit to highest-priority potion to prevent exponential growth
                    if potion_actions:
                        potion_actions.sort(key=lambda x: x[3], reverse=True)
                        potion_actions = [potion_actions[0]]  # Best potion only
                        logger.debug(f"Potion considered: {potion_actions[0][0].name}, score: {potion_actions[0][3]:.1f}")

                if not playable_actions and not potion_actions:
                    continue  # No playable actions for this beam entry

                # Stage 1: FastScore filter - lightweight scoring without simulation
                scored_actions = [
                    (card_idx, card, cost, self.fast_score_action(card, state, context))
                    for card, card_idx, cost in playable_actions
                ]

                # Add potion actions with their priority scores (use priority as fast_score)
                for potion, target, cost, priority in potion_actions:
                    # Use a tuple format that matches card actions but with marker for potion
                    scored_actions.append((('potion', potion, target), potion, cost, priority))

                # Sort by fast_score descending (highest first)
                scored_actions.sort(key=lambda x: x[3], reverse=True)

                # Stage 2: Progressive widening - select top M based on depth
                # M_values: Depth 0→12, 1→10, 2→7, 3→5, 4→4
                M = M_VALUES[min(depth, len(M_VALUES) - 1)]

                # Only full-simulate top M actions
                for card_idx, card, cost, _ in scored_actions[:M]:
                    # Check if this is a potion action (card_idx is a tuple marker for potions)
                    if isinstance(card_idx, tuple) and card_idx[0] == 'potion':
                        # Handle potion action
                        from spirecomm.communication.action import PotionAction
                        _, potion, target = card_idx

                        # Simulate potion use (simplified simulation for now)
                        new_state = copy.deepcopy(state)
                        # Apply potion effect to state
                        if potion.effect_type == 'damage':
                            # Reduce target HP (handle single target or AOE)
                            if potion.target_type == 'all_monsters':
                                for i, m in enumerate(new_state.monsters):
                                    if not m.get('is_gone') and m['hp'] > 0:
                                        new_state.monsters[i]['hp'] = max(0, m['hp'] - potion.effect_value)
                            else:
                                target_index = None
                                if target:
                                    # Match by name first, then closest HP to avoid duplicate-name ambiguity.
                                    candidates = []
                                    for i, m in enumerate(new_state.monsters):
                                        if m['hp'] > 0 and m['name'] == target.name:
                                            hp_delta = abs(m['hp'] - getattr(target, 'current_hp', m['hp']))
                                            candidates.append((hp_delta, i))
                                    if candidates:
                                        candidates.sort(key=lambda x: x[0])
                                        target_index = candidates[0][1]
                                if target_index is None:
                                    # Fallback: first alive monster.
                                    for i, m in enumerate(new_state.monsters):
                                        if m['hp'] > 0 and not m.get('is_gone'):
                                            target_index = i
                                            break
                                if target_index is not None:
                                    m = new_state.monsters[target_index]
                                    m['hp'] = max(0, m['hp'] - potion.effect_value)
                        elif potion.effect_type == 'block':
                            new_state = new_state._replace(player_block=new_state.player_block + potion.effect_value)
                        elif potion.effect_type in ['heal', 'regen']:
                            new_state = new_state._replace(player_hp=min(new_state.player_max_hp, new_state.player_hp + potion.effect_value))
                        elif potion.effect_type == 'buff_strength':
                            new_state = new_state._replace(player_strength=new_state.player_strength + potion.effect_value)

                        # Create potion action
                        if target:
                            action = PotionAction(True, potion=potion, target_monster=target)
                        else:
                            action = PotionAction(True, potion=potion)

                        new_sequence = sequence + [action]

                        # Score this sequence (with small conservation penalty for using potion)
                        current_act = context.act if hasattr(context, 'act') else 1
                        score = self.simulator.calculate_outcome_score(initial_state, new_state, current_act, self.weights, context, new_sequence)
                        total_score = score - 5  # Conservation penalty

                        new_candidates.append((new_sequence, new_state, energy_spent, total_score))
                    else:
                        # Handle card action (original logic)
                        # card_idx is the card index, card is the Card object

                        # === Target exploration with progressive expansion ===
                        if card.has_target and explore_targets:
                            # Progressive target expansion: depth 0→2 targets, depth 1→1-2, depth 2+→1
                            M_targets = 2 if depth == 0 else (1 if depth >= 2 else 2)

                            # Get ranked targets
                            ranked_targets = self._rank_targets(card, context, estimate_damage=True)

                            # Prune targets
                            pruned_targets = self._prune_targets(card, ranked_targets, context)

                            if pruned_targets and len(pruned_targets) > 1:
                                # Explore multiple targets (limited by M_targets)
                                targets_to_explore = pruned_targets[:M_targets]
                                logger.info(f"[TARGET_EXPLORE] Depth {depth}: exploring {len(targets_to_explore)} targets for {card.card_id}")

                                for target, _ in targets_to_explore:
                                    # Simulate playing this card with each target
                                    new_state = self.simulator.simulate_card_play(state, card, target, context=context)
                                    new_state_copy = copy.deepcopy(new_state)
                                    new_state_copy.played_card_uuids.add(card_idx)

                                    # Create action
                                    action = PlayCardAction(card=card, target_monster=target)
                                    new_sequence = sequence + [action]

                                    # Score this sequence
                                    current_act = context.act if hasattr(context, 'act') else 1
                                    score = self.simulator.calculate_outcome_score(initial_state, new_state_copy, current_act, self.weights, context, new_sequence)

                                    # Consider card value from evaluator
                                    card_value = self.card_evaluator.evaluate_card(card, context)
                                    total_score = score + card_value

                                    new_candidates.append((new_sequence, new_state_copy, energy_spent + cost, total_score))
                            else:
                                # Fallback to deterministic if pruning returned 0 or 1 target
                                target = self._find_best_target(card, context)

                                # Simulate playing this card
                                new_state = self.simulator.simulate_card_play(state, card, target, context=context)
                                new_state.played_card_uuids.add(card_idx)

                                # Create action
                                if target:
                                    action = PlayCardAction(card=card, target_monster=target)
                                else:
                                    action = PlayCardAction(card=card)

                                new_sequence = sequence + [action]

                                # Score this sequence
                                current_act = context.act if hasattr(context, 'act') else 1
                                score = self.simulator.calculate_outcome_score(initial_state, new_state, current_act, self.weights, context, new_sequence)

                                # Consider card value from evaluator
                                card_value = self.card_evaluator.evaluate_card(card, context)
                                total_score = score + card_value

                                new_candidates.append((new_sequence, new_state, energy_spent + cost, total_score))
                        else:
                            # Use deterministic targeting (either no target exploration needed, or card has no target)
                            target = self._find_best_target(card, context) if card.has_target else None

                            # Simulate playing this card
                            new_state = self.simulator.simulate_card_play(state, card, target, context=context)
                            new_state.played_card_uuids.add(card_idx)

                            # Create action
                            if target:
                                action = PlayCardAction(card=card, target_monster=target)
                            else:
                                action = PlayCardAction(card=card)

                            new_sequence = sequence + [action]

                            # Score this sequence (with current act for survival threshold)
                            current_act = context.act if hasattr(context, 'act') else 1
                            score = self.simulator.calculate_outcome_score(initial_state, new_state, current_act, self.weights, context, new_sequence)

                            # Consider card value from evaluator
                            card_value = self.card_evaluator.evaluate_card(card, context)
                            total_score = score + card_value

                            new_candidates.append((new_sequence, new_state, energy_spent + cost, total_score))

            if not new_candidates:
                break  # No more valid plays

            # === Transposition table: Deduplicate identical states ===
            # Keep only the best-scoring path to each unique state
            for candidate in new_candidates:
                seq, st, energy, score = candidate
                key = st.state_key(context.playable_cards)

                if key in seen_states:
                    # State seen before - keep best scoring path
                    existing_score = seen_states[key][3]
                    if score > existing_score:
                        seen_states[key] = candidate  # Replace with better path
                else:
                    seen_states[key] = candidate  # First time seeing this state

            # Convert transposition table back to beam
            deduplicated_candidates = list(seen_states.values())

            # Log transposition table stats
            if len(new_candidates) > len(deduplicated_candidates):
                merge_count = len(new_candidates) - len(deduplicated_candidates)
                logger.debug(f"Depth {depth}: {len(new_candidates)} candidates → {len(deduplicated_candidates)} unique (merged {merge_count} duplicates)")

            # Keep top candidates
            deduplicated_candidates.sort(key=lambda x: x[3], reverse=True)
            beam = deduplicated_candidates[:self.beam_width]

            # Track best sequence
            if beam:
                best_sequence, best_state, best_energy, best_score = beam[0]

        # Log final result
        if best_sequence:
            logger.debug(f"Best sequence: {len(best_sequence)} actions, score: {best_score:.1f}")
            # Check if potion is in best sequence
            for action in best_sequence:
                if hasattr(action, 'potion') and action.potion:
                    logger.info(f"Potion selected by beam search: {action.potion.name}")
        else:
            logger.debug("No valid sequence found, falling back to simple plan")

        return best_sequence if best_sequence else self._simple_plan(context)

    def _is_healing_potion(self, potion) -> bool:
        """Check if potion is a healing potion."""
        return potion.effect_type in ['heal', 'regen']

    def _is_damage_potion(self, potion) -> bool:
        """Check if potion is a damage potion."""
        return potion.effect_type == 'damage'

    def _is_block_potion(self, potion) -> bool:
        """Check if potion is a block potion."""
        return potion.effect_type == 'block'

    def _get_incoming_damage(self, context: DecisionContext) -> int:
        """Calculate total incoming damage from all monsters."""
        incoming = 0
        debug_entries = []
        for monster in context.game.monsters:
            if not monster.is_gone and not monster.half_dead:
                if monster.move_adjusted_damage is not None:
                    incoming += monster.move_adjusted_damage * monster.move_hits
                    debug_entries.append(
                        f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                        f"adjusted={monster.move_adjusted_damage} hits={monster.move_hits}"
                    )
                elif monster.intent == Intent.NONE:
                    incoming += 5 * context.act
                    debug_entries.append(
                        f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                        f"adjusted=None fallback=act*5({5 * context.act})"
                    )
                else:
                    debug_entries.append(
                        f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                        f"adjusted=None hits={monster.move_hits}"
                    )
        if debug_entries:
            logger.debug("[INCOMING_DAMAGE] " + " | ".join(debug_entries) + f" => total={incoming}")
        return incoming

    def _score_potion(self, potion, context: DecisionContext, state: SimulationState) -> float:
        """
        Score a potion based on its expected value in the current combat situation.

        Args:
            potion: Potion object
            context: Decision context
            state: Simulation state

        Returns:
            Score value (higher is better)
        """
        score = 0.0
        hp_pct = state.player_hp / max(state.player_max_hp, 1)
        incoming_damage = self._get_incoming_damage(context)
        alive_monsters = [m for m in context.game.monsters if not m.is_gone]

        # Healing potions: high value when HP is low
        if self._is_healing_potion(potion):
            if hp_pct < 0.3:
                score += 50  # Critical HP
            elif hp_pct < 0.5 and incoming_damage > state.player_hp * 0.3:
                score += 30  # In danger

        # Damage potions: high value for lethal or high-threat targets
        elif self._is_damage_potion(potion):
            if alive_monsters:
                # Immediate lethal check for any target (ignore incoming damage gating).
                for i, monster in enumerate(alive_monsters):
                    vuln = context.vulnerable_stacks.get(i, 0) if hasattr(context, 'vulnerable_stacks') else 0
                    damage = potion.effect_value * (1.5 if vuln > 0 else 1.0)
                    if damage >= monster.current_hp:
                        score += 100
                        break

            if alive_monsters and incoming_damage > 0:
                # Bonus for elites/bosses
                if 'Elite' in context.game.room_type or 'Boss' in context.game.room_type:
                    score += 40
                # Bonus for multiple monsters (AOE)
                if len(alive_monsters) >= 2:
                    score += 25
                # Bonus when close to lethal
                total_monster_hp = sum(m.current_hp for m in alive_monsters)
                if total_monster_hp < 50:
                    score += 20

        # Block potions: high value when incoming damage is high
        elif self._is_block_potion(potion):
            if incoming_damage > state.player_hp * 0.4:
                score += 35  # High incoming damage

        # Utility/Buff potions: baseline value in dangerous fights
        else:
            if incoming_damage > state.player_hp * 0.3:
                score += 20

        return score

    def _find_best_potion_target(self, potion, context: DecisionContext) -> Monster:
        """
        Find the best target for a potion.

        Args:
            potion: Potion object
            context: Decision context

        Returns:
            Target monster (or None if no target needed)
        """
        if not context.monsters_alive:
            return None

        # For damage potions, target highest-threat monster
        if self._is_damage_potion(potion):
            return max(context.monsters_alive, key=lambda m: context.compute_threat(m))

        # For debuff potions, target high-HP monsters to maximize debuff value
        elif potion.effect_type.startswith('debuff_'):
            return max(context.monsters_alive, key=lambda m: m.current_hp)

        # Default: highest threat
        return max(context.monsters_alive, key=lambda m: context.compute_threat(m))

    def _get_potion_actions(self, context: DecisionContext, state: SimulationState) -> List[Tuple]:
        """
        Generate potion actions for beam search expansion.

        Args:
            context: Decision context
            state: Simulation state

        Returns:
            List of (potion, target_monster, energy_cost, priority_score) tuples
        """
        from spirecomm.spire.potion import Potion

        potions = context.game.get_real_potions()
        potion_actions = []

        for potion in potions:
            if not potion.can_use:
                continue

            # Calculate priority score based on potion type and game state
            priority = self._score_potion(potion, context, state)

            # Determine target if needed
            target = None
            if potion.requires_target:
                target = self._find_best_potion_target(potion, context)

            # Potions cost 0 energy
            potion_actions.append((potion, target, 0, priority))

        return potion_actions

    def _rank_targets(self, card: Card, context: DecisionContext, estimate_damage: bool = True) -> list:
        """
        Rank targets for a card using threat-based targeting.

        Returns a list of (monster, threat_score) tuples sorted by threat (highest first).
        Separate logic for attacks vs debuff cards.

        Args:
            card: Card being played
            context: Decision context
            estimate_damage: Whether to estimate damage for attack cards (default: True)

        Returns:
            List of (monster, threat_score) tuples sorted by threat descending
        """
        if not context.monsters_alive:
            return []

        # Check if card is an attack
        is_attack = hasattr(card, 'type') and card.type == CardType.ATTACK

        # Rank all monsters by threat
        ranked_targets = []
        for monster in context.monsters_alive:
            threat = context.compute_threat(monster)
            ranked_targets.append((monster, threat))

        # Sort by threat descending
        ranked_targets.sort(key=lambda x: x[1], reverse=True)

        return ranked_targets

    def _prune_targets(self, card: Card, ranked_targets: list, context: DecisionContext) -> list:
        """
        Prune target space to limit beam search expansion.

        Pruning strategy:
        - For attack cards: Keep killable targets + highest threat fallback
        - For debuff cards: Keep top 2 threat targets
        - Skip if > 4 monsters (fallback to deterministic)

        Args:
            card: Card being played
            ranked_targets: List of (monster, threat_score) tuples from _rank_targets()
            context: Decision context

        Returns:
            Pruned list of (monster, threat_score) tuples
        """
        if not ranked_targets:
            return []

        monster_count = len(context.monsters_alive)

        # Skip pruning if too many monsters (fallback to deterministic)
        if monster_count > 4:
            logger.info(f"[TARGET_PRUNING] Skipping - {monster_count} monsters > 4")
            return []

        # Check if cleanup phase (all monsters low HP)
        all_low_hp = all(m.current_hp < 8 for m in context.monsters_alive)
        if all_low_hp:
            logger.info("[TARGET_PRUNING] Cleanup phase detected - using greedy lowest-HP")
            # Use greedy lowest-HP targeting
            low_hp_targets = sorted(
                [(m, threat) for m, threat in ranked_targets],
                key=lambda x: x[0].current_hp
            )
            return low_hp_targets[:1]  # Just the lowest HP target

        is_attack = hasattr(card, 'type') and card.type == CardType.ATTACK

        if is_attack:
            # Estimate damage for attack cards
            base_damage = getattr(card, 'damage', 0)
            if base_damage == 0 or not hasattr(card, 'damage'):
                try:
                    card_name = card.card_id.replace('+', '')
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        base_damage = game_data_loader._parse_card_damage(card_data)
                except:
                    pass

            if base_damage == 0:
                base_damage = 6  # Fallback

            # Add player strength
            total_damage = base_damage + context.player.strength if hasattr(context.player, 'strength') else base_damage

            # Separate killable and non-killable targets
            killable = []
            non_killable = []
            for monster, threat in ranked_targets:
                effective_hp = monster.current_hp + monster.block
                if total_damage >= effective_hp:
                    killable.append((monster, threat))
                else:
                    non_killable.append((monster, threat))

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
            if card.has_target:
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
        all_low_hp = all(m.current_hp < 8 for m in context.monsters_alive)
        if all_low_hp:
            logger.info("[TARGET_EXPLORE] Disabled - cleanup phase (all monsters < 8 HP)")
            return False

        logger.info(f"[TARGET_EXPLORE] Enabled - {monster_count} monsters, {hand_size} cards, {elapsed_time:.1f}ms")
        return True

    def _find_best_target(self, card: Card, context: DecisionContext) -> Monster:
        """
        Find the best target for a card using threat-based targeting.

        Strategy:
        - Attack cards:
          1. Estimate damage
          2. Find killable targets (damage >= monster HP + block)
          3. Target highest threat killable monster, or highest threat overall
        - Debuff cards: highest threat monster (maximize debuff value)
        - Defensive buffs: highest threat monster (protect from biggest threat)

        Args:
            card: Card being played
            context: Decision context

        Returns:
            Target monster
        """
        if not context.monsters_alive:
            return None

        # Check if card is an attack
        is_attack = hasattr(card, 'type') and card.type == CardType.ATTACK

        if is_attack:
            # Estimate damage for this attack
            base_damage = getattr(card, 'damage', 0)

            # Try to get damage from game data
            if base_damage == 0 or not hasattr(card, 'damage'):
                try:
                    card_name = card.card_id.replace('+', '')
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        base_damage = game_data_loader._parse_card_damage(card_data)
                except:
                    pass

            if base_damage == 0:
                base_damage = 6  # Fallback estimate

            # Add player strength
            total_damage = base_damage + context.player.strength if hasattr(context.player, 'strength') else base_damage

            # Find killable targets
            killable_targets = []
            for monster in context.monsters_alive:
                effective_hp = monster.current_hp + monster.block
                if total_damage >= effective_hp:
                    killable_targets.append(monster)

            if killable_targets:
                # Target highest threat killable monster
                return max(killable_targets, key=lambda m: context.compute_threat(m))
            else:
                # No killable targets, target highest threat overall
                ranked_targets = self._rank_targets(card, context, estimate_damage=False)
                return ranked_targets[0][0] if ranked_targets else None
        else:
            # For debuff/buff cards, target highest threat monster
            ranked_targets = self._rank_targets(card, context, estimate_damage=False)
            return ranked_targets[0][0] if ranked_targets else None

    def fast_score_action(self, card: Card, state: SimulationState, context: DecisionContext) -> float:
        """
        Lightweight scoring without full simulation.

        Used in Stage 1 of two-stage action expansion to filter low-value actions
        before expensive full simulation.

        Scoring criteria:
        - Zero-cost cards: +20 (high value)
        - Attacks when monsters alive: +10 (offensive value)
        - Block at low HP: +15 (defensive value)
        - Base damage: +2 per damage point
        - AOE multiplier: ×(1 + 0.5×(monsters-1)) for multi-target attacks

        Args:
            card: Card to score
            state: Current simulation state
            context: Decision context

        Returns:
            Fast score (higher is better)
        """
        score = 0.0

        # === CRITICAL: Rage synergy bonus (play before attacks) ===
        # Rage effect: "Whenever you play an Attack this turn, gain 3 Block"
        # Value depends on how many attack cards can be played after it
        card_name = card.card_id.replace('+', '') if hasattr(card, 'card_id') else ''
        if card_name == 'Rage':
            # Count playable attack cards in hand
            attack_cards = [c for c in context.playable_cards
                          if hasattr(c, 'type') and c.type == CardType.ATTACK]

            # Calculate potential block from Rage (3 block per attack)
            potential_block = len(attack_cards) * 3

            # Base bonus for Rage (it's 0 cost and enables block generation)
            score += 15  # Base value for playing a 0-cost skill

            # Add value based on attack cards in hand
            score += potential_block * 1.5  # 1.5 points per potential block

            # Extra bonus when low HP (defense is more valuable)
            if state.player_hp < 40:
                score += 10

            logger.debug(f"Rage score bonus: {potential_block} potential block from {len(attack_cards)} attacks")

        # Zero-cost bonus (Apex, Clothesline after Corruption, etc.)
        cost = effective_card_cost(card, state.player_energy)
        if cost == 0:
            score += FASTSCORE_ZERO_COST_BONUS

        # Baseline power bonus to avoid pruning setup cards
        if hasattr(card, 'type') and card.type == CardType.POWER:
            power_bonus = FASTSCORE_POWER_BONUS
            if hasattr(context, 'turn') and context.turn <= 2:
                power_bonus += FASTSCORE_POWER_EARLY_BONUS
            score += power_bonus

        # Attack bonus when monsters alive
        monsters_alive = [m for m in state.monsters if not m['is_gone']]
        num_monsters = len(monsters_alive)
        if monsters_alive and hasattr(card, 'type') and card.type == CardType.ATTACK:
            score += FASTSCORE_ATTACK_BONUS

        # Debuff setup bonus when attacks remain (e.g., Shockwave before attacks).
        if monsters_alive and hasattr(card, 'type') and card.type == CardType.SKILL:
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = card_data.get('description', '').lower()
                if 'vulnerable' in description or 'weak' in description:
                    attack_cards = [c for c in context.playable_cards
                                    if hasattr(c, 'type') and c.type == CardType.ATTACK]
                    if attack_cards:
                        is_aoe = game_data_loader._is_card_aoe(card_data) or 'all enemies' in description
                        bonus = 6
                        if 'vulnerable' in description:
                            bonus += 4
                        bonus += min(len(attack_cards), 3) * 2
                        if is_aoe and num_monsters > 1:
                            bonus += 4
                        score += bonus

        # Block bonus at low HP (check by card_id since card.block is not set)
        is_block_card = any(keyword in card_name for keyword in ['Defend', 'Iron Wave', 'Flame Barrier', 'Impervious', 'Entrench'])
        if state.player_hp < 30 and is_block_card:
            score += FASTSCORE_LOWHP_BLOCK_BONUS

        # X-block bonus for cards like Rage (already handled above for Rage)
        if not is_block_card and card_name != 'Rage':
            x_block = self._calculate_x_block(card, state, context)
            if x_block > 0:
                # X-block cards are valuable when you need defense
                if state.player_hp < 40:
                    score += FASTSCORE_LOWHP_BLOCK_BONUS
                score += x_block * 1.0  # 1 point per block gained

        # Detect AOE cards
        is_aoe = False
        if hasattr(card, 'card_id'):
            # Check known AOE cards
            from spirecomm.ai.priorities import IroncladPriority
            if hasattr(context, 'player_class'):
                player_class = str(context.player_class)
            else:
                player_class = 'IRONCLAD'

            if player_class == 'IRONCLAD':
                is_aoe = card.card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']

        # Base damage estimate with AOE multiplier
        base_damage = 0
        if hasattr(card, 'damage') and card.damage:
            base_damage = card.damage
        elif hasattr(card, 'type') and card.type == CardType.ATTACK:
            # Fallback: use game data for damage
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                base_damage = game_data_loader._parse_card_damage(card_data)

            # Check for X-damage cards and calculate dynamically
            if base_damage == 0:
                base_damage = self._calculate_x_damage(card, state, context)

        # Apply AOE multiplier for multi-target attacks
        if is_aoe and num_monsters > 1:
            # AOE multiplier: scales with monster count
            # 2 monsters: 1.5x, 3 monsters: 2.0x, 4 monsters: 2.5x
            aoe_multiplier = 1.0 + 0.5 * (num_monsters - 1)
            score += base_damage * FASTSCORE_DAMAGE_MULTIPLIER * aoe_multiplier
        else:
            # Single-target attack
            score += base_damage * FASTSCORE_DAMAGE_MULTIPLIER

        return score

    def get_confidence(self, context: DecisionContext) -> float:
        """
        Return confidence in combat plan.

        Higher confidence when:
        - Clear lethal line
        - Few decisions to make
        - High energy efficiency possible
        """
        confidence = 0.5

        # Fewer cards = higher confidence (easier to calculate)
        if len(context.playable_cards) <= 3:
            confidence += 0.2
        elif len(context.playable_cards) <= 5:
            confidence += 0.1

        # Check for lethal
        low_hp_monsters = [m for m in context.monsters_alive if m.current_hp < 15]
        if len(low_hp_monsters) > 0 and len(low_hp_monsters) <= len(context.playable_cards):
            confidence += 0.2  # Can probably kill

        # Energy efficiency
        total_energy = sum(c.cost for c in context.playable_cards if c.is_playable)
        if total_energy <= context.energy_available:
            confidence += 0.1  # Can use all energy

        return min(1.0, confidence)
