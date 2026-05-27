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
from spirecomm.ai.heuristics.card_names import canonical_card_name
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
STATUS_CARD_PENALTY = 12.0  # Cost of adding Dazed/Burn/Wound-style deck pollution
ENEMY_STATUS_LOOKAHEAD_WEIGHT = 0.5  # Enemy status predictions are useful but uncertain

# Debuff application bonuses
VULNERABLE_APPLY_BONUS = 6.0
WEAK_APPLY_BONUS = 3.0

# Lookahead risk adjustments for player debuffs
LOOKAHEAD_WEAK_RISK_PER_STACK = 0.05
LOOKAHEAD_FRAIL_RISK_PER_STACK = 0.07
LOOKAHEAD_DEBUFF_RISK_CAP = 0.2
LOOKAHEAD_DAMAGE_DISCOUNT = 0.8

LIVE_MONSTER_ID_TO_WIKI_NAME = {
    'slaverred': 'Red Slaver',
    'redslaver': 'Red Slaver',
    'slaverblue': 'Blue Slaver',
    'blueslaver': 'Blue Slaver',
    'fuzzylousenormal': 'Red Louse',
    'fuzzylousedefensive': 'Green Louse',
    'jawworm': 'Jaw Worm',
    'gremlinnob': 'Gremlin Nob',
    'slimeboss': 'Slime Boss',
    'sphericguardian': 'Spheric Guardian',
}

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


def _monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(monster, dict):
        return monster.get(field_name, default)
    return getattr(monster, field_name, default)


def _normalize_monster_id(monster_id: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(monster_id).lower())


def _canonical_live_monster_name(monster: Any) -> str:
    monster_id = _monster_field(monster, 'monster_id', '') or ''
    mapped_name = LIVE_MONSTER_ID_TO_WIKI_NAME.get(_normalize_monster_id(monster_id))
    if mapped_name:
        return mapped_name
    return str(_monster_field(monster, 'name', '') or '')


def _canonical_card_name(card: Any) -> str:
    return canonical_card_name(card)

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


def _known_damage_upgrade_bonus(card: Any, card_name: str) -> int:
    upgrades = getattr(card, 'upgrades', 0) or 0
    if upgrades <= 0:
        return 0
    if card_name == 'Searing Blow':
        return upgrades * (upgrades + 7) // 2
    return DAMAGE_UPGRADE_BONUS.get(card_name, 0)

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

