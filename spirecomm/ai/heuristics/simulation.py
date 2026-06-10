"""
Fast combat simulation and action planning.

This module implements a combat simulator that can lookahead multiple actions
to find optimal play sequences using beam search.
"""

import copy
import logging
import re
import time
from types import SimpleNamespace
from typing import List, Dict, Tuple, Optional, Any
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster, Intent
from spirecomm.spire.numeric import coerce_float, coerce_int
from spirecomm.communication.action import Action, PlayCardAction, EndTurnAction
from spirecomm.ai.incoming_damage import (
    exploder_explosion_damage,
    known_unknown_move_has_no_immediate_damage,
    known_unknown_move_immediate_damage,
    move_data_immediate_unknown_damage,
)
from spirecomm.ai.intent_utils import intent_is_attack, intent_is_unknown, intent_tokens, monster_intends_attack
from spirecomm.ai.monster_names import (
    canonical_live_monster_name,
    monster_field,
    normalize_monster_id,
)
from spirecomm.ai.decision.base import DecisionContext, CombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.ai.heuristics.combat_state import (
    card_play_key,
    draw_pile_count,
    is_card_played,
    mark_card_played,
    player_block_value,
    player_debuff_stacks,
    player_has_power,
    player_power_amount,
    power_amount,
    power_name,
)
from spirecomm.ai.heuristics.card_costs import (
    effective_card_cost,
    is_x_cost_card,
    raw_card_cost,
    x_effect_energy,
)
from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_hits import fixed_attack_hit_count, strike_card_count
from spirecomm.ai.heuristics.card_types import (
    card_is_playable,
    card_requires_target,
    card_type_name,
    is_attack_card,
)
from spirecomm.ai.heuristics.potions import game_real_potions, potion_can_use
import spirecomm.ai.heuristics.card_upgrades as card_upgrade_helpers
from spirecomm.ai.heuristics.card_upgrades import (
    card_upgrade_count,
    heavy_blade_strength_multiplier,
    is_card_upgraded,
    perfected_strike_bonus_per_strike,
)
from spirecomm.data.loader import (
    _effect_text_for_upgrade as _select_effect_text_for_upgrade,
    game_data_loader,
)

# Configure logging for combat decisions
logger = logging.getLogger(__name__)

PANACHE_DAMAGE = 10
PANACHE_RESET_COUNT = 5
LETTER_OPENER_DAMAGE = 5
BIRD_FACED_URN_HEAL = 2
CHARONS_ASHES_DAMAGE = 3
STONE_CALENDAR_DAMAGE = 52
STONE_CALENDAR_TRIGGER_COUNTER = 7
FAIRY_REVIVE_FRACTION = 0.3
FAIRY_POTION_IDENTIFIERS = {"fairy", "fairypotion", "fairyinabottle"}
TOY_ORNITHOPTER_HEAL = 5
MAGIC_FLOWER_HEAL_NUMERATOR = 3
MAGIC_FLOWER_HEAL_DENOMINATOR = 2
THE_BOOT_MINIMUM_DAMAGE = 5


def _magic_flower_scaled_heal(amount: int) -> int:
    heal = max(0, coerce_int(amount, 0))
    if heal <= 0:
        return 0
    return (heal * MAGIC_FLOWER_HEAL_NUMERATOR + MAGIC_FLOWER_HEAL_DENOMINATOR - 1) // (
        MAGIC_FLOWER_HEAL_DENOMINATOR
    )


def _normalized_potion_identifier(value) -> str:
    return ''.join(ch for ch in str(value or '').lower() if ch.isalnum())


def _potion_attr(potion, attr: str, default=None):
    if isinstance(potion, dict):
        if attr == 'potion_id':
            return potion.get('potion_id', potion.get('id', default))
        if attr == 'id':
            return potion.get('id', potion.get('potion_id', default))
        return potion.get(attr, default)
    return getattr(potion, attr, default)


def _is_fairy_potion(potion) -> bool:
    effect_type = _normalized_potion_identifier(_potion_attr(potion, 'effect_type', ''))
    identifiers = {
        _normalized_potion_identifier(_potion_attr(potion, 'id', '')),
        _normalized_potion_identifier(_potion_attr(potion, 'potion_id', '')),
        _normalized_potion_identifier(_potion_attr(potion, 'name', '')),
    }
    return effect_type == 'fairy' or not identifiers.isdisjoint(FAIRY_POTION_IDENTIFIERS)


def _fairy_potions_for_game(game) -> List[Any]:
    if game is None:
        return []
    try:
        potions = game_real_potions(game)
    except Exception:
        potions = getattr(game, 'potions', []) or []
    return [potion for potion in potions if _is_fairy_potion(potion)]


def _fairy_revive_hp_from_potion(max_hp: int, potion) -> int:
    percent = coerce_float(_potion_attr(potion, 'effect_value', 0), 0.0)
    if percent <= 0 or percent > 1:
        percent = FAIRY_REVIVE_FRACTION
    return max(1, int(max(1, coerce_int(max_hp, 1)) * percent))


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

IRONCLAD_AOE_ATTACK_CARDS = {
    'Cleave',
    'Dramatic Entrance',
    'Whirlwind',
    'Immolate',
    'Thunderclap',
    'Reaper',
}

# Danger threshold penalty
DANGER_PENALTY = 50.0  # Extra penalty when below danger threshold
                      # Threshold = 15 + (act * 5) → Act 1: 20, Act 2: 25, Act 3: 30

# Engine event synergy weights
EXHAULT_SYNERGY_VALUE = 3.0  # Points per exhaust event (Feel No Pain)
DRAW_SYNERGY_VALUE = 3.0  # Points per card drawn
ENERGY_SYNERGY_VALUE = 4.0  # Points per energy gained/saved (Corruption, Bloodletting)
STATUS_CARD_PENALTY = 12.0  # Cost of adding Dazed/Burn/Wound/Void-style deck pollution
ENEMY_STATUS_LOOKAHEAD_WEIGHT = 0.5  # Enemy status predictions are useful but uncertain

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


def _monster_field(monster: Any, field_name: str, default: Any = None) -> Any:
    return monster_field(monster, field_name, default)


_canonical_live_monster_name = canonical_live_monster_name


def _canonical_card_name(card: Any) -> str:
    return canonical_card_name(card)

# Timeout protection
TIMEOUT_BUDGET = 0.15  # Seconds (150ms budget for beam search) - increased from 80ms

