# Implementation Tasks

## Overview
Ordered list of implementation tasks for fixing over-defensive elite combat behavior. Tasks are organized by capability and should be completed in order for incremental value.

---

## Phase 1: Core Detection Infrastructure (Foundation)

### 1.1 Implement EnemyThreatProfiler class
**File**: `spirecomm/ai/decision/base.py`

**Changes**:
- Create new `EnemyThreatProfiler` class
- Implement `analyze_threat(monsters: List[Monster]) -> ThreatCategory`
- Add ThreatCategory enum (REGULAR, ELITE, SCALING, BOSS, HIGH_DEFENSE)
- Implement elite name detection (Gremlin Nob, Slavers, Sentry, etc.)
- Implement scaling detection (strength gain, ritual, multi-enemy)

**Validation**:
- Test threat detection for all elite types
- Test multi-enemy detection (3+ monsters)
- Test power-based scaling detection

**Estimated impact**: Enables combat mode selection

---

### 1.2 Add threat_category to DecisionContext
**File**: `spirecomm/ai/decision/base.py`

**Changes**:
- Add `threat_category` field to DecisionContext
- Call EnemyThreatProfiler during initialization
- Cache threat result for performance
- Add `is_elite` property (True if ELITE or SCALING)

**Validation**:
- Test threat is cached correctly
- Test threat_category is accessible in combat planner
- Verify threat is recalculated between combats

**Estimated impact**: Makes threat info available to all AI components

**Dependencies**: 1.1 (needs EnemyThreatProfiler)

---

## Phase 2: Combat Mode System (elite-aggressive-mode)

### 2.1 Implement CombatMode enumeration
**File**: `spirecomm/ai/heuristics/simulation.py` (or new file)

**Changes**:
- Create CombatMode enum (BALANCED, AGGRESSIVE, SEMI_AGGRESSIVE)
- Define weight profiles for each mode:
  - BALANCED: DAMAGE=2.0, BLOCK=1.5, W_DEATHRISK=8.0, KILL_BONUS=100
  - AGGRESSIVE: DAMAGE=5.0, BLOCK=0.5, W_DEATHRISK=4.0, KILL_BONUS=200
  - SEMI_AGGRESSIVE: DAMAGE=3.5, BLOCK=1.0, W_DEATHRISK=6.0, KILL_BONUS=150

**Validation**:
- Test all three modes exist
- Verify weight profiles are correct
- Test mode enumeration is accessible

**Estimated impact**: Defines distinct combat behaviors

---

### 2.2 Add combat mode to HeuristicCombatPlanner
**File**: `spirecomm/ai/heuristics/simulation.py`

**Changes**:
- Add `combat_mode` parameter to __init__() (default BALANCED)
- Store mode as instance variable
- Select weights based on mode in calculate_outcome_score()
- Apply mode-specific weights to all scoring

**Validation**:
- Test AGGRESSIVE mode uses DAMAGE=5.0, BLOCK=0.5
- Test BALANCED mode uses original weights
- Test mode persists across beam search

**Estimated impact**: Planner uses mode-aware weights

**Dependencies**: 2.1 (needs CombatMode enum)

---

### 2.3 Implement combat mode selector
**File**: `spirecomm/ai/heuristics/simulation.py` or `spirecomm/ai/agent.py`

**Changes**:
- Create `select_combat_mode(threat: ThreatCategory) -> CombatMode` function
- Logic: ELITE/SCALING → AGGRESSIVE, BOSS → SEMI_AGGRESSIVE, REGULAR → BALANCED
- Call selector when creating HeuristicCombatPlanner
- Pass mode to planner constructor

**Validation**:
- Test elite fights select AGGRESSIVE
- Test regular fights select BALANCED
- Test boss fights select SEMI_AGGRESSIVE

**Estimated impact**: Auto-selects appropriate mode per fight

**Dependencies**: 1.2 (needs threat_category), 2.1 (needs CombatMode)

---

## Phase 3: Fast-Kill Detection (dps-check-detection)

### 3.1 Implement damage potential estimator
**File**: `spirecomm/ai/decision/base.py` - EnemyThreatProfiler class

**Changes**:
- Add `estimate_damage_potential(hand: List[Card], context) -> int` method
- Calculate base damage of all playable attacks
- Apply Strength bonuses
- Apply debuffs (Vulnerable 1.5×, Weak 0.75×)
- Consider energy limits

**Validation**:
- Test simple damage calculation (3× Strike = 18)
- Test Vulnerable increases damage
- Test Strength increases damage
- Test energy limits considered

**Estimated impact**: Enables fast-kill detection

---

### 3.2 Implement fast-kill calculator
**File**: `spirecomm/ai/decision/base.py` - EnemyThreatProfiler class

