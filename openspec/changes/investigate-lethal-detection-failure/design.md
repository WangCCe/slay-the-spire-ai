# Design: Lethal Detection Fix

## Architecture Overview

The current combat decision flow for Ironclad is:

```
1. IroncladCombatPlanner.plan_turn()
   ↓
2. CombatEndingDetector.can_kill_all()  # ← LETHAL CHECK
   ↓ (if true)
3. CombatEndingDetector.find_lethal_sequence()  # ← SEQUENCE CONSTRUCTION
   ↓ (if sequence found)
4. Return lethal sequence (skip beam search)
   ↓ (if no lethal)
5. Beam search planning (HeuristicCombatPlanner)
```

**Problem**: This flow has three potential failure points:
1. **Detection failure**: `can_kill_all()` returns false when lethal is actually possible
2. **Construction failure**: `find_lethal_sequence()` returns empty/invalid sequence
3. **Scoring failure**: Beam search doesn't prioritize kill sequences enough

## Component Analysis

### 1. CombatEndingDetector.can_kill_all()

**Current Implementation** (combat_ending.py:30-51):
```python
def can_kill_all(self, context: DecisionContext) -> bool:
    total_possible_damage = self._calculate_max_damage(context)
    total_monster_hp = sum(m.current_hp + m.block for m in context.monsters_alive)
    return total_possible_damage >= total_monster_hp * 1.2  # 20% margin
```

**Issues**:
1. **20% margin is too conservative**: If monsters have 100 HP and we can deal 110 damage, lethal is possible but detection returns False (110 < 120)
2. **No energy validation**: Doesn't check if we can actually afford to play all damage cards
3. **No targeting validation**: Assumes all damage can be focused optimally (fails for single-target attacks vs multiple monsters)

**Proposed Fix**:
```python
def can_kill_all(self, context: DecisionContext) -> bool:
    # Step 1: Calculate max damage (respecting energy constraints)
    affordable_damage = self._calculate_affordable_damage(context)

    # Step 2: Calculate total monster HP
    total_monster_hp = sum(m.current_hp + m.block for m in context.monsters_alive)

    # Step 3: Check with reduced margin (10% instead of 20%)
    has_damage_potential = affordable_damage >= total_monster_hp * 1.1

    # Step 4: Validate targeting (single-target vs AOE constraints)
    targeting_feasible = self._can_target_all_monsters(context, affordable_damage)

    # Step 5: HP safety check (only go for lethal if not too risky)
    hp_safe = context.player_hp_pct > 0.3 or context.player_hp > 30

    return has_damage_potential and targeting_feasible and hp_safe
```

### 2. CombatEndingDetector.find_lethal_sequence()

**Current Implementation** (combat_ending.py:53-104):
```python
def find_lethal_sequence(self, context: DecisionContext) -> List[PlayCardAction]:
    # Greedy approach:
    # 1. Sort monsters by HP (lowest first)
    # 2. Sort attack cards by damage (highest first)
    # 3. Match highest-damage card to each monster
    # 4. Check if damage >= monster HP
```

**Issues**:
1. **No energy tracking**: May suggest playing more cards than affordable
2. **No AOE optimization**: Doesn't consider that AOE (Cleave, Whirlwind) might be better than single-target
3. **No card synergy**: Doesn't account for Strength, Vulnerable, Weak
4. **Premature exit**: Stops after first card that "can kill" without verifying total damage

**Proposed Fix**:
```python
def find_lethal_sequence(self, context: DecisionContext) -> List[PlayCardAction]:
    # Use beam search instead of greedy!
    # Reuse HeuristicCombatPlanner with lethal-focused weights

    lethal_planner = HeuristicCombatPlanner(
        combat_mode=CombatMode.AGGRESSIVE,  # Maximize damage
        beam_width=10,  # Small beam for speed
        max_depth=5
    )

    # Add incentive to kill all monsters
    sequence = lethal_planner.plan_turn(context)

    # Verify sequence actually kills all monsters
    if self._verify_lethal(sequence, context):
        return sequence
    else:
        return []  # Failed to construct valid lethal sequence
```