GUARDIAN_MODE_SHIFT_BLOCK = 20
GUARDIAN_SHARP_HIDE = 3
GUARDIAN_DEFENSIVE_MODE_MOVE_ID = 4


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
    try:
        context_turn = max(1, int(getattr(context, 'turn', 1) or 1))
    except (TypeError, ValueError):
        context_turn = 1

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
        if game_data_loader.is_monster_hibernating(monster_name, context_turn):
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

    @staticmethod
    def _non_negative_int(value) -> int:
        return max(0, coerce_int(value or 0, 0))

    @staticmethod
    def _int_value(value) -> int:
        return coerce_int(value or 0, 0)

    @staticmethod
    def end_turn_status_damage_for_card(card: Any) -> int:
        if _canonical_card_name(card) != 'Burn':
            return 0

        upgraded = card_upgrade_count(card) > 0 or str(getattr(card, 'name', '')).endswith('+')
        return 4 if upgraded else 2

    @staticmethod
    def end_turn_status_hp_loss_for_card(card: Any) -> int:
        if _canonical_card_name(card) != 'Decay':
            return 0

        return 2

    @staticmethod
    def end_turn_exhausts_for_card(card: Any) -> bool:
        return _canonical_card_name(card) == 'Dazed'

    def __init__(self, context: DecisionContext):
        """Initialize simulation state from decision context."""
        self.turn = self._non_negative_int(getattr(context, 'turn', 1)) or 1

        # Player state
        self.player_hp = self._non_negative_int(context.game.current_hp)
        self.player_max_hp = self._non_negative_int(context.game.max_hp)
        fairy_potions = _fairy_potions_for_game(getattr(context, 'game', None))
        self.fairy_revives = len(fairy_potions)
        self.fairy_revive_hp = max(
            (
                _fairy_revive_hp_from_potion(self.player_max_hp, potion)
                for potion in fairy_potions
            ),
            default=0,
        )
        self.player_block = self._non_negative_int(player_block_value(context))
        plated_armor = max(
            self._get_player_power_amount(context, 'Plated Armor'),
            self._get_player_power_amount(context, 'PlatedArmor'),
        )
        self.end_turn_block = (
            self._get_player_power_amount(context, 'Metallicize')
            + plated_armor
        )
        self.player_energy = self._non_negative_int(context.energy_available)
        self.player_strength = self._int_value(context.strength)
        self.player_temp_strength = 0
        self.player_ritual = self._get_player_power_amount(context, 'Ritual')
        self.player_regen = max(
            self._get_player_power_amount(context, 'Regeneration'),
            self._get_player_power_amount(context, 'Regen'),
        )
        self.player_dexterity = self._get_player_power_amount(context, 'Dexterity')
        self.player_temp_dexterity = 0
        flame_barrier = max(
            self._get_player_power_amount(context, 'Flame Barrier'),
            self._get_player_power_amount(context, 'FlameBarrier'),
        )
        self.player_thorns = self._get_player_power_amount(context, 'Thorns') + flame_barrier
        self.player_intangible = max(
            self._get_player_power_amount(context, 'Intangible'),
            self._get_player_power_amount(context, 'IntangiblePlayer'),
        )
        self.player_buffer = max(
            self._get_player_power_amount(context, 'Buffer'),
            self._get_player_power_amount(context, 'BufferPower'),
        )
        self.player_artifact = self._get_player_power_amount(context, 'Artifact')
        self.combat_escaped = False
        self.ascension_level = self._context_ascension_level(context)

        # Player debuffs (binary: >0 means debuffed)
        self.player_vulnerable = self._get_player_debuff_stacks(context, 'Vulnerable')
        self.player_vulnerable_added = 0
        self.player_weak = self._get_player_debuff_stacks(context, 'Weak')
        self.player_frail = self._get_player_debuff_stacks(context, 'Frail')
        self.player_hex = self._get_player_hex_stacks(context)
        self.player_constricted = self._get_player_constricted_stacks(context)
        # Rage power: block gained per attack played.
        self.rage_block_per_attack = self._get_player_power_amount(context, 'Rage')
        self.draw_blocked = (
            self._has_player_power(context, 'No Draw')
            or self._has_player_power(context, 'NoDraw')
        )
        self.card_block_blocked = any(
            self._get_player_debuff_stacks(context, power_name) > 0
            for power_name in ('No Block', 'NoBlock', 'NoBlockPower')
        )
        self.duplication_charges = max(
            self._get_player_power_amount(context, 'DuplicationPower'),
            self._get_player_power_amount(context, 'Duplication'),
        )
        self.double_tap_charges = max(
            self._get_player_power_amount(context, 'Double Tap'),
            self._get_player_power_amount(context, 'DoubleTap'),
        )
        self.panache_counter = self._get_player_power_amount(context, 'Panache')
        self.panache_damage = PANACHE_DAMAGE if (
            self.panache_counter > 0 or self._has_player_power(context, 'Panache')
        ) else 0
        if self.panache_damage > 0 and self.panache_counter <= 0:
            self.panache_counter = PANACHE_RESET_COUNT
        self.pen_nib_counter = self._context_relic_counter(context, 'Pen Nib')
        self.nunchaku_counter = self._context_relic_counter(context, 'Nunchaku')
        self.ornamental_fan_attack_count = self._context_relic_counter(
            context,
            'Ornamental Fan',
        )
        self.letter_opener_counter = self._context_relic_counter(
            context,
            'Letter Opener',
        )
        self.stone_calendar_counter = self._context_relic_counter(
            context,
            'Stone Calendar',
        )
        self.has_orichalcum = (
            bool(getattr(context, 'has_orichalcum', False))
            or self._context_relic_counter(context, 'Orichalcum') is not None
        )
        self.has_tungsten_rod = self._context_relic_counter(context, 'Tungsten Rod') is not None
        self.has_the_boot = self._context_has_the_boot(context)
        self.has_bird_faced_urn = (
            self._context_relic_counter(context, 'Bird Faced Urn') is not None
        )
        self.has_toy_ornithopter = (
            self._context_relic_counter(context, 'Toy Ornithopter') is not None
        )
        self.has_magic_flower = (
            self._context_relic_counter(context, 'Magic Flower') is not None
        )
        self.has_gremlin_horn = (
            self._context_relic_counter(context, 'Gremlin Horn') is not None
        )
        self.necronomicon_available = (
            self._context_relic_counter(context, 'Necronomicon') is not None
        )
        self.charons_ashes_damage_per_exhaust = (
            CHARONS_ASHES_DAMAGE
            if self._context_relic_counter(context, "Charon's Ashes") is not None
            else 0
        )
        self.corruption_active = self._has_player_power(context, 'Corruption')
        self.feel_no_pain_block_per_exhaust = self._get_player_power_amount(context, 'Feel No Pain')
        self.dark_embrace_draw_per_exhaust = self._get_player_power_amount(context, 'Dark Embrace')
        self.juggernaut_damage_on_block = self._get_player_power_amount(context, 'Juggernaut')
        if self.juggernaut_damage_on_block <= 0 and self._has_player_power(context, 'Juggernaut'):
            self.juggernaut_damage_on_block = 5
        self.rupture_strength_per_hp_loss = self._get_player_power_amount(context, 'Rupture')
        if self.rupture_strength_per_hp_loss <= 0 and self._has_player_power(context, 'Rupture'):
            self.rupture_strength_per_hp_loss = 1
        self.end_turn_aoe_damage = self._get_player_power_amount(context, 'Combust')
        if self.end_turn_aoe_damage <= 0 and self._has_player_power(context, 'Combust'):
            self.end_turn_aoe_damage = 5
        self.end_turn_hp_loss = 1 if self.end_turn_aoe_damage > 0 else 0
        self.end_turn_status_damage = 0
        self.end_turn_status_hp_loss = 0
        self.end_turn_exhaust_events = 0
        for card in getattr(context.game, 'hand', []) or []:
            self.end_turn_status_damage += self.end_turn_status_damage_for_card(card)
            self.end_turn_status_hp_loss += self.end_turn_status_hp_loss_for_card(card)
            if self.end_turn_exhausts_for_card(card):
                self.end_turn_exhaust_events += 1

        # Monster state (each monster tracked independently)
        self.monsters = []
        for i, monster in enumerate(context.monsters_alive):
            monster_max_hp = self._non_negative_int(getattr(monster, 'max_hp', 0))
            monster_hp_default = monster_max_hp if monster_max_hp > 0 else 0
            monster_hp = max(
                0,
                coerce_int(getattr(monster, 'current_hp', monster_hp_default), monster_hp_default),
            )
            mode_shift = (
                self._get_monster_power_amount(monster, 'Mode Shift')
                or self._get_monster_power_amount(monster, 'ModeShift')
            )
            monster_state = {
                'monster_id': getattr(monster, 'monster_id', ''),
                'name': monster.name,
                'hp': monster_hp,
                'max_hp': monster_max_hp,
                'block': self._non_negative_int(monster.block if hasattr(monster, 'block') else 0),
                'intent': monster.intent if hasattr(monster, 'intent') else None,
                'move_id': getattr(monster, 'move_id', None),
                'is_gone': monster.is_gone,
                'half_dead': monster.half_dead,
                'is_minion': self._has_monster_power_any(monster, 'Minion', 'MinionPower'),
                'vulnerable': self._non_negative_int(
                    context.vulnerable_stacks.get(i, 0)
                ),  # Vulnerable stacks (by index)
                'weak': self._non_negative_int(
                    context.weak_stacks.get(i, 0)
                ),  # Weak stacks (by index)
                'frail': self._non_negative_int(
                    context.frail_stacks.get(i, 0)
                ),  # Frail stacks (by index)
                'poison': self._get_monster_power_amount(monster, 'Poison'),
                'thorns': self._non_negative_int(
                    context.thorns_stacks.get(i, 0)
                ),  # Thorns/反伤 stacks (by index)
                'retains_block': self._has_monster_power_any(
                    monster,
                    'Barricade',
                    'BarricadePower',
                ),
                'artifact': self._get_monster_power_amount(monster, 'Artifact'),
                'move_base_damage': self._non_negative_int(
                    getattr(monster, 'move_base_damage', 0)
                ),
                'move_adjusted_damage': self._non_negative_int(
                    getattr(monster, 'move_adjusted_damage', 0)
                ),
                'move_hits': self._non_negative_int(getattr(monster, 'move_hits', 1)),
                'strength': self._int_value(getattr(monster, 'strength', 0)),
                'skill_strength_gain': self._get_monster_skill_strength_gain(monster, context),
                'power_strength_gain': self._get_monster_power_strength_gain(monster),
                'end_turn_strength_gain': self._get_monster_end_turn_strength_gain(
                    monster,
                    context,
                ),
                'mode_shift': mode_shift,
                'curl_up_block': self._get_monster_power_amount_any(
                    monster,
                    'Curl Up',
                    'CurlUp',
                    'CurlUpPower',
                ),
                'curl_up_used': False,
                'malleable_block': self._get_monster_power_amount_any(
                    monster,
                    'Malleable',
                    'MalleablePower',
                ),
                'hit_strength_gain': self._get_monster_power_amount_any(
                    monster,
                    'Angry',
                    'AngryPower',
                ),
                'flight_stacks': self._get_monster_power_amount_any(
                    monster,
                    'Flight',
                    'Flying',
                    'FlightPower',
                ),
                'intangible': self._get_monster_power_amount_any(
                    monster,
                    'Intangible',
                    'IntangiblePower',
                    'IntangibleMonster',
                ),
                'explosive': self._get_monster_power_amount_any(
                    monster,
                    'Explosive',
                    'ExplosivePower',
                ),
                'slow_active': self._has_monster_power_any(monster, 'Slow', 'SlowPower'),
                'slow_stacks': self._get_monster_power_amount_any(
                    monster,
                    'Slow',
                    'SlowPower',
                ),
            }
            self.monsters.append(monster_state)

        # Track what we've played
        self.played_card_uuids = set()
        self.energy_spent = 0
        self.total_damage_dealt = 0
        self.monsters_killed = 0
        self.monsters_escaped = 0

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
        self.added_hand_cards = []
        self.rampage_damage_bonus_by_card = {}

    def _get_player_debuff_stacks(self, context: DecisionContext, power_name: str) -> int:
        """Get debuff stacks on the player from powers."""
        return player_debuff_stacks(context, power_name)

    def _get_player_power_amount(self, context: DecisionContext, power_name: str) -> int:
        """Get power amount on the player from powers."""
        return player_power_amount(context, power_name)

    def _has_player_power(self, context: DecisionContext, power_name: str) -> bool:
        return player_has_power(context, power_name)

    @staticmethod
    def _context_relic_counter(context: DecisionContext, relic_name: str) -> Optional[int]:
        target = ''.join(ch for ch in relic_name.lower() if ch.isalnum())
        if not context or not target:
            return None

        relics = []
        for source in (getattr(context, 'game', None), context):
            relics.extend(getattr(source, 'relics', []) or [])

        for relic in relics:
            identifiers = {
                ''.join(ch for ch in str(getattr(relic, attr, '')).lower() if ch.isalnum())
                for attr in ('name', 'relic_id', 'id')
            }
            if target in identifiers:
                return coerce_int(getattr(relic, 'counter', 0), 0)
        return None

    @staticmethod
    def _context_has_the_boot(context: DecisionContext) -> bool:
        return (
            SimulationState._context_relic_counter(context, 'The Boot') is not None
            or SimulationState._context_relic_counter(context, 'Boot') is not None
        )

    def _get_player_hex_stacks(self, context: DecisionContext) -> int:
        """Hex is a persistent Chosen debuff; amount may be -1 in game state."""
        hex_stacks = self._get_player_debuff_stacks(context, 'Hex')
        if self._has_player_power(context, 'Hex') and hex_stacks <= 0:
            return 1
        return max(0, hex_stacks)

    def _get_player_constricted_stacks(self, context: DecisionContext) -> int:
        return max(
            self._get_player_debuff_stacks(context, 'Constricted'),
            self._get_player_debuff_stacks(context, 'ConstrictedPower'),
        )

    def _get_monster_power_amount(self, monster: Any, power_name: str) -> int:
        return power_amount(getattr(monster, 'powers', []), power_name, 1)

    def _get_monster_power_amount_any(self, monster: Any, *power_names: str) -> int:
        """Get a monster power amount while accepting display-name/id variants."""
        if not hasattr(monster, 'powers'):
            return 0

        normalized_names = {
            re.sub(r'[^a-z0-9]', '', name.lower())
            for name in power_names
        }
        for power in monster.powers:
            power_name = self._power_name(power)
            normalized_power_name = re.sub(
                r'[^a-z0-9]',
                '',
                str(power_name or '').lower(),
            )
            if normalized_power_name in normalized_names:
                amount = getattr(power, 'amount', None)
                if amount is None:
                    return 1
                return self._non_negative_int(amount)
        return 0

    def _has_monster_power_any(self, monster: Any, *power_names: str) -> bool:
        """Return whether a monster has any display-name/id variant of a power."""
        if not hasattr(monster, 'powers'):
            return False

        normalized_names = {
            re.sub(r'[^a-z0-9]', '', name.lower())
            for name in power_names
        }
        for power in monster.powers:
            power_name = self._power_name(power)
            normalized_power_name = re.sub(
                r'[^a-z0-9]',
                '',
                str(power_name or '').lower(),
            )
            if normalized_power_name in normalized_names:
                return True
        return False

    def _get_monster_skill_strength_gain(
        self,
        monster: Any,
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Return Strength a monster gains whenever the player plays a Skill."""
        for power in getattr(monster, 'powers', []) or []:
            power_name = str(self._power_name(power) or '').lower()
            if power_name in {'anger', 'enrage'}:
                amount = getattr(power, 'amount', None)
                return self._non_negative_int(amount) if amount is not None else 2

        monster_id = str(getattr(monster, 'monster_id', ''))
        monster_name = str(getattr(monster, 'name', ''))
        if monster_id in {'GremlinNob', 'Gremlin Nob'} or monster_name == 'Gremlin Nob':
            strength_gain = 2
            try:
                monster_data = game_data_loader.get_enhanced_monster_data('Gremlin Nob')
            except Exception:
                monster_data = None

            mechanics = (monster_data or {}).get('special_mechanics', {}) or {}
            if mechanics.get('type') == 'skill_reactive_strength':
                data_gain = mechanics.get('skill_strength_gain', strength_gain)
                if isinstance(data_gain, (int, float)) and not isinstance(data_gain, bool):
                    strength_gain = self._non_negative_int(data_gain)

                modifiers = mechanics.get('ascension_modifiers', {})
                if context is not None and isinstance(modifiers, dict):
                    ascension_level = self._context_ascension_level(context)
                    thresholds = [
                        int(threshold_key.split('+')[0])
                        for threshold_key in modifiers
                        if (
                            isinstance(threshold_key, str)
                            and threshold_key.endswith('+')
                            and threshold_key.split('+')[0].isdigit()
                        )
                    ]
                    for threshold in sorted(thresholds, reverse=True):
                        if ascension_level < threshold:
                            continue
                        modifier = modifiers.get(f"{threshold}+", {})
                        if isinstance(modifier, dict):
                            modified_gain = modifier.get('skill_strength_gain')
                            if (
                                isinstance(modified_gain, (int, float))
                                and not isinstance(modified_gain, bool)
                            ):
                                strength_gain = self._non_negative_int(modified_gain)
                        break
            return max(0, strength_gain)
        return 0

    def _get_monster_power_strength_gain(self, monster: Any) -> int:
        """Return Strength a monster gains whenever the player plays a Power."""
        for power in getattr(monster, 'powers', []) or []:
            power_name = str(self._power_name(power) or '').lower()
            if 'curiosity' in power_name:
                amount = getattr(power, 'amount', None)
                return self._non_negative_int(amount) if amount is not None else 1
        return 0

    def _get_monster_end_turn_strength_gain(
        self,
        monster: Any,
        context: DecisionContext,
    ) -> int:
        """Return deterministic Strength gained after the monster's own turn."""
        ritual_power = self._get_monster_power_amount_any(
            monster,
            'Ritual',
            'RitualPower',
        )
        if ritual_power > 0:
            return ritual_power

        monster_name = _canonical_live_monster_name(monster)
        if not monster_name:
            return 0
        if monster_name != 'Orb Walker':
            return 0

        try:
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        except Exception:
            monster_data = None
        mechanics = (monster_data or {}).get('special_mechanics', {}) or {}
        if mechanics.get('type') != 'strength_up':
            return 0

        gain = mechanics.get('strength_gain', 0)
        return self._resolve_ascension_value(gain, context)

    def _resolve_ascension_value(self, value: Any, context: DecisionContext) -> int:
        if isinstance(value, (int, float)):
            return self._non_negative_int(value)
        if not isinstance(value, dict):
            return 0

        resolved = value.get('normal', 0)
        ascension_level = self._context_ascension_level(context)
        thresholds = []
        for key in value:
            match = re.match(r'ascension_(\d+)\+$', str(key))
            if match:
                thresholds.append((int(match.group(1)), key))
        for threshold, key in sorted(thresholds):
            if ascension_level >= threshold:
                resolved = value[key]

        if isinstance(resolved, (int, float)):
            return self._non_negative_int(resolved)
        return 0

    @staticmethod
    def _context_ascension_level(context: DecisionContext) -> int:
        if hasattr(context, 'game') and hasattr(context.game, 'ascension_level'):
            return max(0, coerce_int(context.game.ascension_level or 0, 0))
        return max(0, coerce_int(getattr(context, 'ascension_level', 0) or 0, 0))

    def _power_name(self, power: Any) -> Optional[str]:
        return power_name(power)

    def clone(self) -> 'SimulationState':
        """Create a deep copy of this state."""
        new_state = SimulationState.__new__(SimulationState)
        for name, value in self.__dict__.items():
            if name == 'monsters':
                value = [monster.copy() for monster in value]
            elif name == 'played_card_uuids':
                value = value.copy()
            elif name == 'rampage_damage_bonus_by_card':
                value = value.copy()
            elif name == 'added_hand_cards':
                value = value.copy()
            setattr(new_state, name, value)
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
        def sortable_value(value):
            return (
                value is None,
                '' if value is None else str(value),
            )

        def sortable_text(value):
            return '' if value is None else str(value)

        def card_identity_for_key(card):
            card_id = getattr(card, 'card_id', None)
            if card_id is None:
                card_id = getattr(card, 'name', '')
            return sortable_text(card_id)

        # Player state (what matters for future decisions)
        player_key = (
            self.player_hp,
            self.player_max_hp,
            self.fairy_revives,
            self.fairy_revive_hp,
            self.player_block,
            self.end_turn_block,
            self.player_energy,
            self.player_strength,
            self.player_temp_strength,
            self.player_ritual,
            self.player_regen,
            self.player_dexterity,
            self.player_temp_dexterity,
            self.player_thorns,
            self.player_intangible,
            self.player_buffer,
            self.player_artifact,
            self.combat_escaped,
            self.monsters_escaped,
            self.player_vulnerable,
            self.player_vulnerable_added,
            self.player_weak,
            self.player_frail,
            self.player_hex,
            self.player_constricted,
            self.rage_block_per_attack,
            self.draw_blocked,
            self.card_block_blocked,
            self.duplication_charges,
            self.double_tap_charges,
            self.panache_counter,
            self.panache_damage,
            self.pen_nib_counter,
            self.nunchaku_counter,
            self.ornamental_fan_attack_count,
            self.letter_opener_counter,
            self.stone_calendar_counter,
            self.has_orichalcum,
            self.has_tungsten_rod,
            self.has_the_boot,
            self.has_bird_faced_urn,
            self.has_toy_ornithopter,
            self.has_magic_flower,
            self.has_gremlin_horn,
            self.necronomicon_available,
            self.corruption_active,
            self.feel_no_pain_block_per_exhaust,
            self.dark_embrace_draw_per_exhaust,
            self.juggernaut_damage_on_block,
            self.rupture_strength_per_hp_loss,
            self.end_turn_aoe_damage,
            self.end_turn_hp_loss,
            self.end_turn_status_damage,
            self.end_turn_status_hp_loss,
            self.end_turn_exhaust_events,
            self.exhaust_events,
            self.cards_drawn,
            self.energy_gained,
            self.energy_saved,
            self.status_cards_added,
            self.dazed_cards_added,
            self.hex_non_attack_triggers,
            tuple(
                sorted(
                    card_identity_for_key(card)
                    for card in getattr(self, 'added_hand_cards', [])
                    if not is_card_played(self.played_card_uuids, card)
                )
            ),
            tuple(
                sorted(
                    (sortable_text(card_key), bonus)
                    for card_key, bonus in self.rampage_damage_bonus_by_card.items()
                )
            ),
        )

        # Monster states (sorted for consistent hashing)
        # Use tuple for immutability and sorting to ensure consistent ordering
        monster_key = tuple(sorted(
            (
                m['hp'],
                m.get('max_hp', m['hp']),
                m['block'],
                m['vulnerable'],
                m['weak'],
                m['frail'],
                m.get('poison', 0),
                m.get('thorns', 0),
                bool(m.get('retains_block', False)),
                m.get('mode_shift', 0),
                m.get('artifact', 0),
                m.get('strength', 0),
                m.get('skill_strength_gain', 0),
                m.get('power_strength_gain', 0),
                m.get('end_turn_strength_gain', 0),
                m.get('curl_up_block', 0),
                bool(m.get('curl_up_used', False)),
                m.get('malleable_block', 0),
                m.get('hit_strength_gain', 0),
                m.get('flight_stacks', 0),
                m.get('intangible', 0),
                m.get('explosive', 0),
                bool(m.get('slow_active', False)),
                m.get('slow_stacks', 0),
                bool(m.get('half_dead', False)),
                m.get('move_base_damage', 0),
                (
                    m.get('move_adjusted_damage', None) is None,
                    m.get('move_adjusted_damage', 0) or 0,
                ),
                (
                    m.get('_simulated_move_adjusted_source', None) is None,
                    m.get('_simulated_move_adjusted_source', 0) or 0,
                ),
                m.get('_simulated_strength_delta', 0),
                m.get('_simulated_temporary_strength_delta', 0),
                bool(m.get('_simulated_weak_applied_to_attack', False)),
                m.get('move_hits', 1) or 1,
                str(m['intent']) if m['intent'] else None,  # Convert intent to string
                sortable_value(m.get('move_id', None)),
                m['is_gone'],
                sortable_value(m.get('monster_id', None)),
                sortable_value(m.get('name', None)),  # Include name for elite/boss identification
            )
            for m in self.monsters
            if not m['is_gone']  # Only include alive monsters
        ))

        # Hand cards (multi-set - sorted list of play-relevant card facts)
        # This represents what cards are available to play
        hand_key = tuple(sorted(
            (
                card_identity_for_key(c),
                sortable_text(getattr(c, 'upgrades', 0)),
                sortable_text(getattr(c, 'cost', 0)),
                sortable_text(getattr(c, 'cost_for_turn', getattr(c, 'cost', 0))),
            )
            for c in list(playable_cards or []) + list(getattr(self, 'added_hand_cards', []))
            if not is_card_played(self.played_card_uuids, c)
        ))

        return (player_key, monster_key, hand_key)

    def turn_block(self) -> int:
        """Block available by the time enemies attack this turn."""
        block = self.player_block + self.end_turn_block
        if self.has_orichalcum and block <= 0:
            block += 6
        return block


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

    @staticmethod
    def _non_negative_int(value) -> int:
        return max(0, coerce_int(value or 0, 0))

    def simulate_card_play(self, state: SimulationState, card: Card,
                          target: Optional[Monster] = None,
                          target_index: Optional[int] = None,
                          context: Optional[DecisionContext] = None) -> SimulationState:
        """
        Simulate playing a single card with accurate damage calculation.

        This simulation accounts for:
        - Actual card costs (cost_for_turn for Snecko Eye, etc.)
        - Strength power bonus
        - Vulnerable debuff (1.5x or Paper Phrog 1.75x damage)
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
        mark_card_played(new_state.played_card_uuids, card)
        self._remove_pending_end_turn_status(new_state, card)
        card_type = card_type_name(card)

        # Use actual cost (for Snecko Eye and other cost modifiers). X-cost
        # cards arrive as -1, but planning should spend all current energy.
        raw_cost = raw_card_cost(card)
        cost = effective_card_cost(card, new_state.player_energy)
        if card_type == 'SKILL' and new_state.corruption_active:
            cost = 0
        base_cost = raw_cost if raw_cost >= 0 else cost
        x_energy_spent = (
            x_effect_energy(card, cost, context)
            if is_x_cost_card(card)
            else None
        )

        # Track energy saved (for Corruption, etc.)
        energy_saved = base_cost - cost
        if energy_saved > 0:
            new_state.energy_saved += energy_saved

        new_state.player_energy -= cost
        new_state.energy_spent += cost
        starting_exhaust_events = new_state.exhaust_events
        card_play_repeats = 1
        if getattr(new_state, 'duplication_charges', 0) > 0:
            card_play_repeats = 2
            new_state.duplication_charges -= 1
        panache_active_before_card = new_state.panache_damage > 0

        # Check special monster abilities before applying card effects
        for i, monster in enumerate(new_state.monsters):
            if self._is_live_monster_state(monster):
                self._handle_death_split(new_state, monster, i)
                self._handle_summoner(new_state, monster)
                self._handle_phase_change(new_state, monster)
                self._handle_hibernation(new_state, monster)

        # Apply card effects based on type
        resolved_target_index = self._resolve_target_index(target, target_index, context)

        for _ in range(card_play_repeats):
            self._apply_slow_card_play(new_state)

            if card_type == 'ATTACK':
                attack_repeats = self._attack_replay_count(new_state, card, cost)
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
                    self._apply_ornamental_fan_block(new_state)
                    self._apply_self_damage(new_state, card)
            elif card_type == 'SKILL':
                new_state.skills_played += 1
                corruption_exhausts_skill = new_state.corruption_active
                self._apply_skill(
                    new_state,
                    card,
                    context,
                    resolved_target_index,
                    x_energy_spent=x_energy_spent,
                )
                self._apply_skill_reactive_monster_powers(new_state)
                self._apply_letter_opener_skill_play(new_state)
                if corruption_exhausts_skill and not self._skill_exhausts_itself(card):
                    new_state.exhaust_events += 1
            elif card_type == 'POWER':
                self._apply_power(new_state, card)
                self._apply_power_reactive_monster_powers(new_state)

            self._apply_hex_card_pollution(new_state, card_type)

            if card_type != 'ATTACK':
                self._apply_self_damage(new_state, card)
                self._apply_blue_candle_curse_hp_loss(new_state, card, context)

            if panache_active_before_card:
                self._apply_panache_card_play(new_state)

        self._apply_feel_no_pain_block(new_state, starting_exhaust_events)
        self._apply_dark_embrace_draw(new_state, starting_exhaust_events)
        self._apply_charons_ashes_damage(new_state, starting_exhaust_events)

        return new_state

    def _attack_replay_count(
        self,
        state: SimulationState,
        card: Card,
        cost: int,
    ) -> int:
        repeats = 1
        if state.double_tap_charges > 0:
            repeats *= 2
            state.double_tap_charges -= 1
        if self._necronomicon_replays_attack(state, card, cost):
            repeats *= 2
            state.necronomicon_available = False
        return repeats

    def _necronomicon_replays_attack(
        self,
        state: SimulationState,
        card: Card,
        cost: int,
    ) -> bool:
        return (
            getattr(state, 'necronomicon_available', False)
            and is_attack_card(card)
            and cost >= 2
        )

    def _apply_skill_reactive_monster_powers(self, state: SimulationState):
        """Apply monster reactions such as Gremlin Nob's Anger after Skill cards."""
        for monster in state.monsters:
            if not self._is_live_monster_state(monster):
                continue

            strength_gain = self._non_negative_int(monster.get('skill_strength_gain', 0))
            monster['skill_strength_gain'] = strength_gain
            if strength_gain <= 0:
                continue

            self._remember_monster_adjusted_damage_source(monster)
            monster['strength'] = monster.get('strength', 0) + strength_gain
            monster['_simulated_strength_delta'] = (
                monster.get('_simulated_strength_delta', 0) + strength_gain
            )
            self._refresh_monster_adjusted_damage_from_debuffs(monster)
            logger.debug(
                "[SKILL_REACTION] %s gained %s Strength from Skill",
                monster.get('name', 'Unknown'),
                strength_gain,
            )

    def _apply_power_reactive_monster_powers(self, state: SimulationState):
        """Apply monster reactions such as Awakened One's Curiosity after Powers."""
        for monster in state.monsters:
            if not self._is_live_monster_state(monster):
                continue

            strength_gain = self._non_negative_int(monster.get('power_strength_gain', 0))
            monster['power_strength_gain'] = strength_gain
            if strength_gain <= 0:
                continue

            self._remember_monster_adjusted_damage_source(monster)
            monster['strength'] = monster.get('strength', 0) + strength_gain
            monster['_simulated_strength_delta'] = (
                monster.get('_simulated_strength_delta', 0) + strength_gain
            )
            self._refresh_monster_adjusted_damage_from_debuffs(monster)
            logger.debug(
                "[POWER_REACTION] %s gained %s Strength from Power",
                monster.get('name', 'Unknown'),
                strength_gain,
            )

    def _apply_panache_card_play(self, state: SimulationState):
        if state.panache_damage <= 0:
            return

        counter = max(1, self._non_negative_int(state.panache_counter))
        if counter > 1:
            state.panache_counter = counter - 1
            return

        for monster in state.monsters:
            if self._is_live_monster_state(monster):
                self._deal_damage_to_monster(
                    state,
                    monster,
                    state.panache_damage,
                    trigger_thorns=False,
                )
        state.panache_counter = PANACHE_RESET_COUNT

    def _apply_letter_opener_skill_play(self, state: SimulationState):
        counter = getattr(state, 'letter_opener_counter', None)
        if counter is None:
            return

        counter = self._non_negative_int(counter)
        if counter < 2:
            state.letter_opener_counter = counter + 1
            return

        for monster in state.monsters:
            if self._is_live_monster_state(monster):
                self._deal_damage_to_monster(
                    state,
                    monster,
                    LETTER_OPENER_DAMAGE,
                    trigger_thorns=False,
                )
        state.letter_opener_counter = 0

    @staticmethod
    def _heal_player(state: SimulationState, amount: int):
        heal = max(0, coerce_int(amount, 0))
        if heal > 0:
            state.player_hp = min(state.player_max_hp, state.player_hp + heal)

    def _apply_bird_faced_urn_power_heal(self, state: SimulationState):
        if getattr(state, 'has_bird_faced_urn', False):
            self._heal_player(state, BIRD_FACED_URN_HEAL)

    def _apply_slow_card_play(self, state: SimulationState):
        """Giant Head's Slow gains a stack whenever the player plays a card."""
        for monster in state.monsters:
            if not self._is_live_monster_state(monster):
                continue
            if not monster.get('slow_active', False):
                continue
            monster['slow_stacks'] = self._non_negative_int(monster.get('slow_stacks', 0)) + 1

    def _apply_hex_card_pollution(self, state: SimulationState, card_type):
        """Chosen's Hex adds Dazed to the draw pile whenever a non-Attack is played."""
        player_hex = self._non_negative_int(getattr(state, 'player_hex', 0))
        state.player_hex = player_hex
        if player_hex <= 0:
            return
        normalized_card_type = card_type_name(card_type)
        if not normalized_card_type or normalized_card_type == 'ATTACK':
            return

        dazed_added = max(1, player_hex)
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
        if target is None or context is None:
            return target_index

        monsters = getattr(context, 'monsters_alive', []) or []
        for idx, monster in enumerate(monsters):
            if monster is target:
                return idx

        target_id = getattr(target, 'monster_id', None)
        live_target_index = getattr(target, 'monster_index', None)
        if (
            isinstance(live_target_index, int)
            and 0 <= live_target_index < len(monsters)
        ):
            monster = monsters[live_target_index]
            if (
                not target_id
                or getattr(monster, 'monster_id', None) == target_id
            ):
                return live_target_index

        target_name = getattr(target, 'name', None)
        target_hp = getattr(target, 'current_hp', None)
        id_candidates = []
        name_candidates = []
        for idx, monster in enumerate(monsters):
            monster_hp = getattr(monster, 'current_hp', None)
            hp_delta = 0
            if target_hp is not None and monster_hp is not None:
                hp_delta = abs(monster_hp - target_hp)

            if target_id and getattr(monster, 'monster_id', None) == target_id:
                id_candidates.append((hp_delta, idx))
            elif getattr(monster, 'name', None) == target_name and (
                target_hp is None or monster_hp == target_hp
            ):
                name_candidates.append((hp_delta, idx))

        for candidates in (id_candidates, name_candidates):
            if candidates:
                candidates.sort(key=lambda x: x[0])
                return candidates[0][1]

        return target_index

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
        dynamic_damage_card = card_name in {'Body Slam', 'Mind Blast', 'Whirlwind'}
        base_damage = self._non_negative_int(getattr(card, 'damage', 0))
        if dynamic_damage_card:
            base_damage = 0
        if base_damage == 0 or not hasattr(card, 'damage'):
            # Use game data for more accurate damage estimation
            card_data = game_data_loader.get_card_data(card_name)
            if card_data and not dynamic_damage_card:
                parsed_damage = game_data_loader._parse_card_damage(card_data)
                base_damage = parsed_damage if parsed_damage is not None else 0

                # Apply upgrade bonus if card is upgraded
                upgrades = card_upgrade_count(card)
                if upgrades > 0 and base_damage:
                    if card_name in card_upgrade_helpers.DAMAGE_UPGRADE_BONUS:
                        upgrade_bonus = card_upgrade_helpers.known_damage_upgrade_bonus(card, card_name)
                        base_damage += upgrade_bonus
                        logger.debug(f"[DAMAGE_UPGRADE] {card_name} (upgrades={upgrades}): {base_damage} damage (+{upgrade_bonus})")
                    else:
                        logger.debug(
                            f"[DAMAGE_UPGRADE_UNKNOWN] {card_name} "
                            f"(upgrades={upgrades}): {base_damage} damage "
                            "(no generic upgrade bonus)"
                        )

            # Check for X-damage cards and calculate dynamically
            if base_damage == 0 and context is not None:
                if x_energy_spent is not None:
                    setattr(state, '_current_x_energy_spent', x_energy_spent)
                try:
                    if card_name == 'Whirlwind' or x_energy_spent is not None:
                        base_damage = self._calculate_x_damage(
                            card,
                            state,
                            context,
                            x_energy_spent=x_energy_spent,
                            per_hit=card_name == 'Whirlwind',
                        )
                    else:
                        base_damage = self._calculate_x_damage(card, state, context)
                finally:
                    if x_energy_spent is not None and hasattr(state, '_current_x_energy_spent'):
                        delattr(state, '_current_x_energy_spent')
                if base_damage is None:
                    base_damage = 0

            if base_damage == 0 and not dynamic_damage_card:
                base_damage = 6  # Fallback estimate for truly unknown cards

        base_damage += self._rampage_damage_bonus(state, card)
        pen_nib_multiplier = self._pen_nib_attack_multiplier(state, consume=True)
        self._apply_nunchaku_attack_energy(state)

        # Handle AOE attacks
        card_data = game_data_loader.get_card_data(card_name)
        is_aoe = False
        if card_data:
            is_aoe = game_data_loader._is_card_aoe(card_data)
        # Also check known AOE cards by name
        if card_name in IRONCLAD_AOE_ATTACK_CARDS:
            is_aoe = True
        hit_count = self._get_attack_hit_count(
            card,
            state,
            context,
            x_energy_spent=x_energy_spent,
        )
        starting_total_damage = state.total_damage_dealt
        target_was_live_at_attack_start = False

        if is_aoe:
            # AOE - apply to all monsters
            for monster in state.monsters:
                if not self._is_live_monster_state(monster):
                    continue
                flight_hit_pending = False
                for _ in range(hit_count):
                    if not self._is_live_monster_state(monster):
                        break
                    damage = self._calculate_attack_damage(card, base_damage, state, context)
                    damage *= pen_nib_multiplier
                    damage = self._apply_player_attack_damage_modifiers(
                        damage,
                        state,
                        monster,
                        context,
                    )
                    damage = self._apply_slow_attack_damage(damage, monster)
                    hp_damage = self._deal_damage_to_monster(
                        state,
                        monster,
                        damage,
                        defer_curl_up_block=hit_count > 1,
                        defer_malleable_block=hit_count > 1,
                        apply_the_boot=True,
                        defer_flight_hit=hit_count > 1,
                    )
                    if hp_damage > 0 and self._is_live_monster_state(monster):
                        flight_hit_pending = True
                    state.damage_instances += 1  # Track each damage instance
                if flight_hit_pending:
                    self._apply_flight_hit(monster)
                self._flush_deferred_reactive_block(monster)
            if card_data:
                description = self._get_card_effect_text(card_name, card_data)
                upgraded = is_card_upgraded(card)
                debuff_effects = self._description_debuff_effects(description, upgraded, card_name)
                if debuff_effects:
                    for monster in state.monsters:
                        if not self._is_live_monster_state(monster):
                            continue
                        self._apply_monster_debuffs(monster, debuff_effects)
        elif self._is_random_target_attack(card) and target_index is None:
            pending_flight_hits = []
            for hit_index in range(hit_count):
                alive_monsters = [
                    monster for monster in state.monsters
                    if self._is_live_monster_state(monster)
                ]
                if not alive_monsters:
                    break
                monster = alive_monsters[hit_index % len(alive_monsters)]
                damage = self._calculate_attack_damage(card, base_damage, state, context)
                damage *= pen_nib_multiplier
                damage = self._apply_player_attack_damage_modifiers(
                    damage,
                    state,
                    monster,
                    context,
                )
                damage = self._apply_slow_attack_damage(damage, monster)
                hp_damage = self._deal_damage_to_monster(
                    state,
                    monster,
                    damage,
                    defer_curl_up_block=hit_count > 1,
                    defer_malleable_block=hit_count > 1,
                    apply_the_boot=True,
                    defer_flight_hit=hit_count > 1,
                )
                if (
                    hp_damage > 0
                    and self._is_live_monster_state(monster)
                    and monster not in pending_flight_hits
                ):
                    pending_flight_hits.append(monster)
                state.damage_instances += 1
            for monster in pending_flight_hits:
                self._apply_flight_hit(monster)
            for monster in state.monsters:
                self._flush_deferred_reactive_block(monster)
        else:
            # Single-target attack
            if target_index is not None and 0 <= target_index < len(state.monsters):
                monster = state.monsters[target_index]
                target_was_live_at_attack_start = self._is_live_monster_state(monster)
                if target_was_live_at_attack_start:
                    target_hit_count = self._get_attack_hit_count_against_monster(
                        card,
                        hit_count,
                        monster,
                    )
                    flight_hit_pending = False
                    if card_name == 'Melter':
                        monster['block'] = 0
                    for _ in range(target_hit_count):
                        if not self._is_live_monster_state(monster):
                            break
                        damage = self._calculate_attack_damage(card, base_damage, state, context)
                        damage *= pen_nib_multiplier
                        damage = self._apply_player_attack_damage_modifiers(
                            damage,
                            state,
                            monster,
                            context,
                        )
                        damage = self._apply_slow_attack_damage(damage, monster)
                        hp_damage = self._deal_damage_to_monster(
                            state,
                            monster,
                            damage,
                            defer_curl_up_block=target_hit_count > 1,
                            defer_malleable_block=target_hit_count > 1,
                            apply_the_boot=True,
                            defer_flight_hit=target_hit_count > 1,
                        )
                        if hp_damage > 0 and self._is_live_monster_state(monster):
                            flight_hit_pending = True
                        state.damage_instances += 1  # Track damage instance
                    if flight_hit_pending:
                        self._apply_flight_hit(monster)
                    self._flush_deferred_reactive_block(monster)

                    # Check for card effects using game data
                    if card_data:
                        description = self._get_card_effect_text(card_name, card_data)
                        upgraded = is_card_upgraded(card)
                        self._apply_monster_debuffs(
                            monster,
                            self._description_debuff_effects(description, upgraded, card_name),
                        )

        self._apply_attack_healing(state, card, starting_total_damage)
        self._apply_attack_resource_effects(
            state,
            card,
            target_index,
            target_was_live_at_attack_start,
        )
        self._apply_attack_draw_effects(state, card, card_data)
        self._apply_attack_block_effects(state, card, card_data)
        self._apply_attack_exhaust_effects(state, card, context, card_data)
        self._apply_card_status_pollution(state, card, card_data)
        self._apply_rampage_scaling(state, card)

    def _rampage_damage_bonus(self, state: SimulationState, card: Card) -> int:
        if _canonical_card_name(card) != 'Rampage':
            return 0
        card_key = card_play_key(card)
        return state.rampage_damage_bonus_by_card.get(card_key, 0)

    def _apply_rampage_scaling(self, state: SimulationState, card: Card):
        if _canonical_card_name(card) != 'Rampage':
            return
        card_key = card_play_key(card)
        state.rampage_damage_bonus_by_card[card_key] = (
            state.rampage_damage_bonus_by_card.get(card_key, 0)
            + (8 if is_card_upgraded(card) else 5)
        )

    def _get_attack_hit_count(
        self,
        card: Card,
        state: SimulationState,
        context: Optional[DecisionContext] = None,
        x_energy_spent: Optional[int] = None,
    ) -> int:
        """Return known hit counts for repeated-hit attacks."""
        card_name = _canonical_card_name(card)

        if card_name in {'Skewer', 'Whirlwind'}:
            energy = x_energy_spent
            if energy is None:
                energy = getattr(state, '_current_x_energy_spent', None)
            if energy is None:
                energy = x_effect_energy(card, getattr(state, 'player_energy', 0), context)
            return max(0, energy)
        fixed_hit_count = fixed_attack_hit_count(card)
        if fixed_hit_count is not None:
            return fixed_hit_count
        if card_name == 'Fiend Fire' and context is not None:
            return len(self._unplayed_hand_cards(state, context, exclude_card=card))

        return 1

    def _is_random_target_attack(self, card: Card) -> bool:
        card_name = _canonical_card_name(card)
        return card_name in {'Sword Boomerang'}

    def _get_attack_hit_count_against_monster(
        self,
        card: Card,
        hit_count: int,
        monster: dict,
    ) -> int:
        card_name = _canonical_card_name(card)
        if card_name == 'Bane' and monster.get('poison', 0) > 0:
            return 2
        return hit_count

    def _apply_attack_healing(self, state: SimulationState, card: Card, starting_total_damage: int):
        card_name = _canonical_card_name(card)
        if card_name == 'Bite':
            heal_amount = 3 if is_card_upgraded(card) else 2
            state.player_hp = min(state.player_max_hp, state.player_hp + heal_amount)
            return

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
        target_was_live_at_attack_start: bool,
    ):
        card_name = _canonical_card_name(card)
        if not target_was_live_at_attack_start:
            return

        if card_name == 'Dropkick':
            if target_index is None or not (0 <= target_index < len(state.monsters)):
                return
            if state.monsters[target_index].get('vulnerable', 0) <= 0:
                return

            state.player_energy += 1
            state.energy_gained += 1
            self._add_card_draw(state, 1)
            return

        if card_name == 'Feed':
            self._apply_feed_max_hp_gain(state, card, target_index)

    def _apply_feed_max_hp_gain(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int],
    ):
        if target_index is None or not (0 <= target_index < len(state.monsters)):
            return

        monster = state.monsters[target_index]
        if not monster.get('is_gone', False) or monster.get('half_dead', False):
            return
        if self._is_minion_monster_state(monster):
            return

        max_hp_gain = 4 if is_card_upgraded(card) else 3
        state.player_max_hp += max_hp_gain
        state.player_hp = min(state.player_max_hp, state.player_hp + max_hp_gain)

    @staticmethod
    def _is_minion_monster_state(monster: dict) -> bool:
        return bool(monster.get('is_minion', False) or monster.get('minion', False))

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

        upgraded = is_card_upgraded(card)
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

        if is_card_upgraded(card):
            block_gain += card_upgrade_helpers.known_block_upgrade_bonus(card, card_name)

        self._add_player_block(
            state,
            self._apply_card_block_modifiers(block_gain, state),
            from_card=True,
        )

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
                if not is_attack_card(hand_card)
            ]
            state.exhaust_events += len(exhausted_cards)
            self._mark_cards_unavailable(state, exhausted_cards)
            self._apply_sentinel_exhaust_energy(state, exhausted_cards)

        if card_data:
            description = self._get_card_effect_text(card_name, card_data)
            if self._card_exhausts_itself(description, is_card_upgraded(card)):
                state.exhaust_events += 1

    def _apply_sentinel_exhaust_energy(self, state: SimulationState, exhausted_cards: List[Card]):
        energy_gain = 0
        for exhausted_card in exhausted_cards:
            card_name = _canonical_card_name(exhausted_card)
            if card_name != 'Sentinel':
                continue

            energy_gain += 3 if is_card_upgraded(exhausted_card) else 2

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
        hand_cards = list(hand_cards or []) + list(getattr(state, 'added_hand_cards', []))

        cards = []
        exclude_key = card_play_key(exclude_card)
        for hand_card in hand_cards:
            card_key = card_play_key(hand_card)
            if hand_card is exclude_card or (exclude_key is not None and card_key == exclude_key):
                continue
            if is_card_played(state.played_card_uuids, hand_card):
                continue
            cards.append(hand_card)
        return cards

    def _mark_cards_unavailable(self, state: SimulationState, cards: List[Card]):
        for card in cards:
            self._record_added_hand_status_exhausted(state, card)
            self._remove_pending_end_turn_status(state, card)
            mark_card_played(state.played_card_uuids, card)

    def _effect_text_for_upgrade(self, description: str, upgraded: bool) -> str:
        return _select_effect_text_for_upgrade(description, upgraded)

    def _card_exhausts_itself(self, description: str, upgraded: bool = False) -> bool:
        description = self._effect_text_for_upgrade(description, upgraded)
        description = (description or '').lower().replace('#', '')
        if any(line.strip() in {'exhaust', 'exhaust.'} for line in description.splitlines()):
            return True
        return bool(re.search(r'\bexhaust\.\s*$', description))

    def _skill_hand_exhaust_count_from_description(self, description: str, upgraded: bool = False) -> int:
        description = self._effect_text_for_upgrade(description, upgraded)
        description = (description or '').lower().replace('#', '')
        match = re.search(r'\bexhaust\s+(?:(\d+)|a|an)\s+cards?\b', description)
        if not match:
            return 0
        return max(1, int(match.group(1) or 1))

    def _skill_hand_exhaust_cards(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext],
        description: str,
        upgraded: bool = False,
    ) -> List[Card]:
        exhaust_count = self._skill_hand_exhaust_count_from_description(description, upgraded)
        if exhaust_count <= 0 or context is None:
            return []
        return self._unplayed_hand_cards(state, context, exclude_card=card)[:exhaust_count]

    def _skill_exhaust_events_from_description(self, description: str, upgraded: bool = False) -> int:
        description = self._effect_text_for_upgrade(description, upgraded)
        description = (description or '').lower().replace('#', '')
        if not description:
            return 0
        if self._card_exhausts_itself(description):
            return 1
        return self._skill_hand_exhaust_count_from_description(description)

    def _skill_exhausts_itself(self, card: Card) -> bool:
        card_name = _canonical_card_name(card)
        card_data = game_data_loader.get_card_data(card_name)
        if not card_data:
            return False
        return self._card_exhausts_itself(
            self._get_card_effect_text(card_name, card_data),
            is_card_upgraded(card),
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
        if card_name == 'Ritual Dagger':
            base_damage += self._positive_card_misc(card)

        if card_name == 'Heavy Blade':
            return max(0, base_damage + state.player_strength * heavy_blade_strength_multiplier(card))

        if card_name == 'Perfected Strike':
            return max(
                0,
                base_damage
                + strike_card_count(context) * perfected_strike_bonus_per_strike(card)
                + state.player_strength,
            )

        return max(0, base_damage + state.player_strength)

    def _pen_nib_attack_multiplier(self, state: Any, consume: bool = False) -> int:
        counter = getattr(state, 'pen_nib_counter', None)
        if counter is None:
            return 1

        counter = self._non_negative_int(counter)
        if counter >= 9:
            if consume:
                state.pen_nib_counter = 0
            return 2

        if consume:
            state.pen_nib_counter = min(9, counter + 1)
        return 1

    def _apply_nunchaku_attack_energy(self, state: SimulationState):
        counter = getattr(state, 'nunchaku_counter', None)
        if counter is None:
            return

        counter = self._non_negative_int(counter)
        if counter >= 9:
            state.nunchaku_counter = 0
            state.player_energy += 1
            state.energy_gained += 1
            return

        state.nunchaku_counter = min(9, counter + 1)

    @staticmethod
    def _positive_card_misc(card: Card) -> int:
        try:
            return max(0, int(getattr(card, 'misc', 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _apply_player_attack_damage_modifiers(
        self,
        damage: int,
        state: SimulationState,
        monster: dict,
        context: DecisionContext = None,
    ) -> int:
        """Apply player Weak and target Vulnerable with one final truncation."""
        if damage <= 0:
            return 0

        player_weak = getattr(state, 'player_weak', 0)
        target_vulnerable = self._non_negative_int(monster.get('vulnerable', 0)) > 0
        if player_weak > 0 and target_vulnerable:
            numerator, denominator = (
                (21, 16)
                if self._context_has_relic(context, 'Paper Phrog')
                else (9, 8)
            )
            return self._apply_damage_multiplier(damage, numerator, denominator)

        if player_weak > 0:
            damage = self._apply_weak_damage(damage, player_weak)
        if target_vulnerable:
            damage = self._apply_vulnerable_damage(damage, monster, context)
        return damage

    def _apply_vulnerable_damage(
        self,
        damage: int,
        monster: dict,
        context: DecisionContext = None,
    ) -> int:
        """Apply target Vulnerable. Binary: any vulnerable stacks multiply damage."""
        if self._non_negative_int(monster.get('vulnerable', 0)) > 0:
            numerator, denominator = (
                (7, 4)
                if self._context_has_relic(context, 'Paper Phrog')
                else (3, 2)
            )
            return self._apply_damage_multiplier(damage, numerator, denominator)
        return damage

    @staticmethod
    def _apply_damage_multiplier(damage: int, numerator: int, denominator: int) -> int:
        return damage * numerator // denominator

    def _apply_slow_attack_damage(self, damage: int, monster: dict) -> int:
        """Apply Giant Head Slow's attack-damage multiplier."""
        slow_stacks = int(monster.get('slow_stacks', 0) or 0)
        if slow_stacks <= 0 or damage <= 0:
            return damage
        return int(damage * (1 + 0.1 * slow_stacks))

    @staticmethod
    def _apply_the_boot_minimum_attack_damage(
        state: SimulationState,
        hp_damage: int,
    ) -> int:
        hp_damage = max(0, coerce_int(hp_damage, 0))
        if (
            getattr(state, 'has_the_boot', False)
            and 0 < hp_damage < THE_BOOT_MINIMUM_DAMAGE
        ):
            return THE_BOOT_MINIMUM_DAMAGE
        return hp_damage

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

    @staticmethod
    def _context_has_relic(context: DecisionContext, relic_name: str) -> bool:
        target = ''.join(ch for ch in relic_name.lower() if ch.isalnum())
        if not context or not target:
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

    def _consume_monster_artifact(self, monster: dict) -> bool:
        artifact = monster.get('artifact', 0)
        if artifact <= 0:
            return False
        monster['artifact'] = artifact - 1
        return True

    def _consume_player_artifact(self, state: SimulationState) -> bool:
        artifact = getattr(state, 'player_artifact', 0)
        if artifact <= 0:
            return False
        state.player_artifact = artifact - 1
        return True

    def _apply_monster_debuff(self, monster: dict, debuff: str, stacks: int):
        if stacks <= 0:
            return
        if self._consume_monster_artifact(monster):
            return
        previous_stacks = monster.get(debuff, 0)
        monster[debuff] = previous_stacks + stacks
        if (
            debuff == 'weak'
            and previous_stacks <= 0
            and self._monster_intends_attack(monster)
        ):
            self._remember_monster_adjusted_damage_source(monster)
            monster['_simulated_weak_applied_to_attack'] = True
            self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _remember_monster_adjusted_damage_source(self, monster: dict):
        if '_simulated_move_adjusted_source' in monster:
            return
        raw_damage = monster.get('move_adjusted_damage', None)
        if isinstance(raw_damage, (int, float)):
            monster['_simulated_move_adjusted_source'] = max(0, raw_damage)

    def _effective_monster_attack_strength(self, monster: dict) -> int:
        return (
            monster.get('strength', 0)
            + monster.get('_simulated_temporary_strength_delta', 0)
        )

    def _refresh_monster_adjusted_damage_from_debuffs(self, monster: dict):
        if not self._monster_intends_attack(monster):
            return

        raw_base_damage = monster.get('move_base_damage', 0)
        if isinstance(raw_base_damage, (int, float)) and raw_base_damage > 0:
            damage = self._apply_monster_strength_to_per_hit_damage(
                raw_base_damage,
                self._effective_monster_attack_strength(monster),
            )
            monster['move_adjusted_damage'] = self._apply_monster_weak_to_per_hit_damage(
                damage,
                monster.get('weak', 0),
            )
            return

        source_damage = monster.get('_simulated_move_adjusted_source', None)
        if not isinstance(source_damage, (int, float)):
            return
        damage = max(
            0,
            source_damage + monster.get('_simulated_strength_delta', 0),
        )
        if monster.get('_simulated_weak_applied_to_attack', False):
            damage = self._apply_monster_weak_to_per_hit_damage(damage, 1)
        monster['move_adjusted_damage'] = damage

    def _apply_monster_poison(self, monster: dict, stacks: int):
        if stacks <= 0:
            return
        if self._consume_monster_artifact(monster):
            return
        monster['poison'] = monster.get('poison', 0) + stacks

    def _apply_player_vulnerable_debuff(self, state: SimulationState, stacks: int) -> bool:
        if stacks <= 0:
            return False
        if self._consume_player_artifact(state):
            return False
        state.player_vulnerable += stacks
        state.player_vulnerable_added += stacks
        return True

    def _queue_player_predicted_debuffs(
        self,
        pending_debuffs: Dict[str, int],
        move_debuffs: Dict[str, int],
        player_artifact: int,
    ) -> int:
        for debuff in ('weak', 'frail', 'vulnerable'):
            stacks = move_debuffs.get(debuff, 0)
            if stacks <= 0:
                continue
            if player_artifact > 0:
                player_artifact -= 1
                continue
            pending_debuffs[debuff] += stacks
        return player_artifact

    def _description_debuff_effects(
        self,
        description: str,
        upgraded: bool,
        card_name: str = '',
        x_energy_spent: Optional[int] = None,
    ) -> List[Tuple[int, str, int]]:
        effects = []
        for debuff in ('weak', 'vulnerable', 'poison'):
            if debuff not in description:
                continue
            stacks = self._extract_debuff_stacks(description, debuff, upgraded)
            if stacks is None:
                stacks = self._extract_x_debuff_stacks(
                    description,
                    debuff,
                    upgraded,
                    x_energy_spent,
                )
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
        enemy_strength_loss = self._enemy_strength_loss_effect(
            description,
            upgraded,
            x_energy_spent,
        )
        if enemy_strength_loss:
            position, stacks, temporary = enemy_strength_loss
            debuff = 'temporary_strength_down' if temporary else 'strength_down'
            effects.append((position, debuff, stacks))
        effects.sort(key=lambda effect: effect[0])
        return effects

    def _x_or_numeric_stack_value(
        self,
        token: str,
        x_energy_spent: Optional[int],
    ) -> Optional[int]:
        token = (token or '').lower().replace(' ', '')
        if token.isdigit():
            return int(token)
        if x_energy_spent is None:
            return None
        if token == 'x':
            return max(0, x_energy_spent)
        if token == 'x+1':
            return max(0, x_energy_spent) + 1
        return None

    def _extract_x_debuff_stacks(
        self,
        description: str,
        keyword: str,
        upgraded: bool,
        x_energy_spent: Optional[int],
    ) -> Optional[int]:
        if x_energy_spent is None:
            return None

        effect_text = self._effect_text_for_upgrade(description, upgraded)
        effect_text = (effect_text or '').lower().replace('#', '')
        keyword_pattern = re.escape(keyword)
        x_token = r'(x(?:\s*\+\s*1)?)'
        patterns = [
            rf'{keyword_pattern}\s*{x_token}',
            rf'{x_token}\s*{keyword_pattern}',
            rf'apply\s*{x_token}\s*{keyword_pattern}',
        ]
        for pattern in patterns:
            match = re.search(pattern, effect_text)
            if match:
                return self._x_or_numeric_stack_value(
                    match.group(1),
                    x_energy_spent,
                )
        return None

    def _enemy_strength_loss_effect(
        self,
        description: str,
        upgraded: bool,
        x_energy_spent: Optional[int] = None,
    ) -> Optional[Tuple[int, int, bool]]:
        effect_text = self._effect_text_for_upgrade(description, upgraded)
        effect_text = (effect_text or '').lower().replace('#', '')
        match = re.search(
            r'\b(?:all\s+)?enem(?:y|ies)\s+los(?:e|es)\s+'
            r'(\d+|x(?:\s*\+\s*1)?)\s+strength\b',
            effect_text,
        )
        if not match:
            return None
        stacks = self._x_or_numeric_stack_value(match.group(1), x_energy_spent)
        if not stacks:
            return None

        sentence_tail = effect_text[match.start():]
        sentence_end = re.search(r'[\.\n]', sentence_tail)
        sentence = sentence_tail[:sentence_end.start()] if sentence_end else sentence_tail
        temporary = 'this turn' in sentence
        return match.start(), stacks, temporary

    def _apply_monster_strength_down(self, monster: dict, stacks: int):
        if stacks <= 0:
            return
        if self._consume_monster_artifact(monster):
            return

        self._remember_monster_adjusted_damage_source(monster)
        monster['strength'] = monster.get('strength', 0) - stacks
        monster['_simulated_strength_delta'] = (
            monster.get('_simulated_strength_delta', 0) - stacks
        )
        self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _apply_monster_temporary_strength_down(self, monster: dict, stacks: int):
        if stacks <= 0:
            return
        if self._consume_monster_artifact(monster):
            return
        self._remember_monster_adjusted_damage_source(monster)
        monster['_simulated_strength_delta'] = (
            monster.get('_simulated_strength_delta', 0) - stacks
        )
        monster['_simulated_temporary_strength_delta'] = (
            monster.get('_simulated_temporary_strength_delta', 0) - stacks
        )
        self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _apply_monster_debuffs(self, monster: dict, effects: List[Tuple[int, str, int]]):
        for _, debuff, stacks in effects:
            if debuff == 'strength_down':
                self._apply_monster_strength_down(monster, stacks)
            elif debuff == 'temporary_strength_down':
                self._apply_monster_temporary_strength_down(monster, stacks)
            elif debuff == 'poison':
                self._apply_monster_poison(monster, stacks)
            else:
                self._apply_monster_debuff(monster, debuff, stacks)

    def _apply_random_enemy_debuffs(
        self,
        state: SimulationState,
        effects: List[Tuple[int, str, int]],
        repeat_count: int,
    ):
        for _ in range(max(1, repeat_count)):
            alive_monsters = [
                monster for monster in state.monsters
                if self._is_live_monster_state(monster)
            ]
            if not alive_monsters:
                return
            monster = min(alive_monsters, key=lambda m: m.get('hp', 0))
            self._apply_monster_debuffs(monster, effects)

    def _extract_effect_repeat_count(self, description: str, upgraded: bool) -> int:
        effect_text = self._effect_text_for_upgrade(description, upgraded).lower()
        match = re.search(r'\b(\d+)\s+times\b', effect_text)
        if match:
            return int(match.group(1))
        return 1

    def _get_card_effect_text(self, card_name: str, card_data: Dict[str, Any]) -> str:
        """Prefer wiki text for effect values because items.json stores base text only."""
        base_card_name = canonical_card_name(card_name).lower()
        try:
            if getattr(game_data_loader, '_wiki_data', None) is None:
                game_data_loader._load_wiki_data()
            wiki_entry = getattr(game_data_loader, '_wiki_data', {}).get(base_card_name)
            if wiki_entry and wiki_entry.get('text'):
                return wiki_entry['text'].lower()
        except Exception:
            pass

        return card_data.get('description', '').lower()

    def _extract_card_status_pollution(self, description: str, upgraded: bool = False) -> Dict[str, int]:
        text = self._effect_text_for_upgrade(description, upgraded).lower()
        text = text.replace('#', '').replace('*', '')
        status_patterns = {
            'dazed': r'dazed',
            'burn': r'burns?',
            'slimed': r'slimed',
            'wound': r'wounds?',
        }
        counts = {}
        for status, pattern in status_patterns.items():
            total = 0
            for match in re.finditer(
                rf'\b(?:add|shuffle)\s+(?:(\d+)|a|an)\s+{pattern}\b',
                text,
                re.IGNORECASE,
            ):
                total += int(match.group(1) or 1)
            counts[status] = total
        counts['total'] = sum(counts.values())
        return counts

    def _apply_card_status_pollution(
        self,
        state: SimulationState,
        card: Card,
        card_data: Optional[Dict[str, Any]] = None,
    ):
        card_name = _canonical_card_name(card)
        if card_data is None:
            card_data = game_data_loader.get_card_data(card_name)
        if not card_data:
            return

        description = self._get_card_effect_text(card_name, card_data)
        upgraded = is_card_upgraded(card)
        counts = self._extract_card_status_pollution(
            description,
            upgraded,
        )
        if counts['total'] <= 0:
            return

        state.status_cards_added += counts['total']
        state.dazed_cards_added += counts['dazed']
        self._add_hand_status_cards(
            state,
            self._extract_hand_status_additions(description, upgraded),
        )

    def _extract_hand_status_additions(
        self,
        description: str,
        upgraded: bool = False,
    ) -> Dict[str, int]:
        text = self._effect_text_for_upgrade(description, upgraded).lower()
        text = text.replace('#', '').replace('*', '')
        status_patterns = {
            'dazed': r'dazed',
            'burn': r'burns?',
            'slimed': r'slimed',
            'wound': r'wounds?',
        }
        counts = {}
        for status, pattern in status_patterns.items():
            total = 0
            for match in re.finditer(
                rf'\badd\s+(?:(\d+)|a|an)\s+{pattern}\s+(?:into|to)\s+your\s+hand\b',
                text,
                re.IGNORECASE,
            ):
                total += int(match.group(1) or 1)
            counts[status] = total
        return counts

    def _add_hand_status_cards(self, state: SimulationState, counts: Dict[str, int]):
        if not hasattr(state, 'added_hand_cards'):
            state.added_hand_cards = []
        status_names = {
            'dazed': 'Dazed',
            'burn': 'Burn',
            'slimed': 'Slimed',
            'wound': 'Wound',
        }
        for status, count in counts.items():
            status_name = status_names.get(status)
            if not status_name or count <= 0:
                continue
            for _ in range(count):
                unique_index = len(state.added_hand_cards)
                state.added_hand_cards.append(
                    SimpleNamespace(
                        card_id=status_name,
                        name=status_name,
                        card_type='STATUS',
                        type='STATUS',
                        cost=-2,
                        cost_for_turn=-2,
                        has_target=False,
                        is_playable=False,
                        uuid=f"sim-hand-{status}-{unique_index}",
                        simulated_added_status=status,
                    )
                )
                if status == 'burn':
                    state.end_turn_status_damage += 2
                elif status == 'dazed':
                    state.end_turn_exhaust_events += 1

    def _record_added_hand_status_exhausted(self, state: SimulationState, card: Card):
        status = getattr(card, 'simulated_added_status', None)
        if not status:
            return
        state.status_cards_added = max(0, getattr(state, 'status_cards_added', 0) - 1)
        if status == 'dazed':
            state.dazed_cards_added = max(0, getattr(state, 'dazed_cards_added', 0) - 1)

    @staticmethod
    def _remove_pending_end_turn_status(state: SimulationState, card: Card):
        status_damage = SimulationState.end_turn_status_damage_for_card(card)
        if status_damage > 0:
            state.end_turn_status_damage = max(
                0,
                getattr(state, 'end_turn_status_damage', 0) - status_damage,
            )

        status_hp_loss = SimulationState.end_turn_status_hp_loss_for_card(card)
        if status_hp_loss > 0:
            state.end_turn_status_hp_loss = max(
                0,
                getattr(state, 'end_turn_status_hp_loss', 0) - status_hp_loss,
            )

        if SimulationState.end_turn_exhausts_for_card(card):
            state.end_turn_exhaust_events = max(
                0,
                getattr(state, 'end_turn_exhaust_events', 0) - 1,
            )

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
        """Apply Frail to card block values before a card gains block."""
        if player_frail > 0:
            return int(block * 0.75)
        return block

    def _add_player_block(
        self,
        state: SimulationState,
        block_gain: int,
        from_card: bool = False,
    ):
        if block_gain <= 0:
            return
        if from_card and getattr(state, 'card_block_blocked', False):
            return
        state.player_block += block_gain
        self._apply_juggernaut_block_damage(state)

    def _apply_juggernaut_block_damage(self, state: SimulationState):
        damage = max(0, getattr(state, 'juggernaut_damage_on_block', 0))
        if damage <= 0:
            return

        alive_monsters = [
            monster
            for monster in state.monsters
            if self._is_live_monster_state(monster)
        ]
        if not alive_monsters:
            return

        monster = min(alive_monsters, key=lambda m: m.get('hp', 0))
        self._deal_damage_to_monster(state, monster, damage, trigger_thorns=False)
        state.damage_instances += 1

    def _apply_card_block_modifiers(self, block: int, state: SimulationState) -> int:
        """Apply player modifiers for block gained by a card."""
        block = self._non_negative_int(block)
        block_with_dexterity = max(0, block + getattr(state, 'player_dexterity', 0))
        return self._apply_frail_block(block_with_dexterity, state.player_frail)

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
            weak_expired = False
            for debuff in ('weak', 'vulnerable', 'frail'):
                if monster.get(debuff, 0) > 0:
                    previous_stacks = monster[debuff]
                    monster[debuff] = max(0, previous_stacks - 1)
                    if debuff == 'weak' and monster[debuff] == 0:
                        weak_expired = True
            temporary_strength_delta = monster.pop(
                '_simulated_temporary_strength_delta',
                0,
            )
            if temporary_strength_delta:
                monster['_simulated_strength_delta'] = (
                    monster.get('_simulated_strength_delta', 0)
                    - temporary_strength_delta
                )
                if monster.get('_simulated_strength_delta') == 0:
                    monster.pop('_simulated_strength_delta', None)
                self._refresh_monster_adjusted_damage_from_debuffs(monster)
            if weak_expired:
                monster.pop('_simulated_weak_applied_to_attack', None)
                self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _extract_move_debuffs(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> Dict[str, int]:
        """Extract debuff stacks applied to the player from a monster move."""
        def _get_stack(key: str) -> int:
            value = move.get(key, 0)
            if isinstance(value, bool):
                return 1 if value else 0
            if isinstance(value, (int, float)):
                return int(value)
            return 0

        def _random_debuff_risk() -> Tuple[Optional[str], int]:
            raw_candidates = move.get('random_debuff', [])
            if isinstance(raw_candidates, str):
                candidates = [raw_candidates]
            elif isinstance(raw_candidates, list):
                candidates = raw_candidates
            else:
                candidates = []

            normalized = {
                str(candidate).strip().lower()
                for candidate in candidates
            }
            if not normalized:
                return None, 0

            stacks = (
                _get_stack('debuff_count')
                or _get_stack('random_debuff_count')
                or 1
            )
            if context is not None:
                stacks = self._apply_ascension_move_value(
                    move,
                    context,
                    'debuff_count',
                    stacks,
                )
            if stacks <= 0:
                return None, 0

            for debuff in ('vulnerable', 'frail', 'weak'):
                if debuff in normalized:
                    return debuff, stacks
            return None, 0

        debuffs = {
            'weak': _get_stack('weak') or _get_stack('weak_applied') or _get_stack('weak_amount'),
            'frail': _get_stack('frail') or _get_stack('frail_applied') or _get_stack('frail_amount'),
            'vulnerable': _get_stack('vulnerable') or _get_stack('vulnerable_applied') or _get_stack('vulnerable_amount'),
        }
        random_debuff, random_stacks = _random_debuff_risk()
        if random_debuff is not None:
            debuffs[random_debuff] = max(debuffs[random_debuff], random_stacks)
        if context is None:
            return debuffs

        for debuff in ('weak', 'frail', 'vulnerable'):
            debuffs[debuff] = self._apply_ascension_move_value(move, context, debuff, debuffs[debuff])
            debuffs[debuff] = self._apply_ascension_move_value(
                move,
                context,
                f'{debuff}_applied',
                debuffs[debuff],
            )
            debuffs[debuff] = self._apply_ascension_move_value(
                move,
                context,
                f'{debuff}_amount',
                debuffs[debuff],
            )
        return debuffs

    def _extract_move_strength_gain(self, move: Dict[str, Any], context: Optional[DecisionContext] = None) -> int:
        """Extract monster Strength gained by a predicted move."""
        modifier_key = 'strength_gain'
        value = move.get('strength_gain')
        if value is None and 'ritual_gain' in move:
            modifier_key = 'ritual_gain'
            value = move.get('ritual_gain', 0)
        if isinstance(value, bool):
            strength_gain = 0
        elif isinstance(value, (int, float)):
            strength_gain = max(0, int(value))
        elif isinstance(value, dict):
            numeric_values = [
                int(v) for v in value.values()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            strength_gain = max(numeric_values, default=0)
        else:
            strength_gain = 0

        if context is None:
            return strength_gain
        return max(0, self._apply_ascension_move_value(
            move,
            context,
            modifier_key,
            strength_gain,
        ))

    def _extract_move_all_enemies_strength_gain(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Extract Strength gained by every monster from a predicted move."""
        value = move.get('all_enemies_strength_gain')
        modifier_key = 'all_enemies_strength_gain'
        if value is None:
            effect = str(move.get('effect') or move.get('description') or '')
            if not re.search(r'\ball\s+enemies\s+gain\b.*\bstrength\b', effect, re.IGNORECASE):
                return 0
            value = move.get('strength_gain', 0)
            modifier_key = 'strength_gain'

        strength_gain = self._positive_numeric_move_value(value)
        if context is None:
            return strength_gain
        return max(0, self._apply_ascension_move_value(
            move,
            context,
            modifier_key,
            strength_gain,
        ))

    def _extract_move_constricted(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Extract Constricted stacks applied to the player from a monster move."""
        constricted = 0
        for key in ('constricted', 'constricted_applied', 'constricted_amount'):
            constricted = self._positive_numeric_move_value(move.get(key))
            if constricted > 0:
                break
        if constricted <= 0 or context is None:
            return constricted

        for key in ('constricted', 'constricted_applied', 'constricted_amount'):
            constricted = self._apply_ascension_move_value(
                move,
                context,
                key,
                constricted,
            )
        return max(0, constricted)

    def _extract_move_hex(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Extract Hex stacks applied to the player from a monster move."""
        hex_stacks = 0
        for key in ('hex', 'hex_applied', 'hex_amount'):
            value = move.get(key)
            if isinstance(value, bool):
                hex_stacks = 1 if value else 0
            else:
                hex_stacks = self._positive_numeric_move_value(value)
            if hex_stacks > 0:
                break

        if hex_stacks <= 0:
            effect = str(move.get('effect') or move.get('description') or '')
            if re.search(
                r'\b(?:apply|applies|applied|applying)\s+hex\b',
                effect,
                re.IGNORECASE,
            ):
                hex_stacks = 1

        if hex_stacks <= 0 or context is None:
            return hex_stacks

        for key in ('hex', 'hex_applied', 'hex_amount'):
            hex_stacks = self._apply_ascension_move_value(
                move,
                context,
                key,
                hex_stacks,
            )
        return max(0, hex_stacks)

    def _extract_move_entangled(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Extract Entangled stacks applied to the player from a monster move."""
        entangled = 0
        for key in ('entangled', 'entangled_applied', 'entangled_amount'):
            value = move.get(key)
            if isinstance(value, bool):
                entangled = 1 if value else 0
            else:
                entangled = self._positive_numeric_move_value(value)
            if entangled > 0:
                break

        if entangled <= 0:
            effect = str(move.get('effect') or move.get('description') or '')
            if re.search(
                r'\b(?:apply|applies|applied|applying)\s+\d*\s*entangled\b',
                effect,
                re.IGNORECASE,
            ):
                entangled = 1

        if entangled <= 0 or context is None:
            return entangled

        for key in ('entangled', 'entangled_applied', 'entangled_amount'):
            entangled = self._apply_ascension_move_value(
                move,
                context,
                key,
                entangled,
            )
        return max(0, entangled)

    def _extract_move_confused(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Extract Confused applications to the player from a monster move."""
        confused = 0
        for key in ('confused', 'confused_applied', 'confused_amount'):
            value = move.get(key)
            if isinstance(value, bool):
                confused = 1 if value else 0
            else:
                confused = self._positive_numeric_move_value(value)
            if confused > 0:
                break

        if confused <= 0:
            effect = str(move.get('effect') or move.get('description') or '')
            if re.search(
                (
                    r'\b(?:inflict|inflicts|inflicted|apply|applies|applied|applying)'
                    r'\s+\d*\s*confused\b'
                ),
                effect,
                re.IGNORECASE,
            ):
                confused = 1

        if confused <= 0 or context is None:
            return confused

        for key in ('confused', 'confused_applied', 'confused_amount'):
            confused = self._apply_ascension_move_value(
                move,
                context,
                key,
                confused,
            )
        return max(0, confused)

    def _extract_move_draw_reduction(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> int:
        """Extract Draw Reduction applications to the player from a monster move."""
        draw_reduction = 0
        for key in ('draw_reduction', 'draw_reduction_applied', 'draw_reduction_amount'):
            draw_reduction = self._positive_numeric_move_value(move.get(key))
            if draw_reduction > 0:
                break

        if draw_reduction <= 0:
            effect = str(move.get('effect') or move.get('description') or '')
            match = re.search(r'\bappl(?:y|ies)\s+(\d+)\s+draw reduction\b', effect, re.IGNORECASE)
            if match:
                draw_reduction = int(match.group(1))

        if draw_reduction <= 0 or context is None:
            return draw_reduction

        for key in ('draw_reduction', 'draw_reduction_applied', 'draw_reduction_amount'):
            draw_reduction = self._apply_ascension_move_value(
                move,
                context,
                key,
                draw_reduction,
            )
        return max(0, draw_reduction)

    def _positive_numeric_move_value(self, value: Any) -> int:
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

    def _extract_move_status_cards(
        self,
        move: Dict[str, Any],
        context: Optional[DecisionContext] = None,
    ) -> Dict[str, int]:
        """Extract status cards added by a monster move from wiki data fields."""
        def _get_count(*keys: str) -> int:
            for key in keys:
                if key not in move:
                    continue
                value = move.get(key, 0)
                if isinstance(value, bool):
                    if value:
                        return 1
                    continue
                if isinstance(value, (int, float)):
                    count = int(value)
                    if count > 0:
                        return count
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
        void = _get_count('void', 'void_count', 'void_added', 'void_cards_added')
        if dazed == 0:
            dazed = _parse_effect_count('Dazed')
        if burn == 0:
            burn = _parse_effect_count('Burn')
        if slimed == 0:
            slimed = _parse_effect_count('Slimed')
        if wound == 0:
            wound = _parse_effect_count('Wound')
        if void == 0:
            void = _parse_effect_count('Void')
        if context is not None:
            dazed = self._apply_ascension_move_value(move, context, 'dazed', dazed)
            burn = self._apply_ascension_move_value(move, context, 'burn_count', burn)
            burn = self._apply_ascension_move_value(move, context, 'burn_cards_added', burn)
            slimed = self._apply_ascension_move_value(move, context, 'slimed_count', slimed)
            slimed = self._apply_ascension_move_value(move, context, 'slimed_added', slimed)
            wound = self._apply_ascension_move_value(move, context, 'wound_count', wound)
            wound = self._apply_ascension_move_value(move, context, 'wound_added', wound)
            void = self._apply_ascension_move_value(move, context, 'void_count', void)
            void = self._apply_ascension_move_value(move, context, 'void_added', void)
            void = self._apply_ascension_move_value(move, context, 'void_cards_added', void)
        total = dazed + burn + slimed + wound + void
        return {
            'total': total,
            'dazed': dazed,
            'burn': burn,
            'slimed': slimed,
            'wound': wound,
            'void': void,
        }

    def _calculate_x_damage(
        self,
        card: Card,
        state: SimulationState,
        context: DecisionContext,
        x_energy_spent: Optional[int] = None,
        per_hit: bool = False,
    ) -> int:
        """
        Calculate dynamic damage for X-damage cards.

        Dynamic-damage cards have variable damage based on game state:
        - Body Slam: damage = player_block
        - Mind Blast: damage = cards in draw pile
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

        elif card_name == 'Mind Blast':
            return draw_pile_count(context)

        elif card_name == 'Whirlwind':
            # Combat simulation needs per-hit damage so Weak, Vulnerable,
            # thorns, and damage instance tracking happen once per hit.
            energy = x_energy_spent
            if energy is None:
                energy = getattr(state, '_current_x_energy_spent', None)
            if energy is None:
                fallback_energy = getattr(state, 'player_energy', 0)
                energy = x_effect_energy(card, fallback_energy, context)
            energy = max(0, energy)
            per_hit_damage = 8 if is_card_upgraded(card) else 5
            if per_hit:
                return per_hit_damage
            strength = getattr(state, 'player_strength', 0)
            return max(0, per_hit_damage + strength) * energy

        # Fallback: not an X-damage card
        return 0

    @classmethod
    def _count_draw_pile_cards(cls, context: Optional[DecisionContext]) -> int:
        return draw_pile_count(context)

    @classmethod
    def _count_discard_pile_cards(cls, context: Optional[DecisionContext]) -> int:
        return cls._count_card_pile(context, 'discard_pile', 'discard_pile_size')

    @staticmethod
    def _count_card_pile(
        context: Optional[DecisionContext],
        pile_attr: str,
        size_attr: str,
    ) -> int:
        game = getattr(context, 'game', None)
        for owner in (game, context):
            pile = getattr(owner, pile_attr, None)
            if pile is not None:
                try:
                    return max(0, len(pile))
                except TypeError:
                    try:
                        return max(0, int(pile))
                    except (TypeError, ValueError):
                        return 0

        for owner in (game, context):
            size = getattr(owner, size_attr, None)
            if size is not None:
                try:
                    return max(0, int(size))
                except (TypeError, ValueError):
                    return 0

        return 0

    def _calculate_x_block(
        self,
        card: Card,
        state: SimulationState,
        context: DecisionContext,
        x_energy_spent: Optional[int] = None,
    ) -> int:
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
        card_name = _canonical_card_name(card)
        if card_name == 'Reinforced Body':
            energy = x_energy_spent
            if energy is None:
                energy = getattr(state, '_current_x_energy_spent', None)
            if energy is None:
                energy = (
                    x_effect_energy(card, getattr(state, 'player_energy', 0), context)
                )
            per_energy_block = 9 if is_card_upgraded(card) else 7
            return max(0, energy) * per_energy_block

        if card_name == 'Stack':
            block = self._count_discard_pile_cards(context)
            if is_card_upgraded(card):
                block += 3
            return block

        if card_name == 'Genetic Algorithm':
            return 1 + self._positive_card_misc(card)

        # Fallback: not an X-block card
        return 0

    def _deal_damage_to_monster(
        self,
        state: SimulationState,
        monster: dict,
        damage: int,
        trigger_thorns: bool = True,
        defer_curl_up_block: bool = False,
        defer_malleable_block: bool = False,
        apply_the_boot: bool = False,
        defer_flight_hit: bool = False,
    ):
        """Deal damage to monster, accounting for block and thorns."""
        if not self._is_live_monster_state(monster):
            return 0
        try:
            damage = max(0, int(damage or 0))
        except (TypeError, ValueError):
            damage = 0
        if damage <= 0:
            return 0

        if trigger_thorns:
            damage = self._apply_flight_damage_reduction(monster, damage)
            if damage <= 0:
                return 0

        damage = self._apply_monster_intangible_damage_cap(monster, damage)
        if damage <= 0:
            return 0

        # Damage block first
        block_damage = min(damage, monster['block'])
        monster['block'] -= block_damage

        # Remaining damage to HP
        hp_damage = max(0, damage - block_damage)
        if apply_the_boot:
            hp_damage = self._apply_the_boot_minimum_attack_damage(state, hp_damage)
        hp_damage = min(hp_damage, max(0, monster['hp']))
        monster['hp'] -= hp_damage
        state.total_damage_dealt += hp_damage

        if trigger_thorns and hp_damage > 0 and monster['hp'] > 0:
            self._apply_shifting_strength_loss(monster, hp_damage)

        if trigger_thorns and damage > 0:
            # Apply thorns/Sharp Hide as fixed damage per attack hit.
            thorns = monster.get('thorns', 0)
            if thorns > 0:
                self._damage_player(state, thorns, trigger_rupture=False)

        if trigger_thorns and hp_damage > 0 and monster['hp'] > 0:
            if not defer_flight_hit:
                self._apply_flight_hit(monster)
            self._apply_reactive_monster_block(
                monster,
                defer_curl_up_block=defer_curl_up_block,
                defer_malleable_block=defer_malleable_block,
            )
            self._apply_reactive_monster_strength(monster)
            self._apply_guardian_mode_shift(monster, hp_damage)

        # Check if killed
        if monster['hp'] <= 0:
            self._apply_monster_death_effects(state, monster)
            self._mark_monster_defeated(state, monster)

        return hp_damage

    def _apply_shifting_strength_loss(self, monster: dict, hp_damage: int):
        if hp_damage <= 0 or not self._has_shifting_strength_loss(monster):
            return

        self._remember_monster_adjusted_damage_source(monster)
        monster['_simulated_strength_delta'] = (
            monster.get('_simulated_strength_delta', 0) - hp_damage
        )
        monster['_simulated_temporary_strength_delta'] = (
            monster.get('_simulated_temporary_strength_delta', 0) - hp_damage
        )
        self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _has_shifting_strength_loss(self, monster: dict) -> bool:
        monster_name = _canonical_live_monster_name(monster)
        if not monster_name:
            return False

        try:
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        except Exception:
            monster_data = None

        mechanics = (monster_data or {}).get('special_mechanics', {}) or {}
        return (
            mechanics.get('type') == 'fading_shifting'
            and bool(mechanics.get('shifting'))
        ) or monster_name == 'Transient'

    def _mark_monster_defeated(self, state: SimulationState, monster: dict):
        if self._has_life_link(monster):
            if self._has_live_life_link_partner(state, monster):
                monster['half_dead'] = True
                monster['is_gone'] = False
                monster['block'] = 0
                monster['intent'] = Intent.STUN
                monster['move_base_damage'] = 0
                monster['move_adjusted_damage'] = 0
                monster['move_hits'] = 0
                return

            self._mark_life_link_group_gone(state, monster)
            return

        monster['is_gone'] = True
        monster['half_dead'] = False
        state.monsters_killed += 1
        self._apply_gremlin_horn_kill_reward(state)

    def _has_life_link(self, monster: dict) -> bool:
        monster_name = _canonical_live_monster_name(monster)
        if not monster_name:
            return False

        try:
            monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        except Exception:
            monster_data = None

        mechanics = (monster_data or {}).get('special_mechanics', {}) or {}
        return mechanics.get('type') == 'life_link'

    def _is_life_link_group_member(self, monster: dict, candidate: dict) -> bool:
        return (
            self._has_life_link(candidate)
            and _canonical_live_monster_name(candidate)
            == _canonical_live_monster_name(monster)
        )

    def _has_live_life_link_partner(self, state: SimulationState, monster: dict) -> bool:
        return any(
            other is not monster
            and self._is_life_link_group_member(monster, other)
            and self._is_live_monster_state(other)
            for other in state.monsters
        )

    def _mark_life_link_group_gone(self, state: SimulationState, monster: dict):
        for other in state.monsters:
            if other is not monster and not self._is_life_link_group_member(monster, other):
                continue
            if other.get('is_gone', False):
                continue
            if other is monster or other.get('half_dead', False) or other.get('hp', 0) <= 0:
                other['is_gone'] = True
                other['half_dead'] = False
                other['block'] = 0
                state.monsters_killed += 1
                self._apply_gremlin_horn_kill_reward(state)

    def _apply_gremlin_horn_kill_reward(self, state: SimulationState):
        if not getattr(state, 'has_gremlin_horn', False):
            return
        state.player_energy += 1
        state.energy_gained += 1
        self._add_card_draw(state, 1)

    def _apply_reactive_monster_block(
        self,
        monster: dict,
        defer_curl_up_block: bool = False,
        defer_malleable_block: bool = False,
    ):
        """Apply non-lethal attack-damage reactions such as Curl Up and Malleable."""
        curl_up_block = self._non_negative_int(monster.get('curl_up_block', 0))
        monster['curl_up_block'] = curl_up_block
        if curl_up_block > 0 and not monster.get('curl_up_used', False):
            if defer_curl_up_block:
                monster['_deferred_curl_up_block'] = (
                    self._non_negative_int(monster.get('_deferred_curl_up_block', 0))
                    + curl_up_block
                )
            else:
                monster['block'] += curl_up_block
            monster['curl_up_used'] = True
            monster['curl_up_block'] = 0

        malleable_block = self._non_negative_int(monster.get('malleable_block', 0))
        monster['malleable_block'] = malleable_block
        if malleable_block > 0:
            if defer_malleable_block:
                monster['_deferred_malleable_block'] = (
                    self._non_negative_int(monster.get('_deferred_malleable_block', 0))
                    + malleable_block
                )
            else:
                monster['block'] += malleable_block
            monster['malleable_block'] = malleable_block + 1

    def _flush_deferred_reactive_block(self, monster: dict):
        deferred_curl_up_block = self._non_negative_int(
            monster.pop('_deferred_curl_up_block', 0)
        )
        deferred_block = self._non_negative_int(monster.pop('_deferred_malleable_block', 0))
        if deferred_curl_up_block <= 0 and deferred_block <= 0:
            return
        if not self._is_live_monster_state(monster) or monster.get('hp', 0) <= 0:
            return
        monster['block'] += deferred_curl_up_block + deferred_block

    def _apply_flight_damage_reduction(self, monster: dict, damage: int) -> int:
        """Apply Byrd Flight's attack damage reduction."""
        flight_stacks = self._non_negative_int(monster.get('flight_stacks', 0))
        monster['flight_stacks'] = flight_stacks
        if flight_stacks <= 0:
            return damage
        return max(0, int(damage * 0.5))

    def _apply_monster_intangible_damage_cap(self, monster: dict, damage: int) -> int:
        """Apply monster Intangible's per-hit damage cap."""
        intangible = self._non_negative_int(monster.get('intangible', 0))
        monster['intangible'] = intangible
        if intangible <= 0:
            return damage
        if damage <= 0:
            return 0
        return 1

    def _apply_flight_hit(self, monster: dict):
        """Count down Byrd Flight and stun the monster when it is knocked down."""
        flight_stacks = self._non_negative_int(monster.get('flight_stacks', 0))
        monster['flight_stacks'] = flight_stacks
        if flight_stacks <= 0:
            return

        flight_stacks = max(0, flight_stacks - 1)
        monster['flight_stacks'] = flight_stacks
        if flight_stacks > 0:
            return

        monster['intent'] = Intent.STUN
        monster['move_base_damage'] = 0
        monster['move_adjusted_damage'] = 0
        monster['move_hits'] = 0

    def _apply_reactive_monster_strength(self, monster: dict):
        """Apply non-lethal attack-damage Strength reactions such as Angry."""
        strength_gain = self._non_negative_int(monster.get('hit_strength_gain', 0))
        monster['hit_strength_gain'] = strength_gain
        if strength_gain <= 0:
            return

        self._remember_monster_adjusted_damage_source(monster)
        monster['strength'] = monster.get('strength', 0) + strength_gain
        monster['_simulated_strength_delta'] = (
            monster.get('_simulated_strength_delta', 0) + strength_gain
        )
        self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _apply_guardian_mode_shift(self, monster: dict, hp_damage: int):
        """Apply The Guardian's Mode Shift transition after attack HP damage."""
        if not self._is_guardian(monster):
            return

        mode_shift = self._non_negative_int(monster.get('mode_shift', 0))
        monster['mode_shift'] = mode_shift
        if mode_shift <= 0:
            return

        mode_shift = max(0, mode_shift - hp_damage)
        monster['mode_shift'] = mode_shift
        if mode_shift == 0:
            monster['block'] += GUARDIAN_MODE_SHIFT_BLOCK
            monster['thorns'] = max(monster.get('thorns', 0), GUARDIAN_SHARP_HIDE)
            monster['intent'] = Intent.BUFF
            monster['move_id'] = GUARDIAN_DEFENSIVE_MODE_MOVE_ID
            monster['move_base_damage'] = 0
            monster['move_adjusted_damage'] = 0
            monster['move_hits'] = 0

    def _is_guardian(self, monster: dict) -> bool:
        monster_id = str(monster.get('monster_id', ''))
        monster_name = str(monster.get('name', ''))
        return monster_id == 'TheGuardian' or monster_name == 'The Guardian'

    def _apply_monster_death_effects(self, state: SimulationState, monster: dict):
        """Apply deterministic monster death effects such as Fungi Beast spores."""
        if monster.get('death_effect_applied'):
            return
        monster['death_effect_applied'] = True

        monster_name = _canonical_live_monster_name(monster)
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

        applied = self._apply_player_vulnerable_debuff(state, amount)
        if not applied:
            logger.debug(
                "[DEATH_EFFECT] %s Vulnerable blocked by player Artifact",
                monster_name,
            )
            return
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
            self._lose_player_hp(projected, hp_loss)

        status_hp_loss = max(0, getattr(projected, 'end_turn_status_hp_loss', 0))
        if status_hp_loss > 0:
            self._lose_player_hp(projected, status_hp_loss, trigger_rupture=False)

        constricted_loss = max(0, getattr(projected, 'player_constricted', 0))
        if constricted_loss > 0:
            self._lose_player_hp(projected, constricted_loss, trigger_rupture=False)

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

        self._apply_stone_calendar_end_turn(projected)

        end_turn_block = max(0, getattr(projected, 'end_turn_block', 0))
        if end_turn_block > 0:
            projected.end_turn_block = 0
            self._add_player_block(projected, end_turn_block)

        status_damage = max(0, getattr(projected, 'end_turn_status_damage', 0))
        if status_damage > 0:
            blocked = min(projected.player_block, status_damage)
            projected.player_block -= blocked
            unblocked = status_damage - blocked
            if unblocked > 0:
                self._lose_player_hp(projected, unblocked, trigger_rupture=False)

        end_turn_exhaust_events = max(
            0,
            getattr(projected, 'end_turn_exhaust_events', 0),
        )
        if end_turn_exhaust_events > 0 and projected.player_hp > 0:
            starting_exhaust_events = projected.exhaust_events
            projected.exhaust_events += end_turn_exhaust_events
            self._apply_feel_no_pain_block(projected, starting_exhaust_events)
            self._apply_dark_embrace_draw(projected, starting_exhaust_events)
            self._apply_charons_ashes_damage(projected, starting_exhaust_events)

        projected.end_turn_aoe_damage = 0
        projected.end_turn_hp_loss = 0
        projected.end_turn_status_damage = 0
        projected.end_turn_status_hp_loss = 0
        projected.end_turn_exhaust_events = 0
        temp_strength = getattr(projected, 'player_temp_strength', 0)
        if temp_strength:
            projected.player_strength -= temp_strength
            projected.player_temp_strength = 0
        ritual_strength = max(0, getattr(projected, 'player_ritual', 0))
        if ritual_strength:
            projected.player_strength += ritual_strength
        regen = max(0, getattr(projected, 'player_regen', 0))
        if regen:
            regen_heal = (
                _magic_flower_scaled_heal(regen)
                if getattr(projected, 'has_magic_flower', False)
                else regen
            )
            projected.player_hp = min(projected.player_max_hp, projected.player_hp + regen_heal)
            projected.player_regen = regen - 1
        temp_dexterity = getattr(projected, 'player_temp_dexterity', 0)
        if temp_dexterity:
            projected.player_dexterity -= temp_dexterity
            projected.player_temp_dexterity = 0
        projected = self._apply_monster_escape_intents(projected)
        projected = self._revive_ready_darklings(projected)
        projected = self._materialize_pending_death_splits(projected)
        projected = self._materialize_end_turn_summons(projected)
        return projected

    def _apply_stone_calendar_end_turn(self, state: SimulationState):
        counter = getattr(state, 'stone_calendar_counter', None)
        if counter is None:
            return

        counter = self._non_negative_int(counter)
        if counter == STONE_CALENDAR_TRIGGER_COUNTER:
            for monster in state.monsters:
                if self._is_live_monster_state(monster):
                    self._deal_damage_to_monster(
                        state,
                        monster,
                        STONE_CALENDAR_DAMAGE,
                        trigger_thorns=False,
                    )
        state.stone_calendar_counter = counter + 1

    def _apply_monster_escape_intents(self, state: SimulationState) -> SimulationState:
        for monster in state.monsters:
            if not self._should_escape_at_end_turn(monster):
                continue
            monster['is_gone'] = True
            monster['half_dead'] = False
            state.monsters_escaped += 1
        return state

    def _should_escape_at_end_turn(self, monster: dict) -> bool:
        if not self._is_live_monster_state(monster):
            return False

        if self._intent_name(monster.get('intent', '')).upper() == 'ESCAPE':
            return True

        identifiers = {
            normalize_monster_id(monster.get('name', '')),
            normalize_monster_id(monster.get('monster_id', '')),
            normalize_monster_id(monster.get('id', '')),
            normalize_monster_id(_canonical_live_monster_name(monster)),
        }
        return (
            coerce_int(monster.get('move_id', -1), -1) == 3
            and bool(identifiers & {'looter', 'mugger'})
        )

    def _revive_ready_darklings(self, state: SimulationState) -> SimulationState:
        for monster in state.monsters:
            if not self._darkling_revival_ready(monster):
                continue
            max_hp = max(1, coerce_int(monster.get('max_hp', 0), 0))
            monster['hp'] = max(1, max_hp // 2)
            monster['is_gone'] = False
            monster['half_dead'] = False
            monster['block'] = 0
        return state

    def _darkling_revival_ready(self, monster: dict) -> bool:
        return (
            self._is_darkling_monster_state(monster)
            and bool(monster.get('half_dead', False))
            and coerce_int(monster.get('hp', 0), 0) <= 0
            and self._intent_name(monster.get('intent', '')).lower()
            in {'buff', 'intentbuff'}
        )

    @staticmethod
    def _is_darkling_monster_state(monster: dict) -> bool:
        identifiers = {
            normalize_monster_id(monster.get('name', '')),
            normalize_monster_id(monster.get('monster_id', '')),
            normalize_monster_id(monster.get('id', '')),
            normalize_monster_id(_canonical_live_monster_name(monster)),
        }
        return 'darkling' in identifiers

    def _materialize_end_turn_summons(self, state: SimulationState) -> SimulationState:
        """Add deterministic minions for the current summoning monster move."""
        new_monsters = []
        changed = False

        for monster in state.monsters:
            new_monsters.append(monster)
            summon_names = self._end_turn_summon_names(monster)
            if not summon_names:
                continue

            live_minions = self._live_summoned_minion_count(state, summon_names)
            max_minions = self._summoner_max_minions(monster, summon_names)
            open_slots = max(0, max_minions - live_minions)
            if open_slots <= 0:
                continue

            for child_index, child_name in enumerate(summon_names[:open_slots]):
                summoned = self._make_summoned_monster(child_name, monster, state, child_index)
                if summoned is None:
                    continue
                new_monsters.append(summoned)
                changed = True

        if changed:
            state.monsters = new_monsters
            state.primary_target = None

        return state

    def _end_turn_summon_names(self, monster: dict) -> List[str]:
        if not self._is_live_monster_state(monster):
            return []

        monster_name = _canonical_live_monster_name(monster)
        if not monster_name:
            return []

        move = self._current_summon_move(monster_name, monster)
        if not move:
            return []

        raw_summons = move.get('summons')
        if isinstance(raw_summons, str):
            summon_names = [raw_summons]
        elif isinstance(raw_summons, list):
            summon_names = [name for name in raw_summons if isinstance(name, str)]
        else:
            summon_names = []

        summon_names = self._concrete_summon_names(summon_names)
        if not summon_names:
            return []

        count = self._summon_count_from_move(move, len(summon_names))
        if count <= 0:
            return []
        if len(summon_names) == 1 and count > 1:
            summon_names = summon_names * count
        return summon_names[:count]

    def _current_summon_move(self, monster_name: str, monster: dict) -> Optional[Dict[str, Any]]:
        move_id = coerce_int(monster.get('move_id'), None)
        if move_id is None:
            return None

        for move in game_data_loader.get_monster_moves(monster_name):
            if 'summons' not in move:
                continue
            if coerce_int(move.get('move_id'), None) == move_id:
                return move
        return None

    def _concrete_summon_names(self, summon_names: List[str]) -> List[str]:
        concrete_names = []
        for raw_name in summon_names:
            child_name = self._canonical_monster_name(raw_name)
            if not game_data_loader.get_enhanced_monster_data(child_name):
                logger.debug("[SUMMON] Skipping unknown summoned monster %s", raw_name)
                continue
            concrete_names.append(child_name)
        return concrete_names

    def _summon_count_from_move(self, move: Dict[str, Any], default_count: int) -> int:
        count = move.get('summon_count')
        if isinstance(count, dict):
            values = [
                coerce_int(value, None)
                for value in count.values()
            ]
            values = [value for value in values if value is not None]
            return max(values, default=default_count)
        return max(0, coerce_int(count, default_count))

    def _summoner_max_minions(self, monster: dict, summon_names: List[str]) -> int:
        monster_name = _canonical_live_monster_name(monster)
        monster_data = game_data_loader.get_enhanced_monster_data(monster_name)
        mechanics = monster_data.get('special_mechanics', {}) if monster_data else {}
        return max(
            len(summon_names),
            coerce_int(mechanics.get('max_minions'), len(summon_names)),
        )

    def _live_summoned_minion_count(self, state: SimulationState, summon_names: List[str]) -> int:
        summon_name_set = {
            normalize_monster_id(name)
            for name in summon_names
        }
        return sum(
            1
            for candidate in state.monsters
            if (
                self._is_live_monster_state(candidate)
                and normalize_monster_id(_canonical_live_monster_name(candidate)) in summon_name_set
            )
        )

    def _make_summoned_monster(
        self,
        child_name: str,
        parent: dict,
        state: SimulationState,
        child_index: int,
    ) -> Optional[dict]:
        child_name = self._canonical_monster_name(child_name)
        hp = self._summoned_monster_hp(child_name, state)
        if hp <= 0:
            return None

        attack_damage, attack_hits, move_id = self._strongest_known_attack_move_values(child_name)
        monster_data = game_data_loader.get_enhanced_monster_data(child_name) or {}
        return {
            'monster_id': monster_data.get('monster_id', child_name),
            'name': child_name,
            'hp': hp,
            'max_hp': hp,
            'block': 0,
            'intent': Intent.ATTACK if attack_damage > 0 else Intent.UNKNOWN,
            'move_id': move_id,
            'is_gone': False,
            'half_dead': False,
            'is_minion': True,
            'vulnerable': 0,
            'weak': 0,
            'frail': 0,
            'poison': 0,
            'thorns': 0,
            'artifact': 0,
            'move_base_damage': attack_damage,
            'move_adjusted_damage': attack_damage,
            'move_hits': attack_hits,
            'strength': 0,
            'skill_strength_gain': 0,
            'power_strength_gain': 0,
            'end_turn_strength_gain': 0,
            'summoned_by': parent.get('name', ''),
            'summon_child_index': child_index,
        }

    def _summoned_monster_hp(self, child_name: str, state: SimulationState) -> int:
        monster_data = game_data_loader.get_enhanced_monster_data(child_name)
        hp_range = self._monster_hp_range_from_data(
            monster_data.get('hp_ranges') if monster_data else None,
            child_name,
            getattr(state, 'ascension_level', 0),
        )
        if hp_range is None:
            return 0
        return max(1, hp_range[1])

    def _monster_hp_range_from_data(
        self,
        hp_ranges: Any,
        monster_name: str,
        ascension_level: int,
    ) -> Optional[Tuple[int, int]]:
        if not isinstance(hp_ranges, dict):
            return None

        thresholds = []
        for key in hp_ranges:
            match = re.match(r'ascension_(\d+)\+$', str(key))
            if match:
                thresholds.append((int(match.group(1)), key))
        for threshold, key in sorted(thresholds, reverse=True):
            if ascension_level >= threshold:
                hp_range = self._extract_monster_hp_tuple(hp_ranges[key], monster_name)
                if hp_range is not None:
                    return hp_range

        if 'normal' in hp_ranges:
            hp_range = self._extract_monster_hp_tuple(hp_ranges['normal'], monster_name)
            if hp_range is not None:
                return hp_range

        return self._extract_monster_hp_tuple(hp_ranges, monster_name)

    def _extract_monster_hp_tuple(
        self,
        range_data: Any,
        monster_name: str,
    ) -> Optional[Tuple[int, int]]:
        if not isinstance(range_data, dict):
            return None
        minimum = coerce_int(range_data.get('min'), None)
        maximum = coerce_int(range_data.get('max'), None)
        if minimum is not None and maximum is not None:
            return minimum, maximum

        normalized_name = str(monster_name or '').lower()
        for key, value in range_data.items():
            if str(key).lower() != normalized_name:
                continue
            return self._extract_monster_hp_tuple(value, monster_name)
        return None

    def _apply_skill(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext] = None,
        target_index: Optional[int] = None,
        x_energy_spent: Optional[int] = None,
    ):
        """Apply skill card effects."""
        if self._apply_block_multiplier_skill(state, card):
            return
        if self._apply_second_wind(state, card, context):
            return
        if self._apply_double_tap(state, card):
            return

        card_name = _canonical_card_name(card)
        if card_name == 'Havoc':
            self._apply_havoc_top_card(state, context)
        self._apply_skill_healing(state, card)

        # Block skills - apply frail multiplier if player has frail
        block_gain = self._non_negative_int(getattr(card, 'block', 0))
        if block_gain > 0:
            logger.debug(f"[BLOCK_SKILL] Using card.block attribute: {block_gain} for {card_name}")
            block_gain = self._apply_card_block_modifiers(block_gain, state)
            self._add_player_block(state, block_gain, from_card=True)
        else:
            # Check for X-block cards first
            if context is not None:
                block_gain = self._calculate_x_block(
                    card,
                    state,
                    context,
                    x_energy_spent=x_energy_spent,
                )
                if block_gain > 0:
                    logger.debug(f"[BLOCK_X] X-block calculated: {block_gain} for {card_name}")
                    # Apply frail multiplier
                    block_gain = self._apply_card_block_modifiers(block_gain, state)
                    self._add_player_block(state, block_gain, from_card=True)
                else:
                    # Not an X-block card - try to get block from game data
                    # (needed because Card objects don't have block attribute set)
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        block_data = dict(card_data)
                        upgrades = card_upgrade_count(card)
                        block_data['name'] = f"{card_name}+" if upgrades > 0 else card_name
                        base_block = game_data_loader._parse_card_block(block_data)
                        if base_block and base_block > 0:
                            # Apply upgrade bonus if card is upgraded
                            if upgrades > 0:
                                base_data = dict(card_data)
                                base_data['name'] = card_name
                                unupgraded_block = game_data_loader._parse_card_block(base_data)
                                if unupgraded_block is not None and base_block != unupgraded_block:
                                    logger.debug(f"[BLOCK_UPGRADE_PARSED] {card_name} (upgrades={upgrades}): {base_block} block")
                                else:
                                    # Some upgrades (for example Armaments+) improve the non-block effect.
                                    # Only apply a manual bonus when the card is explicitly mapped.
                                    upgrade_bonus = card_upgrade_helpers.known_block_upgrade_bonus(card, card_name)
                                    if upgrade_bonus > 0:
                                        base_block += upgrade_bonus
                                        logger.debug(f"[BLOCK_UPGRADE] {card_name} (upgrades={upgrades}): {base_block} block (+{upgrade_bonus})")
                                    else:
                                        logger.debug(f"[BLOCK_UPGRADE_NO_BLOCK_CHANGE] {card_name} (upgrades={upgrades}): {base_block} block")
                            else:
                                logger.debug(f"[BLOCK_BASE] {card_name} (upgrades={upgrades}): {base_block} block")

                            block_gain = self._apply_card_block_modifiers(base_block, state)
                            self._add_player_block(state, block_gain, from_card=True)
                        else:
                            logger.debug(f"[BLOCK_NONE] No block found for {card_name}")
                    else:
                        logger.debug(f"[BLOCK_NODATA] No card data found for {card_name}")
        if _canonical_card_name(card) == 'Rage':
            rage_gain = 5 if is_card_upgraded(card) else 3
            state.rage_block_per_attack += rage_gain
        if card_name == 'Flame Barrier':
            state.player_thorns += 6 if is_card_upgraded(card) else 4
        if card_name == 'Panic Button':
            state.card_block_blocked = True

        self._apply_strength_skill(state, card, target_index)
        self._apply_energy_gain_skill(state, card)
        self._apply_enemy_strength_skill(state, card, target_index)
        self._apply_catalyst_skill(state, card, target_index)

        # Apply enemy debuffs from skill cards (e.g., Shockwave).
        try:
            card_name = _canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = self._get_card_effect_text(card_name, card_data)
                upgrades = is_card_upgraded(card)
                has_debuff = any(
                    debuff in description
                    for debuff in ('vulnerable', 'weak', 'poison', 'strength down')
                )
                has_debuff = (
                    has_debuff
                    or self._enemy_strength_loss_effect(
                        description,
                        upgrades,
                        x_energy_spent,
                    ) is not None
                )
                # Disarm is handled above as a data-independent fallback.
                if has_debuff and card_name != 'Disarm':
                    effect_text = self._effect_text_for_upgrade(
                        description,
                        upgrades,
                    ).lower()
                    is_aoe = 'all enemies' in effect_text
                    debuff_effects = self._description_debuff_effects(
                        description,
                        upgrades,
                        card_name,
                        x_energy_spent=x_energy_spent,
                    )
                    if is_aoe:
                        if debuff_effects:
                            for monster in state.monsters:
                                if not self._is_live_monster_state(monster):
                                    continue
                                self._apply_monster_debuffs(monster, debuff_effects)
                    elif (
                        debuff_effects
                        and target_index is not None
                        and 0 <= target_index < len(state.monsters)
                    ):
                        monster = state.monsters[target_index]
                        if self._is_live_monster_state(monster):
                            self._apply_monster_debuffs(monster, debuff_effects)
                    elif debuff_effects and 'random enemy' in description:
                        self._apply_random_enemy_debuffs(
                            state,
                            debuff_effects,
                            self._extract_effect_repeat_count(description, upgrades),
                        )
        except Exception:
            pass

        # Track exhaust events (for Feel No Pain, etc.)
        try:
            card_name = _canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = self._get_card_effect_text(card_name, card_data)
                upgraded = is_card_upgraded(card)
                exhaust_events = self._skill_exhaust_events_from_description(
                    description,
                    upgraded,
                )
                hand_exhaust_count = self._skill_hand_exhaust_count_from_description(
                    description,
                    upgraded,
                )
                if hand_exhaust_count > 0:
                    exhausted_cards = self._skill_hand_exhaust_cards(
                        state,
                        card,
                        context,
                        description,
                        upgraded,
                    )
                    if exhausted_cards:
                        self._mark_cards_unavailable(state, exhausted_cards)
                        self._apply_sentinel_exhaust_energy(state, exhausted_cards)
                    exhaust_events = (
                        max(0, exhaust_events - hand_exhaust_count)
                        + len(exhausted_cards)
                    )
                state.exhaust_events += exhaust_events
                # Track draw events
                if 'draw' in description:
                    self._add_card_draw(
                        state,
                        self._extract_draw_count(description, upgraded),
                    )
        except:
            pass

        self._apply_card_status_pollution(state, card)

        if _canonical_card_name(card) == 'Battle Trance':
            state.draw_blocked = True

    def _apply_skill_healing(self, state: SimulationState, card: Card):
        card_name = _canonical_card_name(card)
        if card_name != 'Bandage Up':
            return

        heal_amount = 6 if is_card_upgraded(card) else 4
        state.player_hp = min(state.player_max_hp, state.player_hp + heal_amount)

    def _apply_havoc_top_card(
        self,
        state: SimulationState,
        context: Optional[DecisionContext],
    ):
        self._apply_top_draw_card_by_effect(
            state,
            context,
            exhaust_by_effect=True,
        )

    def _apply_top_draw_card_by_effect(
        self,
        state: SimulationState,
        context: Optional[DecisionContext],
        exhaust_by_effect: bool = False,
    ):
        top_card = self._draw_pile_top_card(state, context)
        if top_card is None:
            return

        top_card_type = card_type_name(top_card)
        mark_card_played(state.played_card_uuids, top_card)

        top_card_exhausted_by_effect = False
        if top_card_type == 'ATTACK':
            target_index = self._havoc_top_attack_target_index(state, top_card)
            state.attacks_played += 1
            self._apply_attack(
                state,
                top_card,
                target=None,
                target_index=target_index,
                context=context,
                x_energy_spent=0 if is_x_cost_card(top_card) else None,
            )
            self._apply_rage_block(state)
            self._apply_ornamental_fan_block(state)
            self._apply_self_damage(state, top_card)
            top_card_exhausted_by_effect = self._card_exhausts_itself_from_data(top_card)
        elif top_card_type == 'SKILL':
            state.skills_played += 1
            self._apply_skill(
                state,
                top_card,
                context,
                target_index=None,
                x_energy_spent=0 if is_x_cost_card(top_card) else None,
            )
            self._apply_skill_reactive_monster_powers(state)
            self._apply_self_damage(state, top_card)
            top_card_exhausted_by_effect = self._card_exhausts_itself_from_data(top_card)
        elif top_card_type == 'POWER':
            self._apply_power(state, top_card)
            self._apply_power_reactive_monster_powers(state)
            self._apply_self_damage(state, top_card)

        if exhaust_by_effect and not top_card_exhausted_by_effect:
            state.exhaust_events += 1

    @staticmethod
    def _draw_pile_top_card(
        state: SimulationState,
        context: Optional[DecisionContext],
    ) -> Optional[Card]:
        game = getattr(context, 'game', None)
        for owner in (game, context):
            draw_pile = getattr(owner, 'draw_pile', None)
            if isinstance(draw_pile, list) and draw_pile:
                for top_card in reversed(draw_pile):
                    if not isinstance(top_card, Card):
                        continue
                    if is_card_played(state.played_card_uuids, top_card):
                        continue
                    return top_card
        return None

    def _havoc_top_attack_target_index(
        self,
        state: SimulationState,
        card: Card,
    ) -> Optional[int]:
        if self._is_aoe_attack_card(card) or self._is_random_target_attack(card):
            return None
        alive_indices = [
            idx for idx, monster in enumerate(state.monsters)
            if self._is_live_monster_state(monster)
        ]
        if len(alive_indices) == 1:
            return alive_indices[0]
        return None

    def _is_aoe_attack_card(self, card: Card) -> bool:
        card_name = _canonical_card_name(card)
        if card_name in IRONCLAD_AOE_ATTACK_CARDS:
            return True
        card_data = game_data_loader.get_card_data(card_name)
        return bool(card_data and game_data_loader._is_card_aoe(card_data))

    def _card_exhausts_itself_from_data(self, card: Card) -> bool:
        card_data = game_data_loader.get_card_data(_canonical_card_name(card))
        if not card_data:
            return False
        return self._card_exhausts_itself(
            self._get_card_effect_text(_canonical_card_name(card), card_data),
            is_card_upgraded(card),
        )

    def _apply_power(self, state: SimulationState, card: Card):
        """Apply power card effects."""
        card_id = _canonical_card_name(card)
        upgraded = is_card_upgraded(card)

        # Demon Form starts gaining Strength on future turns, not immediately.
        if card_id == 'Demon Form':
            pass

        # Berserk applies Vulnerable immediately and grants extra energy on future turns.
        elif card_id == 'Berserk':
            vulnerable = 1 if upgraded else 2
            self._apply_player_vulnerable_debuff(state, vulnerable)

        # Inflame - adds strength
        elif card_id == 'Inflame':
            state.player_strength += 3 if upgraded else 2

        # Corruption - skills cost 0 (track for synergy evaluation)
        elif card_id == 'Corruption':
            state.corruption_active = True

        # Feel No Pain - gain block when cards exhaust
        elif card_id == 'Feel No Pain':
            state.feel_no_pain_block_per_exhaust += 4 if upgraded else 3

        # Dark Embrace - draw when cards exhaust
        elif card_id == 'Dark Embrace':
            state.dark_embrace_draw_per_exhaust += 1

        # Juggernaut - damage a random enemy whenever block is gained.
        elif card_id == 'Juggernaut':
            state.juggernaut_damage_on_block += 7 if upgraded else 5

        # Panache - every fifth later card play deals AOE damage.
        elif card_id == 'Panache':
            state.panache_counter = PANACHE_RESET_COUNT
            state.panache_damage = PANACHE_DAMAGE

        # Metallicize - end-turn block applies before enemies attack, but not immediately.
        elif card_id == 'Metallicize':
            state.end_turn_block += 4 if upgraded else 3

        # Rupture - card HP loss grants Strength once per HP-loss event.
        elif card_id == 'Rupture':
            state.rupture_strength_per_hp_loss += 2 if upgraded else 1

        # Combust - end-turn HP loss and AOE damage happen before enemies attack.
        elif card_id == 'Combust':
            state.end_turn_hp_loss += 1
            state.end_turn_aoe_damage += 7 if upgraded else 5

        # Draw power
        elif card_id == 'Draw':
            self._add_card_draw(state, 2 if upgraded else 1)

        # Energy gain (Bloodletting, etc.)
        elif 'energy' in card_id.lower() or card_id in ['Demon Form', 'Combust']:
            # Track energy gained
            try:
                card_data = game_data_loader.get_card_data(card_id)
                if card_data:
                    description = card_data.get('description', '').lower()
                    energy_match = re.search(r'gain (\d+) energy', description)
                    if energy_match:
                        state.energy_gained += int(energy_match.group(1))
            except:
                pass

        # Other powers can be added as needed
        self._apply_bird_faced_urn_power_heal(state)

    def _apply_feel_no_pain_block(self, state: SimulationState, starting_exhaust_events: int):
        exhaust_delta = state.exhaust_events - starting_exhaust_events
        if exhaust_delta <= 0 or state.feel_no_pain_block_per_exhaust <= 0:
            return

        for _ in range(exhaust_delta):
            self._add_player_block(state, state.feel_no_pain_block_per_exhaust)

    def _apply_dark_embrace_draw(self, state: SimulationState, starting_exhaust_events: int):
        exhaust_delta = state.exhaust_events - starting_exhaust_events
        if exhaust_delta <= 0 or state.dark_embrace_draw_per_exhaust <= 0:
            return

        self._add_card_draw(state, exhaust_delta * state.dark_embrace_draw_per_exhaust)

    def _apply_charons_ashes_damage(self, state: SimulationState, starting_exhaust_events: int):
        exhaust_delta = state.exhaust_events - starting_exhaust_events
        damage = getattr(state, 'charons_ashes_damage_per_exhaust', 0)
        if exhaust_delta <= 0 or damage <= 0:
            return

        for _ in range(exhaust_delta):
            for monster in state.monsters:
                if not self._is_live_monster_state(monster):
                    continue
                self._deal_damage_to_monster(
                    state,
                    monster,
                    damage,
                    trigger_thorns=False,
                )

    def _apply_strength_skill(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int] = None,
    ):
        """Apply immediate Strength-changing Ironclad skills."""
        card_id = _canonical_card_name(card)
        upgrades = card_upgrade_count(card)

        if card_id == 'Flex':
            strength_gain = 4 if upgrades > 0 else 2
            state.player_strength += strength_gain
            if state.player_artifact > 0:
                state.player_artifact -= 1
            else:
                state.player_temp_strength += strength_gain
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
            return (
                self._is_live_monster_state(monster)
                and self._monster_intends_attack(monster)
            )

        return any(
            self._is_live_monster_state(monster)
            and self._monster_intends_attack(monster)
            for monster in state.monsters
        )

    def _monster_intends_attack(self, monster: dict) -> bool:
        intent = monster.get('intent')
        if intent is None:
            return False
        return intent_is_attack(intent)

    def _apply_energy_gain_skill(self, state: SimulationState, card: Card):
        card_id = _canonical_card_name(card)
        upgrades = card_upgrade_count(card)
        energy_gain = 0

        if card_id == 'Bloodletting':
            energy_gain = 3 if upgrades > 0 else 2
        elif card_id in {'Offering', 'Seeing Red'}:
            energy_gain = 2

        if energy_gain <= 0:
            return

        state.player_energy += energy_gain
        state.energy_gained += energy_gain

    def _apply_catalyst_skill(
        self,
        state: SimulationState,
        card: Card,
        target_index: Optional[int],
    ):
        card_id = _canonical_card_name(card)
        if card_id != 'Catalyst':
            return
        if target_index is None or not (0 <= target_index < len(state.monsters)):
            return

        monster = state.monsters[target_index]
        if not self._is_live_monster_state(monster):
            return

        current_poison = monster.get('poison', 0)
        if current_poison <= 0:
            return

        multiplier = 3 if is_card_upgraded(card) else 2
        self._apply_monster_poison(monster, current_poison * (multiplier - 1))

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
            if not is_attack_card(hand_card)
        ]
        exhausted_count = len(exhausted_cards)
        if exhausted_count <= 0:
            return True

        block_per_card = 7 if is_card_upgraded(card) else 5
        block_gain = self._apply_card_block_modifiers(block_per_card, state)
        for _ in range(exhausted_count):
            self._add_player_block(state, block_gain, from_card=True)
        state.exhaust_events += exhausted_count
        self._mark_cards_unavailable(state, exhausted_cards)
        self._apply_sentinel_exhaust_energy(state, exhausted_cards)
        return True

    def _apply_double_tap(self, state: SimulationState, card: Card) -> bool:
        card_id = _canonical_card_name(card)
        if card_id != 'Double Tap':
            return False

        state.double_tap_charges += 2 if is_card_upgraded(card) else 1
        return True

    def _apply_block_multiplier_skill(self, state: SimulationState, card: Card) -> bool:
        card_id = _canonical_card_name(card)
        if card_id != 'Entrench':
            return False

        self._add_player_block(state, state.player_block)
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
        if not self._is_live_monster_state(monster):
            return

        if self._consume_monster_artifact(monster):
            return

        strength_loss = 3 if is_card_upgraded(card) else 2
        self._remember_monster_adjusted_damage_source(monster)
        monster['strength'] = monster.get('strength', 0) - strength_loss
        monster['_simulated_strength_delta'] = (
            monster.get('_simulated_strength_delta', 0) - strength_loss
        )
        self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _apply_rage_block(self, state: SimulationState):
        """Apply Rage block trigger after playing an attack."""
        if state.rage_block_per_attack <= 0:
            return
        self._add_player_block(state, state.rage_block_per_attack)

    def _apply_ornamental_fan_block(self, state: SimulationState):
        counter = getattr(state, 'ornamental_fan_attack_count', None)
        if counter is None:
            return

        counter = self._non_negative_int(counter) + 1
        state.ornamental_fan_attack_count = counter
        if counter % 3 == 0:
            self._add_player_block(state, 4)

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

            self._lose_player_hp(state, hp_loss)
        except Exception:
            pass

    def _apply_blue_candle_curse_hp_loss(
        self,
        state: SimulationState,
        card: Card,
        context: Optional[DecisionContext],
    ):
        if card_type_name(card) != 'CURSE':
            return
        if not self._context_has_relic(context, 'Blue Candle'):
            return

        self._lose_player_hp(state, 1)

    @staticmethod
    def _effective_player_hp_loss(state: SimulationState, amount: int) -> int:
        hp_loss = max(0, coerce_int(amount, 0))
        if hp_loss > 0 and getattr(state, 'has_tungsten_rod', False):
            hp_loss = max(0, hp_loss - 1)
        if hp_loss > 0 and FastCombatSimulator._consume_player_buffer(state):
            return 0
        return hp_loss

    @staticmethod
    def _consume_player_buffer(state: SimulationState) -> bool:
        buffer_charges = max(0, coerce_int(getattr(state, 'player_buffer', 0), 0))
        if buffer_charges <= 0:
            return False
        state.player_buffer = buffer_charges - 1
        return True

    @staticmethod
    def _fairy_revive_hp(state: SimulationState) -> int:
        revive_hp = coerce_int(getattr(state, 'fairy_revive_hp', 0), 0)
        if revive_hp > 0:
            return revive_hp
        max_hp = max(1, coerce_int(getattr(state, 'player_max_hp', 1), 1))
        return max(1, int(max_hp * FAIRY_REVIVE_FRACTION))

    @staticmethod
    def _consume_fairy_revive_if_dead(state: SimulationState) -> bool:
        if coerce_int(getattr(state, 'player_hp', 0), 0) > 0:
            return False
        revive_count = max(0, coerce_int(getattr(state, 'fairy_revives', 0), 0))
        if revive_count <= 0:
            return False
        state.fairy_revives = revive_count - 1
        state.player_hp = FastCombatSimulator._fairy_revive_hp(state)
        return True

    @staticmethod
    def _projected_player_hp_after_loss(state: SimulationState, amount: int) -> int:
        hp_loss = max(0, coerce_int(amount, 0))
        hp_after_loss = max(0, coerce_int(getattr(state, 'player_hp', 0), 0) - hp_loss)
        if hp_after_loss > 0:
            return hp_after_loss
        if max(0, coerce_int(getattr(state, 'fairy_revives', 0), 0)) > 0:
            return FastCombatSimulator._fairy_revive_hp(state)
        return 0

    def _projected_hp_loss_after_block(
        self,
        state: SimulationState,
        incoming_damage: int,
        block: int,
    ) -> int:
        damage_events = self._estimate_incoming_damage_events(
            getattr(state, 'monsters', []),
            getattr(state, 'player_vulnerable_added', 0),
            getattr(state, 'player_intangible', 0),
        )
        incoming_total = max(0, coerce_int(incoming_damage, 0))
        if incoming_total <= 0:
            damage_events = []
        else:
            event_total = sum(damage_events)
            if event_total > incoming_total:
                damage_events = [incoming_total]
            elif 0 < event_total < incoming_total:
                damage_events = list(damage_events) + [incoming_total - event_total]
        if not damage_events:
            damage_events = [incoming_total]
        return self._projected_hp_loss_after_damage_events(state, damage_events, block)

    @staticmethod
    def _projected_hp_loss_after_damage_events(
        state: SimulationState,
        damage_events,
        block: int,
    ) -> int:
        projected_state = state.clone()
        remaining_block = max(0, coerce_int(block, 0))
        hp_loss = 0
        for amount in damage_events or []:
            damage = max(0, coerce_int(amount, 0))
            if damage <= 0:
                continue
            if remaining_block > 0:
                blocked = min(remaining_block, damage)
                remaining_block -= blocked
                damage -= blocked
            if damage <= 0:
                continue
            hp_loss += FastCombatSimulator._effective_player_hp_loss(
                projected_state,
                damage,
            )
        return hp_loss

    @staticmethod
    def _lose_player_hp(
        state: SimulationState,
        amount: int,
        *,
        trigger_rupture: bool = True,
    ):
        hp_loss = FastCombatSimulator._effective_player_hp_loss(state, amount)
        if hp_loss <= 0:
            return

        state.player_hp = max(0, state.player_hp - hp_loss)
        FastCombatSimulator._consume_fairy_revive_if_dead(state)
        if trigger_rupture and state.rupture_strength_per_hp_loss > 0:
            state.player_strength += state.rupture_strength_per_hp_loss

    @staticmethod
    def _damage_player(
        state: SimulationState,
        amount: int,
        *,
        trigger_rupture: bool = True,
    ) -> int:
        damage = max(0, coerce_int(amount, 0))
        if damage <= 0:
            return 0

        block = max(0, coerce_int(getattr(state, 'player_block', 0), 0))
        blocked = min(block, damage)
        state.player_block = block - blocked
        remaining = damage - blocked
        if remaining <= 0:
            return 0

        hp_before = max(0, coerce_int(getattr(state, 'player_hp', 0), 0))
        hp_loss = FastCombatSimulator._effective_player_hp_loss(state, remaining)
        if hp_loss <= 0:
            return 0

        state.player_hp = max(0, hp_before - hp_loss)
        FastCombatSimulator._consume_fairy_revive_if_dead(state)
        if trigger_rupture and state.rupture_strength_per_hp_loss > 0:
            state.player_strength += state.rupture_strength_per_hp_loss
        return hp_loss

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
            and not monster.get('half_dead', False)
            and monster.get('hp', monster.get('current_hp', 1)) > 0
        )

    def _estimate_incoming_damage_events(
        self,
        monsters_state: list,
        player_vulnerable_added: int = 0,
        player_intangible: int = 0,
    ) -> list[int]:
        events = []
        for monster in monsters_state:
            events.extend(
                self._estimate_monster_incoming_damage_events(
                    monster,
                    player_vulnerable_added,
                    player_intangible,
                )
            )
        return [event for event in events if event > 0]

    def _estimate_monster_incoming_damage_events(
        self,
        monster: dict,
        player_vulnerable_added: int = 0,
        player_intangible: int = 0,
    ) -> list[int]:
        if not self._is_live_monster_state(monster):
            return []

        intent = monster.get('intent')
        if intent is None:
            return []

        explosion_damage = exploder_explosion_damage(monster)
        if explosion_damage > 0:
            return [1 if player_intangible > 0 else explosion_damage]

        if intent_is_attack(intent):
            has_adjusted_damage = 'move_adjusted_damage' in monster
            raw_damage = monster.get('move_adjusted_damage', None)
            damage = max(0, raw_damage) if isinstance(raw_damage, (int, float)) else 0
            hits = self._positive_monster_hits(monster)
            should_use_damage_fallback = not has_adjusted_damage or raw_damage is None

            if should_use_damage_fallback:
                damage = monster.get('move_base_damage', 0)

            if should_use_damage_fallback and damage == 0:
                monster_name = str(monster.get('name', '') or '')
                damage = 15 if ('elite' in monster_name.lower() or 'boss' in monster_name.lower()) else 8

            if should_use_damage_fallback:
                damage = self._apply_monster_strength_to_per_hit_damage(
                    damage,
                    monster.get('strength', 0),
                )
                damage = self._apply_monster_weak_to_per_hit_damage(
                    damage,
                    monster.get('weak', 0),
                )

            total = max(0, coerce_int(damage, 0)) * hits
            if player_vulnerable_added > 0:
                total = self._apply_player_vulnerable_damage(
                    total,
                    player_vulnerable_added,
                    hits,
                )
            if player_intangible > 0 and total > 0:
                return [1] * hits
            if total <= 0:
                return []
            if hits > 1:
                per_hit, remainder = divmod(total, hits)
                if remainder == 0:
                    return [per_hit] * hits
            return [total]

        known_unknown_damage = known_unknown_move_immediate_damage(monster)
        if known_unknown_damage > 0:
            return [1 if player_intangible > 0 else known_unknown_damage]
        return []

    def _estimate_incoming_damage(
        self,
        monsters_state: list,
        player_vulnerable_added: int = 0,
        player_intangible: int = 0,
    ) -> int:
        """
        Estimate expected incoming damage from monsters next turn.

        Args:
            monsters_state: List of monster state dictionaries
            player_vulnerable_added: Vulnerable stacks newly applied during simulation.
                Current game intent damage already includes pre-existing player Vulnerable.
            player_intangible: Intangible stacks active for the upcoming enemy attacks.

        Returns:
            Expected total damage
        """
        total_damage = 0
        debug_entries = []
        intent_present = False
        attack_intent_present = False

        for monster in monsters_state:
            monster_hp = monster.get('hp', monster.get('current_hp', 1))
            if (
                monster.get('is_gone', False)
                or monster.get('half_dead', False)
                or monster_hp <= 0
            ):
                if monster.get('is_gone', False):
                    skip_reason = "gone"
                elif monster.get('half_dead', False):
                    skip_reason = "half_dead"
                else:
                    skip_reason = "dead"
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

            intent_str = self._intent_name(intent)

            # Estimate damage based on intent
            intent_present = True
            if intent_is_attack(intent):
                attack_intent_present = True
                # Use actual monster damage data from game state
                has_adjusted_damage = 'move_adjusted_damage' in monster
                raw_damage = monster.get('move_adjusted_damage', None)
                damage = max(0, raw_damage) if isinstance(raw_damage, (int, float)) else 0
                hits = self._positive_monster_hits(monster)
                damage_source = "adjusted"
                should_use_damage_fallback = not has_adjusted_damage or raw_damage is None

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

                if should_use_damage_fallback:
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
                if player_intangible > 0 and total > 0:
                    total = min(total, hits)

                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    f"intent={intent_str} damage={damage} hits={hits} source={damage_source}"
                )
                total_damage += total
            else:
                known_unknown_damage = known_unknown_move_immediate_damage(monster)
                if known_unknown_damage > 0:
                    total = known_unknown_damage
                    if player_intangible > 0:
                        total = 1
                    debug_entries.append(
                        f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                        f"intent={intent_str} damage={known_unknown_damage} source=known_unknown"
                    )
                    total_damage += total
                    continue

                debug_entries.append(
                    f"{monster.get('name', 'Unknown')}[{monster.get('monster_id', '?')}|move={monster.get('move_id', '?')}]:"
                    f"skip=intent={intent_str}"
                )

        if total_damage > 0:
            logger.debug(f"[INCOMING_DAMAGE] Estimated total incoming damage: {total_damage}")
        elif debug_entries and (attack_intent_present or intent_present):
            logger.info("[INCOMING_DAMAGE_ZERO] " + " | ".join(debug_entries))

        return total_damage

    def _estimate_player_thorns_damage(self, state: SimulationState) -> int:
        """Estimate damage current attackers will take from player Thorns."""
        player_thorns = max(0, getattr(state, 'player_thorns', 0))
        if player_thorns <= 0:
            return 0

        projected = state.clone()
        total_damage = 0
        for monster in projected.monsters:
            if (
                not self._is_live_monster_state(monster)
                or not self._monster_intends_attack(monster)
            ):
                continue
            if not monster.get('retains_block', False):
                monster['block'] = 0
            for attack_damage in self._estimate_monster_incoming_damage_events(
                monster,
                getattr(projected, 'player_vulnerable_added', 0),
                getattr(projected, 'player_intangible', 0),
            ):
                self._damage_player(projected, attack_damage, trigger_rupture=False)
                if projected.player_hp <= 0:
                    return total_damage

                block = max(0, coerce_int(monster.get('block', 0), 0))
                blocked = min(block, player_thorns)
                monster['block'] = block - blocked
                hp_damage = min(
                    max(0, player_thorns - blocked),
                    max(0, coerce_int(monster.get('hp', 0), 0)),
                )
                monster['hp'] = max(0, coerce_int(monster.get('hp', 0), 0) - hp_damage)
                total_damage += hp_damage
                if not self._is_live_monster_state(monster):
                    break
        return total_damage

    def _get_enemy_lookahead_depth(self, state: SimulationState, context: DecisionContext, max_depth: int = 2) -> int:
        """Gate lookahead depth based on combat complexity and data availability."""
        try:
            monsters_alive = sum(
                1 for monster in state.monsters
                if self._is_live_monster_state(monster)
            )
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
        previous_prediction_context = getattr(self, "_prediction_context", None)
        previous_prediction_monsters = getattr(self, "_prediction_monsters", None)
        previous_prediction_monster = getattr(self, "_prediction_monster", None)
        self._prediction_context = context
        self._prediction_monsters = state.monsters
        try:
            current_turn = self._non_negative_int(getattr(context, 'turn', 1)) or 1
            for monster in state.monsters:
                if not self._is_live_monster_state(monster):
                    continue

                current_move = self._current_monster_move(monster)
                if self._is_live_phase_transition_move(monster, current_move):
                    return True

                monster_name = _canonical_live_monster_name(monster)
                if not monster_name:
                    continue
                max_hp = monster.get('max_hp', monster.get('hp', 1))
                hp_percent = monster.get('hp', max_hp) / max_hp if max_hp > 0 else 1.0
                self._prediction_monster = monster
                try:
                    predicted_moves = self._predict_monster_moves(
                        monster_name,
                        current_turn,
                        hp_percent,
                        context,
                    )
                finally:
                    if previous_prediction_monster is None:
                        self.__dict__.pop("_prediction_monster", None)
                    else:
                        self._prediction_monster = previous_prediction_monster
                if not predicted_moves:
                    continue

                if current_move and not self._move_can_deal_immediate_damage(current_move):
                    future_attack_after_current_move = any(
                        self._move_can_deal_immediate_damage(prediction.get('move', {}))
                        for prediction in predicted_moves
                    )
                    if future_attack_after_current_move:
                        return True

                first_move = predicted_moves[0].get('move', {})
                later_attack = any(
                    self._move_can_deal_immediate_damage(prediction.get('move', {}))
                    for prediction in predicted_moves[1:]
                )
                if later_attack and not self._move_can_deal_immediate_damage(first_move):
                    return True

            return False
        finally:
            if previous_prediction_context is None:
                self.__dict__.pop("_prediction_context", None)
            else:
                self._prediction_context = previous_prediction_context
            if previous_prediction_monsters is None:
                self.__dict__.pop("_prediction_monsters", None)
            else:
                self._prediction_monsters = previous_prediction_monsters
            if previous_prediction_monster is None:
                self.__dict__.pop("_prediction_monster", None)
            else:
                self._prediction_monster = previous_prediction_monster

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
        previous_prediction_context = getattr(self, "_prediction_context", None)
        previous_prediction_monsters = getattr(self, "_prediction_monsters", None)
        previous_prediction_monster = getattr(self, "_prediction_monster", None)
        self._prediction_context = context
        try:
            lookahead_state = state.clone()
            self._prediction_monsters = lookahead_state.monsters
            logger.info(
                "[LOOKAHEAD_ENTRY] turns=%s monsters=%s hp=%s/%s",
                look_ahead,
                len([m for m in lookahead_state.monsters if self._is_live_monster_state(m)]),
                lookahead_state.player_hp,
                lookahead_state.player_max_hp
            )
            total_future_damage = 0
            current_turn = self._non_negative_int(getattr(context, 'turn', 1)) or 1

            player_vulnerable = lookahead_state.player_vulnerable
            player_weak = lookahead_state.player_weak
            player_frail = lookahead_state.player_frail
            player_constricted = max(0, getattr(lookahead_state, 'player_constricted', 0))
            player_artifact = max(0, getattr(lookahead_state, 'player_artifact', 0))

            for step in range(look_ahead):
                turn_damage = 0
                turn_block_remaining = (
                    max(0, coerce_int(lookahead_state.turn_block(), 0))
                    if step == 0
                    else 0
                )
                pending_debuffs = {'weak': 0, 'frail': 0, 'vulnerable': 0}
                pending_constricted = 0
                any_predictions = False
                split_due_this_turn = False

                if step > 0 and player_constricted > 0:
                    discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                    turn_damage += int(player_constricted * discount)

                lookahead_state = self._revive_ready_darklings(lookahead_state)
                for idx, monster in enumerate(lookahead_state.monsters):
                    if not self._is_live_monster_state(monster):
                        continue

                    split_info = self._get_death_split_info(monster)
                    if split_info and self._is_death_split_due(monster, split_info):
                        monster['split_pending'] = True
                        split_due_this_turn = True
                        continue

                    explosion_damage = exploder_explosion_damage(monster)
                    if explosion_damage > 0:
                        discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                        turn_damage += int(explosion_damage * discount)
                        monster['hp'] = 0
                        monster['block'] = 0
                        monster['is_gone'] = True
                        monster['half_dead'] = False
                        continue

                    monster_name = _canonical_live_monster_name(monster)
                    if not monster_name:
                        continue

                    max_hp = monster.get('max_hp', monster['hp'])
                    hp_percent = monster['hp'] / max_hp if max_hp > 0 else 1.0
                    move = self._current_monster_move(monster) if step == 0 else None
                    if move is None:
                        self._prediction_monster = monster
                        try:
                            move = self._predicted_monster_move_for_step(
                                monster_name,
                                current_turn,
                                step,
                                hp_percent,
                            )
                        finally:
                            self._prediction_monster = previous_prediction_monster
                    if move:
                        any_predictions = True

                    if move:
                        target_turn = current_turn + step
                        move_damage = self._move_damage_value(move, lookahead_state, target_turn=target_turn)
                        move_damage = self._apply_ascension_move_value(
                            move,
                            context,
                            'damage',
                            move_damage,
                        )
                        move_hits = self._move_hit_count(move, target_turn=target_turn)
                        move_hits = self._apply_ascension_move_value(
                            move,
                            context,
                            'hits',
                            move_hits,
                        )

                        move_is_attack = intent_is_attack(move.get('intent', ''))
                        move_is_known_unknown_damage = (
                            not move_is_attack
                            and self._move_has_known_unknown_immediate_damage(move)
                        )
                        if (move_is_attack or move_is_known_unknown_damage) and move_damage > 0:
                            if move_is_attack:
                                per_hit_damage = self._apply_monster_strength_to_per_hit_damage(
                                    move_damage,
                                    self._effective_monster_attack_strength(monster),
                                )
                                per_hit_damage = self._apply_monster_weak_to_per_hit_damage(
                                    per_hit_damage,
                                    monster.get('weak', 0),
                                )
                                damage = per_hit_damage * move_hits
                                effective_player_vulnerable = (
                                    player_vulnerable + pending_debuffs['vulnerable']
                                )
                                damage = self._apply_player_vulnerable_damage(
                                    damage,
                                    effective_player_vulnerable,
                                    move_hits,
                                )
                                damage = self._apply_debuff_risk_multiplier(damage, player_weak, player_frail)
                                hp_loss = max(0, damage - turn_block_remaining)
                                turn_block_remaining = max(0, turn_block_remaining - damage)
                                self._apply_shelled_parasite_attack_buff_heal(
                                    monster,
                                    hp_loss,
                                    move.get('intent', monster.get('intent', '')),
                                )
                            else:
                                damage = move_damage * move_hits
                            discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                            turn_damage += int(damage * discount)

                        move_debuffs = self._extract_move_debuffs(move, context)
                        player_artifact = self._queue_player_predicted_debuffs(
                            pending_debuffs,
                            move_debuffs,
                            player_artifact,
                        )
                        constricted = self._extract_move_constricted(move, context)
                        if constricted > 0:
                            if player_artifact > 0:
                                player_artifact -= 1
                            else:
                                pending_constricted += constricted
                        all_enemies_strength_gain = (
                            self._extract_move_all_enemies_strength_gain(move, context)
                        )
                        if all_enemies_strength_gain > 0:
                            self._apply_all_live_monsters_strength_gain(
                                lookahead_state,
                                all_enemies_strength_gain,
                            )
                        else:
                            strength_gain = self._extract_move_strength_gain(move, context)
                            if strength_gain > 0:
                                self._apply_predicted_monster_strength_gain(
                                    monster,
                                    strength_gain,
                                )
                        if self._move_clears_monster_debuffs(move):
                            self._clear_monster_debuffs(monster)
                    else:
                        has_adjusted_damage = 'move_adjusted_damage' in monster
                        adjusted_damage = monster.get('move_adjusted_damage', None)
                        should_use_damage_fallback = (
                            not has_adjusted_damage or adjusted_damage is None
                        )
                        fallback_damage = (
                            monster.get('move_base_damage', 0)
                            if should_use_damage_fallback
                            else adjusted_damage
                        )
                        fallback_damage = self._numeric_damage_value(fallback_damage)
                        if fallback_damage > 0:
                            move_hits = monster.get('move_hits', 1)
                            per_hit_damage = fallback_damage
                            if should_use_damage_fallback:
                                per_hit_damage = self._apply_monster_strength_to_per_hit_damage(
                                    per_hit_damage,
                                    self._effective_monster_attack_strength(monster),
                                )
                                per_hit_damage = self._apply_monster_weak_to_per_hit_damage(
                                    per_hit_damage,
                                    monster.get('weak', 0),
                                )
                            damage = per_hit_damage * move_hits
                            effective_player_vulnerable = (
                                player_vulnerable + pending_debuffs['vulnerable']
                            )
                            damage = self._apply_player_vulnerable_damage(
                                damage,
                                effective_player_vulnerable,
                                move_hits,
                            )
                            damage = self._apply_debuff_risk_multiplier(damage, player_weak, player_frail)
                            hp_loss = max(0, damage - turn_block_remaining)
                            turn_block_remaining = max(0, turn_block_remaining - damage)
                            self._apply_shelled_parasite_attack_buff_heal(
                                monster,
                                hp_loss,
                                monster.get('intent', ''),
                            )
                            discount = LOOKAHEAD_DAMAGE_DISCOUNT ** step
                            turn_damage += int(damage * discount)

                total_future_damage += turn_damage

                player_vulnerable = max(0, player_vulnerable + pending_debuffs['vulnerable'] - 1)
                player_weak = max(0, player_weak + pending_debuffs['weak'] - 1)
                player_frail = max(0, player_frail + pending_debuffs['frail'] - 1)
                player_constricted = max(0, player_constricted + pending_constricted)
                lookahead_state.player_constricted = player_constricted
                self._decrement_monster_turn_debuffs(lookahead_state)
                self._apply_monster_end_turn_strength_gains(lookahead_state)

                logger.debug(
                    f"[LOOKAHEAD_TURN] step={step + 1} damage={turn_damage} "
                    f"debuffs=V{player_vulnerable}/W{player_weak}/F{player_frail}/C{player_constricted}"
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
        finally:
            if previous_prediction_context is None:
                self.__dict__.pop("_prediction_context", None)
            else:
                self._prediction_context = previous_prediction_context
            if previous_prediction_monsters is None:
                self.__dict__.pop("_prediction_monsters", None)
            else:
                self._prediction_monsters = previous_prediction_monsters
            if previous_prediction_monster is None:
                self.__dict__.pop("_prediction_monster", None)
            else:
                self._prediction_monster = previous_prediction_monster

    def _apply_shelled_parasite_attack_buff_heal(
        self,
        monster: Dict[str, Any],
        hp_loss: int,
        intent: Any,
    ):
        heal_amount = max(0, coerce_int(hp_loss, 0))
        if heal_amount <= 0:
            return
        if not self._is_shelled_parasite_monster(monster):
            return
        if not self._is_attack_buff_intent(intent):
            return

        current_hp = max(0, coerce_int(monster.get('hp', 0), 0))
        max_hp = max(current_hp, coerce_int(monster.get('max_hp', current_hp), current_hp))
        if max_hp <= 0:
            return
        monster['hp'] = min(max_hp, current_hp + heal_amount)

    @staticmethod
    def _is_shelled_parasite_monster(monster: Dict[str, Any]) -> bool:
        identifiers = {
            normalize_monster_id(monster.get('name', '')),
            normalize_monster_id(monster.get('monster_id', '')),
            normalize_monster_id(monster.get('id', '')),
            normalize_monster_id(_canonical_live_monster_name(monster)),
        }
        return 'shelledparasite' in identifiers or 'shellparasite' in identifiers

    def _is_attack_buff_intent(self, intent: Any) -> bool:
        tokens = intent_tokens(intent)
        if 'ATTACK' in tokens and 'BUFF' in tokens:
            return True
        return 'attackbuff' in self._intent_name(intent).replace('_', '').lower()

    def _apply_monster_end_turn_strength_gains(self, state: SimulationState):
        for monster in state.monsters:
            if not self._is_live_monster_state(monster):
                continue

            strength_gain = int(monster.get('end_turn_strength_gain', 0) or 0)
            if strength_gain <= 0:
                continue

            self._remember_monster_adjusted_damage_source(monster)
            monster['strength'] = monster.get('strength', 0) + strength_gain
            monster['_simulated_strength_delta'] = (
                monster.get('_simulated_strength_delta', 0) + strength_gain
            )
            self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _apply_all_live_monsters_strength_gain(
        self,
        state: SimulationState,
        strength_gain: int,
    ):
        for monster in state.monsters:
            if not self._is_live_monster_state(monster):
                continue
            self._apply_predicted_monster_strength_gain(monster, strength_gain)

    def _apply_predicted_monster_strength_gain(self, monster: dict, strength_gain: int):
        if strength_gain <= 0:
            return
        self._remember_monster_adjusted_damage_source(monster)
        monster['strength'] = monster.get('strength', 0) + strength_gain
        monster['_simulated_strength_delta'] = (
            monster.get('_simulated_strength_delta', 0) + strength_gain
        )
        self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def _move_clears_monster_debuffs(self, move: Dict[str, Any]) -> bool:
        if move.get('clears_debuffs') or move.get('removes_debuffs'):
            return True
        effect = str(move.get('effect') or move.get('description') or '')
        return bool(re.search(r'\b(?:removes?|clears?)\s+all\s+debuffs\b', effect, re.IGNORECASE))

    def _clear_monster_debuffs(self, monster: dict):
        changed = False
        for debuff in ('weak', 'vulnerable', 'frail'):
            if monster.get(debuff, 0) > 0:
                monster[debuff] = 0
                changed = True
        if changed:
            monster.pop('_simulated_weak_applied_to_attack', None)
            self._refresh_monster_adjusted_damage_from_debuffs(monster)

    def simulate_enemy_status_lookahead(
        self,
        state: SimulationState,
        context: DecisionContext,
        look_ahead: int = 2,
    ) -> Dict[str, int]:
        """Estimate draw/status and control disruption from near-future monster moves."""
        totals = {
            'total': 0,
            'dazed': 0,
            'burn': 0,
            'slimed': 0,
            'wound': 0,
            'void': 0,
            'hex': 0,
            'entangled': 0,
            'confused': 0,
            'draw_reduction': 0,
        }
        previous_prediction_context = getattr(self, "_prediction_context", None)
        previous_prediction_monsters = getattr(self, "_prediction_monsters", None)
        previous_prediction_monster = getattr(self, "_prediction_monster", None)
        self._prediction_context = context
        self._prediction_monsters = state.monsters
        try:
            current_turn = self._non_negative_int(getattr(context, 'turn', 1)) or 1
            player_artifact = max(0, getattr(state, 'player_artifact', 0))
            for step in range(look_ahead):
                for monster in state.monsters:
                    if not self._is_live_monster_state(monster):
                        continue

                    move = self._current_monster_move(monster) if step == 0 else None
                    if move is None:
                        monster_name = _canonical_live_monster_name(monster)
                        if not monster_name:
                            continue
                        max_hp = monster.get('max_hp', monster['hp'])
                        hp_percent = monster['hp'] / max_hp if max_hp > 0 else 1.0
                        self._prediction_monster = monster
                        try:
                            move = self._predicted_monster_move_for_step(
                                monster_name,
                                current_turn,
                                step,
                                hp_percent,
                            )
                        finally:
                            self._prediction_monster = previous_prediction_monster

                    if not move:
                        continue

                    counts = self._extract_move_status_cards(move, context)
                    for key in totals:
                        totals[key] += counts.get(key, 0)
                    hex_stacks = self._extract_move_hex(move, context)
                    if hex_stacks > 0:
                        if player_artifact > 0:
                            player_artifact -= 1
                        else:
                            dazed_risk = max(1, hex_stacks)
                            totals['hex'] += hex_stacks
                            totals['dazed'] += dazed_risk
                            totals['total'] += dazed_risk
                    entangled = self._extract_move_entangled(move, context)
                    if entangled > 0:
                        if player_artifact > 0:
                            player_artifact -= 1
                        else:
                            totals['entangled'] += entangled
                            totals['total'] += entangled
                    confused = self._extract_move_confused(move, context)
                    if confused > 0:
                        if player_artifact > 0:
                            player_artifact -= 1
                        else:
                            totals['confused'] += confused
                            totals['total'] += confused
                    draw_reduction = self._extract_move_draw_reduction(move, context)
                    if draw_reduction > 0:
                        if player_artifact > 0:
                            player_artifact -= 1
                        else:
                            totals['draw_reduction'] += draw_reduction
                            totals['total'] += draw_reduction

            if totals['total'] > 0:
                logger.info(
                    "[STATUS_LOOKAHEAD] predicted=%s dazed=%s burn=%s slimed=%s wound=%s void=%s hex=%s entangled=%s confused=%s draw_reduction=%s",
                    totals['total'],
                    totals['dazed'],
                    totals['burn'],
                    totals['slimed'],
                    totals['wound'],
                    totals['void'],
                    totals['hex'],
                    totals['entangled'],
                    totals['confused'],
                    totals['draw_reduction'],
                )
            return totals
        except Exception as e:
            logger.warning(f"[STATUS_LOOKAHEAD] Failed to simulate enemy disruption: {e}")
            return totals
        finally:
            if previous_prediction_context is None:
                self.__dict__.pop("_prediction_context", None)
            else:
                self._prediction_context = previous_prediction_context
            if previous_prediction_monsters is None:
                self.__dict__.pop("_prediction_monsters", None)
            else:
                self._prediction_monsters = previous_prediction_monsters
            if previous_prediction_monster is None:
                self.__dict__.pop("_prediction_monster", None)
            else:
                self._prediction_monster = previous_prediction_monster

    def _predicted_monster_move_for_step(
        self,
        monster_name: str,
        current_turn: int,
        step: int,
        hp_percent: float,
    ) -> Optional[Dict[str, Any]]:
        context = getattr(self, "_prediction_context", None)
        target_turn = current_turn + step
        predictions = self._predict_monster_moves(
            monster_name,
            current_turn,
            hp_percent,
            context,
        )
        for prediction in predictions:
            if prediction.get('turn') == target_turn:
                return prediction.get('move', None)

        if predictions and step == 0:
            return predictions[0].get('move', None)

        predictions = self._predict_monster_moves(
            monster_name,
            target_turn,
            hp_percent,
            context,
        )
        if predictions:
            return predictions[0].get('move', None)
        return None

    def _predict_monster_moves(
        self,
        monster_name: str,
        current_turn: int,
        hp_percent: float,
        context: Optional[DecisionContext] = None,
    ) -> List[Dict[str, Any]]:
        try:
            ascension_level = (
                self._context_ascension_level(context)
                if context is not None
                else 0
            )
            other_enemy_names = self._context_other_enemy_names(context, monster_name)
            other_enemy_count = len(other_enemy_names) if other_enemy_names is not None else None
            same_monster_index = self._context_same_monster_index(context, monster_name)
            try:
                return game_data_loader.predict_monster_moves(
                    monster_name,
                    current_turn,
                    hp_percent,
                    ascension_level=ascension_level,
                    other_enemy_count=other_enemy_count,
                    other_enemy_names=other_enemy_names,
                    same_monster_index=same_monster_index,
                )
            except TypeError:
                try:
                    return game_data_loader.predict_monster_moves(
                        monster_name,
                        current_turn,
                        hp_percent,
                        ascension_level=ascension_level,
                        other_enemy_count=other_enemy_count,
                        other_enemy_names=other_enemy_names,
                    )
                except TypeError:
                    pass
                try:
                    return game_data_loader.predict_monster_moves(
                        monster_name,
                        current_turn,
                        hp_percent,
                        ascension_level=ascension_level,
                        other_enemy_count=other_enemy_count,
                    )
                except TypeError:
                    pass
                try:
                    return game_data_loader.predict_monster_moves(
                        monster_name,
                        current_turn,
                        hp_percent,
                        ascension_level=ascension_level,
                    )
                except TypeError:
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

            if intent_is_attack(live_intent) and live_damage > 0:
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
        move_tokens = intent_tokens(move.get('intent', ''))
        live_tokens = intent_tokens(live_intent)
        if not move_tokens or not live_tokens:
            return False
        if move_tokens == live_tokens:
            return True

        live_has_attack = 'ATTACK' in live_tokens
        move_has_attack = 'ATTACK' in move_tokens
        if live_has_attack:
            if not move_has_attack:
                return False
            for required_tag in ('DEFEND', 'DEBUFF', 'BUFF'):
                if required_tag in live_tokens and required_tag not in move_tokens:
                    return False
            return True

        if move_has_attack:
            return False
        if 'DEBUFF' in live_tokens and 'DEBUFF' in move_tokens:
            return True
        if 'BUFF' in live_tokens and 'BUFF' in move_tokens:
            return True
        if 'DEFEND' in live_tokens and ('DEFEND' in move_tokens or 'BLOCK' in move_tokens):
            return True
        return False

    def _move_has_known_unknown_immediate_damage(self, move: Dict[str, Any]) -> bool:
        return move_data_immediate_unknown_damage(move) > 0

    def _move_can_deal_immediate_damage(self, move: Dict[str, Any]) -> bool:
        if not move:
            return False
        return (
            intent_is_attack(move.get('intent', ''))
            or self._move_has_known_unknown_immediate_damage(move)
        )

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

    def _apply_ascension_move_value(self, move: Dict[str, Any], context: DecisionContext, key: str, base_value: int) -> int:
        ascension_modifiers = move.get('ascension_modifiers', {})
        if not isinstance(ascension_modifiers, dict):
            return base_value

        ascension_level = self._context_ascension_level(context)
        thresholds = [
            int(threshold_key.split('+')[0])
            for threshold_key in ascension_modifiers
            if (
                isinstance(threshold_key, str)
                and threshold_key.endswith('+')
                and threshold_key.split('+')[0].isdigit()
            )
        ]
        for threshold in sorted(thresholds, reverse=True):
            if ascension_level < threshold:
                continue
            modifier = ascension_modifiers.get(f"{threshold}+", {})
            if isinstance(modifier, dict):
                if key in modifier:
                    value = self._optional_numeric_damage_value(modifier.get(key))
                    return value if value is not None else base_value
                if key == 'damage' and 'damage_bonus' in modifier:
                    bonus = self._optional_numeric_damage_value(modifier.get('damage_bonus'))
                    return base_value + bonus if bonus is not None else base_value
            break

        return base_value

    def _context_ascension_level(self, context: DecisionContext) -> int:
        if hasattr(context, 'game') and hasattr(context.game, 'ascension_level'):
            return max(0, coerce_int(context.game.ascension_level or 0, 0))
        return max(0, coerce_int(getattr(context, 'ascension_level', 0) or 0, 0))

    def _context_other_enemy_count(
        self,
        context: Optional[DecisionContext],
        monster_name: str,
    ) -> Optional[int]:
        other_enemy_names = self._context_other_enemy_names(context, monster_name)
        return len(other_enemy_names) if other_enemy_names is not None else None

    def _context_other_enemy_names(
        self,
        context: Optional[DecisionContext],
        monster_name: str,
    ) -> Optional[List[str]]:
        monsters = self._context_prediction_monsters(context)
        if not monsters:
            return None

        target_name = str(monster_name or '').lower()
        other_names = []
        target_monster = getattr(self, "_prediction_monster", None)
        skipped_target_by_name = target_monster is not None
        for monster in monsters:
            if not self._is_live_context_monster(monster):
                continue
            candidate_name = str(_canonical_live_monster_name(monster) or '').lower()
            if target_monster is not None:
                if monster is target_monster:
                    continue
            elif candidate_name == target_name and not skipped_target_by_name:
                skipped_target_by_name = True
                continue
            if candidate_name:
                other_names.append(_canonical_live_monster_name(monster))
        return other_names

    def _context_same_monster_index(
        self,
        context: Optional[DecisionContext],
        monster_name: str,
    ) -> Optional[int]:
        target_monster = getattr(self, "_prediction_monster", None)
        if target_monster is None:
            return None

        monsters = self._context_prediction_monsters(context)
        if not monsters:
            return None

        target_name = str(monster_name or '').lower()
        same_name_index = 0
        for monster in monsters:
            if not self._is_live_context_monster(monster):
                continue
            candidate_name = str(_canonical_live_monster_name(monster) or '').lower()
            if candidate_name != target_name:
                continue
            if monster is target_monster:
                return same_name_index
            same_name_index += 1
        return None

    def _context_prediction_monsters(self, context: Optional[DecisionContext]) -> Optional[List[Any]]:
        prediction_monsters = getattr(self, "_prediction_monsters", None)
        if prediction_monsters is not None:
            return prediction_monsters
        if context is None:
            return None

        game = getattr(context, 'game', None)
        monsters = getattr(game, 'monsters', None) if game is not None else None
        if monsters is None:
            monsters = getattr(context, 'monsters_alive', None)
        return monsters

    @staticmethod
    def _is_live_context_monster(monster: Any) -> bool:
        hp = coerce_int(
            monster_field(
                monster,
                'current_hp',
                monster_field(monster, 'hp', 1),
            ),
            0,
        )
        return (
            not monster_field(monster, 'is_gone', False)
            and not monster_field(monster, 'half_dead', False)
            and hp > 0
        )

    def _move_hit_count(self, move: Dict[str, Any], target_turn: Optional[int] = None) -> int:
        move_name = str(move.get('name', ''))
        if move_name == 'Divider':
            return 6
        formula_hits = self._formula_hit_count(move.get('hits_formula'), target_turn)
        if formula_hits is not None:
            return formula_hits
        return max(1, coerce_int(move.get('hits', move.get('move_hits', 1)) or 1, 1))

    def _formula_damage_value(self, formula: Any, target_turn: Optional[int]) -> Optional[int]:
        if not isinstance(formula, dict):
            return None

        formula_type = formula.get('type')
        turn = max(1, coerce_int(target_turn or 1, 1))

        if formula_type == 'linear_by_turn':
            base = coerce_int(formula.get('base', 0) or 0, 0)
            per_turn = coerce_int(formula.get('per_turn', 0) or 0, 0)
            turn_offset = coerce_int(formula.get('turn_offset', 0) or 0, 0)
            return base + per_turn * max(0, turn + turn_offset)

        if formula_type == 'linear_after_turn':
            base = coerce_int(formula.get('base', 0) or 0, 0)
            increment = coerce_int(formula.get('increment', 0) or 0, 0)
            first_turn = max(1, coerce_int(formula.get('first_turn', 1) or 1, 1))
            bonus = increment * max(0, turn - first_turn)
            max_bonus = coerce_int(formula.get('max_bonus'), None)
            if max_bonus is not None:
                bonus = min(bonus, max_bonus)
            return base + bonus

        return None

    def _formula_hit_count(self, formula: Any, target_turn: Optional[int]) -> Optional[int]:
        if not isinstance(formula, dict):
            return None
        if formula.get('type') != 'ceil_turn_divisor':
            return None

        divisor = max(1, coerce_int(formula.get('divisor', 1) or 1, 1))
        turn = max(1, coerce_int(target_turn or 1, 1))
        hits = (turn + divisor - 1) // divisor
        min_hits = coerce_int(formula.get('min_hits'), None)
        max_hits = coerce_int(formula.get('max_hits'), None)
        if min_hits is not None:
            hits = max(hits, min_hits)
        if max_hits is not None:
            hits = min(hits, max_hits)
        return max(0, hits)

    def _numeric_damage_value(self, damage: Any) -> int:
        value = self._optional_numeric_damage_value(damage)
        return value if value is not None else 0

    def _optional_numeric_damage_value(self, damage: Any) -> Optional[int]:
        if not isinstance(damage, dict):
            return coerce_int(damage, None)

        numeric_values = []
        for key in ('max', 'normal', 'base', 'min'):
            value = coerce_int(damage.get(key), None)
            if value is not None:
                return value
        for value in damage.values():
            coerced = coerce_int(value, None)
            if coerced is not None:
                numeric_values.append(coerced)
        return max(numeric_values, default=None)

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

            split_hp = max(0, coerce_int(monster.get('hp', 0), 0))
            if split_hp <= 0:
                gone_monster = monster.copy()
                gone_monster['is_gone'] = True
                new_monsters.append(gone_monster)
                continue

            monster_name = monster.get('name', 'Unknown')
            threshold, split_names = split_info
            max_hp = max(0, coerce_int(monster.get('max_hp', split_hp), split_hp))
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
        monster_name = _canonical_live_monster_name(monster)
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
            split_names = [monster_name] * max(0, coerce_int(split_count, 0))
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
        threshold = coerce_float(threshold, 50.0)
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
        hp = max(0, coerce_int(monster.get('hp', 0), 0))
        max_hp = max(0, coerce_int(monster.get('max_hp', hp), hp))
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
        damage, hits, _move_id = self._strongest_known_attack_move_values(monster_name)
        return int(damage * hits)

    def _strongest_known_attack_move_values(self, monster_name: str) -> Tuple[int, int, Optional[int]]:
        best_damage = 0
        best_hits = 1
        best_move_id = None
        for move in game_data_loader.get_monster_moves(monster_name):
            damage = self._numeric_damage_value(move.get('damage'))
            if not intent_is_attack(move.get('intent', '')) or damage <= 0:
                continue
            hits = self._move_hit_count(move)
            total = int(damage * hits)
            if total <= best_damage:
                continue
            best_damage = damage
            best_hits = hits
            best_move_id = coerce_int(move.get('move_id'), None)
        return best_damage, best_hits, best_move_id

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

            monster_name = _canonical_live_monster_name(monster)
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

            monster_name = _canonical_live_monster_name(monster)
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

            monster_name = _canonical_live_monster_name(monster)
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
            elif intent_is_attack(intent) or 'DEBUFF' in intent_tokens(intent) or move_damage > 0:
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
                m['hp']
                for m in final_state.monsters
                if self._is_live_monster_state(m)
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

    def _outcome_total_damage(
        self,
        initial_state: SimulationState,
        final_state: SimulationState,
    ) -> int:
        tracked_damage = max(
            0,
            coerce_int(getattr(final_state, 'total_damage_dealt', 0), 0)
            - coerce_int(getattr(initial_state, 'total_damage_dealt', 0), 0),
        )
        if tracked_damage > 0:
            return tracked_damage

        initial_hp = sum(m['hp'] for m in initial_state.monsters)
        final_existing_hp = sum(
            m['hp']
            for m in final_state.monsters[:len(initial_state.monsters)]
            if not self._is_lifecycle_spawned_monster(m)
        )
        return max(0, initial_hp - final_existing_hp)

    @staticmethod
    def _is_lifecycle_spawned_monster(monster: dict) -> bool:
        return bool(
            monster.get('summoned_by')
            or monster.get('split_materialized')
        )

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

        if getattr(final_state, 'combat_escaped', False):
            return self._score_combat_escape(final_state, current_act, weights)

        final_state = self.project_end_turn_effects(final_state)
        score = 0.0

        # 1. Monsters killed (high priority)
        initial_alive = sum(1 for m in initial_state.monsters if self._is_live_monster_state(m))
        final_alive = sum(1 for m in final_state.monsters if self._is_live_monster_state(m))
        escaped_monsters = max(
            0,
            getattr(final_state, 'monsters_escaped', 0)
            - getattr(initial_state, 'monsters_escaped', 0),
        )
        kills = max(0, initial_alive - final_alive - escaped_monsters)
        score += kills * weights['KILL_BONUS']

        # ALL_LETHAL_BONUS: Exponential bonus for killing all monsters
        if final_alive == 0 and initial_alive > 0 and escaped_monsters == 0:
            score += ALL_LETHAL_BONUS
            logger.debug(f"[ALL_LETHAL_BONUS] +{ALL_LETHAL_BONUS} score for killing all {initial_alive} monsters")

        # 2. Damage dealt (with multi-monster bonuses)
        total_damage = self._outcome_total_damage(initial_state, final_state)

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

        thorns_damage = self._estimate_player_thorns_damage(final_state)
        if thorns_damage > 0:
            score += thorns_damage * weights['DAMAGE_WEIGHT']
            logger.debug(
                "[THORNS_SCORE] +%.1f for %s reflected damage",
                thorns_damage * weights['DAMAGE_WEIGHT'],
                thorns_damage,
            )

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
            aoe_cards = IRONCLAD_AOE_ATTACK_CARDS

            for action in sequence:
                if getattr(action, 'card', None) is not None:
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
                        upgrades = card_upgrade_count(action.card)
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
            getattr(final_state, 'player_intangible', 0),
        )
        hp_loss_next_turn = self._projected_hp_loss_after_block(
            final_state,
            expected_incoming,
            final_turn_block,
        )

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
        hp_after_next_turn = self._projected_player_hp_after_loss(
            final_state,
            hp_loss_next_turn,
        )
        if hp_after_next_turn <= 0:
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
                        "[FUTURE_STATUS_PENALTY] -%.1f score for %s predicted status/control effects",
                        future_status_penalty,
                        future_status['total'],
                    )
            except Exception as e:
                logger.warning(f"[FUTURE_DAMAGE_PENALTY] Failed to apply future damage penalty: {e}")

        # Danger threshold penalty (act-dependent)
        danger_threshold = 15 + (current_act * 5)  # Act 1: 20, Act 2: 25, Act 3: 30
        if hp_after_next_turn < danger_threshold:
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

    def _score_combat_escape(
        self,
        state: SimulationState,
        current_act: int,
        weights: dict,
    ) -> float:
        expected_incoming = self._estimate_incoming_damage(
            state.monsters,
            state.player_vulnerable_added,
            getattr(state, 'player_intangible', 0),
        )
        hp_loss_avoided = self._projected_hp_loss_after_block(
            state,
            expected_incoming,
            state.turn_block(),
        )
        score = hp_loss_avoided * weights['W_DEATHRISK']

        act = max(1, coerce_int(current_act, 1))
        danger_threshold = 15 + (act * 5)
        if hp_loss_avoided >= state.player_hp:
            score += DANGER_PENALTY
        elif state.player_hp - hp_loss_avoided < danger_threshold:
            score += DANGER_PENALTY * 0.5

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

    def _simulate_planner_card_play(
        self,
        state: SimulationState,
        card: Card,
        target: Optional[Monster] = None,
        context: Optional[DecisionContext] = None,
    ) -> SimulationState:
        new_state = self.simulator.simulate_card_play(
            state,
            card,
            target,
            context=context,
        )
        mark_card_played(new_state.played_card_uuids, card)
        return new_state

    @staticmethod
    def _card_cost_for_state(card, state: SimulationState) -> int:
        cost = effective_card_cost(card, state.player_energy)
        if (
            card_type_name(card) == 'SKILL'
            and getattr(state, 'corruption_active', False)
        ):
            return 0
        return cost

    def _calculate_x_block(
        self,
        card: Card,
        state: SimulationState,
        context: DecisionContext,
    ) -> int:
        return self.simulator._calculate_x_block(card, state, context)

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
        energy_available = self._non_negative_int(
            getattr(context, 'energy_available', 3)
        )
        logger.debug(f"Energy available: {energy_available}")

        # === Adaptive beam width by act ===
        # Act 1: 12 (simple enemies, less search needed)
        # Act 2: 18 (moderate complexity)
        # Act 3: 25 (high complexity, elites/bosses)
        if hasattr(context, 'act'):
            act = self._non_negative_int(getattr(context, 'act', 1)) or 1
            adaptive_width = [BEAM_WIDTH_ACT1, BEAM_WIDTH_ACT2, BEAM_WIDTH_ACT3]
            self.beam_width = adaptive_width[min(act - 1, 2)] if act <= 3 else BEAM_WIDTH_ACT3

        # === Adaptive max_depth by hand size and energy ===
        playable_count = len(context.playable_cards)
        potions = game_real_potions(context.game)
        has_usable_potion = any(
            potion_can_use(potion)
            for potion in potions
        )

        # Count zero-cost cards (they enable deeper chains)
        extra_zero_cost = sum(
            1
            for c in context.playable_cards
            if getattr(c, 'cost_for_turn', None) is not None and raw_card_cost(c) == 0
        )

        # Extra energy beyond base 3
        extra_energy = max(0, energy_available - 3)

        # Calculate adaptive depth: base 3 + bonuses
        # More cards, zero-cost cards, or extra energy → deeper search
        adaptive_depth = 3 + extra_energy + (extra_zero_cost // 2)

        # Cap at available actions. Potions are only explored at depth 0.
        action_depth_cap = playable_count + (1 if has_usable_potion else 0)
        adaptive_depth = min(adaptive_depth, action_depth_cap)

        # Hard cap at MAX_DEPTH_CAP to avoid excessive search (timeout protection)
        self.max_depth = min(adaptive_depth, MAX_DEPTH_CAP)

        # Log adaptive parameters
        logger.debug(f"Beam width: {self.beam_width}")
        logger.debug(f"Max depth: {self.max_depth}")
        logger.debug(f"Zero-cost cards: {extra_zero_cost}")
        logger.debug(f"Extra energy: {extra_energy}")

        if not context.playable_cards and not has_usable_potion:
            decision_time = (time.time() - decision_start) * 1000
            logger.debug(f"No playable cards. Decision time: {decision_time:.1f}ms")
            return []  # No playable cards, end turn

        # If only 1-2 cards and no potions, simple evaluation is sufficient
        if len(context.playable_cards) <= 2 and not has_usable_potion:
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

        if card_requires_target(best_card, IRONCLAD_AOE_ATTACK_CARDS):
            # Find best target
            target = self._find_best_target(best_card, context)
            return [PlayCardAction(card=best_card, target_monster=target)]
        else:
            return [PlayCardAction(card=best_card)]

    def _beam_search_plan(self, context: DecisionContext) -> List[Action]:
        """Use beam search to find optimal action sequence with state deduplication."""
        initial_state = SimulationState(context)

        # === Timeout protection: Track start time ===
        start_time = time.time()
        timeout_budget = TIMEOUT_BUDGET  # Configurable timeout budget

        # Initialize beam with empty sequence
        beam = [([], initial_state, 0, 0)]  # (actions, state, energy_spent, score)

        best_sequence = []
        best_score = float('-inf')

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

            for sequence, state, energy_spent, _beam_score in beam:
                if getattr(state, 'combat_escaped', False):
                    continue

                # === Two-stage action expansion ===
                # Collect playable cards
                playable_actions = []
                for card in context.playable_cards:
                    card_idx = id(card)
                    if not is_card_played(state.played_card_uuids, card):
                        cost = self._card_cost_for_state(card, state)
                        if cost <= state.player_energy:
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

                        new_state = self._simulate_potion_use(
                            state,
                            potion,
                            target,
                            context=context,
                        )

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
                        if card_requires_target(card, IRONCLAD_AOE_ATTACK_CARDS) and explore_targets:
                            # Progressive target expansion: depth 0→2 targets, depth 1→1-2, depth 2+→1
                            M_targets = 2 if depth == 0 else (1 if depth >= 2 else 2)

                            # Get ranked targets
                            ranked_targets = self._rank_targets(
                                card,
                                context,
                                estimate_damage=True,
                                state=state,
                            )

                            # Prune targets
                            pruned_targets = self._prune_targets(
                                card,
                                ranked_targets,
                                context,
                                state=state,
                            )

                            if pruned_targets and len(pruned_targets) > 1:
                                # Explore multiple targets (limited by M_targets)
                                targets_to_explore = pruned_targets[:M_targets]
                                card_name = _canonical_card_name(card)
                                logger.info(f"[TARGET_EXPLORE] Depth {depth}: exploring {len(targets_to_explore)} targets for {card_name}")

                                for target, _ in targets_to_explore:
                                    # Simulate playing this card with each target
                                    new_state = self._simulate_planner_card_play(state, card, target, context=context)
                                    new_state_copy = copy.deepcopy(new_state)

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
                                target = self._find_best_target(
                                    card,
                                    context,
                                    state=state,
                                )

                                # Simulate playing this card
                                new_state = self._simulate_planner_card_play(state, card, target, context=context)

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
                            target = (
                                self._find_best_target(card, context, state=state)
                                if card_requires_target(card, IRONCLAD_AOE_ATTACK_CARDS)
                                else None
                            )

                            # Simulate playing this card
                            new_state = self._simulate_planner_card_play(state, card, target, context=context)

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

            # Deduplicate identical states within this depth.
            # Older depths must not re-enter the beam or they can crowd out
            # lower-scoring partial sequences that need another play to pay off.
            depth_states = {}
            for candidate in new_candidates:
                seq, st, energy, score = candidate
                key = st.state_key(context.playable_cards)

                if key in depth_states:
                    existing_score = depth_states[key][3]
                    if score > existing_score:
                        depth_states[key] = candidate
                else:
                    depth_states[key] = candidate

            deduplicated_candidates = list(depth_states.values())

            # Log transposition table stats
            if len(new_candidates) > len(deduplicated_candidates):
                merge_count = len(new_candidates) - len(deduplicated_candidates)
                logger.debug(f"Depth {depth}: {len(new_candidates)} candidates → {len(deduplicated_candidates)} unique (merged {merge_count} duplicates)")

            # Keep top candidates
            deduplicated_candidates.sort(key=lambda x: x[3], reverse=True)
            beam = deduplicated_candidates[:self.beam_width]

            # Track the best sequence found across all depths.
            if beam and beam[0][3] > best_score:
                best_sequence = beam[0][0]
                best_score = beam[0][3]

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
        return potion.effect_type == 'damage'

    def _is_block_potion(self, potion) -> bool:
        """Check if potion is a block potion."""
        return potion.effect_type in ['block', 'plated_armor', 'metallicize']

    def _is_escape_potion(self, potion) -> bool:
        """Check if potion immediately exits combat."""
        return potion.effect_type == 'escape'

    @staticmethod
    def _non_negative_int(value) -> int:
        return max(0, coerce_int(value or 0, 0))

    @staticmethod
    def _is_live_monster_object(monster) -> bool:
        return (
            HeuristicCombatPlanner._non_negative_int(getattr(monster, 'current_hp', 0)) > 0
            and not getattr(monster, 'is_gone', False)
            and not getattr(monster, 'half_dead', False)
        )

    @staticmethod
    def _positive_live_move_hits(monster) -> int:
        return max(1, coerce_int(getattr(monster, 'move_hits', 1) or 1, 1))

    def _get_incoming_damage(self, context: DecisionContext) -> int:
        """Calculate total incoming damage from all monsters."""
        incoming = 0
        debug_entries = []
        for monster in context.game.monsters:
            if self._is_live_monster_object(monster):
                raw_adjusted_damage = getattr(monster, 'move_adjusted_damage', None)
                adjusted_damage = (
                    None
                    if raw_adjusted_damage is None
                    else self._non_negative_int(raw_adjusted_damage)
                )
                if adjusted_damage is not None and monster_intends_attack(monster):
                    incoming += max(0, adjusted_damage) * self._positive_live_move_hits(monster)
                    debug_entries.append(
                        f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                        f"adjusted={adjusted_damage} hits={monster.move_hits}"
                    )
                elif intent_is_unknown(getattr(monster, 'intent', None)):
                    known_damage = known_unknown_move_immediate_damage(monster)
                    if known_damage > 0:
                        incoming += known_damage
                        debug_entries.append(
                            f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                            f"known_unknown_damage={known_damage}"
                        )
                        continue
                    if known_unknown_move_has_no_immediate_damage(monster):
                        debug_entries.append(
                            f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                            "known_no_damage_unknown"
                        )
                        continue
                    fallback_act = self._non_negative_int(getattr(context, 'act', 1)) or 1
                    incoming += 5 * fallback_act
                    debug_entries.append(
                        f"{monster.name}[{monster.monster_id}|move={monster.move_id}]:intent={monster.intent} "
                        f"adjusted=None fallback=act*5({5 * fallback_act})"
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
                    damage = self._non_negative_int(potion.effect_value)
                    monster_hp = self._non_negative_int(getattr(monster, 'current_hp', 0))
                    if damage >= monster_hp:
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
                total_monster_hp = sum(
                    self._non_negative_int(getattr(m, 'current_hp', 0))
                    for _i, m in alive_monsters
                )
                if total_monster_hp < 50:
                    score += 20

        # Block potions: high value when incoming damage is high
        elif self._is_block_potion(potion):
            if incoming_damage > state.player_hp * 0.4:
                score += 35  # High incoming damage

        # Escape potions: survival value without kill/lethal rewards
        elif self._is_escape_potion(potion):
            if alive_monsters:
                hp_loss_avoided = max(0, incoming_damage - state.turn_block())
                if hp_loss_avoided >= state.player_hp:
                    score += 120
                elif hp_loss_avoided > 0:
                    score += 20 + (hp_loss_avoided * 2)

        # Utility/Buff potions: baseline value in dangerous fights
        else:
            if incoming_damage > state.player_hp * 0.3:
                score += 20

        return score

    def _simulate_potion_use(
        self,
        state: SimulationState,
        potion,
        target,
        context: Optional[DecisionContext] = None,
    ) -> SimulationState:
        new_state = copy.deepcopy(state)
        self._apply_potion_effect(new_state, potion, target, context=context)
        return new_state

    def _apply_toy_ornithopter_potion_heal(self, state: SimulationState):
        if getattr(state, 'has_toy_ornithopter', False):
            state.player_hp = min(
                state.player_max_hp,
                state.player_hp + TOY_ORNITHOPTER_HEAL,
            )

    def _apply_potion_effect(
        self,
        state: SimulationState,
        potion,
        target,
        context: Optional[DecisionContext] = None,
    ):
        if potion.effect_type == 'damage':
            if potion.target_type == 'all_monsters':
                for monster in state.monsters:
                    if self.simulator._is_live_monster_state(monster):
                        self.simulator._deal_damage_to_monster(
                            state,
                            monster,
                            potion.effect_value,
                            trigger_thorns=False,
                        )
                        state.damage_instances += 1

            else:
                target_index = self._state_monster_index_for_potion_target(state, target)
                if target_index is not None:
                    monster = state.monsters[target_index]
                    if self.simulator._is_live_monster_state(monster):
                        self.simulator._deal_damage_to_monster(
                            state,
                            monster,
                            potion.effect_value,
                            trigger_thorns=False,
                        )
                        state.damage_instances += 1
        elif potion.effect_type == 'poison':
            target_index = self._state_monster_index_for_potion_target(state, target)
            if target_index is not None:
                self.simulator._apply_monster_poison(
                    state.monsters[target_index],
                    potion.effect_value,
                )
        elif potion.effect_type in ['debuff_weak', 'debuff_vulnerable']:
            target_index = self._state_monster_index_for_potion_target(state, target)
            if target_index is not None:
                debuff = 'weak' if potion.effect_type == 'debuff_weak' else 'vulnerable'
                self.simulator._apply_monster_debuff(
                    state.monsters[target_index],
                    debuff,
                    potion.effect_value,
                )
        elif potion.effect_type == 'block':
            self.simulator._add_player_block(state, potion.effect_value)
        elif potion.effect_type in ['plated_armor', 'metallicize']:
            state.end_turn_block += potion.effect_value
        elif potion.effect_type == 'heal':
            state.player_hp = min(state.player_max_hp, state.player_hp + potion.effect_value)
        elif potion.effect_type == 'regen':
            state.player_regen = getattr(state, 'player_regen', 0) + potion.effect_value
        elif potion.effect_type == 'heal_percent':
            heal_amount = int(state.player_max_hp * potion.effect_value)
            state.player_hp = min(state.player_max_hp, state.player_hp + heal_amount)
        elif potion.effect_type == 'max_hp':
            state.player_max_hp += potion.effect_value
            state.player_hp += potion.effect_value
        elif potion.effect_type == 'buff_strength':
            state.player_strength += potion.effect_value
        elif potion.effect_type == 'ritual':
            state.player_ritual = getattr(state, 'player_ritual', 0) + potion.effect_value
        elif potion.effect_type == 'temp_strength':
            state.player_strength += potion.effect_value
            if state.player_artifact > 0:
                state.player_artifact -= 1
            else:
                state.player_temp_strength += potion.effect_value
        elif potion.effect_type == 'buff_dexterity':
            state.player_dexterity += potion.effect_value
        elif potion.effect_type == 'temp_dexterity':
            state.player_dexterity += potion.effect_value
            if state.player_artifact > 0:
                state.player_artifact -= 1
            else:
                state.player_temp_dexterity += potion.effect_value
        elif potion.effect_type == 'thorns':
            state.player_thorns += potion.effect_value
        elif potion.effect_type == 'intangible':
            state.player_intangible += potion.effect_value
        elif potion.effect_type == 'artifact':
            state.player_artifact += potion.effect_value
        elif potion.effect_type == 'energy':
            state.player_energy += potion.effect_value
            state.energy_gained += potion.effect_value
        elif potion.effect_type == 'play_top_cards':
            for _ in range(self._non_negative_int(potion.effect_value)):
                self.simulator._apply_top_draw_card_by_effect(
                    state,
                    context,
                    exhaust_by_effect=False,
                )
        elif potion.effect_type in ['draw', 'draw_randomize_cost']:
            self.simulator._add_card_draw(state, potion.effect_value)
        elif potion.effect_type == 'escape':
            state.combat_escaped = True

        self._apply_toy_ornithopter_potion_heal(state)

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

        # For direct damage potions, prefer immediate lethal before threat.
        if self._is_damage_potion(potion):
            if getattr(potion, 'effect_type', None) == 'damage':
                damage = self._non_negative_int(getattr(potion, 'effect_value', 0))
                killable_targets = [
                    monster
                    for monster in context.monsters_alive
                    if damage >= self._non_negative_int(getattr(monster, 'current_hp', 0))
                ]
                if killable_targets:
                    return max(killable_targets, key=lambda m: context.compute_threat(m))
            return max(context.monsters_alive, key=lambda m: context.compute_threat(m))

        # For debuff potions, target high-HP monsters to maximize debuff value
        elif potion.effect_type.startswith('debuff_'):
            return max(
                context.monsters_alive,
                key=lambda m: self._non_negative_int(getattr(m, 'current_hp', 0)),
            )

        # Default: highest threat
        return max(context.monsters_alive, key=lambda m: context.compute_threat(m))

    @staticmethod
    def _state_monster_index_for_potion_target(state, target):
        if target:
            target_index = getattr(target, 'monster_index', None)
            if (
                isinstance(target_index, int)
                and 0 <= target_index < len(state.monsters)
            ):
                monster = state.monsters[target_index]
                if FastCombatSimulator._is_live_monster_state(monster):
                    return target_index

            target_id = getattr(target, 'monster_id', None)
            target_name = getattr(target, 'name', None)
            id_candidates = []
            name_candidates = []
            for i, monster in enumerate(state.monsters):
                if not FastCombatSimulator._is_live_monster_state(monster):
                    continue
                hp_delta = abs(
                    monster.get('hp', 0)
                    - getattr(target, 'current_hp', monster.get('hp', 0))
                )
                if target_id and monster.get('monster_id') == target_id:
                    id_candidates.append((hp_delta, i))
                elif monster.get('name') == target_name:
                    name_candidates.append((hp_delta, i))
            for candidates in (id_candidates, name_candidates):
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    return candidates[0][1]

        for i, monster in enumerate(state.monsters):
            if FastCombatSimulator._is_live_monster_state(monster):
                return i
        return None

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

        potions = game_real_potions(context.game)
        potion_actions = []

        for potion in potions:
            if not potion_can_use(potion):
                continue

            # Calculate priority score based on potion type and game state
            priority = self._score_potion(potion, context, state)

            # Determine target if needed
            target = None
            if getattr(potion, "requires_target", False):
                target = self._find_best_potion_target(potion, context)
                if target is None:
                    continue

            # Potions cost 0 energy
            potion_actions.append((potion, target, 0, priority))

        return potion_actions

    def _live_target_options(
        self,
        context: DecisionContext,
        state: Optional[SimulationState] = None,
    ) -> list:
        """Return context monsters that are still alive in the simulated state."""
        options = []
        for idx, monster in enumerate(getattr(context, 'monsters_alive', []) or []):
            simulated_monster = None
            if state is not None:
                if idx >= len(getattr(state, 'monsters', [])):
                    continue
                simulated_monster = state.monsters[idx]
                if not self.simulator._is_live_monster_state(simulated_monster):
                    continue
            options.append((idx, monster, simulated_monster))
        return options

    def _simulated_target_state(
        self,
        context: DecisionContext,
        state: Optional[SimulationState],
        target: Monster,
    ) -> Optional[dict]:
        if state is None:
            return None
        for idx, monster in enumerate(getattr(context, 'monsters_alive', []) or []):
            if monster is target and idx < len(getattr(state, 'monsters', [])):
                return state.monsters[idx]
        return None

    def _target_effective_hp(
        self,
        context: DecisionContext,
        state: Optional[SimulationState],
        target: Monster,
    ) -> int:
        simulated = self._simulated_target_state(context, state, target)
        if simulated is not None:
            return (
                self._non_negative_int(simulated.get('hp', 0))
                + self._non_negative_int(simulated.get('block', 0))
            )
        return (
            self._non_negative_int(getattr(target, 'current_hp', 0))
            + self._non_negative_int(getattr(target, 'block', 0))
        )

    def _target_current_hp(
        self,
        context: DecisionContext,
        state: Optional[SimulationState],
        target: Monster,
    ) -> int:
        simulated = self._simulated_target_state(context, state, target)
        if simulated is not None:
            return self._non_negative_int(simulated.get('hp', 0))
        return self._non_negative_int(getattr(target, 'current_hp', 0))

    def _context_player_strength(
        self,
        context: DecisionContext,
        state: Optional[SimulationState] = None,
    ) -> int:
        if state is not None and hasattr(state, 'player_strength'):
            return coerce_int(getattr(state, 'player_strength', 0) or 0, 0)
        if hasattr(context, 'strength'):
            return coerce_int(getattr(context, 'strength', 0) or 0, 0)
        player = getattr(context, 'player', None)
        if player is None:
            player = getattr(getattr(context, 'game', None), 'player', None)
        return coerce_int(getattr(player, 'strength', 0) or 0, 0)

    def _target_index(self, context: DecisionContext, target: Monster) -> Optional[int]:
        for idx, monster in enumerate(getattr(context, 'monsters_alive', []) or []):
            if monster is target:
                return idx
        return None

    def _target_indexed_stack(
        self,
        context: DecisionContext,
        target_idx: Optional[int],
        stack_attr: str,
    ) -> int:
        if target_idx is None:
            return 0
        stacks = getattr(context, stack_attr, {})
        if isinstance(stacks, dict):
            return self._non_negative_int(stacks.get(target_idx, 0))
        if isinstance(stacks, (list, tuple)) and target_idx < len(stacks):
            return self._non_negative_int(stacks[target_idx])
        return 0

    def _target_power_stack(
        self,
        target: Monster,
        power: str,
        direct_attr: str,
    ) -> int:
        direct = getattr(target, direct_attr, None)
        if direct is not None:
            return self._non_negative_int(direct)
        return self._non_negative_int(power_amount(getattr(target, 'powers', []), power, 1))

    def _fallback_target_state(
        self,
        context: DecisionContext,
        state: Optional[SimulationState],
        target: Monster,
    ) -> dict:
        simulated = self._simulated_target_state(context, state, target)
        if simulated is not None:
            return simulated

        target_idx = self._target_index(context, target)
        return {
            'hp': self._target_current_hp(context, state, target),
            'block': self._non_negative_int(getattr(target, 'block', 0)),
            'vulnerable': (
                self._target_indexed_stack(context, target_idx, 'vulnerable_stacks')
                or self._target_power_stack(target, 'Vulnerable', 'vulnerable')
            ),
            'weak': (
                self._target_indexed_stack(context, target_idx, 'weak_stacks')
                or self._target_power_stack(target, 'Weak', 'weak')
            ),
            'poison': self._target_power_stack(target, 'Poison', 'poison'),
            'slow_stacks': (
                self._target_power_stack(target, 'Slow', 'slow_stacks')
                or self._target_power_stack(target, 'SlowPower', 'slow_stacks')
            ),
        }

    def _estimate_attack_damage_without_simulation(
        self,
        card: Card,
        context: DecisionContext,
        state: Optional[SimulationState] = None,
        target: Optional[Monster] = None,
    ) -> int:
        card_name = _canonical_card_name(card)
        strength = self._context_player_strength(context, state)
        estimator_state = state or SimpleNamespace(
            player_strength=strength,
            player_block=player_block_value(context),
            player_energy=self._non_negative_int(getattr(context, 'energy_available', 0)),
            player_weak=player_debuff_stacks(context, 'Weak'),
            added_hand_cards=[],
            played_card_uuids=set(),
            rampage_damage_bonus_by_card={},
            pen_nib_counter=SimulationState._context_relic_counter(context, 'Pen Nib'),
            has_the_boot=SimulationState._context_has_the_boot(context),
        )

        dynamic_damage_card = card_name in {'Body Slam', 'Mind Blast', 'Whirlwind'}
        base_damage = self._non_negative_int(getattr(card, 'damage', 0))
        if dynamic_damage_card:
            base_damage = self.simulator._calculate_x_damage(
                card,
                estimator_state,
                context,
                per_hit=card_name == 'Whirlwind',
            )

        if base_damage == 0 and not dynamic_damage_card:
            try:
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    parsed_damage = game_data_loader._parse_card_damage(card_data)
                    if parsed_damage is not None:
                        base_damage = (
                            parsed_damage
                            + card_upgrade_helpers.known_damage_upgrade_bonus(card, card_name)
                        )
            except Exception:
                base_damage = 0

        if base_damage == 0 and not dynamic_damage_card:
            base_damage = 6

        if state is not None:
            base_damage += self.simulator._rampage_damage_bonus(state, card)

        target_state = (
            self._fallback_target_state(context, state, target)
            if target is not None
            else {}
        )
        per_hit_damage = self.simulator._calculate_attack_damage(
            card,
            base_damage,
            estimator_state,
            context,
        )
        per_hit_damage *= self.simulator._pen_nib_attack_multiplier(
            estimator_state,
            consume=False,
        )
        per_hit_damage = self.simulator._apply_player_attack_damage_modifiers(
            per_hit_damage,
            estimator_state,
            target_state,
            context,
        )
        per_hit_damage = self.simulator._apply_slow_attack_damage(per_hit_damage, target_state)
        per_hit_damage = self.simulator._apply_the_boot_minimum_attack_damage(
            estimator_state,
            per_hit_damage,
        )

        hit_count = self.simulator._get_attack_hit_count(card, estimator_state, context)
        hit_count = self.simulator._get_attack_hit_count_against_monster(
            card,
            hit_count,
            target_state,
        )
        return max(0, per_hit_damage) * max(0, hit_count)

    def _estimate_attack_damage_to_target(
        self,
        card: Card,
        context: DecisionContext,
        state: Optional[SimulationState],
        target: Monster,
        target_idx: Optional[int] = None,
    ) -> int:
        before = self._target_effective_hp(context, state, target)
        if before <= 0:
            return 0

        if target_idx is None:
            target_idx = self._target_index(context, target)

        if (
            state is not None
            and hasattr(state, 'clone')
            and target_idx is not None
            and 0 <= target_idx < len(getattr(state, 'monsters', []))
        ):
            result = self.simulator.simulate_card_play(
                state.clone(),
                card,
                target=target,
                target_index=target_idx,
                context=context,
            )
            if target_idx < len(getattr(result, 'monsters', [])):
                monster = result.monsters[target_idx]
                after = (
                    self._non_negative_int(monster.get('hp', 0))
                    + self._non_negative_int(monster.get('block', 0))
                )
                return max(0, before - after)

        return self._estimate_attack_damage_without_simulation(
            card,
            context,
            state=state,
            target=target,
        )

    def _rank_targets(
        self,
        card: Card,
        context: DecisionContext,
        estimate_damage: bool = True,
        state: Optional[SimulationState] = None,
    ) -> list:
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
        target_options = self._live_target_options(context, state)
        if not target_options:
            return []

        # Rank all monsters by threat
        ranked_targets = []
        for _idx, monster, _simulated_monster in target_options:
            threat = context.compute_threat(monster)
            ranked_targets.append((monster, threat))

        # Sort by threat descending
        ranked_targets.sort(key=lambda x: x[1], reverse=True)

        return ranked_targets

    def _prune_targets(
        self,
        card: Card,
        ranked_targets: list,
        context: DecisionContext,
        state: Optional[SimulationState] = None,
    ) -> list:
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

        monster_count = len(ranked_targets)

        # Skip pruning if too many monsters (fallback to deterministic)
        if monster_count > 4:
            logger.info(f"[TARGET_PRUNING] Skipping - {monster_count} monsters > 4")
            return []

        # Check if cleanup phase (all monsters low HP)
        all_low_hp = all(
            self._target_current_hp(context, state, monster) < 8
            for monster, _threat in ranked_targets
        )
        if all_low_hp:
            logger.info("[TARGET_PRUNING] Cleanup phase detected - using greedy lowest-HP")
            # Use greedy lowest-HP targeting
            low_hp_targets = sorted(
                [(m, threat) for m, threat in ranked_targets],
                key=lambda x: self._target_current_hp(context, state, x[0])
            )
            return low_hp_targets[:1]  # Just the lowest HP target

        is_attack = is_attack_card(card)

        if is_attack:
            # Separate killable and non-killable targets
            killable = []
            non_killable = []
            for monster, threat in ranked_targets:
                effective_hp = self._target_effective_hp(context, state, monster)
                estimated_damage = self._estimate_attack_damage_to_target(
                    card,
                    context,
                    state,
                    monster,
                )
                if estimated_damage >= effective_hp:
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
            if card_requires_target(card, IRONCLAD_AOE_ATTACK_CARDS):
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
        all_low_hp = all(
            self._non_negative_int(getattr(m, 'current_hp', 0)) < 8
            for m in context.monsters_alive
        )
        if all_low_hp:
            logger.info("[TARGET_EXPLORE] Disabled - cleanup phase (all monsters < 8 HP)")
            return False

        logger.info(f"[TARGET_EXPLORE] Enabled - {monster_count} monsters, {hand_size} cards, {elapsed_time:.1f}ms")
        return True

    def _find_best_target(
        self,
        card: Card,
        context: DecisionContext,
        state: Optional[SimulationState] = None,
    ) -> Monster:
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
        target_options = self._live_target_options(context, state)
        if not target_options:
            return None

        # Check if card is an attack
        is_attack = is_attack_card(card)

        if is_attack:
            # Find killable targets
            killable_targets = []
            for idx, monster, _simulated_monster in target_options:
                effective_hp = self._target_effective_hp(context, state, monster)
                estimated_damage = self._estimate_attack_damage_to_target(
                    card,
                    context,
                    state,
                    monster,
                    target_idx=idx,
                )
                if estimated_damage >= effective_hp:
                    killable_targets.append(monster)

            if killable_targets:
                # Target highest threat killable monster
                return max(killable_targets, key=lambda m: context.compute_threat(m))
            else:
                # No killable targets, target highest threat overall
                ranked_targets = self._rank_targets(
                    card,
                    context,
                    estimate_damage=False,
                    state=state,
                )
                return ranked_targets[0][0] if ranked_targets else None
        else:
            # For debuff/buff cards, target highest threat monster
            ranked_targets = self._rank_targets(
                card,
                context,
                estimate_damage=False,
                state=state,
            )
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
        normalized_card_type = card_type_name(card)
        card_is_attack = is_attack_card(card)
        if card_name == 'Rage':
            # Count playable attack cards in hand
            attack_cards = [c for c in context.playable_cards
                          if is_attack_card(c)]

            rage_block = 5 if is_card_upgraded(card) else 3
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
        cost = self._card_cost_for_state(card, state)
        if cost == 0:
            score += FASTSCORE_ZERO_COST_BONUS

        # Baseline power bonus to avoid pruning setup cards
        if normalized_card_type == 'POWER':
            power_bonus = FASTSCORE_POWER_BONUS
            if hasattr(context, 'turn'):
                context_turn = self._non_negative_int(context.turn) or 1
                if context_turn <= 2:
                    power_bonus += FASTSCORE_POWER_EARLY_BONUS
            score += power_bonus

        # Attack bonus when monsters alive
        monsters_alive = [
            m for m in state.monsters
            if self.simulator._is_live_monster_state(m)
        ]
        num_monsters = len(monsters_alive)
        if monsters_alive and card_is_attack:
            score += FASTSCORE_ATTACK_BONUS

        # Debuff setup bonus when attacks remain (e.g., Shockwave before attacks).
        if monsters_alive and normalized_card_type == 'SKILL':
            card_name = _canonical_card_name(card)
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = self.simulator._get_card_effect_text(card_name, card_data)
                upgraded = is_card_upgraded(card)
                effect_text = self.simulator._effect_text_for_upgrade(description, upgraded).lower()
                if 'vulnerable' in effect_text or 'weak' in effect_text:
                    attack_cards = [c for c in context.playable_cards
                                    if is_attack_card(c)]
                    if attack_cards:
                        is_aoe = 'all enemies' in effect_text
                        bonus = 6
                        if 'vulnerable' in effect_text:
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
        if hasattr(context, 'player_class'):
            player_class = str(context.player_class)
        else:
            player_class = 'IRONCLAD'

        if player_class == 'IRONCLAD':
            is_aoe = card_name in IRONCLAD_AOE_ATTACK_CARDS

        # Base damage estimate with AOE multiplier
        base_damage = 0
        if card_is_attack:
            base_damage = self._estimate_attack_damage_without_simulation(
                card,
                context,
                state=state,
            )

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
        low_hp_monsters = [
            m
            for m in context.monsters_alive
            if self._non_negative_int(getattr(m, 'current_hp', 0)) < 15
        ]
        if len(low_hp_monsters) > 0 and len(low_hp_monsters) <= len(context.playable_cards):
            confidence += 0.2  # Can probably kill

        # Energy efficiency
        energy_available = self._non_negative_int(
            getattr(context, 'energy_available', 0)
        )
        total_energy = sum(
            effective_card_cost(c, energy_available)
            for c in context.playable_cards
            if card_is_playable(c)
        )
        if total_energy <= energy_available:
            confidence += 0.1  # Can use all energy

        return min(1.0, confidence)