**Changes**:
- Add `can_fast_kill(context) -> Tuple[bool, int]` method
- Sum current HP of all monsters
- Compare against damage_potential
- Return (True, 1) if killable this turn
- Return (True, 2) if killable in 2 turns
- Return (False, 999) otherwise

**Validation**:
- Test one-turn kill detected
- Test two-turn kill detected
- Test impossible to fast kill

**Estimated impact**: AI recognizes lethal lines

**Dependencies**: 3.1 (needs damage_potential)

---

### 3.3 Add LETHAL_BONUS to scoring
**File**: `spirecomm/ai/heuristics/simulation.py`

**Changes**:
- Define LETHAL_BONUS = 300
- Check fast_kill result in calculate_outcome_score()
- If sequence achieves lethal: add +300 bonus
- Add +150 bonus for two-turn kills

**Validation**:
- Test lethal sequence receives +300 bonus
- Test non-lethal sequence no bonus
- Test lethal bonus outweighs defensive plays

**Estimated impact**: Beam search prioritizes winning lines

**Dependencies**: 3.2 (needs fast_kill detection)

---

### 3.4 Add fast-kill result caching
**File**: `spirecomm/ai/decision/base.py` - DecisionContext class

**Changes**:
- Add `fast_kill_result` field (cached Tuple[bool, int])
- Calculate once at turn start
- Recalculate on turn change or hand change
- Use cache in all scoring

**Validation**:
- Test fast-kill calculated once per turn
- Test cache reused in beam search
- Test cache invalidated on turn change

**Estimated impact**: Maintains performance

**Dependencies**: 3.2

---

## Phase 4: Progressive Aggression (progressive-aggression)

### 4.1 Implement aggression state machine
**File**: `spirecomm/ai/heuristics/simulation.py` or new file

**Changes**:
- Create AggressionState enum (RUSHING, EVALUATING, FINISHING, FAILED_PIVOT)
- Implement `get_aggression_state(turn, enemy_hp_pct) -> AggressionState`
- State transition logic:
  - Turn 1-2: RUSHING
  - Turn 3-4: EVALUATING (check HP%)
  - HP < 30%: FINISHING (from any state)
  - HP > 50% after turn 3: FAILED_PIVOT

**Validation**:
- Test initial state is RUSHING
- Test transition to EVALUATING on turn 3
- Test transition to FINISHING at low HP
- Test transition to FAILED_PIVOT at high HP after turn 3

**Estimated impact**: Dynamic aggression based on fight progress

---

### 4.2 Implement turn-based aggression multiplier
**File**: `spirecomm/ai/heuristics/simulation.py`

**Changes**:
- Add `calculate_aggression_multiplier(state: AggressionState, turn: int) -> float`
- Multiplier values:
  - RUSHING: 1.0
  - FINISHING: 1.0
  - EVALUATING (turn 3): 0.6
  - EVALUATING (turn 4): 0.4
  - FAILED_PIVOT: 0.2 (or switch to BALANCED mode)

**Validation**:
- Test turn 1 multiplier = 1.0
- Test turn 3 multiplier = 0.6
- Test turn 5 multiplier = 0.2

**Estimated impact**: Reduces damage priority over time

**Dependencies**: 4.1 (needs aggression state)

---

### 4.3 Implement enemy HP percentage calculation
**File**: `spirecomm/ai/decision/base.py` - DecisionContext class

**Changes**:
- Add `enemy_hp_pct` property
- Sum current HP of all alive monsters
- Sum max HP of all alive monsters
- Calculate percentage: current / max
- Cache result for performance

**Validation**:
- Test single monster HP%
- Test multi-monster HP aggregation
- Test dead monsters excluded

**Estimated impact**: Enables HP-based state transitions

**Dependencies**: 1.2 (needs monster access)

---

### 4.4 Integrate aggression multiplier into scoring
**File**: `spirecomm/ai/heuristics/simulation.py`

**Changes**:
- In calculate_outcome_score(), get aggression state
- Calculate multiplier based on state and turn
- Apply multiplier to damage score: damage_score × multiplier
- Log state and multiplier for debugging

**Validation**:
- Test turn 1 damage receives 1.0× multiplier
- Test turn 3 damage receives 0.6× multiplier
- Test FINISHING state locks multiplier at 1.0

**Estimated impact**: Progressive aggression in action

**Dependencies**: 4.1, 4.2, 4.3

---

### 4.5 Implement defensive pivot on failed rush
**File**: `spirecomm/ai/heuristics/simulation.py`

**Changes**:
- Detect FAILED_PIVOT state
- Switch combat_mode from AGGRESSIVE to BALANCED
- Persist mode change for remainder of fight
- Log pivot event

**Validation**:
- Test pivot triggers when HP > 50% on turn 3
- Test BALANCED weights used after pivot
- Test pivot doesn't trigger if HP < 50%