### 3. Beam Search Scoring

**Current Scoring** (simulation.py:660-732):
```python
# Monsters killed bonus
score += kills * KILL_BONUS  # KILL_BONUS = 100

# Damage dealt
score += total_damage * DAMAGE_WEIGHT  # DAMAGE_WEIGHT = 2.0

# Block gained
score += block_gained * BLOCK_WEIGHT  # BLOCK_WEIGHT = 1.5
```

**Issues**:
1. **KILL_BONUS too low**: Killing a 10 HP monster with a 12 damage card gives score = 100 + (12 × 2.0) = 124
2. **Block overvalued**: Playing Defend (5 block) gives score = 5 × 1.5 = 7.5, which is competitive with low-damage attacks
3. **No all-or-nothing bonus**: Killing 2/3 monsters gets 2×100 = 200, but killing 3/3 should be worth much more

**Proposed Fix**:
```python
# ALL_MONSTERS_KILLED bonus (exponential)
all_killed = (final_alive == 0)
if all_killed:
    score += ALL_LETHAL_BONUS  # 500 points (huge incentive)

# Regular kill bonus (per monster)
score += kills * KILL_BONUS  # 100

# Reduce block priority when lethal is possible
if lethal_is_possible(context):
    score += block_gained * (BLOCK_WEIGHT * 0.3)  # Penalize defense by 70%
```

### 4. SimpleAgent (Silent/Defect)

**Current Implementation**: No lethal detection at all

**Proposed Addition**:
```python
def get_play_card_action(self):
    # NEW: Check for lethal before card selection
    if self._has_lethal_damage():
        lethal_action = self._get_lethal_action()
        if lethal_action:
            return lethal_action

    # Existing logic...
    playable_cards = [card for card in self.game.hand if card.is_playable]
    # ... rest of current implementation
```

## Data Flow

### Current Flow (Buggy)
```
Game State → CombatEndingDetector
            ↓
            can_kill_all() returns False (bug!)
            ↓
            Falls through to beam search
            ↓
            Beam search explores defensive sequences
            ↓
            Defensive sequence scores higher than kill sequence
            ↓
            AI plays Defend instead of Strike
            ↓
            Monsters survive, AI takes damage next turn
```

### Proposed Flow (Fixed)
```
Game State → CombatEndingDetector
            ↓
            can_kill_all() returns True (fixed!)
            ↓
            find_lethal_sequence() uses beam search with AGGRESSIVE mode
            ↓
            Returns lethal sequence [Strike, Strike, Bash]
            ↓
            Verification: Simulate sequence, confirm all monsters die
            ↓
            Return lethal sequence (skip beam search)
            ↓
            Monsters killed, combat ends, no damage taken
```

## Key Design Decisions

### Decision 1: Reduce Margin from 20% to 10%
**Rationale**:
- 20% margin was conservative to avoid over-aggression
- In practice, this causes false negatives (missing lethal lines)
- 10% is still safe enough to account for targeting suboptimalities

**Trade-off**: Slightly increased risk of failed lethal attempts, but significantly more lethal opportunities detected

### Decision 2: Use Beam Search for Sequence Construction
**Rationale**:
- Greedy approach is too simple for complex card interactions
- Beam search already exists and is optimized
- Reusing code reduces maintenance burden

**Trade-off**: Slightly slower than greedy, but still fast enough (<50ms for small beam)

### Decision 3: Add HP Safety Threshold
**Rationale**:
- Going for lethal at 5 HP is risky (Thorns, retaliation damage, etc.)
- Only go for lethal when player has safe HP buffer

**Trade-off**: Will skip some lethal opportunities at low HP, but prevents deaths from miscalculations

### Decision 4: Exponential Bonus for All-Kill
**Rationale**:
- Killing all monsters should be worth much more than killing some
- Linear bonus (100 per kill) doesn't differentiate between 2/3 and 3/3 kills
- Exponential bonus (500 for all) creates strong incentive to close out games

