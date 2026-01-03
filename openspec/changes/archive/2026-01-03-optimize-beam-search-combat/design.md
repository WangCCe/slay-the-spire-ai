# Design: Beam Search Combat Optimization

## Context

The OptimizedAgent uses beam search to plan combat action sequences for Ironclad at A20. The current implementation in `spirecomm/ai/heuristics/simulation.py` has three categories of issues:

1. **Game mechanic bugs** - Incorrect debuff multiplier calculations
2. **Scoring misalignment** - Optimizes for damage instead of survival
3. **Performance inefficiencies** - Redundant state exploration, lack of adaptive pruning

**Stakeholders:**
- Players seeking consistent A20 completion
- Developers maintaining the AI decision systems
- Researchers studying heuristic game AI

**Constraints:**
- Must respond within ~100ms per turn (Communication Mod timeout)
- No external dependencies (standard library only)
- Must handle complex combat scenarios (4+ monsters, 10+ cards in hand)
- Compatible with existing SimpleAgent fallback

## Goals / Non-Goals

**Goals:**
1. Fix all game mechanic simulation bugs (debuffs, block, damage)
2. Rebalance scoring from damage-first to survival-first while maintaining offensive pressure
3. Reduce beam search redundancy via transposition tables
4. Add intelligent replan triggers for dynamic game states
5. Improve action space pruning to enable deeper search within time budget

**Non-Goals:**
- Complete rewrite of combat system (incremental improvements only)
- Machine learning models (stay purely heuristic)
- Support for other characters (Ironclad-only optimization)
- Real-time UI visualization of beam search process

## Decisions

### Decision 1: Debuff Multiplier Fix

**What:** Change Vulnerable/Weak/Frail from layer-based multipliers to binary presence multipliers

**Current (incorrect):**
```python
damage *= (1 + 0.5 * vulnerable_layers)  # Wrong: 1 layer = 1.5x, 2 layers = 2.0x
```

**Fixed (correct):**
```python
if vulnerable > 0:
    damage *= 1.5  # Binary: any vulnerable = 1.5x
if weak > 0:
    attack_damage *= 0.75  # Binary: any weak = 0.75x
if frail > 0:
    block_gain *= 0.75  # Binary: any frail = 0.75x
```

**Why:**
- Slay the Spire mechanics use debuff stacks as duration counters, not intensity multipliers
- Current implementation systematically undervalues debuff cards
- Fixing this is low-risk but high-impact

**Alternatives considered:**
- Keep layer-based: Rejected as incorrect per game mechanics
- Remove debuff simulation entirely: Rejected as it loses critical information

### Decision 2: Survival-First Scoring

**What:** Add heavy penalties for expected HP loss and death risk

**Implementation:**
```python
def evaluate_sequence(self, initial_state, final_state):
    # ... existing scoring ...

    # Estimate next turn incoming damage
    expected_incoming = self._estimate_incoming_damage(final_state.monsters)
    hp_loss = max(0, expected_incoming - final_state.player_block)

    # Death penalty (infinite score = avoid at all costs)
    if hp_loss >= final_state.player_hp:
        return float('-inf')

    # Survival penalty (weighted heavily: 5-12x damage score)
    W_DEATHRISK = 8.0
    score -= hp_loss * W_DEATHRISK

    # Danger threshold penalty
    danger_threshold = 15 + (act * 5)  # Act 1: 20, Act 2: 25, Act 3: 30
    if final_state.player_hp - hp_loss < danger_threshold:
        score -= 50  # Extra penalty for dangerous low HP
```

**Why:**
- A20's "first principle" is survival over optimal damage
- Prevents reckless plays that trade HP for minor tempo gains
- Maintains offensive pressure via existing damage/killing bonuses

**Alternatives considered:**
- Keep damage-first: Rejected as inconsistent with high-level play
- Use reinforcement learning: Rejected due to complexity and training requirements

### Decision 3: Transposition Table

**What:** Deduplicate identical game states during beam search

**Implementation:**
```python
class SimulationState:
    def state_key(self):
        """Create hashable key for state deduplication."""
        player_key = (
            self.player_hp,
            self.player_block,
            self.player_energy,
            self.player_strength,
            self.vulnerable,
            self.weak,
            self.frail
        )
        monster_keys = tuple(sorted(
            (m['hp'], m['block'], m['vulnerable'], m['weak'], m['intent'])
            for m in self.monsters
        ))
        hand_key = tuple(sorted(c.card_id for c in self.hand_cards))

        return (player_key, monster_keys, hand_key)

# In beam search:
seen_states = {}
for candidate in new_candidates:
    key = candidate.state.state_key()
    if key in seen_states:
        if candidate.score > seen_states[key].score:
            seen_states[key] = candidate  # Keep best path to this state
    else:
        seen_states[key] = candidate

beam = list(seen_states.values())[:self.beam_width]
```

