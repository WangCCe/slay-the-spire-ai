"""
Fast combat simulation and action planning.

This module implements a combat simulator that can lookahead multiple actions
to find optimal play sequences using beam search.
"""

import copy
import logging
import time
from typing import List, Dict, Tuple, Optional
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action, PlayCardAction, EndTurnAction
from spirecomm.ai.decision.base import DecisionContext, CombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator

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

# Progressive widening M values (Stage 2 of two-stage expansion)
M_VALUES = [20, 18, 15, 12, 10]  # Number of actions to full-simulate at each depth
                                  # Decreases with depth: 20→18→15→12→10 (increased from 12→10→7→5→4)

# Timeout protection
TIMEOUT_BUDGET = 0.15  # Seconds (150ms budget for beam search) - increased from 80ms


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
        self.player_block = context.game.player.block if hasattr(context.game.player, 'block') else 0
        self.player_energy = context.energy_available
        self.player_strength = context.strength

        # Player debuffs (binary: >0 means debuffed)
        self.player_vulnerable = self._get_player_debuff_stacks(context, 'Vulnerable')
        self.player_weak = self._get_player_debuff_stacks(context, 'Weak')
        self.player_frail = self._get_player_debuff_stacks(context, 'Frail')

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

    def clone(self) -> 'SimulationState':
        """Create a deep copy of this state."""
        new_state = SimulationState.__new__(SimulationState)
        new_state.player_hp = self.player_hp
        new_state.player_block = self.player_block
        new_state.player_energy = self.player_energy
        new_state.player_strength = self.player_strength
        new_state.player_vulnerable = self.player_vulnerable
        new_state.player_weak = self.player_weak
        new_state.player_frail = self.player_frail
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
            self.player_frail
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

    def simulate_card_play(self, state: SimulationState, card: Card,
                          target: Optional[Monster] = None,
                          target_index: Optional[int] = None) -> SimulationState:
        """
        Simulate playing a single card with accurate damage calculation.

        This simulation accounts for:
        - Actual card costs (cost_for_turn for Snecko Eye, etc.)
        - Strength power bonus
        - Vulnerable debuff (1.5x damage)
        - Monster block
        - AOE vs single-target
        - Power effects (Demon Form, Inflame, etc.)

        Args:
            state: Current simulation state
            card: Card to play
            target: Target monster (if applicable)
            target_index: Index of target in monsters list

        Returns:
            New simulation state after playing the card
        """
        new_state = state.clone()

        # Use actual cost (for Snecko Eye and other cost modifiers)
        cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
        base_cost = card.cost if hasattr(card, 'cost') else cost

        # Track energy saved (for Corruption, etc.)
        energy_saved = base_cost - cost
        if energy_saved > 0:
            new_state.energy_saved += energy_saved

        new_state.player_energy -= cost
        new_state.energy_spent += cost

        # Apply card effects based on type
        card_type = str(card.type) if hasattr(card, 'type') else 'UNKNOWN'

        if card_type == 'ATTACK':
            new_state.attacks_played += 1
            self._apply_attack(new_state, card, target, target_index if target_index is not None else -1)
        elif card_type == 'SKILL':
            new_state.skills_played += 1
            self._apply_skill(new_state, card)
        elif card_type == 'POWER':
            self._apply_power(new_state, card)

        return new_state

    def _apply_attack(self, state: SimulationState, card: Card,
                     target: Optional[Monster], target_index: int):
        """Apply attack card effects with proper damage calculation."""
        base_damage = getattr(card, 'damage', 0)
        if base_damage == 0 or not hasattr(card, 'damage'):
            # Use game data for more accurate damage estimation
            from spirecomm.data.loader import game_data_loader
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = card_data.get('description', '').lower()
                import re
                damage_match = re.search(r'deal (\d+) damage', description)
                if damage_match:
                    base_damage = int(damage_match.group(1))
            if base_damage == 0:
                base_damage = 6  # Fallback estimate

        # Handle AOE attacks
        from spirecomm.data.loader import game_data_loader
        card_name = card.card_id.replace('+', '')
        card_data = game_data_loader.get_card_data(card_name)
        is_aoe = False
        if card_data:
            description = card_data.get('description', '').lower()
            is_aoe = 'all' in description or 'every' in description or 'each' in description
        # Also check known AOE cards by name
        if card.card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper', 'Carnage']:
            is_aoe = True

        if is_aoe:
            # AOE - apply to all monsters
            for monster in state.monsters:
                if monster['is_gone']:
                    continue
                damage = base_damage + state.player_strength
                damage = self._apply_vulnerable_damage(damage, monster)
                damage = self._apply_weak_damage(damage, monster.get('weak', 0))
                self._deal_damage_to_monster(state, monster, damage)
                state.damage_instances += 1  # Track each damage instance
        else:
            # Single-target attack
            if target_index is not None and target_index < len(state.monsters):
                monster = state.monsters[target_index]
                if not monster['is_gone']:
                    damage = base_damage + state.player_strength
                    damage = self._apply_vulnerable_damage(damage, monster)
                    damage = self._apply_weak_damage(damage, monster.get('weak', 0))
                    self._deal_damage_to_monster(state, monster, damage)
                    state.damage_instances += 1  # Track damage instance

                    # Check for card effects using game data
                    if card_data:
                        description = card_data.get('description', '').lower()
                        # Bash applies vulnerable
                        if 'vulnerable' in description:
                            vulnerable_stacks = re.search(r'vulnerable (\d+)', description)
                            if vulnerable_stacks:
                                monster['vulnerable'] += int(vulnerable_stacks.group(1))
                            else:
                                monster['vulnerable'] += 2 if card.upgrades > 0 else 1
                        # Other effects could be added here based on game data
                        elif 'weak' in description:
                            weak_stacks = re.search(r'weak (\d+)', description)
                            if weak_stacks:
                                monster['weak'] += int(weak_stacks.group(1))
                            else:
                                monster['weak'] += 1

    def _apply_vulnerable_damage(self, damage: int, monster: dict) -> int:
        """Apply vulnerable multiplier (1.5x). Binary: any vulnerable stacks = 1.5x damage."""
        if monster.get('vulnerable', 0) > 0:
            return int(damage * 1.5)
        return damage

    def _apply_weak_damage(self, damage: int, player_weak: int) -> int:
        """Apply weak multiplier (0.75x). Binary: any weak stacks = 0.75x damage."""
        if player_weak > 0:
            return int(damage * 0.75)
        return damage

    def _apply_frail_block(self, block: int, player_frail: int) -> int:
        """Apply frail multiplier (0.75x). Binary: any frail stacks = 0.75x block gained."""
        if player_frail > 0:
            return int(block * 0.75)
        return block

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

    def _apply_skill(self, state: SimulationState, card: Card):
        """Apply skill card effects."""
        # Block skills - apply frail multiplier if player has frail
        if hasattr(card, 'block') and card.block is not None:
            block_gain = card.block
            block_gain = self._apply_frail_block(block_gain, state.player_frail)
            state.player_block += block_gain

        # Track exhaust events (for Feel No Pain, etc.)
        try:
            from spirecomm.data.loader import game_data_loader
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                description = card_data.get('description', '').lower()
                # Check if card exhausts
                if 'exhaust' in description or card.card_id in ['Pommel Strike', 'Offering', 'Reaper']:
                    state.exhaust_events += 1
                # Track draw events
                if 'draw' in description:
                    import re
                    draw_match = re.search(r'draw (\d+)', description)
                    if draw_match:
                        state.cards_drawn += int(draw_match.group(1))
        except:
            pass

    def _apply_power(self, state: SimulationState, card: Card):
        """Apply power card effects."""
        card_id = card.card_id

        # Demon Form - adds strength
        if card_id == 'Demon Form':
            state.player_strength += 2 if card.upgrades > 0 else 1

        # Inflame - adds strength
        elif card_id == 'Inflame':
            state.player_strength += 2 if card.upgrades > 0 else 1

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
                from spirecomm.data.loader import game_data_loader
                card_name = card.card_id.replace('+', '')
                card_data = game_data_loader.get_card_data(card_name)
                if card_data:
                    description = card_data.get('description', '').lower()
                    import re
                    energy_match = re.search(r'gain (\d+) energy', description)
                    if energy_match:
                        state.energy_gained += int(energy_match.group(1))
            except:
                pass

        # Other powers can be added as needed

    def _estimate_incoming_damage(self, monsters_state: list) -> int:
        """
        Estimate expected incoming damage from monsters next turn.

        Args:
            monsters_state: List of monster state dictionaries

        Returns:
            Expected total damage
        """
        total_damage = 0

        for monster in monsters_state:
            if monster['is_gone']:
                continue

            intent = monster.get('intent')
            if intent is None:
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
            if 'ATTACK' in intent_str.upper() or 'ATTACK_BUFF' in intent_str.upper() or 'ATTACK_DEBUFF' in intent_str.upper() or 'ATTACK_DEFEND' in intent_str.upper():
                # Use actual monster damage data from game state
                damage = monster.get('move_adjusted_damage', 0)

                # Fallback to base_damage if adjusted_damage not available
                if damage == 0:
                    damage = monster.get('move_base_damage', 0)
                    if damage > 0:
                        logger.debug(f"[DAMAGE_FALLBACK] Monster '{monster.get('name', 'Unknown')}' using base_damage={damage}")

                # If still no damage data, use conservative estimate based on monster
                if damage == 0:
                    # Conservative estimate by monster name/type (can be improved)
                    monster_name = monster.get('name', '')
                    if 'elite' in monster_name.lower() or 'boss' in monster_name.lower():
                        damage = 15  # Elite/boss hit harder
                        logger.warning(f"[DAMAGE_FALLBACK] Monster '{monster_name}' using ELITE fallback damage={damage} (no damage data available)")
                    else:
                        damage = 8  # Normal monster
                        logger.warning(f"[DAMAGE_FALLBACK] Monster '{monster_name}' using NORMAL fallback damage={damage} (no damage data available)")

                # Adjust for monster strength
                strength = monster.get('strength', 0)
                if strength > 0:
                    logger.debug(f"[DAMAGE_FALLBACK] Monster '{monster.get('name', 'Unknown')}' has Strength {strength}, damage: {damage} → {damage + strength}")
                    damage += strength

                total_damage += damage

        if total_damage > 0:
            logger.debug(f"[INCOMING_DAMAGE] Estimated total incoming damage: {total_damage}")

        return total_damage

    def calculate_outcome_score(self, initial_state: SimulationState, final_state: SimulationState, current_act: int = 1) -> float:
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

        Returns:
            Outcome score
        """
        score = 0.0

        # 1. Monsters killed (high priority)
        initial_alive = sum(1 for m in initial_state.monsters if not m['is_gone'])
        final_alive = sum(1 for m in final_state.monsters if not m['is_gone'])
        kills = initial_alive - final_alive
        score += kills * KILL_BONUS

        # 2. Damage dealt
        total_damage = sum(m['hp'] for m in initial_state.monsters) - \
                      sum(m['hp'] for m in final_state.monsters)
        score += total_damage * DAMAGE_WEIGHT

        # 3. Block gained (defensive value)
        block_gained = final_state.player_block - initial_state.player_block
        score += block_gained * BLOCK_WEIGHT

        # 4. Energy efficiency (prefer using most energy)
        energy_used = initial_state.player_energy - final_state.player_energy
        score += energy_used * ENERGY_EFFICIENCY_WEIGHT

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
        if expected_incoming == 0 and block_gained > 0:
            # Heavy penalty: block cards are completely wasted this turn
            score -= block_gained * 10.0  # 10 points per block wasted
            logger.debug(f"[USELESS_DEFENSE_PENALTY] -{block_gained * 10.0:.1f} score for {block_gained} wasted block")

        # Death penalty (infinite score = avoid at all costs)
        if hp_loss_next_turn >= final_state.player_hp:
            return float('-inf')

        # Survival penalty (weighted heavily)
        score -= hp_loss_next_turn * W_DEATHRISK

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

        return score


class HeuristicCombatPlanner(CombatPlanner):
    """
    Combat planner using heuristic evaluation and beam search.

    This planner uses beam search to find good action sequences without
    exhaustively searching all possibilities.
    """

    def __init__(self, card_evaluator: SynergyCardEvaluator = None,
                 beam_width: int = 10, max_depth: int = 4, player_class: str = None, act: int = 1):
        """
        Initialize the combat planner.

        Args:
            card_evaluator: Card evaluator for value calculations
            beam_width: Number of candidates to keep at each depth (optional, adaptive if act provided)
            max_depth: Maximum number of cards to lookahead
            player_class: Player class for class-specific logic
            act: Current act number (1, 2, 3) for adaptive beam width
        """
        self.card_evaluator = card_evaluator or SynergyCardEvaluator()
        self.simulator = FastCombatSimulator(self.card_evaluator)

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
            if time.time() - start_time > timeout_budget:
                # Timeout! Return best sequence found (may be empty → use simple plan)
                logger.warning(f"Beam search timeout at depth {depth}! Time: {(time.time() - start_time) * 1000:.1f}ms (budget: {timeout_budget * 1000:.1f}ms)")
                break
            new_candidates = []

            for sequence, state, energy_spent in beam:
                # === Two-stage action expansion ===
                # Collect playable cards
                playable_actions = []
                for card in context.playable_cards:
                    card_idx = id(card)
                    if card_idx not in state.played_card_uuids:
                        cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
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
                    (card, card_idx, cost, self.fast_score_action(card, state, context))
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
                for action_info, card_or_potion, cost, _ in scored_actions[:M]:
                    # Check if this is a potion action
                    if isinstance(action_info, tuple) and action_info[0] == 'potion':
                        # Handle potion action
                        from spirecomm.communication.action import PotionAction
                        _, potion, target = action_info

                        # Simulate potion use (simplified simulation for now)
                        new_state = copy.deepcopy(state)
                        # Apply potion effect to state
                        if potion.effect_type == 'damage' and target:
                            # Reduce target HP
                            for i, m in enumerate(new_state.monsters):
                                if m.current_hp > 0 and (m.name == target.name or m.current_hp == target.current_hp):
                                    new_state.monsters[i] = m._replace(current_hp=max(0, m.current_hp - potion.effect_value))
                                    break
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
                        score = self.simulator.calculate_outcome_score(initial_state, new_state, current_act)
                        total_score = score - 5  # Conservation penalty

                        new_candidates.append((new_sequence, new_state, energy_spent, total_score))
                    else:
                        # Handle card action (original logic)
                        card = card_or_potion
                        card_idx = action_info  # For cards, action_info is the card_idx

                        # Determine target
                        target = self._find_best_target(card, context) if card.has_target else None

                        # Simulate playing this card
                        new_state = self.simulator.simulate_card_play(state, card, target)
                        new_state.played_card_uuids.add(card_idx)

                        # Create action
                        if target:
                            action = PlayCardAction(card=card, target_monster=target)
                        else:
                            action = PlayCardAction(card=card)

                        new_sequence = sequence + [action]

                        # Score this sequence (with current act for survival threshold)
                        current_act = context.act if hasattr(context, 'act') else 1
                        score = self.simulator.calculate_outcome_score(initial_state, new_state, current_act)

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
        for monster in context.game.monsters:
            if not monster.is_gone and not monster.half_dead:
                if monster.move_adjusted_damage is not None:
                    incoming += monster.move_adjusted_damage * monster.move_hits
                elif monster.intent == Intent.NONE:
                    incoming += 5 * context.act
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
        is_attack = hasattr(card, 'type') and str(card.type) == 'ATTACK'

        if is_attack:
            # Estimate damage for this attack
            base_damage = getattr(card, 'damage', 0)

            # Try to get damage from game data
            if base_damage == 0 or not hasattr(card, 'damage'):
                try:
                    from spirecomm.data.loader import game_data_loader
                    card_name = card.card_id.replace('+', '')
                    card_data = game_data_loader.get_card_data(card_name)
                    if card_data:
                        description = card_data.get('description', '').lower()
                        import re
                        damage_match = re.search(r'deal (\d+) damage', description)
                        if damage_match:
                            base_damage = int(damage_match.group(1))
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
                return max(context.monsters_alive, key=lambda m: context.compute_threat(m))
        else:
            # For debuff/buff cards, target highest threat monster
            return max(context.monsters_alive, key=lambda m: context.compute_threat(m))

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

        # Zero-cost bonus (Apex, Clothesline after Corruption, etc.)
        cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
        if cost == 0:
            score += FASTSCORE_ZERO_COST_BONUS

        # Attack bonus when monsters alive
        monsters_alive = [m for m in state.monsters if not m['is_gone']]
        num_monsters = len(monsters_alive)
        if monsters_alive and hasattr(card, 'type') and str(card.type) == 'ATTACK':
            score += FASTSCORE_ATTACK_BONUS

        # Block bonus at low HP
        if state.player_hp < 30 and hasattr(card, 'block') and card.block is not None:
            score += FASTSCORE_LOWHP_BLOCK_BONUS

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
                is_aoe = card.card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper', 'Carnage']

        # Base damage estimate with AOE multiplier
        base_damage = 0
        if hasattr(card, 'damage') and card.damage:
            base_damage = card.damage
        elif hasattr(card, 'type') and str(card.type) == 'ATTACK':
            # Fallback: use game data for damage
            from spirecomm.data.loader import game_data_loader
            card_name = card.card_id.replace('+', '')
            card_data = game_data_loader.get_card_data(card_name)
            if card_data:
                import re
                description = card_data.get('description', '').lower()
                damage_match = re.search(r'deal (\d+) damage', description)
                if damage_match:
                    base_damage = int(damage_match.group(1))

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
