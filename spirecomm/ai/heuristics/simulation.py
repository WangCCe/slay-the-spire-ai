"""
Fast combat simulation and action planning.

This module implements a combat simulator that can lookahead multiple actions
to find optimal play sequences using beam search.
"""

import copy
from typing import List, Dict, Tuple, Optional
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action, PlayCardAction, EndTurnAction
from spirecomm.ai.decision.base import DecisionContext, CombatPlanner
from spirecomm.ai.heuristics.card import SynergyCardEvaluator


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
        return new_state


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
        new_state.player_energy -= cost
        new_state.energy_spent += cost

        # Apply card effects based on type
        card_type = str(card.type) if hasattr(card, 'type') else 'UNKNOWN'

        if card_type == 'ATTACK':
            self._apply_attack(new_state, card, target, target_index if target_index is not None else -1)
        elif card_type == 'SKILL':
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
        else:
            # Single-target attack
            if target_index is not None and target_index < len(state.monsters):
                monster = state.monsters[target_index]
                if not monster['is_gone']:
                    damage = base_damage + state.player_strength
                    damage = self._apply_vulnerable_damage(damage, monster)
                    damage = self._apply_weak_damage(damage, monster.get('weak', 0))
                    self._deal_damage_to_monster(state, monster, damage)

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

        # Draw cards - simplified (we don't simulate actual draws)
        # Just account for the potential value in scoring
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

                # If still no damage data, use conservative estimate based on monster
                if damage == 0:
                    # Conservative estimate by monster name/type (can be improved)
                    monster_name = monster.get('name', '')
                    if 'elite' in monster_name.lower() or 'boss' in monster_name.lower():
                        damage = 15  # Elite/boss hit harder
                    else:
                        damage = 8  # Normal monster

                # Adjust for monster strength
                damage += monster.get('strength', 0)

                total_damage += damage

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
        score += kills * 100  # Big bonus for kills

        # 2. Damage dealt
        total_damage = sum(m['hp'] for m in initial_state.monsters) - \
                      sum(m['hp'] for m in final_state.monsters)
        score += total_damage * 2

        # 3. Block gained (defensive value)
        block_gained = final_state.player_block - initial_state.player_block
        score += block_gained * 1.5

        # 4. Energy efficiency (prefer using most energy)
        energy_used = initial_state.player_energy - final_state.player_energy
        score += energy_used * 3

        # 5. HP preserved (very important)
        hp_lost = initial_state.player_hp - final_state.player_hp
        score -= hp_lost * 10  # Penalty for taking damage

        # 6. Survival-first scoring (estimate next turn incoming damage)
        expected_incoming = self._estimate_incoming_damage(final_state.monsters)
        hp_loss_next_turn = max(0, expected_incoming - final_state.player_block)

        # Death penalty (infinite score = avoid at all costs)
        if hp_loss_next_turn >= final_state.player_hp:
            return float('-inf')

        # Survival penalty (weighted heavily: W_DEATHRISK = 8.0)
        W_DEATHRISK = 8.0
        score -= hp_loss_next_turn * W_DEATHRISK

        # Danger threshold penalty (act-dependent)
        danger_threshold = 15 + (current_act * 5)  # Act 1: 20, Act 2: 25, Act 3: 30
        if final_state.player_hp - hp_loss_next_turn < danger_threshold:
            score -= 50  # Extra penalty for dangerous low HP

        return score


class HeuristicCombatPlanner(CombatPlanner):
    """
    Combat planner using heuristic evaluation and beam search.

    This planner uses beam search to find good action sequences without
    exhaustively searching all possibilities.
    """

    def __init__(self, card_evaluator: SynergyCardEvaluator = None,
                 beam_width: int = 10, max_depth: int = 4, player_class: str = None):
        """
        Initialize the combat planner.

        Args:
            card_evaluator: Card evaluator for value calculations
            beam_width: Number of candidates to keep at each depth
            max_depth: Maximum number of cards to lookahead
            player_class: Player class for class-specific logic
        """
        self.card_evaluator = card_evaluator or SynergyCardEvaluator()
        self.simulator = FastCombatSimulator(self.card_evaluator)
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.player_class = player_class

    def plan_turn(self, context: DecisionContext) -> List[Action]:
        """
        Plan optimal action sequence for this turn.

        Uses beam search to find good sequences efficiently.

        Args:
            context: Current decision context

        Returns:
            List of actions to execute (may be empty)
        """
        if not context.playable_cards:
            return []  # No playable cards, end turn

        # If only 1-2 cards, simple evaluation is sufficient
        if len(context.playable_cards) <= 2:
            return self._simple_plan(context)

        # Use beam search for complex situations
        return self._beam_search_plan(context)

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
        """Use beam search to find optimal action sequence."""
        initial_state = SimulationState(context)

        # Initialize beam with empty sequence
        beam = [([], initial_state, 0)]  # (actions, state, energy_spent)

        best_sequence = []
        best_score = float('-inf')

        for depth in range(self.max_depth):
            new_candidates = []

            for sequence, state, energy_spent in beam:
                # Try each remaining playable card
                for card in context.playable_cards:
                    card_idx = id(card)  # Use id to track played cards

                    if card_idx not in state.played_card_uuids:
                        cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost

                        # Check if we have enough energy
                        if energy_spent + cost <= context.energy_available:
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

            # Keep top candidates
            new_candidates.sort(key=lambda x: x[3], reverse=True)
            beam = new_candidates[:self.beam_width]

            # Track best sequence
            if beam:
                best_sequence, best_state, best_energy, best_score = beam[0]

        return best_sequence if best_sequence else self._simple_plan(context)

    def _find_best_target(self, card: Card, context: DecisionContext) -> Monster:
        """
        Find the best target for a card.

        Strategy:
        - Attack cards: lowest HP (for kills)
        - Debuff cards: highest HP (maximize duration)
        - Defensive buffs: highest HP (tank protection)

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
            # Target lowest HP monster
            return min(context.monsters_alive, key=lambda m: m.current_hp)
        else:
            # Target highest HP monster for debuffs/buffs
            return max(context.monsters_alive, key=lambda m: m.current_hp)

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