**Why:**
- Different action sequences can reach identical states (e.g., play A then B = play B then A)
- Deduplication increases effective beam width without computation cost
- Enables deeper search within same time budget

**Alternatives considered:**
- No deduplication: Rejected as wasteful of beam budget
- Full canonicalization: Rejected due to complexity and hash cost

### Decision 4: Replan Triggers

**What:** Detect when cached plan becomes invalid and re-run beam search

**Implementation:**
```python
class TurnPlanSignature:
    """Signature of turn state for cache validation."""
    def __init__(self, context):
        self.hand_cards = tuple(c.uuid for c in context.hand)
        self.energy = context.energy_available
        self.monster_signature = tuple(
            (m.current_hp, m.block, m.intent, m.is_gone)
            for m in context.monsters
        )
        self.has_drawn_cards = False  # Set to True if draw events occur
        self.has_random_effects = False  # Set for random targeting/shuffle

class OptimizedAgent:
    def should_replan(self, prev_signature, current_context):
        """Check if cached plan is still valid."""
        if not prev_signature:
            return True

        current_sig = TurnPlanSignature(current_context)

        # Replan if hand/energy/monsters changed unexpectedly
        if (current_sig.hand_cards != prev_signature.hand_cards or
            current_sig.energy != prev_signature.energy or
            current_sig.monster_signature != prev_signature.monster_signature):
            return True

        # Replan if random events occurred
        if current_sig.has_drawn_cards or current_sig.has_random_effects:
            return True

        return False

    def get_next_action_in_game(self, context):
        # Check if we need to replan
        if self.should_replan(self.current_plan_signature, context):
            self.current_action_sequence = self.plan_turn(context)
            self.current_action_index = 0
            self.current_plan_signature = TurnPlanSignature(context)

        # Execute current action
        if self.current_action_index < len(self.current_action_sequence):
            action = self.current_action_sequence[self.current_action_index]
            self.current_action_index += 1
            return action
        else:
            return EndTurnAction()
```

**Why:**
- Card draws (Pommel Strike, Battle Trance, Offering) invalidate previous optimal sequence
- Monster deaths change target priorities dramatically
- Energy changes (Bloodletting, potions) create new action possibilities
- Prevents executing obviously suboptimal cached plans

**Alternatives considered:**
- Never replan: Rejected as misses opportunities from draws/deaths
- Replan every action: Rejected as too slow (beam search is expensive)

### Decision 5: Two-Stage Action Expansion

**What:** Filter low-value actions before expensive simulation

**Implementation:**
```python
def fast_score_action(self, action, state):
    """Lightweight scoring without full simulation."""
    score = 0

    if isinstance(action, PlayCardAction):
        card = action.card

        # Prefer zero-cost
        if card.cost_for_turn == 0:
            score += 20

        # Prefer attacks when monsters alive
        if card.type == 'ATTACK':
            score += 10

        # Prefer block when low HP
        if card.type == 'SKILL' and hasattr(card, 'block'):
            if state.player_hp < 30:
                score += 15

        # Simple damage estimate
        if hasattr(card, 'damage'):
            score += card.damage * 2

    return score

def beam_search(self, context):
    # Progressive widening parameters
    M_values = [12, 10, 7, 5, 4]  # Depth 0-4

    for depth in range(self.max_depth):
        candidates = []

        for sequence, state in beam:
            # Get all playable actions
            actions = self.get_playable_actions(state)

            # Stage 1: Fast score filter
            scored_actions = [(a, fast_score_action(a, state)) for a in actions]
            scored_actions.sort(key=lambda x: x[1], reverse=True)

            # Stage 2: Full simulation for top M only
            M = M_values[min(depth, len(M_values)-1)]
            for action, _ in scored_actions[:M]:
                new_state = self.simulator.simulate(action, state)
                full_score = self.evaluate_sequence(initial_state, new_state)
                candidates.append((sequence + [action], new_state, full_score))

        # Keep top beam_width
        candidates.sort(key=lambda x: x[2], reverse=True)
        beam = candidates[:self.beam_width]
```

**Why:**
- Reduces simulation count from O(actions^depth) to O(M^depth) where M << actions
- Enables deeper search (5+ cards) within time budget
- Progressive widening accounts for decreasing quality of deeper sequences

**Alternatives considered:**
- Expand all actions: Rejected as causes exponential explosion with large hands
- Fixed action limit per depth: Rejected as less adaptive than progressive widening

### Decision 6: Threat-Based Targeting

**What:** Prioritize targets by threat level, not just lowest HP