**Estimated impact**: Prevents suicidal failed rushes

**Dependencies**: 4.1, 2.3 (needs combat mode switching)

---

## Phase 5: Integration and Tuning

### 5.1 Update agent to use combat mode system
**File**: `spirecomm/ai/agent.py`

**Changes**:
- In OptimizedAgent, get threat_category from context
- Call select_combat_mode()
- Pass mode to HeuristicCombatPlanner constructor
- Ensure mode is recalculated each combat

**Validation**:
- Test agent creates planner with correct mode
- Test mode switches between combats
- Verify logging shows mode selection

**Estimated impact**: End-to-end integration

**Dependencies**: 1.2, 2.3

---

### 5.2 Update ironclad_combat.py for consistency
**File**: `spirecomm/ai/heuristics/ironclad_combat.py`

**Changes**:
- Update IroncladCombatPlanner to use combat modes
- Apply same mode-based weights
- Ensure consistency with HeuristicCombatPlanner

**Validation**:
- Test IroncladCombatPlanner uses AGGRESSIVE in elite fights
- Verify scoring consistency

**Estimated impact**: Consistent behavior across planners

**Dependencies**: 2.2, 2.3

---

### 5.3 Manual testing - Act 1 elites
**Testing**:

**Test cases** (run 5 games each at A20):
1. Gremlin Nob - verify fast kill strategy
2. Three Slavers - verify AOE/focus fire
3. Sentry - verify aggressive damage

**Metrics**:
- Turns to kill (target: 3-5 turns)
- Damage taken (target: <30 HP)
- Win rate (target: >80%)

**Validation**:
- Compare against baseline (current over-defensive)
- Verify faster kills
- Verify less damage taken

**Estimated impact**: Real-world validation

**Dependencies**: All previous tasks

---

### 5.4 Manual testing - Regular fights
**Testing**:

**Test cases** (run 10 games at A20):
1. Regular hallway fights (Cultist, Jaw Worm, Fungi Beast)
2. Verify no behavior change
3. Verify BALANCED mode used

**Metrics**:
- Win rate (should match baseline)
- HP expenditure (should match baseline)
- No regression

**Validation**:
- Confirm no regression in regular fights
- Verify BALANCED mode is default

**Estimated impact**: Ensures backward compatibility

**Dependencies**: All previous tasks

---

### 5.5 Tuning and adjustment
**Optimization**:

Based on test results:

1. **Adjust AGGRESSIVE weights** if needed:
   - If still losing elites: Increase DAMAGE_WEIGHT to 6.0-7.0
   - If taking too much damage: Increase BLOCK_WEIGHT to 0.8-1.0

2. **Adjust aggression multipliers** if needed:
   - If dying too fast on turn 3-4: Reduce multipliers
   - If not aggressive enough: Increase multipliers

3. **Adjust LETHAL_BONUS** if needed:
   - If not prioritizing lethal: Increase to 400-500
   - If overcommitting to risky lethals: Decrease to 200-250

**Validation**:
- Re-run elite tests
- Re-run regular fight tests
- Verify improvements

**Estimated impact**: Optimized weights

**Dependencies**: 5.3, 5.4

---

## Phase 6: Documentation and Version Bump

### 6.1 Update AI version
**File**: `spirecomm/ai/statistics.py`

**Changes**:
- Increment AI version to 3.3.0-fix-over-defense
- Add changelog entry

**Validation**:
- Verify version updated
- Check changelog accuracy

**Estimated impact**: Proper versioning

**Dependencies**: All implementation complete

---

### 6.2 Update CLAUDE.md documentation
**File**: `CLAUDE.md`

**Changes**:
- Document combat mode system
- Document elite/scaling detection
- Document progressive aggression
- Add troubleshooting guide

**Validation**:
- Verify documentation is clear
- Check for completeness

**Estimated impact**: Future maintainability

**Dependencies**: 6.1

---

## Task Summary

**Total tasks**: 24

**Critical path**: 1.1 → 1.2 → 2.1 → 2.2 → 2.3 → 3.1 → 3.2 → 3.3 → 4.1 → 4.2 → 4.3 → 4.4 → 5.1 → 5.3

**Parallelizable**: 1.1 can be done in parallel with 2.1

**Estimated effort**:
- Phase 1: 2-3 hours
- Phase 2: 3-4 hours
- Phase 3: 2-3 hours
- Phase 4: 3-4 hours
- Phase 5: 4-6 hours (testing)
- Phase 6: 1 hour

**Total**: 15-21 hours

**Milestone 1** (after Phase 2): Combat mode system works
**Milestone 2** (after Phase 4): All features implemented
**Milestone 3** (after Phase 5): Tested and tuned
**Milestone 4** (after Phase 6): Ready for production
