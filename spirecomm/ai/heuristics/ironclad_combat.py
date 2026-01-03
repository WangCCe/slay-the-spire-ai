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
from typing import List, Tuple, Optional
from .simulation import CombatPlanner, SimulationState, FastCombatSimulator
from .combat_ending import CombatEndingDetector
from .monster_database import evaluate_monster_threat, get_monster_info
from ..decision.base import DecisionContext
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action, PlayCardAction
from spirecomm.ai.heuristics.card import SynergyCardEvaluator

logger = logging.getLogger(__name__)


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
        import sys
        playable_cards = context.playable_cards

        if not playable_cards:
            return []

        # Log turn start
        logger.info(f"[COMBAT] Turn {context.turn}, Floor {context.floor}, Act {context.act}")
        logger.info(f"[COMBAT] Playable cards: {len(playable_cards)}, Energy: {context.energy_available}")
        # Log card IDs for debugging
        card_ids = [card.card_id for card in playable_cards]
        logger.info(f"[COMBAT] Cards in hand: {', '.join(card_ids)}")
        logger.info(f"[COMBAT] Monsters: {len(context.monsters_alive)}, HP: {context.player_hp_pct:.1%}")

        # Log monster intents for debugging over-defense issues
        for i, monster in enumerate(context.monsters_alive):
            intent_str = str(monster.intent) if hasattr(monster, 'intent') else 'UNKNOWN'
            logger.info(f"[COMBAT] Monster {i+1}: {monster.name}, Intent: {intent_str}, HP: {monster.current_hp}/{monster.max_hp}")

        # Step 1: Check for lethal (can we kill all monsters this turn?)
        if self.combat_ending_detector.can_kill_all(context):
            logger.info("[COMBAT] Lethal detected!")
            lethal_sequence = self.combat_ending_detector.find_lethal_sequence(context)
            if lethal_sequence:
                logger.info(f"[COMBAT] Lethal sequence: {len(lethal_sequence)} cards")
                return lethal_sequence

        # Step 2: Determine adaptive parameters based on complexity
        beam_width, max_depth = self._get_adaptive_parameters(context, playable_cards)
        logger.info(f"[COMBAT] Beam search: width={beam_width}, depth={max_depth}")

        # Step 3: Use beam search to find optimal sequence
        sequence = self._beam_search_turn(context, playable_cards, beam_width, max_depth)
        logger.info(f"[COMBAT] Best sequence: {len(sequence)} cards")
        # Log card IDs in best sequence for debugging
        if sequence:
            seq_card_ids = []
            for action in sequence:
                if hasattr(action, 'card') and action.card:
                    seq_card_ids.append(action.card.card_id)
            logger.info(f"[COMBAT] Sequence cards: {', '.join(seq_card_ids)}")
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
        best_score = float('-inf')

        for depth in range(max_depth):
            new_candidates = []

            for sequence, state, energy_spent, score in beam:
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

                    # === NEW: Set primary target on first attack ===
                    # If this is the first attack (no primary target yet), set it
                    if state.primary_target is None and target_idx is not None:
                        # Check if this is an attack card (not AOE)
                        is_attack = hasattr(card, 'type') and str(card.type) == 'ATTACK'
                        is_single_target = target_idx is not None and card.card_id not in ['Cleave', 'Whirlwind', 'Immolate', 'Thunderclap', 'Reaper']
                        if is_attack and is_single_target:
                            new_state.primary_target = target_idx

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
        """
        Choose best target for card given current simulation state.

        Implements focused fire: prioritizes primary_target to concentrate damage
        and kill monsters faster, reducing total damage taken.
        """
        if not state.monsters:
            return None, None

        card_id = card.card_id
        alive_monsters = [(i, m) for i, m in enumerate(state.monsters) if not m['is_gone']]
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
            if primary_idx < len(state.monsters) and not state.monsters[primary_idx]['is_gone']:
                # Primary target still alive - focus fire on it
                if primary_idx < len(context.monsters_alive):
                    return context.monsters_alive[primary_idx], primary_idx
            else:
                # Primary target is dead - clear it
                state.primary_target = None

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
        if hasattr(card, 'type') and str(card.type) == 'ATTACK':
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

        # Special handling for monsters that require quick kills
        cultist_ritual = self._is_cultist_ritual_turn(context)
        has_cultist = self._has_cultist(context)
        has_gremlin_nob = self._has_gremlin_nob(context)
        lagavulin_hibernating = self._is_lagavulin_hibernating(context)
        has_lagavulin = self._has_lagavulin(context)
        
        # Determine if we should prioritize attack over defense
        # These monsters have scaling damage or dangerous mechanics
        if cultist_ritual:
            # Cultist is gaining Strength, will attack next turn with more damage
            damage_weight = 5.0
            block_penalty = True
        elif lagavulin_hibernating:
            # Lagavulin is hibernating, will deal massive damage when it wakes up
            damage_weight = 5.0
            block_penalty = True
        elif has_gremlin_nob or has_lagavulin or has_cultist:
            # These monsters have scaling damage or dangerous mechanics
            # Defense is not sustainable - always prioritize attacking
            damage_weight = 4.0
            block_penalty = True
        else:
            damage_weight = 3.0
            block_penalty = False

        # 1. Monsters killed (huge bonus)
        kills = final_state.monsters_killed
        score += kills * 200

        # 2. Damage dealt
        damage = final_state.total_damage_dealt
        score += damage * damage_weight

        # 3. Block (only valuable when taking damage, but less valuable than attacking)
        # Defense is temporary (blocks 1 turn), while killing monsters is permanent
        block_gained = final_state.player_block - initial_state.player_block
        incoming_damage = context.incoming_damage

        if block_penalty and block_gained > 0:
            # Heavily penalize block against monsters with scaling/dangerous mechanics
            # This prevents the AI from prolonging the battle
            score -= block_gained * 10
        elif incoming_damage > initial_state.player_block:
            # Need block - value it, but less than damage
            # Defense is temporary (blocks 1 turn), attack is permanent (kills monsters)
            score += min(block_gained, incoming_damage) * 2  # Reduced from 5 to 2
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
                        c.card_id not in ['Bash', 'Strike_R', 'Defend_R']
                        and hasattr(c, 'damage') and c.damage > 10
                        for c in context.playable_cards
                        if c.uuid != card.uuid
                    )
                    if big_attack_pending:
                        score += 25

                # Hybrid cards (block + damage) - special handling
                if card_id in ['Iron Wave', 'Flame Barrier']:
                    # Value both the block and damage aspects
                    if hasattr(card, 'block') and card.block > 0:
                        score += card.block * 3  # Value block
                    if hasattr(card, 'damage') and card.damage > 0:
                        score += card.damage * 1.5  # Value damage
                    # Bonus for hybrid nature
                    score += 15
                
                # High priority cards that need special handling
                elif card_id == 'Immolate':
                    # Immolate: high damage + card draw, despite self-damage
                    if hasattr(card, 'damage') and card.damage > 0:
                        score += card.damage * 2.0  # Value damage highly
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
                    if hasattr(card, 'damage') and card.damage > 0:
                        score += card.damage * monster_count * 0.5  # Value per target
                
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
                    has_high_damage = any(c.card_id in ['Perfected Strike', 'Heavy Blade', 'Body Slam']
                                       for c in context.playable_cards)
                    if has_high_damage:
                        score += 20

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
        card_id = card.card_id
        
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
                if context.incoming_damage > context.game.current_hp * 0.8:
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
                    from spirecomm.spire.character import Intent
                    if monster.intent != Intent.ATTACK and monster.intent != Intent.ATTACK_BUFF:
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
        return any(monster.monster_id == "Gremlin Nob" for monster in context.monsters_alive)

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
                    from spirecomm.spire.character import Intent
                    if monster.intent == Intent.DEFEND:
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