**Implementation:**
```python
def compute_threat(self, monster, state):
    """Calculate threat level of a monster."""
    threat = 0

    # Expected damage next turn (from intent)
    if monster.intent == Intent.ATTACK:
        threat += monster.get_expected_damage()

    # Debuff threat (applies Weak/Vulnerable)
    if monster.intent in [Intent.DEBUFF, Intent.DEBUFF_WEAK, Intent.DEBUFF_VULNERABLE]:
        threat += 10  # Weak/Vulnerable significantly reduces survival

    # Scaling threat (grows stronger over time)
    if monster.name in ['Gremlin Nob', 'The Guardian', 'Hexaghost']:
        threat += 15  # Elite/boss scaling threat

    # AOE threat (affects all monsters)
    if monster.intent == Intent.ATTACK_BUFF:
        threat += 8  # Buffs other monsters

    return threat

def find_best_target(self, card, context):
    """Select target maximizing threat reduction + kill value."""
    if not context.monsters_alive:
        return None

    # Calculate killable monsters
    killable = []
    for monster in context.monsters_alive:
        damage = self._estimate_damage(card, monster)
        if damage >= monster.current_hp + monster.block:
            killable.append(monster)

    # If we can kill something, prioritize by threat
    if killable:
        return max(killable, key=lambda m: self.compute_threat(m, context))

    # Otherwise, target highest threat
    return max(context.monsters_alive, key=lambda m: self.compute_threat(m, context))
```

**Why:**
- "Kill lowest HP" fails when high-threat enemies have moderate HP
- Reducing incoming damage is more valuable than damaging tanky elites
- Aligns with survival-first scoring philosophy

**Alternatives considered:**
- Keep lowest-HP targeting: Rejected as ignores threat diversity
- Random targeting: Rejected as obviously suboptimal

## Risks / Trade-offs

### Risk 1: Increased Decision Latency

**Risk:** Transposition table hashing and two-stage expansion may increase per-turn compute time

**Mitigation:**
- Profile with test_combat_system.py before and after changes
- Implement timeout budget (80ms max) and fallback to cached plan
- Reduce beam_width or max_depth if timeout exceeded

### Risk 2: Over-Conservative Play

**Risk:** Heavy survival penalties may cause excessively defensive plays (wasting energy on unnecessary block)

**Mitigation:**
- Tune W_DEATHRISK weight via playtesting (target: 5-12 range)
- Keep damage/killing bonuses to maintain offensive pressure
- Monitor average energy waste in logs

### Risk 3: Replan Trigger False Positives

**Risk:** Too-sensitive replan triggers cause frequent replanning, defeating caching purpose

**Mitigation:**
- Use strict equality for hand/energy/monsters (no approximate comparisons)
- Only set has_drawn_cards/has_random_effects flags when actual events occur
- Track replan frequency in logs (target: <2 replans per turn average)

### Risk 4: State Key Collisions

**Risk:** Simplified state_key may treat distinct states as identical

**Mitigation:**
- Include all game-relevant fields in key (HP, block, debuffs, intent)
- Use tuple (not frozenset) to preserve monster identity
- Add unit tests for state_key uniqueness

## Migration Plan

**Phase 1 (Critical Fixes):**
1. Fix debuff multipliers in simulation.py
2. Add survival scoring to evaluate_sequence
3. Add unit tests for debuff calculations
4. Verify with test_combat_system.py
5. Deploy and monitor A20 win rate

**Phase 2 (Performance):**
1. Add state_key() method to SimulationState
2. Implement transposition table in beam_search
3. Profile decision time, tune beam_width
4. Add timeout protection
5. Deploy and monitor decision latency

**Phase 3 (Adaptive Planning):**
1. Implement TurnPlanSignature class
2. Add should_replan() to OptimizedAgent
3. Integrate with action execution loop
4. Monitor replan frequency in logs
5. Deploy and verify timing

**Phase 4 (Targeting Quality):**
1. Implement compute_threat() in decision/base.py
2. Update find_best_target() to use threat
3. Add two-stage action expansion
4. Tune M_values via playtesting
5. Final deployment and validation

**Rollback:**
- Each phase is independently deployable
- Previous phases remain stable if later phases have issues
- SimpleAgent unaffected by all changes (fallback available)

## Open Questions

1. **What should the exact survival penalty weight be?**
   - Recommendation: Start with W_DEATHRISK=8.0, tune based on playtesting
   - Metric: Target ~15-25 HP loss per act (not <5, not >40)

2. **Should beam width increase with act difficulty?**
   - Recommendation: Act 1: 12, Act 2: 18, Act 3: 25 (with transposition)
   - Justification: Later acts have more complex combats

3. **How to handle random effects in simulation (e.g., Ragnaros)?**
   - Recommendation: Assume average outcome (damage to random enemy = damage to lowest-HP)
   - Alternative: Branch simulation for each possible outcome (too expensive)

4. **Should we cache transposition table across turns?**
   - Recommendation: No (state changes too much between turns)
   - Justification: Monster intents change, player draws new cards, relics trigger

5. **How to measure "success" for each phase?**
   - Metrics: A20 win rate, average HP loss per combat, decision time (p50, p99)
   - Baseline: Current OptimizedAgent performance
   - Target: +10-15% win rate, -5-10 HP loss per combat, <100ms p99 decision time