**Trade-off**: May cause AI to overcommit to failed lethal, but HP safety check mitigates this

## Implementation Strategy

### Phase 1: Add Instrumentation (Low Risk)
1. Add detailed logging to `CombatEndingDetector`
2. Log lethal detection results (true/false with reasons)
3. Log sequence construction attempts
4. Run test games to collect data

### Phase 2: Fix Detection Logic (Medium Risk)
1. Implement `can_kill_all()` improvements (reduce margin, add energy check)
2. Implement `_can_target_all_monsters()` helper
3. Add HP safety threshold check
4. Test with logged failure cases

### Phase 3: Fix Sequence Construction (Medium Risk)
1. Rewrite `find_lethal_sequence()` to use beam search
2. Implement `_verify_lethal()` simulation helper
3. Add fallback to greedy if beam search fails
4. Test constructed sequences for validity

### Phase 4: Beam Search Scoring (Low Risk)
1. Add ALL_LETHAL_BONUS constant
2. Implement `lethal_is_possible()` helper for beam search
3. Reduce block weight when lethal available
4. Test with variety of combat scenarios

### Phase 5: SimpleAgent Extension (Low Risk)
1. Implement `_has_lethal_damage()` for SimpleAgent
2. Implement `_get_lethal_action()` for SimpleAgent
3. Test with Silent and Defect

## Validation Plan

### Unit Tests (Manual)
1. **Lethal detection test cases**:
   - Single monster, exact lethal damage
   - Single monster, overkill damage
   - Two monsters, need AOE
   - Two monsters, single-target sufficient
   - Low HP, should skip risky lethal

2. **Sequence construction test cases**:
   - Simple: [Strike, Strike] kills 10 HP monster
   - Complex: [Bash, Strike] with Vulnerable kills 20 HP monster
   - AOE: [Cleave] kills two 8 HP monsters
   - Energy-constrained: [Strike, Strike, Strike] with only 2 energy

3. **Scoring test cases**:
   - Lethal sequence vs defensive sequence (lethal should win)
   - Near-lethal vs full defense (lethal should still win)
   - High damage vs high block (damage should win when lethal possible)

### Integration Tests
1. Run 20 games with Ironclad, monitor ai_debug.log for:
   - "[COMBAT] Lethal detected!" frequency
   - Lethal sequence execution success rate
   - No crashes or infinite loops

2. Run 10 games each with Silent and Defect, verify:
   - Lethal detection works for all classes
   - No regression in win rate

### Success Metrics
1. **Detection accuracy**: 95%+ of true lethal situations detected
2. **Execution success**: 100% of detected lethal sequences successfully execute
3. **Win rate**: No regression in overall win rate (target: maintain current win rate)
4. **Performance**: Lethal detection + construction completes in <50ms

## Rollback Plan

If issues are detected after deployment:

1. **Immediate rollback**: Revert changes to `combat_ending.py` and `ironclad_combat.py`
2. **Parameter tuning**: Adjust margin from 1.1 to 1.15 or 1.2 if too aggressive
3. **Disable lethal detection**: Add feature flag to skip lethal check entirely if bugs are critical

## Open Questions

1. **What is the actual failure rate?**
   - Need to analyze logs to determine if detection fails 10% or 50% of the time
   - Will affect parameter tuning (margin, HP threshold)

2. **Should we add card-specific logic?**
   - E.g., prioritize Reaper for lethal at low HP (heals to safe range)
   - E.g., prefer Limit Break + Strength buildup over immediate lethal
   - **Decision**: No, keep it simple for now. Add later if needed.

3. **How to handle multi-turn lethal?**
   - E.g., "Play Demon Form this turn, kill all next turn"
   - **Decision**: Out of scope. Only fix single-turn lethal for now.

4. **Should lethal detection be a separate module?**
   - Currently embedded in `CombatEndingDetector`
   - **Decision**: Keep existing structure, only refactor if it grows too complex.
