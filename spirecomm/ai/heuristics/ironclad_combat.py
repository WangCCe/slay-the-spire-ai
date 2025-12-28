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

import sys
from typing import List, Tuple, Optional
from .simulation import CombatPlanner, SimulationState, FastCombatSimulator
from .combat_ending import CombatEndingDetector
from ..decision.base import DecisionContext
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action, PlayCardAction
from spirecomm.ai.heuristics.card import SynergyCardEvaluator


class IroncladCombatPlanner(CombatPlanner):
    """
    Ironclad-specific combat planner with beam search and expert strategies.

    Key features:
    1. Combat ending detection - don't over-defend when lethal is possible
    2. Beam search - find optimal card sequences, not greedy single-card plays
    3. Smart targeting - Bash high HP, kill low HP, AOE optimization
    4. Ironclad-specific logic - Demon Form timing, Limit Break threshold, etc.
    """

    def __init__(self, card_evaluator=None, beam_width=10, max_depth=5):
        """
        Initialize Ironclad combat planner.

        Args:
            card_evaluator: Card evaluator for fallback
            beam_width: Number of candidates to keep in beam search
            max_depth: Maximum depth for beam search
        """
        self.card_evaluator = card_evaluator or SynergyCardEvaluator()
        self.simulator = FastCombatSimulator(self.card_evaluator)
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.combat_ending_detector = CombatEndingDetector()

    def plan_turn(self, context: DecisionContext) -> List[Action]:
        """
        Plan optimal turn using Ironclad-specific strategies.

        Returns:
            List of actions to execute in order
        """
        playable_cards = context.playable_cards

        if not playable_cards:
            return []

        # Step 1: Check for lethal (can we kill all monsters this turn?)
        if self.combat_ending_detector.can_kill_all(context):
            lethal_sequence = self.combat_ending_detector.find_lethal_sequence(context)
            if lethal_sequence:
                return lethal_sequence

        # Step 2: Determine adaptive parameters based on complexity
        beam_width, max_depth = self._get_adaptive_parameters(context, playable_cards)

        # Step 3: Use beam search to find optimal sequence
        return self._beam_search_turn(context, playable_cards, beam_width, max_depth)

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

        # Simple局面 (1-3 cards, 1-2 monsters)
        if num_playable <= 3 and num_monsters <= 2:
            return 8, 3

        # Medium局面 (4-6 cards, 2-3 monsters)
        elif num_playable <= 6 and num_monsters <= 3:
            return 12, 4

        # Complex局面 (7+ cards or 4+ monsters) - deeper search
        else:
            return 15, 5

    def _beam_search_turn(self, context: DecisionContext,
                         playable_cards: List[Card],
                         beam_width: int, max_depth: int) -> List[Action]:
        """Use beam search to find best action sequence."""
        initial_state = SimulationState(context)

        # Initialize beam with empty sequence
        beam = [([], initial_state, 0)]  # (actions, state, energy_spent)

        best_sequence = []
        best_score = float('-inf')

        for depth in range(max_depth):
            new_candidates = []

            for sequence, state, energy_spent in beam:
                # Try each remaining card
                for card in playable_cards:
                    card_uuid = card.uuid if hasattr(card, 'uuid') else id(card)

                    if card_uuid in state.played_card_uuids:
                        continue

                    # Check energy
                    cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
                    if energy_spent + cost > context.energy_available:
                        continue

                    # Select target
                    target, target_idx = self._choose_target_for_card(card, context, state)

                    # Simulate
                    new_state = self.simulator.simulate_card_play(
                        state, card, target, target_idx
                    )
                    new_state.played_card_uuids.add(card_uuid)

                    # Create action
                    if target:
                        action = PlayCardAction(card=card, target_monster=target)
                    else:
                        action = PlayCardAction(card=card)

                    new_sequence = sequence + [action]

                    # Score
                    score = self._score_sequence(new_sequence, initial_state, new_state, context)

                    new_candidates.append((new_sequence, new_state, energy_spent + cost, score))

            if not new_candidates:
                break

            # Keep top candidates
            new_candidates.sort(key=lambda x: x[3], reverse=True)
            beam = new_candidates[:beam_width]

            if beam:
                best_sequence, best_state, best_energy, best_score = beam[0]

        return best_sequence if best_sequence else self._fallback_plan(context, playable_cards)

    def _choose_target_for_card(self, card: Card, context: DecisionContext,
                                state: SimulationState) -> Tuple[Optional[Monster], Optional[int]]:
        """Choose best target for card given current simulation state."""
        if not state.monsters:
            return None, None

        card_id = card.card_id

        # AOE cards - no targeting needed
        if card_id in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap']:
            return None, None

        # Bash - highest HP (maximize vulnerable duration)
        if card_id == 'Bash':
            highest_hp_idx = max(enumerate(state.monsters),
                               key=lambda x: x[1]['hp'] if not x[1]['is_gone'] else 0)
            # Return actual monster object for action creation
            if highest_hp_idx[0] < len(context.monsters_alive):
                return context.monsters_alive[highest_hp_idx[0]], highest_hp_idx[0]

        # Body Slam - lowest HP (finish off weakened enemies)
        if card_id == 'Body Slam':
            lowest_hp_idx = min(enumerate(state.monsters),
                              key=lambda x: x[1]['hp'] if not x[1]['is_gone'] else 999)
            if lowest_hp_idx[0] < len(context.monsters_alive):
                return context.monsters_alive[lowest_hp_idx[0]], lowest_hp_idx[0]

        # Standard attacks - lowest HP target that's not already vulnerable
        if hasattr(card, 'type') and str(card.type) == 'ATTACK':
            # Prefer non-vulnerable targets if damage is similar
            non_vulnerable = [(i, m) for i, m in enumerate(state.monsters)
                            if not m['is_gone'] and m.get('vulnerable', 0) == 0]
            if non_vulnerable:
                lowest_idx = min(non_vulnerable, key=lambda x: x[1]['hp'])
                if lowest_idx[0] < len(context.monsters_alive):
                    return context.monsters_alive[lowest_idx[0]], lowest_idx[0]

            # Otherwise lowest HP
            lowest_hp_idx = min(enumerate(state.monsters),
                              key=lambda x: x[1]['hp'] if not x[1]['is_gone'] else 999)
            if lowest_hp_idx[0] < len(context.monsters_alive):
                return context.monsters_alive[lowest_hp_idx[0]], lowest_hp_idx[0]

        # Default - first alive monster
        for i, m in enumerate(state.monsters):
            if not m['is_gone']:
                if i < len(context.monsters_alive):
                    return context.monsters_alive[i], i

        return None, None

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
        """
        score = 0.0

        # 1. Monsters killed (huge bonus)
        kills = final_state.monsters_killed
        score += kills * 200

        # 2. Damage dealt
        damage = final_state.total_damage_dealt
        score += damage * 3

        # 3. Block (only valuable when taking damage)
        block_gained = final_state.player_block - initial_state.player_block
        incoming_damage = context.incoming_damage

        if incoming_damage > initial_state.player_block:
            # Need block - value it highly
            score += min(block_gained, incoming_damage) * 5
        else:
            # Already safe - minimal value
            score += block_gained * 0.5

        # 4. Energy efficiency
        energy_used = final_state.energy_spent
        score += energy_used * 2

        # 5. Strategic bonus for card types
        for action in sequence:
            if isinstance(action, PlayCardAction):
                card = action.card
                card_id = card.card_id

                # Powers are valuable early
                if card_id == 'Demon Form' and context.turn <= 3:
                    score += 50

                # Draw cards help consistency
                if self._is_draw_card(card):
                    score += 15

                # Limit Break with high strength
                if card_id == 'Limit Break' and context.strength >= 5:
                    score += 40

                # Bash before big attacks
                if card_id == 'Bash':
                    # Check if we have big attacks remaining
                    big_attack_pending = any(
                        c.card_id not in ['Bash', 'Strike_R', 'Defend_R']
                        and hasattr(c, 'damage') and c.damage > 10
                        for c in context.playable_cards
                        if c.uuid != card.uuid
                    )
                    if big_attack_pending:
                        score += 25

        return score

    def _is_draw_card(self, card: Card) -> bool:
        """Check if card draws cards."""
        draw_keywords = ['draw', 'pommel strike', 'shrug it off', 'battle trance']
        card_lower = card.card_id.lower()
        return any(kw in card_lower for kw in draw_keywords)

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
            if best_card.has_target and context.monsters_alive:
                target, _ = self._choose_target_for_card(best_card, context, SimulationState(context))
                return [PlayCardAction(card=best_card, target_monster=target)]
            else:
                return [PlayCardAction(card=best_card)]

        return []

    def _get_card_priority(self, card: Card, context: DecisionContext) -> float:
        """Get priority score for a card (simplified version of existing logic)."""
        card_type = str(card.type) if hasattr(card, 'type') else 'UNKNOWN'

        # Powers first
        if card_type == 'POWER':
            if card.card_id == 'Demon Form' and context.turn <= 3:
                return 1000
            return 600 if context.turn <= 3 else 400

        # Draw cards
        if self._is_draw_card(card):
            return 800

        # Bash before attacks
        if card.card_id == 'Bash':
            return 850 if self._should_bash_now(context) else 100

        # Attacks
        if card_type == 'ATTACK':
            if card.card_id == 'Reaper' and len(context.monsters_alive) >= 2:
                return 900 if context.strength >= 5 else 700
            if card.card_id == 'Body Slam' and context.game.player.block >= 20:
                return 950
            return 700

        # Defense (only if needed)
        if self._is_defensive_card(card):
            return 700 if context.incoming_damage > context.game.player.block else 200

        return 400

    def _should_bash_now(self, context: DecisionContext) -> bool:
        """Check if Bash should be played now."""
        # Bash is good if we have big attacks to follow up
        big_attacks = [
            c for c in context.playable_cards
            if c.card_id != 'Bash' and hasattr(c, 'type') and str(c.type) == 'ATTACK'
            and hasattr(c, 'damage') and c.damage > 10
        ]
        return len(big_attacks) > 0

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is defensive."""
        if hasattr(card, 'block') and card.block:
            return True
        defensive_keywords = ['defend', 'iron wave', 'flame barrier']
        card_lower = card.card_id.lower()
        return any(kw in card_lower for kw in defensive_keywords)

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