GUARDIAN_MODE_SHIFT_BLOCK = 20
GUARDIAN_SHARP_HIDE = 3


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
        monster_name = _canonical_live_monster_name(monster)
        # Check for summoners
        if game_data_loader.is_monster_summoner(monster_name):
            has_summoner = True

        # Check for phase change
        if game_data_loader.does_monster_have_phase_change(monster_name):
            has_phase_change = True

        # Check for hibernation
        if game_data_loader.is_monster_hibernating(monster_name, context.turn):
            has_hibernating = True

        # Check for death split
        if game_data_loader.does_monster_have_death_split(monster_name):
            has_death_split = True

        # Check for duo boss
        if game_data_loader.is_monster_duo_boss(monster_name):
            has_duo_boss = True

        # Get threat profile
        threat_profile = game_data_loader.get_monster_threat_profile(monster_name)
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
        monster_type = game_data_loader.get_monster_type(monster_name)
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
        self.turn = getattr(context, 'turn', 1)

        # Player state
        self.player_hp = context.game.current_hp
        self.player_max_hp = context.game.max_hp
        self.player_block = context.game.player.block if hasattr(context.game.player, 'block') else 0
        self.end_turn_block = self._get_player_power_amount(context, 'Metallicize')
        self.player_energy = context.energy_available
        self.player_strength = context.strength

        # Player debuffs (binary: >0 means debuffed)
        self.player_vulnerable = self._get_player_debuff_stacks(context, 'Vulnerable')
        self.player_vulnerable_added = 0
        self.player_weak = self._get_player_debuff_stacks(context, 'Weak')
        self.player_frail = self._get_player_debuff_stacks(context, 'Frail')
        self.player_hex = self._get_player_hex_stacks(context)
        # Rage power: block gained per attack played.
        self.rage_block_per_attack = self._get_player_power_amount(context, 'Rage')
        self.draw_blocked = (
            self._has_player_power(context, 'No Draw')
            or self._has_player_power(context, 'NoDraw')
        )
        self.double_tap_charges = 0
        self.corruption_active = self._has_player_power(context, 'Corruption')
        self.feel_no_pain_block_per_exhaust = self._get_player_power_amount(context, 'Feel No Pain')
        self.dark_embrace_draw_per_exhaust = self._get_player_power_amount(context, 'Dark Embrace')
        self.rupture_strength_per_hp_loss = self._get_player_power_amount(context, 'Rupture')
        if self.rupture_strength_per_hp_loss <= 0 and self._has_player_power(context, 'Rupture'):
            self.rupture_strength_per_hp_loss = 1
        self.end_turn_aoe_damage = self._get_player_power_amount(context, 'Combust')
        if self.end_turn_aoe_damage <= 0 and self._has_player_power(context, 'Combust'):
            self.end_turn_aoe_damage = 5
        self.end_turn_hp_loss = 1 if self.end_turn_aoe_damage > 0 else 0

        # Monster state (each monster tracked independently)
        self.monsters = []
        for i, monster in enumerate(context.monsters_alive):
            mode_shift = (
                self._get_monster_power_amount(monster, 'Mode Shift')
                or self._get_monster_power_amount(monster, 'ModeShift')
            )
            monster_state = {
                'monster_id': getattr(monster, 'monster_id', ''),
                'name': monster.name,
                'hp': monster.current_hp,
                'max_hp': monster.max_hp,
                'block': monster.block if hasattr(monster, 'block') else 0,
                'intent': monster.intent if hasattr(monster, 'intent') else None,
                'move_id': getattr(monster, 'move_id', None),
                'is_gone': monster.is_gone,
                'half_dead': monster.half_dead,
                'vulnerable': context.vulnerable_stacks.get(i, 0),  # Vulnerable stacks (by index)
                'weak': context.weak_stacks.get(i, 0),  # Weak stacks (by index)
                'frail': context.frail_stacks.get(i, 0),  # Frail stacks (by index)
                'thorns': context.thorns_stacks.get(i, 0),  # Thorns/反伤 stacks (by index)
                'artifact': self._get_monster_power_amount(monster, 'Artifact'),
                'move_base_damage': monster.move_base_damage if hasattr(monster, 'move_base_damage') else 0,
                'move_adjusted_damage': monster.move_adjusted_damage if hasattr(monster, 'move_adjusted_damage') else 0,
                'move_hits': monster.move_hits if hasattr(monster, 'move_hits') else 1,
                'strength': monster.strength if hasattr(monster, 'strength') else 0,
                'skill_strength_gain': self._get_monster_skill_strength_gain(monster),
                'mode_shift': mode_shift,
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
        self.status_cards_added = 0  # Future draw-pile/discard pollution
        self.dazed_cards_added = 0  # Chosen Hex / Sentries / Reckless Charge-style pollution
        self.hex_non_attack_triggers = 0

    def _get_player_debuff_stacks(self, context: DecisionContext, power_name: str) -> int:
        """Get debuff stacks on the player from powers."""
        if not hasattr(context.game, 'player') or not hasattr(context.game.player, 'powers'):
            return 0

        for power in context.game.player.powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 1
        return 0

    def _get_player_power_amount(self, context: DecisionContext, power_name: str) -> int:
        """Get power amount on the player from powers."""
        if not hasattr(context.game, 'player') or not hasattr(context.game.player, 'powers'):
            return 0

        for power in context.game.player.powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 0
        return 0

    def _has_player_power(self, context: DecisionContext, power_name: str) -> bool:
        if not hasattr(context.game, 'player') or not hasattr(context.game.player, 'powers'):
            return False
        return any(self._power_name(power) == power_name for power in context.game.player.powers)

    def _get_player_hex_stacks(self, context: DecisionContext) -> int:
        """Hex is a persistent Chosen debuff; amount may be -1 in game state."""
        hex_stacks = self._get_player_debuff_stacks(context, 'Hex')
        if self._has_player_power(context, 'Hex') and hex_stacks <= 0:
            return 1
        return max(0, hex_stacks)

    def _get_monster_power_amount(self, monster: Any, power_name: str) -> int:
        if not hasattr(monster, 'powers'):
            return 0

        for power in monster.powers:
            if self._power_name(power) == power_name:
                amount = getattr(power, 'amount', None)
                return amount if amount is not None else 1
        return 0

    def _get_monster_skill_strength_gain(self, monster: Any) -> int:
        """Return Strength a monster gains whenever the player plays a Skill."""
        for power in getattr(monster, 'powers', []) or []:
            power_name = str(self._power_name(power) or '').lower()
            if power_name in {'anger', 'angry', 'enrage'}:
                amount = getattr(power, 'amount', None)
                return max(0, int(amount)) if amount is not None else 2

        monster_id = str(getattr(monster, 'monster_id', ''))
        monster_name = str(getattr(monster, 'name', ''))
        if monster_id in {'GremlinNob', 'Gremlin Nob'} or monster_name == 'Gremlin Nob':
            return 2
        return 0

    def _power_name(self, power: Any) -> Optional[str]:
        return (
            getattr(power, 'name', None)
            or getattr(power, 'power_name', None)
            or getattr(power, 'power_id', None)
        )

    def clone(self) -> 'SimulationState':
        """Create a deep copy of this state."""
        new_state = SimulationState.__new__(SimulationState)
        new_state.turn = self.turn
        new_state.player_hp = self.player_hp
        new_state.player_max_hp = self.player_max_hp
        new_state.player_block = self.player_block
        new_state.end_turn_block = self.end_turn_block
        new_state.player_energy = self.player_energy
        new_state.player_strength = self.player_strength
        new_state.player_vulnerable = self.player_vulnerable
        new_state.player_vulnerable_added = self.player_vulnerable_added
        new_state.player_weak = self.player_weak
        new_state.player_frail = self.player_frail
        new_state.player_hex = self.player_hex
        new_state.rage_block_per_attack = self.rage_block_per_attack
        new_state.draw_blocked = self.draw_blocked
        new_state.double_tap_charges = self.double_tap_charges
        new_state.corruption_active = self.corruption_active
        new_state.feel_no_pain_block_per_exhaust = self.feel_no_pain_block_per_exhaust
        new_state.dark_embrace_draw_per_exhaust = self.dark_embrace_draw_per_exhaust
        new_state.rupture_strength_per_hp_loss = self.rupture_strength_per_hp_loss
        new_state.end_turn_aoe_damage = self.end_turn_aoe_damage
        new_state.end_turn_hp_loss = self.end_turn_hp_loss
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
        new_state.status_cards_added = self.status_cards_added
        new_state.dazed_cards_added = self.dazed_cards_added
        new_state.hex_non_attack_triggers = self.hex_non_attack_triggers
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
            self.end_turn_block,
            self.player_energy,
            self.player_strength,
            self.player_vulnerable,
            self.player_vulnerable_added,
            self.player_weak,
            self.player_frail,
            self.player_hex,
            self.rage_block_per_attack,
            self.draw_blocked,
            self.double_tap_charges,
            self.corruption_active,
            self.feel_no_pain_block_per_exhaust,
            self.dark_embrace_draw_per_exhaust,
            self.rupture_strength_per_hp_loss,
            self.end_turn_aoe_damage,
            self.end_turn_hp_loss,
            self.status_cards_added,
            self.dazed_cards_added,
            self.hex_non_attack_triggers,
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
                m.get('thorns', 0),
                m.get('mode_shift', 0),
                m.get('artifact', 0),
                m.get('strength', 0),
                m.get('skill_strength_gain', 0),
                str(m['intent']) if m['intent'] else None,  # Convert intent to string
                m.get('move_id', None),
                m['is_gone'],
                m.get('monster_id', ''),
                m['name']  # Include name for elite/boss identification
            )
            for m in self.monsters
            if not m['is_gone']  # Only include alive monsters
        ))

        # Hand cards (multi-set - sorted list of card IDs)
        # This represents what cards are available to play
        hand_key = tuple(sorted(
            c.card_id for c in playable_cards
            if id(c) not in self.played_card_uuids
            and (not getattr(c, 'uuid', None) or c.uuid not in self.played_card_uuids)
        ))

        return (player_key, monster_key, hand_key)

    def turn_block(self) -> int:
        """Block available by the time enemies attack this turn."""
        return self.player_block + self.end_turn_block


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
        card_type = card.type if hasattr(card, 'type') else None

        # Use actual cost (for Snecko Eye and other cost modifiers). X-cost
        # cards arrive as -1, but planning should spend all current energy.
        raw_cost = raw_card_cost(card)
        cost = effective_card_cost(card, new_state.player_energy)
        if card_type == CardType.SKILL and new_state.corruption_active:
            cost = 0
        base_cost = raw_cost if raw_cost >= 0 else cost
        x_energy_spent = cost if is_x_cost_card(card) else None

        # Track energy saved (for Corruption, etc.)
        energy_saved = base_cost - cost
        if energy_saved > 0:
            new_state.energy_saved += energy_saved

        new_state.player_energy -= cost
        new_state.energy_spent += cost
        starting_exhaust_events = new_state.exhaust_events

        # Check special monster abilities before applying card effects
        for i, monster in enumerate(new_state.monsters):
            if not monster['is_gone']:
                self._handle_death_split(new_state, monster, i)
                self._handle_summoner(new_state, monster)
                self._handle_phase_change(new_state, monster)
                self._handle_hibernation(new_state, monster)

        # Apply card effects based on type
        resolved_target_index = self._resolve_target_index(target, target_index, context)

        if card_type == CardType.ATTACK:
            attack_repeats = 1
            if new_state.double_tap_charges > 0:
                attack_repeats = 2
                new_state.double_tap_charges -= 1
            for _ in range(attack_repeats):
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
                self._apply_self_damage(new_state, card)
        elif card_type == CardType.SKILL:
            new_state.skills_played += 1
            corruption_exhausts_skill = new_state.corruption_active
            self._apply_skill(new_state, card, context, resolved_target_index)
            self._apply_skill_reactive_monster_powers(new_state)
            if corruption_exhausts_skill and not self._skill_exhausts_itself(card):
                new_state.exhaust_events += 1
        elif card_type == CardType.POWER:
            self._apply_power(new_state, card)

        self._apply_hex_card_pollution(new_state, card_type)

        if card_type != CardType.ATTACK:
            self._apply_self_damage(new_state, card)

        self._apply_feel_no_pain_block(new_state, starting_exhaust_events)
        self._apply_dark_embrace_draw(new_state, starting_exhaust_events)

        return new_state

    def _apply_skill_reactive_monster_powers(self, state: SimulationState):
        """Apply monster reactions such as Gremlin Nob's Anger after Skill cards."""
        for monster in state.monsters:
            if monster.get('is_gone'):
                continue

            strength_gain = int(monster.get('skill_strength_gain', 0) or 0)
            if strength_gain <= 0:
                continue

            monster['strength'] = monster.get('strength', 0) + strength_gain
            logger.debug(
                "[SKILL_REACTION] %s gained %s Strength from Skill",
                monster.get('name', 'Unknown'),
                strength_gain,
            )

    def _apply_hex_card_pollution(self, state: SimulationState, card_type: Optional[CardType]):
        """Chosen's Hex adds Dazed to the draw pile whenever a non-Attack is played."""
        if getattr(state, 'player_hex', 0) <= 0:
            return
        if card_type is None or card_type == CardType.ATTACK:
            return

        dazed_added = max(1, int(state.player_hex))
        state.dazed_cards_added += dazed_added
        state.status_cards_added += dazed_added
        state.hex_non_attack_triggers += 1

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
        card_name = _canonical_card_name(card)
        dynamic_damage_card = card_name in {'Body Slam', 'Whirlwind'}
        base_damage = getattr(card, 'damage', 0)
        if base_damage is None:
            base_damage = 0
        if dynamic_damage_card:
            base_damage = 0
        if base_damage == 0 or not hasattr(card, 'damage'):
            # Use game data for more accurate damage estimation
            card_data = game_data_loader.get_card_data(card_name)
            if card_data and not dynamic_damage_card:
                parsed_damage = game_data_loader._parse_card_damage(card_data)
                base_damage = parsed_damage if parsed_damage is not None else 0

                # Apply upgrade bonus if card is upgraded
                upgrades = getattr(card, 'upgrades', 0)
                if upgrades > 0 and base_damage:
                    # Check if we have a known upgrade bonus for this card
                    if card_name in DAMAGE_UPGRADE_BONUS:
                        # Use known bonus
                        upgrade_bonus = _known_damage_upgrade_bonus(card, card_name)
                        base_damage += upgrade_bonus
                        logger.debug(f"[DAMAGE_UPGRADE] {card.card_id} (upgrades={upgrades}): {base_damage} damage (+{upgrade_bonus})")
                    else:
                        logger.debug(
                            f"[DAMAGE_UPGRADE_UNKNOWN] {card.card_id} "
                            f"(upgrades={upgrades}): {base_damage} damage "
                            "(no generic upgrade bonus)"
                        )

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

            if base_damage == 0 and not dynamic_damage_card:
                base_damage = 6  # Fallback estimate for truly unknown cards

        # Handle AOE attacks
        card_data = game_data_loader.get_card_data(card_name)
        is_aoe = False
        if card_data:
            is_aoe = game_data_loader._is_card_aoe(card_data)
        # Also check known AOE cards by name
        if card_name in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']:
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
                    damage = self._apply_weak_damage(damage, getattr(state, 'player_weak', 0))
                    damage = self._apply_vulnerable_damage(damage, monster)
                    self._deal_damage_to_monster(state, monster, damage)
                    state.damage_instances += 1  # Track each damage instance
            if card_data:
                description = self._get_card_effect_text(card_name, card_data)
                upgraded = getattr(card, 'upgrades', 0) > 0
                debuff_effects = self._description_debuff_effects(description, upgraded, card_name)
                if debuff_effects:
                    for monster in state.monsters:
                        if monster['is_gone']:
                            continue
                        self._apply_monster_debuffs(monster, debuff_effects)
        elif self._is_random_target_attack(card) and target_index is None:
            for hit_index in range(hit_count):
                alive_monsters = [monster for monster in state.monsters if not monster['is_gone']]
                if not alive_monsters:
                    break
                monster = alive_monsters[hit_index % len(alive_monsters)]
                damage = self._calculate_attack_damage(card, base_damage, state, context)
                damage = self._apply_weak_damage(damage, getattr(state, 'player_weak', 0))
                damage = self._apply_vulnerable_damage(damage, monster)
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
                        damage = self._apply_weak_damage(damage, getattr(state, 'player_weak', 0))
                        damage = self._apply_vulnerable_damage(damage, monster)
                        self._deal_damage_to_monster(state, monster, damage)
                        state.damage_instances += 1  # Track damage instance

                    # Check for card effects using game data
                    if card_data:
                        description = self._get_card_effect_text(card_name, card_data)
                        upgraded = getattr(card, 'upgrades', 0) > 0
                        self._apply_monster_debuffs(
                            monster,
                            self._description_debuff_effects(description, upgraded, card_name),
                        )

        self._apply_attack_healing(state, card, starting_total_damage)
        self._apply_attack_resource_effects(state, card, target_index)
        self._apply_attack_draw_effects(state, card, card_data)
        self._apply_attack_block_effects(state, card, card_data)
        self._apply_attack_exhaust_effects(state, card, context, card_data)

    def _get_attack_hit_count(
        self,
        card: Card,
        state: SimulationState,
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Return known static hit counts for repeated-hit Ironclad attacks."""
        card_name = _canonical_card_name(card)
        upgrades = getattr(card, 'upgrades', 0)

        if card_name == 'Twin Strike':
            return 2
        if card_name == 'Sword Boomerang':
            return 4 if upgrades > 0 else 3
        if card_name == 'Pummel':
            return 5 if upgrades > 0 else 4
        if card_name == 'Fiend Fire' and context is not None:
            return len(self._unplayed_hand_cards(state, context, exclude_card=card))

        return 1

    def _is_random_target_attack(self, card: Card) -> bool:
        card_name = _canonical_card_name(card)
        return card_name in {'Sword Boomerang'}

    def _apply_attack_healing(self, state: SimulationState, card: Card, starting_total_damage: int):
        card_name = _canonical_card_name(card)
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
        card_name = _canonical_card_name(card)
        if card_name != 'Dropkick':
            return
        if target_index is None or not (0 <= target_index < len(state.monsters)):
            return
        if state.monsters[target_index].get('vulnerable', 0) <= 0:
            return

        state.player_energy += 1
        state.energy_gained += 1
        self._add_card_draw(state, 1)

    def _apply_attack_draw_effects(
        self,
        state: SimulationState,
        card: Card,
        card_data: Optional[Dict[str, Any]],
    ):
        if not card_data:
            return

        card_name = _canonical_card_name(card)
        if card_name == 'Dropkick':
            return
        description = self._get_card_effect_text(card_name, card_data)
        if 'draw' not in description:
            return

        upgraded = getattr(card, 'upgrades', 0) > 0
        self._add_card_draw(state, self._extract_draw_count(description, upgraded))

    def _apply_attack_block_effects(
        self,
        state: SimulationState,
        card: Card,
        card_data: Optional[Dict[str, Any]],
    ):
        card_name = _canonical_card_name(card)
        if card_name != 'Iron Wave':
            return

        block_gain = None
        if card_data:
            block_gain = game_data_loader._parse_card_block(card_data)
        if block_gain is None:
            block_gain = 5

        upgrades = getattr(card, 'upgrades', 0)
        if upgrades > 0:
            block_gain += BLOCK_UPGRADE_BONUS.get(card_name, 2)

        state.player_block += self._apply_frail_block(block_gain, state.player_frail)

    def _apply_attack_exhaust_effects(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext],
        card_data: Optional[Dict[str, Any]],
    ):
        """Track attack-card exhaust events so exhaust synergies can score correctly."""
        card_name = _canonical_card_name(card)

        if card_name == 'Fiend Fire' and context is not None:
            exhausted_cards = self._unplayed_hand_cards(state, context, exclude_card=card)
            state.exhaust_events += len(exhausted_cards)
            self._mark_cards_unavailable(state, exhausted_cards)
            self._apply_sentinel_exhaust_energy(state, exhausted_cards)
        elif card_name == 'Sever Soul' and context is not None:
            exhausted_cards = [
                hand_card
                for hand_card in self._unplayed_hand_cards(state, context, exclude_card=card)
                if getattr(hand_card, 'type', None) != CardType.ATTACK
            ]
            state.exhaust_events += len(exhausted_cards)
            self._mark_cards_unavailable(state, exhausted_cards)
            self._apply_sentinel_exhaust_energy(state, exhausted_cards)

        if card_data:
            description = self._get_card_effect_text(card_name, card_data)
            if self._card_exhausts_itself(description, getattr(card, 'upgrades', 0) > 0):
                state.exhaust_events += 1

    def _apply_sentinel_exhaust_energy(self, state: SimulationState, exhausted_cards: List[Card]):
        energy_gain = 0
        for exhausted_card in exhausted_cards:
            card_name = _canonical_card_name(exhausted_card)
            if card_name != 'Sentinel':
                continue

            energy_gain += 3 if getattr(exhausted_card, 'upgrades', 0) > 0 else 2

        if energy_gain <= 0:
            return

        state.player_energy += energy_gain
        state.energy_gained += energy_gain

    def _unplayed_hand_cards(
        self,
        state: SimulationState,
        context: DecisionContext,
        exclude_card: Optional[Card] = None,
    ) -> List[Card]:
        hand_cards = getattr(getattr(context, 'game', None), 'hand', None)
        if not hand_cards:
            hand_cards = getattr(context, 'playable_cards', [])

        cards = []
        exclude_key = self._card_identity(exclude_card) if exclude_card is not None else None
        for hand_card in hand_cards:
            card_key = self._card_identity(hand_card)
            if hand_card is exclude_card or (exclude_key is not None and card_key == exclude_key):
                continue
            if card_key in state.played_card_uuids or id(hand_card) in state.played_card_uuids:
                continue
            cards.append(hand_card)
        return cards

    @staticmethod
    def _card_identity(card: Optional[Card]):
        if card is None:
            return None
        return getattr(card, 'uuid', None) or id(card)

    def _mark_cards_unavailable(self, state: SimulationState, cards: List[Card]):
        for card in cards:
            card_key = self._card_identity(card)
            if card_key is not None:
                state.played_card_uuids.add(card_key)
            state.played_card_uuids.add(id(card))

    def _effect_text_for_upgrade(self, description: str, upgraded: bool) -> str:
        text = (description or '').replace('\\n', '\n')

        def select_upgrade_value(match):
            return match.group(2 if upgraded else 1)

        text = re.sub(r'\[([^\[\]|]*)\|([^\[\]]*)\]', select_upgrade_value, text)
        text = re.sub(
            r'\[([^\[\]|]*)\|',
            lambda match: '' if upgraded else match.group(1),
            text,
        )
        return text

    def _card_exhausts_itself(self, description: str, upgraded: bool = False) -> bool:
        description = self._effect_text_for_upgrade(description, upgraded)
        description = (description or '').lower().replace('#', '')
        if any(line.strip() in {'exhaust', 'exhaust.'} for line in description.splitlines()):
            return True
        return bool(re.search(r'\bexhaust\.\s*$', description))

    def _skill_exhaust_events_from_description(self, description: str, upgraded: bool = False) -> int:
        description = self._effect_text_for_upgrade(description, upgraded)
        description = (description or '').lower().replace('#', '')
        if not description:
            return 0
        if self._card_exhausts_itself(description):
            return 1
        if re.search(r'\bexhaust\s+\d+\s+cards?\b', description):
            return 1
        return 0

    def _skill_exhausts_itself(self, card: Card) -> bool:
        card_name = _canonical_card_name(card)
        card_data = game_data_loader.get_card_data(card_name)
        if not card_data:
            return False
        return self._card_exhausts_itself(
            self._get_card_effect_text(card_name, card_data),
            getattr(card, 'upgrades', 0) > 0,
        )

    def _calculate_attack_damage(
        self,
        card: Card,
        base_damage: int,
        state: SimulationState,
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Apply Strength, including cards with non-standard Strength scaling."""
        card_name = _canonical_card_name(card)

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

    def _apply_player_vulnerable_damage(
        self,
        damage: int,
        player_vulnerable: int,
        hit_count: int = 1,
    ) -> int:
        """Apply player Vulnerable using the game's per-hit rounding."""
        if player_vulnerable > 0:
            if hit_count > 1:
                per_hit_damage, remainder = divmod(damage, hit_count)
                if remainder == 0:
                    return int(per_hit_damage * 1.5) * hit_count
            return int(damage * 1.5)
        return damage

    def _apply_weak_damage(self, damage: int, player_weak: int) -> int:
        """Apply weak multiplier (0.75x). Binary: any weak stacks = 0.75x damage."""
        if player_weak > 0:
            return int(damage * 0.75)
        return damage

    def _consume_monster_artifact(self, monster: dict) -> bool:
        artifact = monster.get('artifact', 0)
        if artifact <= 0:
            return False
        monster['artifact'] = artifact - 1
        return True

    def _apply_monster_debuff(self, monster: dict, debuff: str, stacks: int):
        if stacks <= 0:
            return
        if self._consume_monster_artifact(monster):
            return
        monster[debuff] = monster.get(debuff, 0) + stacks

    def _description_debuff_effects(
        self,
        description: str,
        upgraded: bool,
        card_name: str = '',
    ) -> List[Tuple[int, str, int]]:
        effects = []
        for debuff in ('weak', 'vulnerable'):
            if debuff not in description:
                continue
            stacks = self._extract_debuff_stacks(description, debuff, upgraded)
            if stacks is None and card_name == 'Shockwave':
                stacks = 5 if upgraded else 3
            if not stacks:
                continue
            position = description.find(debuff)
            effects.append((position if position >= 0 else 9999, debuff, stacks))
        if 'strength down' in description:
            stacks = self._extract_debuff_stacks(description, 'strength down', upgraded)
            if stacks is None and card_name == 'Shockwave':
                stacks = 5 if upgraded else 3
            if stacks:
                position = description.find('strength down')
                effects.append((position if position >= 0 else 9999, 'strength_down', stacks))
        effects.sort(key=lambda effect: effect[0])
        return effects

    def _apply_monster_strength_down(self, monster: dict, stacks: int):
        if stacks <= 0:
            return
        if self._consume_monster_artifact(monster):
            return

        monster['strength'] = monster.get('strength', 0) - stacks
        if self._monster_intends_attack(monster):
            monster['move_adjusted_damage'] = max(
                0,
                monster.get('move_adjusted_damage', 0) - stacks,
            )

    def _apply_monster_debuffs(self, monster: dict, effects: List[Tuple[int, str, int]]):
        for _, debuff, stacks in effects:
            if debuff == 'strength_down':
                self._apply_monster_strength_down(monster, stacks)
            else:
                self._apply_monster_debuff(monster, debuff, stacks)

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

    def _extract_draw_count(self, description: str, upgraded: bool) -> int:
        """Extract card draw count, including wiki [base|upgraded] notation."""
        effect_text = self._effect_text_for_upgrade(description, upgraded).lower()
        draw_match = re.search(r'draw\s+(\d+)\s+cards?', effect_text)
        if draw_match:
            return int(draw_match.group(1))

        return 0

    def _add_card_draw(self, state: SimulationState, count: int):
        if count <= 0 or state.draw_blocked:
            return
        state.cards_drawn += count

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

    def _apply_monster_strength_to_per_hit_damage(self, damage: int, strength: int) -> int:
        """Apply monster Strength or Strength Down to one hit of enemy damage."""
        if strength == 0:
            return damage
        return max(0, damage + strength)

    def _apply_monster_weak_to_per_hit_damage(self, damage: int, monster_weak: int) -> int:
        """Apply monster Weak to one hit of enemy damage."""
        if monster_weak <= 0:
            return damage
        return int(damage * 0.75)

    def _decrement_monster_turn_debuffs(self, state: SimulationState):
        for monster in state.monsters:
            if monster.get('is_gone'):
                continue
            for debuff in ('weak', 'vulnerable', 'frail'):
                if monster.get(debuff, 0) > 0:
                    monster[debuff] = max(0, monster[debuff] - 1)

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

    def _extract_move_strength_gain(self, move: Dict[str, Any]) -> int:
        """Extract monster Strength gained by a predicted move."""
        value = move.get('strength_gain', 0)
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return max(0, int(value))
        if isinstance(value, dict):
            numeric_values = [
                int(v) for v in value.values()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            return max(numeric_values, default=0)
        return 0

    def _extract_move_status_cards(self, move: Dict[str, Any]) -> Dict[str, int]:
        """Extract status cards added by a monster move from wiki data fields."""
        def _get_count(*keys: str) -> int:
            for key in keys:
                value = move.get(key, 0)
                if isinstance(value, bool):
                    return 1 if value else 0
                if isinstance(value, (int, float)):
                    return int(value)
            return 0

        def _parse_effect_count(card_name: str) -> int:
            effect = str(move.get('effect') or move.get('description') or '')
            if not effect:
                return 0

            match = re.search(rf'\b(\d+)\s+{re.escape(card_name)}s?\b', effect, re.IGNORECASE)
            if match:
                return int(match.group(1))

            if re.search(rf'\b(?:a|an)\s+{re.escape(card_name)}\b', effect, re.IGNORECASE):
                return 1
            return 0

        dazed = _get_count('dazed', 'dazed_count', 'dazed_added')
        burn = _get_count('burn', 'burn_count', 'burn_added')
        slimed = _get_count('slimed', 'slimed_count', 'slimed_added')
        wound = _get_count('wound', 'wounds', 'wound_count', 'wound_added')
        if dazed == 0:
            dazed = _parse_effect_count('Dazed')
        if burn == 0:
            burn = _parse_effect_count('Burn')
        if slimed == 0:
            slimed = _parse_effect_count('Slimed')
        if wound == 0:
            wound = _parse_effect_count('Wound')
        total = dazed + burn + slimed + wound
        return {
            'total': total,
            'dazed': dazed,
            'burn': burn,
            'slimed': slimed,
            'wound': wound,
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
        card_name = _canonical_card_name(card)

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

    def _deal_damage_to_monster(
        self,
        state: SimulationState,
        monster: dict,
        damage: int,
        trigger_thorns: bool = True,
    ):
        """Deal damage to monster, accounting for block and thorns."""
        # Damage block first
        block_damage = min(damage, monster['block'])
        monster['block'] -= block_damage

        # Remaining damage to HP
        hp_damage = min(max(0, damage - block_damage), max(0, monster['hp']))
        monster['hp'] -= hp_damage
        state.total_damage_dealt += hp_damage

        if trigger_thorns and damage > 0:
            # Apply thorns/Sharp Hide as fixed damage per attack hit.
            thorns = monster.get('thorns', 0)
            if thorns > 0:
                state.player_hp = max(0, state.player_hp - thorns)

        if trigger_thorns and hp_damage > 0 and monster['hp'] > 0:
            self._apply_guardian_mode_shift(monster, hp_damage)

        # Check if killed
        if monster['hp'] <= 0:
            self._apply_monster_death_effects(state, monster)
            monster['is_gone'] = True
            state.monsters_killed += 1

    def _apply_guardian_mode_shift(self, monster: dict, hp_damage: int):
        """Apply The Guardian's Mode Shift transition after attack HP damage."""
        if not self._is_guardian(monster):
            return

        mode_shift = monster.get('mode_shift', 0)
        if mode_shift <= 0:
            return

        mode_shift = max(0, mode_shift - hp_damage)
        monster['mode_shift'] = mode_shift
        if mode_shift == 0:
            monster['block'] += GUARDIAN_MODE_SHIFT_BLOCK
            monster['thorns'] = max(monster.get('thorns', 0), GUARDIAN_SHARP_HIDE)

    def _is_guardian(self, monster: dict) -> bool:
        monster_id = str(monster.get('monster_id', ''))
        monster_name = str(monster.get('name', ''))
        return monster_id == 'TheGuardian' or monster_name == 'The Guardian'

    def _apply_monster_death_effects(self, state: SimulationState, monster: dict):
        """Apply deterministic monster death effects such as Fungi Beast spores."""
        if monster.get('death_effect_applied'):
            return
        monster['death_effect_applied'] = True

        monster_name = monster.get('name', '')
        if not monster_name:
            return

        try:
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        except Exception:
            monster_data = None
        if not monster_data:
            return

        mechanics = monster_data.get('special_mechanics', {}) or {}
        death_effect = mechanics.get('death_effect', {}) or {}
        effect_type = death_effect.get('type')
        if effect_type != 'apply_vulnerable':
            return

        amount = int(death_effect.get('amount', 0) or 0)
        if amount <= 0:
            return

        state.player_vulnerable += amount
        state.player_vulnerable_added += amount
        logger.debug(
            "[DEATH_EFFECT] %s applied %s Vulnerable to player",
            monster_name,
            amount,
        )

    def project_end_turn_effects(self, state: SimulationState) -> SimulationState:
        """Project deterministic end-of-turn effects before enemy attacks."""
        projected = state.clone()

        hp_loss = max(0, getattr(projected, 'end_turn_hp_loss', 0))
        if hp_loss > 0:
            projected.player_hp = max(0, projected.player_hp - hp_loss)
            if projected.rupture_strength_per_hp_loss > 0:
                projected.player_strength += projected.rupture_strength_per_hp_loss

        aoe_damage = max(0, getattr(projected, 'end_turn_aoe_damage', 0))
        if aoe_damage > 0:
            for monster in projected.monsters:
                if monster['is_gone']:
                    continue
                self._deal_damage_to_monster(
                    projected,
                    monster,
                    aoe_damage,
                    trigger_thorns=False,
                )

        projected.end_turn_aoe_damage = 0
        projected.end_turn_hp_loss = 0
        projected = self._materialize_pending_death_splits(projected)
        return projected

    def _apply_skill(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext] = None,
        target_index: Optional[int] = None,
    ):
        """Apply skill card effects."""
        if self._apply_block_multiplier_skill(state, card):
            return
        if self._apply_second_wind(state, card, context):
            return
        if self._apply_double_tap(state, card):
            return

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
                    card_name = _canonical_card_name(card)
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        block_data = dict(card_data)
                        upgrades = getattr(card, 'upgrades', 0)
                        block_data['name'] = f"{card_name}+" if upgrades > 0 else card_name
                        base_block = game_data_loader._parse_card_block(block_data)
                        if base_block and base_block > 0:
                            # Apply upgrade bonus if card is upgraded
                            if upgrades > 0:
                                base_data = dict(card_data)
                                base_data['name'] = card_name
                                unupgraded_block = game_data_loader._parse_card_block(base_data)
                                if unupgraded_block is not None and base_block != unupgraded_block:
                                    logger.debug(f"[BLOCK_UPGRADE_PARSED] {card.card_id} (upgrades={upgrades}): {base_block} block")
                                else:
                                    # Some upgrades (for example Armaments+) improve the non-block effect.
                                    # Only apply a manual bonus when the card is explicitly mapped.
                                    upgrade_bonus = BLOCK_UPGRADE_BONUS.get(card_name)
                                    if upgrade_bonus is not None:
                                        base_block += upgrade_bonus
                                        logger.debug(f"[BLOCK_UPGRADE] {card.card_id} (upgrades={upgrades}): {base_block} block (+{upgrade_bonus})")
                                    else:
                                        logger.debug(f"[BLOCK_UPGRADE_NO_BLOCK_CHANGE] {card.card_id} (upgrades={upgrades}): {base_block} block")
                            else:
                                logger.debug(f"[BLOCK_BASE] {card.card_id} (upgrades={upgrades}): {base_block} block")

                            block_gain = self._apply_frail_block(base_block, state.player_frail)
                            state.player_block += block_gain
                        else:
                            logger.debug(f"[BLOCK_NONE] No block found for {card.card_id}")
                    else:
                        logger.debug(f"[BLOCK_NODATA] No card data found for {card_name}")
        if _canonical_card_name(card) == 'Rage':
            rage_gain = 5 if getattr(card, 'upgrades', 0) > 0 else 3
            state.rage_block_per_attack += rage_gain

        self._apply_strength_skill(state, card, target_index)
        self._apply_energy_gain_skill(state, card)
        self._apply_enemy_strength_skill(state, card, target_index)

        # Apply enemy debuffs from skill cards (e.g., Shockwave).
        try:
            card_name = _canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = self._get_card_effect_text(card_name, card_data)
                has_debuff = 'vulnerable' in description or 'weak' in description
                if has_debuff:
                    upgrades = getattr(card, 'upgrades', 0) > 0
                    is_aoe = game_data_loader._is_card_aoe(card_data) or 'all enemies' in description
                    if is_aoe:
                        debuff_effects = self._description_debuff_effects(description, upgrades, card_name)
                        if debuff_effects:
                            for monster in state.monsters:
                                if monster['is_gone']:
                                    continue
                                self._apply_monster_debuffs(monster, debuff_effects)
        except Exception:
            pass

        # Track exhaust events (for Feel No Pain, etc.)
        try:
            card_name = _canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = self._get_card_effect_text(card_name, card_data)
                upgraded = getattr(card, 'upgrades', 0) > 0
                state.exhaust_events += self._skill_exhaust_events_from_description(
                    description,
                    upgraded,
                )
                # Track draw events
                if 'draw' in description:
                    self._add_card_draw(
                        state,
                        self._extract_draw_count(description, upgraded),
                    )
        except:
            pass

        if _canonical_card_name(card) == 'Battle Trance':
            state.draw_blocked = True

    def _apply_power(self, state: SimulationState, card: Card):
        """Apply power card effects."""
        card_id = _canonical_card_name(card)

        # Demon Form starts gaining Strength on future turns, not immediately.
        if card_id == 'Demon Form':
            pass

        # Berserk applies Vulnerable immediately and grants extra energy on future turns.
        elif card_id == 'Berserk':
            vulnerable = 1 if card.upgrades > 0 else 2
            state.player_vulnerable += vulnerable
            state.player_vulnerable_added += vulnerable
            state.energy_gained += 1

        # Inflame - adds strength
        elif card_id == 'Inflame':
            state.player_strength += 3 if card.upgrades > 0 else 2

        # Corruption - skills cost 0 (track for synergy evaluation)
        elif card_id == 'Corruption':
            state.corruption_active = True

        # Feel No Pain - gain block when cards exhaust
        elif card_id == 'Feel No Pain':
            state.feel_no_pain_block_per_exhaust = 4 if card.upgrades > 0 else 3

        # Dark Embrace - draw when cards exhaust
        elif card_id == 'Dark Embrace':
            state.dark_embrace_draw_per_exhaust = 1

        # Metallicize - end-turn block applies before enemies attack, but not immediately.
        elif card_id == 'Metallicize':
            state.end_turn_block += 4 if card.upgrades > 0 else 3

        # Rupture - card HP loss grants Strength once per HP-loss event.
        elif card_id == 'Rupture':
            state.rupture_strength_per_hp_loss += 2 if card.upgrades > 0 else 1

        # Combust - end-turn HP loss and AOE damage happen before enemies attack.
        elif card_id == 'Combust':
            state.end_turn_hp_loss += 1
            state.end_turn_aoe_damage += 7 if card.upgrades > 0 else 5

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

    def _apply_feel_no_pain_block(self, state: SimulationState, starting_exhaust_events: int):
        exhaust_delta = state.exhaust_events - starting_exhaust_events
        if exhaust_delta <= 0 or state.feel_no_pain_block_per_exhaust <= 0:
            return

        block_gain = exhaust_delta * state.feel_no_pain_block_per_exhaust
        state.player_block += self._apply_frail_block(block_gain, state.player_frail)

    def _apply_dark_embrace_draw(self, state: SimulationState, starting_exhaust_events: int):
        exhaust_delta = state.exhaust_events - starting_exhaust_events
        if exhaust_delta <= 0 or state.dark_embrace_draw_per_exhaust <= 0:
            return

        self._add_card_draw(state, exhaust_delta * state.dark_embrace_draw_per_exhaust)

    def _apply_strength_skill(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int] = None,
    ):
        """Apply immediate Strength-changing Ironclad skills."""
        card_id = _canonical_card_name(card)
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
        card_id = _canonical_card_name(card)
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

    def _apply_second_wind(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext],
    ) -> bool:
        card_id = _canonical_card_name(card)
        if card_id != 'Second Wind':
            return False
        if context is None:
            return False

        exhausted_cards = [
            hand_card
            for hand_card in self._unplayed_hand_cards(state, context, exclude_card=card)
            if getattr(hand_card, 'type', None) != CardType.ATTACK
        ]
        exhausted_count = len(exhausted_cards)
        if exhausted_count <= 0:
            return True

        block_per_card = 7 if getattr(card, 'upgrades', 0) > 0 else 5
        block_gain = self._apply_frail_block(block_per_card * exhausted_count, state.player_frail)
        state.player_block += block_gain
        state.exhaust_events += exhausted_count
        self._mark_cards_unavailable(state, exhausted_cards)
        self._apply_sentinel_exhaust_energy(state, exhausted_cards)
        return True

    def _apply_double_tap(self, state: SimulationState, card: Card) -> bool:
        card_id = _canonical_card_name(card)
        if card_id != 'Double Tap':
            return False

        state.double_tap_charges += 2 if getattr(card, 'upgrades', 0) > 0 else 1
        return True

    def _apply_block_multiplier_skill(self, state: SimulationState, card: Card) -> bool:
        card_id = _canonical_card_name(card)
        if card_id != 'Entrench':
            return False

        state.player_block *= 2
        return True

    def _apply_enemy_strength_skill(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int],
    ):
        card_id = _canonical_card_name(card)
        if card_id != 'Disarm':
            return
        if target_index is None or not (0 <= target_index < len(state.monsters)):
            return

        monster = state.monsters[target_index]
        if monster['is_gone']:
            return

        if self._consume_monster_artifact(monster):
            return

        strength_loss = 3 if getattr(card, 'upgrades', 0) > 0 else 2
        monster['strength'] = monster.get('strength', 0) - strength_loss
        if self._monster_intends_attack(monster):
            monster['move_adjusted_damage'] = max(
                0,
                monster.get('move_adjusted_damage', 0) - strength_loss,
            )

    def _apply_rage_block(self, state: SimulationState):
        """Apply Rage block trigger after playing an attack."""
        if state.rage_block_per_attack <= 0:
            return
        block_gain = self._apply_frail_block(state.rage_block_per_attack, state.player_frail)
        state.player_block += block_gain

    def _apply_self_damage(self, state: SimulationState, card: Card):
        """Apply HP costs for cards that damage the player to fuel effects."""
        try:
            card_name = _canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if not card_data:
                return

            description = card_data.get('description', '') or ''
            normalized_description = description.lower()
            if (
                'at the end of your turn' in normalized_description
                or 'at the start of your turn' in normalized_description
            ):
                return
            match = re.search(r'lose (\d+) hp', normalized_description)
            if not match:
                return

            hp_loss = int(match.group(1))
            if hp_loss <= 0:
                return

            state.player_hp = max(0, state.player_hp - hp_loss)
            if state.rupture_strength_per_hp_loss > 0:
                state.player_strength += state.rupture_strength_per_hp_loss
        except Exception:
            pass

    @staticmethod
    def _positive_monster_hits(monster: dict) -> int:
        try:
            return max(1, int(monster.get('move_hits', 1) or 1))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _is_live_monster_state(monster: dict) -> bool:
        return (
            not monster.get('is_gone', False)
            and monster.get('hp', monster.get('current_hp', 1)) > 0
        )

    def _estimate_incoming_damage(
        self,
        monsters_state: list,
        player_vulnerable_added: int = 0,
    ) -> int:
        """
        Estimate expected incoming damage from monsters next turn.

        Args:
            monsters_state: List of monster state dictionaries
            player_vulnerable_added: Vulnerable stacks newly applied during simulation.
                Current game intent damage already includes pre-existing player Vulnerable.

        Returns:
            Expected total damage
        """
        total_damage = 0
        debug_entries = []
        intent_present = False
        attack_intent_present = False

        for monster in monsters_state:
            monster_hp = monster.get('hp', monster.get('current_hp', 1))
            if monster.get('is_gone', False) or monster_hp <= 0:
                skip_reason = "gone" if monster.get('is_gone', False) else "dead"
                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    f"skip={skip_reason}"
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
                raw_damage = monster.get('move_adjusted_damage', 0)
                damage = max(0, raw_damage) if isinstance(raw_damage, (int, float)) else 0
                hits = self._positive_monster_hits(monster)
                damage_source = "adjusted"
                should_use_damage_fallback = raw_damage is None or raw_damage == 0

                # Fallback to base_damage if adjusted_damage not available
                if should_use_damage_fallback:
                    damage = monster.get('move_base_damage', 0)
                    if damage > 0:
                        damage_source = "base"
                        logger.debug(f"[DAMAGE_FALLBACK] Monster '{monster.get('name', 'Unknown')}' using base_damage={damage}")

                # If still no damage data, use conservative estimate based on monster
                if should_use_damage_fallback and damage == 0:
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

                # Adjust per-hit damage for monster Strength, including Strength Down.
                strength = monster.get('strength', 0)
                adjusted_damage = self._apply_monster_strength_to_per_hit_damage(damage, strength)
                if adjusted_damage != damage:
                    logger.debug(
                        f"[DAMAGE_FALLBACK] Monster '{monster.get('name', 'Unknown')}' has Strength {strength}, "
                        f"damage: {damage} -> {adjusted_damage}"
                    )
                    damage = adjusted_damage
                damage = self._apply_monster_weak_to_per_hit_damage(
                    damage,
                    monster.get('weak', 0),
                )

                total = damage * hits
                if player_vulnerable_added > 0:
                    total = self._apply_player_vulnerable_damage(
                        total,
                        player_vulnerable_added,
                        hits,
                    )

                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    f"intent={intent_str} damage={damage} hits={hits} source={damage_source}"
                )
                total_damage += total
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

            if self._needs_multi_turn_enemy_lookahead(state, context):
                return max_depth

            if monsters_alive <= 1 and playable_cards <= 3:
                return 1

            return max_depth
        except Exception:
            return max_depth

    def _needs_multi_turn_enemy_lookahead(
        self,
        state: SimulationState,
        context: DecisionContext,
    ) -> bool:
        current_turn = getattr(context, 'turn', 1)
        for monster in state.monsters:
            if monster.get('is_gone'):
                continue

            current_move = self._current_monster_move(monster)
            if self._is_live_phase_transition_move(monster, current_move):
                return True

            monster_name = _canonical_live_monster_name(monster)
            if not monster_name:
                continue
            max_hp = monster.get('max_hp', monster.get('hp', 1))
            hp_percent = monster.get('hp', max_hp) / max_hp if max_hp > 0 else 1.0
            predicted_moves = self._predict_monster_moves(monster_name, current_turn, hp_percent)
            if not predicted_moves:
                continue

            first_move = predicted_moves[0].get('move', {})
            first_intent = str(first_move.get('intent', '')).upper()
            later_attack = any(
                'ATTACK' in str(prediction.get('move', {}).get('intent', '')).upper()
                for prediction in predicted_moves[1:]
            )
            if later_attack and 'ATTACK' not in first_intent:
                return True

        return False

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
            lookahead_state = state.clone()
            logger.info(
                "[LOOKAHEAD_ENTRY] turns=%s monsters=%s hp=%s/%s",
                look_ahead,
                len([m for m in lookahead_state.monsters if not m['is_gone']]),
                lookahead_state.player_hp,
                lookahead_state.player_max_hp
            )
            total_future_damage = 0
            current_turn = getattr(context, 'turn', 1)

            player_vulnerable = lookahead_state.player_vulnerable
            player_weak = lookahead_state.player_weak
            player_frail = lookahead_state.player_frail

            for step in range(look_ahead):
                turn_damage = 0
                pending_debuffs = {'weak': 0, 'frail': 0, 'vulnerable': 0}
                any_predictions = False
                split_due_this_turn = False

                for idx, monster in enumerate(lookahead_state.monsters):
                    if monster['is_gone']:
                        continue

                    split_info = self._get_death_split_info(monster)
                    if split_info and self._is_death_split_due(monster, split_info):
                        monster['split_pending'] = True
                        split_due_this_turn = True
                        continue

                    monster_name = _canonical_live_monster_name(monster)
                    if not monster_name:
                        continue

                    max_hp = monster.get('max_hp', monster['hp'])
                    hp_percent = monster['hp'] / max_hp if max_hp > 0 else 1.0
                    move = self._current_monster_move(monster) if step == 0 else None
                    if move is None:
                        move = self._predicted_monster_move_for_step(
                            monster_name,
                            current_turn,
                            step,
                            hp_percent,
                        )
                    if move:
                        any_predictions = True

                    if move:
                        move_intent = move.get('intent', '').upper()
                        target_turn = current_turn + step
                        move_damage = self._move_damage_value(move, lookahead_state, target_turn=target_turn)
                        move_hits = self._move_hit_count(move, target_turn=target_turn)

                        if 'ATTACK' in move_intent and move_damage > 0:
                            current_strength = monster.get('strength', 0)
                            per_hit_damage = self._apply_monster_strength_to_per_hit_damage(
                                move_damage,
                                current_strength,
                            )
                            per_hit_damage = self._apply_monster_weak_to_per_hit_damage(
                                per_hit_damage,
                                monster.get('weak', 0),
                            )
                            damage = per_hit_damage * move_hits
                            damage = self._apply_player_vulnerable_damage(
                                damage,
                                player_vulnerable,
                                move_hits,
                            )
                            damage = self._apply_debuff_risk_multiplier(damage, player_weak, player_frail)
                            discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                            turn_damage += int(damage * discount)

                        move_debuffs = self._extract_move_debuffs(move)
                        pending_debuffs['weak'] += move_debuffs['weak']
                        pending_debuffs['frail'] += move_debuffs['frail']
                        pending_debuffs['vulnerable'] += move_debuffs['vulnerable']
                        strength_gain = self._extract_move_strength_gain(move)
                        if strength_gain > 0:
                            monster['strength'] = monster.get('strength', 0) + strength_gain
                    else:
                        fallback_damage = monster.get('move_adjusted_damage', 0) or monster.get('move_base_damage', 0)
                        fallback_damage = self._numeric_damage_value(fallback_damage)
                        if fallback_damage > 0:
                            move_hits = monster.get('move_hits', 1)
                            current_strength = monster.get('strength', 0)
                            per_hit_damage = self._apply_monster_strength_to_per_hit_damage(
                                fallback_damage,
                                current_strength,
                            )
                            per_hit_damage = self._apply_monster_weak_to_per_hit_damage(
                                per_hit_damage,
                                monster.get('weak', 0),
                            )
                            damage = per_hit_damage * move_hits
                            damage = self._apply_player_vulnerable_damage(
                                damage,
                                player_vulnerable,
                                move_hits,
                            )
                            damage = self._apply_debuff_risk_multiplier(damage, player_weak, player_frail)
                            discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                            turn_damage += int(damage * discount)

                total_future_damage += turn_damage

                player_vulnerable = max(0, player_vulnerable + pending_debuffs['vulnerable'] - 1)
                player_weak = max(0, player_weak + pending_debuffs['weak'] - 1)
                player_frail = max(0, player_frail + pending_debuffs['frail'] - 1)
                self._decrement_monster_turn_debuffs(lookahead_state)

                logger.debug(
                    f"[LOOKAHEAD_TURN] step={step + 1} damage={turn_damage} "
                    f"debuffs=V{player_vulnerable}/W{player_weak}/F{player_frail}"
                )

                if split_due_this_turn:
                    lookahead_state = self._materialize_pending_death_splits(lookahead_state)
                elif not any_predictions:
                    break

            if total_future_damage > 0:
                logger.info(f"[LOOKAHEAD] Predicted damage over next {look_ahead} turns: {total_future_damage}")

            return total_future_damage

        except Exception as e:
            logger.warning(f"[LOOKAHEAD] Failed to simulate enemy lookahead: {e}")
            return 0

    def simulate_enemy_status_lookahead(
        self,
        state: SimulationState,
        context: DecisionContext,
        look_ahead: int = 2,
    ) -> Dict[str, int]:
        """Estimate status-card pollution from current and near-future monster moves."""
        totals = {'total': 0, 'dazed': 0, 'burn': 0, 'slimed': 0, 'wound': 0}
        try:
            current_turn = getattr(context, 'turn', 1)
            for step in range(look_ahead):
                for monster in state.monsters:
                    if monster['is_gone']:
                        continue

                    move = self._current_monster_move(monster) if step == 0 else None
                    if move is None:
                        monster_name = _canonical_live_monster_name(monster)
                        if not monster_name:
                            continue
                        max_hp = monster.get('max_hp', monster['hp'])
                        hp_percent = monster['hp'] / max_hp if max_hp > 0 else 1.0
                        move = self._predicted_monster_move_for_step(
                            monster_name,
                            current_turn,
                            step,
                            hp_percent,
                        )

                    if not move:
                        continue

                    counts = self._extract_move_status_cards(move)
                    for key in totals:
                        totals[key] += counts.get(key, 0)

            if totals['total'] > 0:
                logger.info(
                    "[STATUS_LOOKAHEAD] predicted=%s dazed=%s burn=%s slimed=%s wound=%s",
                    totals['total'],
                    totals['dazed'],
                    totals['burn'],
                    totals['slimed'],
                    totals['wound'],
                )
            return totals
        except Exception as e:
            logger.warning(f"[STATUS_LOOKAHEAD] Failed to simulate enemy status pollution: {e}")
            return totals

    def _predicted_monster_move_for_step(
        self,
        monster_name: str,
        current_turn: int,
        step: int,
        hp_percent: float,
    ) -> Optional[Dict[str, Any]]:
        target_turn = current_turn + step
        predictions = self._predict_monster_moves(monster_name, current_turn, hp_percent)
        for prediction in predictions:
            if prediction.get('turn') == target_turn:
                return prediction.get('move', None)

        if predictions and step == 0:
            return predictions[0].get('move', None)

        predictions = self._predict_monster_moves(monster_name, target_turn, hp_percent)
        if predictions:
            return predictions[0].get('move', None)
        return None

    def _predict_monster_moves(
        self,
        monster_name: str,
        current_turn: int,
        hp_percent: float,
    ) -> List[Dict[str, Any]]:
        try:
            return game_data_loader.predict_monster_moves(
                monster_name,
                current_turn,
                hp_percent,
            )
        except AttributeError:
            return []

    def _current_monster_move(self, monster: dict) -> Optional[Dict[str, Any]]:
        """Return the current move from live state move_id when available."""
        move_id = monster.get('move_id', None)
        try:
            moves = game_data_loader.get_monster_moves(_canonical_live_monster_name(monster))
        except AttributeError:
            return None

        if move_id is not None:
            live_intent = self._intent_name(monster.get('intent', '')).upper()
            for move in moves:
                if move.get('move_id') == move_id:
                    if not live_intent or self._move_intent_matches_live(move, live_intent):
                        return move
                    break

        return self._find_current_move_by_live_state(monster, moves)

    def _find_current_move_by_live_state(
        self,
        monster: dict,
        moves: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        live_intent = self._intent_name(monster.get('intent', '')).upper()
        if not live_intent:
            return None

        live_damage = (
            monster.get('move_adjusted_damage', 0)
            or monster.get('move_base_damage', 0)
            or 0
        )
        live_hits = monster.get('move_hits', 1) or 1

        matches = []
        for move in moves:
            if not self._move_intent_matches_live(move, live_intent):
                continue

            if 'ATTACK' in live_intent and live_damage > 0:
                move_damage = self._numeric_damage_value(move.get('damage', 0))
                move_hits = self._move_hit_count(move)
                if move_damage > 0 and move_damage * move_hits != live_damage * live_hits:
                    continue

            matches.append(move)

        phase_transition_move = self._phase_transition_live_move(monster, matches)
        if phase_transition_move:
            return phase_transition_move

        if len(matches) == 1:
            return matches[0]
        return matches[0] if matches else None

    def _phase_transition_live_move(
        self,
        monster: dict,
        moves: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        transition_move_name = self._live_phase_transition_move_name(monster)
        if not transition_move_name:
            return None

        for move in moves:
            if move.get('name') == transition_move_name:
                return move
        return None

    def _is_live_phase_transition_move(
        self,
        monster: dict,
        move: Optional[Dict[str, Any]],
    ) -> bool:
        if not move:
            return False
        transition_move_name = self._live_phase_transition_move_name(monster)
        return bool(transition_move_name and move.get('name') == transition_move_name)

    def _live_phase_transition_move_name(self, monster: dict) -> Optional[str]:
        monster_name = _canonical_live_monster_name(monster)
        if not monster_name:
            return None

        try:
            pattern = game_data_loader.get_monster_pattern(monster_name)
        except AttributeError:
            return None

        if not isinstance(pattern, dict):
            return None

        phases = pattern.get('phases')
        if not isinstance(phases, list):
            return None

        max_hp = _monster_field(monster, 'max_hp', _monster_field(monster, 'hp', 1))
        hp = _monster_field(monster, 'hp', max_hp)
        hp_percent = hp / max_hp if max_hp and max_hp > 0 else 1.0
        for idx, phase in enumerate(phases):
            threshold = phase.get('hp_threshold')
            if threshold is None or hp_percent >= (threshold / 100.0):
                continue
            if phase.get('transition_move'):
                return phase.get('transition_move')
            for next_phase in phases[idx + 1:]:
                transition_move = next_phase.get('transition_move')
                if transition_move:
                    return transition_move
        return None

    def _intent_name(self, intent: Any) -> str:
        if hasattr(intent, 'name'):
            return str(intent.name)
        text = str(intent or '')
        return text.rsplit('.', 1)[-1]

    def _move_intent_matches_live(self, move: Dict[str, Any], live_intent: str) -> bool:
        move_intent = str(move.get('intent', '')).upper()
        if not move_intent or not live_intent:
            return False
        if move_intent == live_intent:
            return True

        live_has_attack = 'ATTACK' in live_intent
        move_has_attack = 'ATTACK' in move_intent
        if live_has_attack:
            if not move_has_attack:
                return False
            for required_tag in ('DEFEND', 'DEBUFF', 'BUFF'):
                if required_tag in live_intent and required_tag not in move_intent:
                    return False
            return True

        if move_has_attack:
            return False
        if live_intent == 'DEBUFF' and 'DEBUFF' in move_intent:
            return True
        if live_intent == 'BUFF' and 'BUFF' in move_intent:
            return True
        if live_intent == 'DEFEND' and ('DEFEND' in move_intent or 'BLOCK' in move_intent):
            return True
        return False

    def calculate_future_monster_damage(self, state: SimulationState, context: DecisionContext, look_ahead: int = 2) -> int:
        """Compatibility wrapper for future damage prediction."""
        return self.simulate_enemy_lookahead(state, context, look_ahead)

    def _move_damage_value(
        self,
        move: Dict[str, Any],
        state: SimulationState,
        target_turn: Optional[int] = None,
    ) -> int:
        """Return a numeric damage estimate for predicted monster moves."""
        move_name = str(move.get('name', ''))
        if move_name == 'Divider':
            return (max(0, state.player_hp) // 12) + 1
        formula_damage = self._formula_damage_value(move.get('damage_formula'), target_turn)
        if formula_damage is not None:
            return formula_damage
        return self._numeric_damage_value(move.get('damage', 0))

    def _move_hit_count(self, move: Dict[str, Any], target_turn: Optional[int] = None) -> int:
        move_name = str(move.get('name', ''))
        if move_name == 'Divider':
            return 6
        formula_hits = self._formula_hit_count(move.get('hits_formula'), target_turn)
        if formula_hits is not None:
            return formula_hits
        return move.get('hits', move.get('move_hits', 1)) or 1

    def _formula_damage_value(self, formula: Any, target_turn: Optional[int]) -> Optional[int]:
        if not isinstance(formula, dict):
            return None

        formula_type = formula.get('type')
        turn = int(target_turn or 1)

        if formula_type == 'linear_by_turn':
            base = int(formula.get('base', 0) or 0)
            per_turn = int(formula.get('per_turn', 0) or 0)
            turn_offset = int(formula.get('turn_offset', 0) or 0)
            return base + per_turn * max(0, turn + turn_offset)

        if formula_type == 'linear_after_turn':
            base = int(formula.get('base', 0) or 0)
            increment = int(formula.get('increment', 0) or 0)
            first_turn = int(formula.get('first_turn', 1) or 1)
            bonus = increment * max(0, turn - first_turn)
            max_bonus = formula.get('max_bonus')
            if isinstance(max_bonus, (int, float)):
                bonus = min(bonus, int(max_bonus))
            return base + bonus

        return None

    def _formula_hit_count(self, formula: Any, target_turn: Optional[int]) -> Optional[int]:
        if not isinstance(formula, dict):
            return None
        if formula.get('type') != 'ceil_turn_divisor':
            return None

        divisor = max(1, int(formula.get('divisor', 1) or 1))
        turn = max(1, int(target_turn or 1))
        hits = (turn + divisor - 1) // divisor
        min_hits = formula.get('min_hits')
        max_hits = formula.get('max_hits')
        if isinstance(min_hits, (int, float)):
            hits = max(hits, int(min_hits))
        if isinstance(max_hits, (int, float)):
            hits = min(hits, int(max_hits))
        return hits

    def _numeric_damage_value(self, damage: Any) -> int:
        if isinstance(damage, (int, float)):
            return int(damage)
        if isinstance(damage, dict):
            for key in ('max', 'normal', 'base', 'min'):
                value = damage.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
            numeric_values = [
                value for value in damage.values()
                if isinstance(value, (int, float))
            ]
            return int(max(numeric_values, default=0))
        return 0

    def _hexaghost_divider_damage(self, player_hp: int) -> int:
        return ((max(0, player_hp) // 12) + 1) * 6

    def _materialize_pending_death_splits(self, state: SimulationState) -> SimulationState:
        """Replace due death-split monsters with their spawned monsters for future-turn simulation."""
        new_monsters = []
        changed = False

        for monster in state.monsters:
            split_info = self._get_death_split_info(monster)
            if not split_info or not self._is_death_split_due(monster, split_info):
                new_monsters.append(monster)
                continue

            split_hp = max(0, int(monster.get('hp', 0)))
            if split_hp <= 0:
                gone_monster = monster.copy()
                gone_monster['is_gone'] = True
                new_monsters.append(gone_monster)
                continue

            monster_name = monster.get('name', 'Unknown')
            threshold, split_names = split_info
            max_hp = monster.get('max_hp', split_hp)
            hp_percent = (split_hp / max_hp * 100) if max_hp > 0 else 0
            logger.info(
                "[DEATH_SPLIT] Materializing %s at %.1f%% HP (threshold: %s%%) into %s",
                monster_name,
                hp_percent,
                threshold,
                ", ".join(split_names),
            )
            new_monsters.extend(
                self._make_split_monster(child_name, split_hp, monster, child_index)
                for child_index, child_name in enumerate(split_names)
            )
            changed = True

        if changed:
            state.monsters = new_monsters
            state.primary_target = None

        return state

    def _get_death_split_info(self, monster: dict) -> Optional[Tuple[float, List[str]]]:
        monster_name = monster.get('name', '')
        if not monster_name:
            return None

        monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        if not monster_data:
            return None

        special_mechanics = monster_data.get('special_mechanics', {})
        if special_mechanics.get('type') not in {'death_split', 'split'}:
            return None

        split_names = special_mechanics.get('splits_into') or []
        if not split_names:
            split_count = special_mechanics.get('split_count', 0)
            split_names = [monster_name] * int(split_count)
        if not split_names:
            return None
        split_names = [self._canonical_monster_name(name) for name in split_names]

        split_conditions = special_mechanics.get('split_conditions', {})
        threshold = (
            split_conditions.get('hp_threshold')
            or special_mechanics.get('split_threshold_percent')
            or special_mechanics.get('split_threshold')
            or 50
        )
        threshold = float(threshold)
        if threshold <= 1:
            threshold *= 100

        return threshold, list(split_names)

    def _canonical_monster_name(self, monster_name: str) -> str:
        monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        if monster_data and monster_data.get('name'):
            return monster_data['name']
        return monster_name

    def _is_death_split_due(self, monster: dict, split_info: Tuple[float, List[str]]) -> bool:
        if monster.get('is_gone') or monster.get('split_materialized'):
            return False

        threshold, _split_names = split_info
        hp = monster.get('hp', 0)
        max_hp = monster.get('max_hp', hp)
        if hp <= 0 or max_hp <= 0:
            return False

        hp_percent = hp / max_hp * 100
        return hp_percent <= threshold

    def _make_split_monster(self, child_name: str, inherited_hp: int, parent: dict, child_index: int) -> dict:
        child_name = self._canonical_monster_name(child_name)
        attack_damage = self._strongest_known_attack_damage(child_name)
        return {
            'name': child_name,
            'hp': inherited_hp,
            'max_hp': inherited_hp,
            'block': 0,
            'intent': Intent.UNKNOWN,
            'move_id': None,
            'is_gone': False,
            'half_dead': False,
            'vulnerable': 0,
            'weak': 0,
            'frail': 0,
            'thorns': 0,
            'move_base_damage': attack_damage,
            'move_adjusted_damage': attack_damage,
            'move_hits': 1,
            'strength': 0,
            'split_parent': parent.get('name', ''),
            'split_child_index': child_index,
            'split_materialized': True,
        }

    def _strongest_known_attack_damage(self, monster_name: str) -> int:
        damage_values = []
        for move in game_data_loader.get_monster_moves(monster_name):
            intent = str(move.get('intent', '')).upper()
            damage = self._numeric_damage_value(move.get('damage'))
            if 'ATTACK' not in intent or damage <= 0:
                continue
            hits = move.get('hits', move.get('move_hits', 1)) or 1
            damage_values.append(int(damage * hits))
        return max(damage_values, default=0)

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

            split_info = self._get_death_split_info(monster)
            if not split_info:
                return

            split_threshold, split_names = split_info
            max_hp = monster.get('max_hp', monster['hp'])
            hp_percent = (monster['hp'] / max_hp * 100) if max_hp > 0 else 0

            if hp_percent <= split_threshold and not monster.get('split_pending', False):
                logger.info(
                    "[DEATH_SPLIT] %s at %.1f%% HP (threshold: %s%%) - split pending into %s",
                    monster_name,
                    hp_percent,
                    split_threshold,
                    ", ".join(split_names),
                )
                monster['split_pending'] = True

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

            monster.pop('is_hibernating', None)
            monster.pop('is_awakened', None)

            # Prefer the live game intent over turn-count guesses. Lagavulin
            # wakes immediately when damaged, so an attacking/debuffing intent
            # is authoritative even if the global turn is still early.
            intent = monster.get('intent')
            intent_name = getattr(intent, 'name', str(intent or '')).upper()
            move_damage = monster.get('move_adjusted_damage', 0) or monster.get('move_base_damage', 0) or 0

            if intent_name == 'SLEEP':
                is_hibernating = True
            elif 'ATTACK' in intent_name or 'DEBUFF' in intent_name or move_damage > 0:
                is_hibernating = False
            else:
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
            turn_block = final_state.turn_block()
            if turn_block >= expected_damage * 0.8:
                # Good blocking - sufficient block for incoming damage
                bonus += 50.0
                logger.debug(f"[TIMING_BONUS] Threat spike: +50.0 for proper blocking")
            else:
                # Under-blocking - penalty
                bonus -= 30.0
                logger.debug(f"[TIMING_BONUS] Threat spike: -30.0 for under-blocking (block={turn_block}, damage={expected_damage})")

        # Preparation bonus: reward building block for future spike
        elif timing.value == "PREPARATION":
            if self.timing_context.future_damage_curve:
                future_damage = self.timing_context.future_damage_curve[0]
                if final_state.turn_block() >= future_damage * 0.6:
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

        final_state = self.project_end_turn_effects(final_state)
        score = 0.0

        # 1. Monsters killed (high priority)
        initial_alive = sum(1 for m in initial_state.monsters if self._is_live_monster_state(m))
        final_alive = sum(1 for m in final_state.monsters if self._is_live_monster_state(m))
        kills = max(0, initial_alive - final_alive)
        score += kills * weights['KILL_BONUS']

        # ALL_LETHAL_BONUS: Exponential bonus for killing all monsters
        if final_alive == 0 and initial_alive > 0:
            score += ALL_LETHAL_BONUS
            logger.debug(f"[ALL_LETHAL_BONUS] +{ALL_LETHAL_BONUS} score for killing all {initial_alive} monsters")

        # 2. Damage dealt (with multi-monster bonuses)
        total_damage = sum(m['hp'] for m in initial_state.monsters) - \
                      sum(m['hp'] for m in final_state.monsters)

        # Multi-monster detection and adaptive damage weighting
        num_monsters = len([m for m in initial_state.monsters if self._is_live_monster_state(m)])

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
            if not self._is_live_monster_state(before) or not self._is_live_monster_state(after):
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
                    card_id = _canonical_card_name(action.card)

                    if card_id in aoe_cards:
                        aoe_bonus = 40 if num_monsters >= 3 else 20
                        score += aoe_bonus
                        logger.info(f"[OUTCOME_AOE] +{aoe_bonus} for {card_id} in {num_monsters}-monster fight")

        # 3. Block gained (defensive value)
        initial_turn_block = initial_state.turn_block()
        final_turn_block = final_state.turn_block()
        block_gained = final_turn_block - initial_turn_block

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
        total_monster_hp = sum(
            m['hp'] + m['block']
            for m in initial_state.monsters
            if self._is_live_monster_state(m)
        )
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
        expected_incoming = self._estimate_incoming_damage(
            final_state.monsters,
            final_state.player_vulnerable_added,
        )
        hp_loss_next_turn = max(0, expected_incoming - final_turn_block)

        # Log defensive analysis for debugging
        if block_gained > 0 or final_turn_block > 0:
            logger.debug(f"[DEFENSE_ANALYSIS] block_gained={block_gained}, final_block={final_turn_block}, "
                        f"expected_incoming={expected_incoming}, hp_loss_next_turn={hp_loss_next_turn}, "
                        f"player_hp={final_state.player_hp}")

        # Detect over-defense (block significantly exceeds incoming damage)
        if final_turn_block > expected_incoming * 1.5 and expected_incoming > 0:
            logger.warning(f"[OVER_DEFENSE] Block ({final_turn_block}) is {final_turn_block / max(expected_incoming, 1):.1f}x incoming damage ({expected_incoming}) - wasting resources!")

        # Detect useless defense (block when no incoming damage)
        if expected_incoming == 0 and final_turn_block > 0:
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

                future_status = self.simulate_enemy_status_lookahead(
                    final_state,
                    context,
                    look_ahead=lookahead_turns,
                )
                if future_status.get('total', 0) > 0:
                    future_status_penalty = (
                        future_status['total']
                        * STATUS_CARD_PENALTY
                        * ENEMY_STATUS_LOOKAHEAD_WEIGHT
                    )
                    score -= future_status_penalty
                    logger.info(
                        "[FUTURE_STATUS_PENALTY] -%.1f score for %s predicted status cards",
                        future_status_penalty,
                        future_status['total'],
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

        # Status pollution value: Dazed/Burn/Wound cards reduce future hand quality.
        status_penalty = final_state.status_cards_added * STATUS_CARD_PENALTY
        if status_penalty > 0:
            score -= status_penalty
            logger.info(
                "[STATUS_POLLUTION] -%.1f for %s added status cards (%s Dazed)",
                status_penalty,
                final_state.status_cards_added,
                final_state.dazed_cards_added,
            )

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
                        if potion.effect_type in ['damage', 'poison']:
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
                        elif potion.effect_type in ['block', 'plated_armor', 'metallicize']:
                            new_state.player_block += potion.effect_value
                        elif potion.effect_type in ['heal', 'regen']:
                            new_state.player_hp = min(new_state.player_max_hp, new_state.player_hp + potion.effect_value)
                        elif potion.effect_type == 'heal_percent':
                            heal_amount = int(new_state.player_max_hp * potion.effect_value)
                            new_state.player_hp = min(new_state.player_max_hp, new_state.player_hp + heal_amount)
                        elif potion.effect_type == 'max_hp':
                            new_state.player_max_hp += potion.effect_value
                            new_state.player_hp += potion.effect_value
                        elif potion.effect_type in ['buff_strength', 'temp_strength']:
                            new_state.player_strength += potion.effect_value
                        elif potion.effect_type == 'energy':
                            new_state.player_energy += potion.effect_value
                            new_state.energy_gained += potion.effect_value
                        elif potion.effect_type in ['draw', 'draw_randomize_cost']:
                            new_state.cards_drawn += potion.effect_value

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
        return potion.effect_type in ['heal', 'heal_percent', 'regen', 'fairy', 'max_hp']

    def _is_damage_potion(self, potion) -> bool:
        """Check if potion is a damage potion."""
        return potion.effect_type in ['damage', 'poison']

    def _is_block_potion(self, potion) -> bool:
        """Check if potion is a block potion."""
        return potion.effect_type in ['block', 'plated_armor', 'metallicize']

    @staticmethod
    def _is_live_monster_object(monster) -> bool:
        return (
            getattr(monster, 'current_hp', 0) > 0
            and not getattr(monster, 'is_gone', False)
            and not getattr(monster, 'half_dead', False)
        )

    @staticmethod
    def _positive_live_move_hits(monster) -> int:
        try:
            return max(1, int(getattr(monster, 'move_hits', 1) or 1))
        except (TypeError, ValueError):
            return 1

    def _get_incoming_damage(self, context: DecisionContext) -> int:
        """Calculate total incoming damage from all monsters."""
        incoming = 0
        debug_entries = []
        for monster in context.game.monsters:
            if self._is_live_monster_object(monster):
                adjusted_damage = monster.move_adjusted_damage
                if adjusted_damage is not None:
                    incoming += max(0, adjusted_damage) * self._positive_live_move_hits(monster)
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
        alive_monsters = [
            (i, m)
            for i, m in enumerate(context.game.monsters)
            if self._is_live_monster_object(m)
        ]

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
                for i, monster in alive_monsters:
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
                total_monster_hp = sum(m.current_hp for _i, m in alive_monsters)
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
                    card_name = _canonical_card_name(card)
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        parsed_damage = game_data_loader._parse_card_damage(card_data)
                        if parsed_damage is not None:
                            base_damage = parsed_damage + _known_damage_upgrade_bonus(card, card_name)
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
                    card_name = _canonical_card_name(card)
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        parsed_damage = game_data_loader._parse_card_damage(card_data)
                        if parsed_damage is not None:
                            base_damage = parsed_damage + _known_damage_upgrade_bonus(card, card_name)
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
        card_name = _canonical_card_name(card)
        if card_name == 'Rage':
            # Count playable attack cards in hand
            attack_cards = [c for c in context.playable_cards
                          if hasattr(c, 'type') and c.type == CardType.ATTACK]

            rage_block = 5 if getattr(card, 'upgrades', 0) > 0 else 3
            potential_block = len(attack_cards) * rage_block

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
            card_name = _canonical_card_name(card)
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
            if hasattr(context, 'player_class'):
                player_class = str(context.player_class)
            else:
                player_class = 'IRONCLAD'

            if player_class == 'IRONCLAD':
                is_aoe = card_name in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']

        # Base damage estimate with AOE multiplier
        base_damage = 0
        if hasattr(card, 'damage') and card.damage:
            base_damage = card.damage
        elif hasattr(card, 'type') and card.type == CardType.ATTACK:
            # Fallback: use game data for damage
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                parsed_damage = game_data_loader._parse_card_damage(card_data)
                if parsed_damage is not None:
                    base_damage = parsed_damage + _known_damage_upgrade_bonus(card, card_name)

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
