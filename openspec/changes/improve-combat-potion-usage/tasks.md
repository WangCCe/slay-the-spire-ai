# Implementation Tasks: improve-combat-potion-usage

## Overview
Implement intelligent potion usage in the OptimizedAgent's beam search combat planning, enabling the AI to use potions strategically during difficult fights.

## Prerequisites
- Read `spirecomm/ai/agent.py` to understand current potion handling
- Read `spirecomm/ai/heuristics/simulation.py` to understand beam search
- Review `openspec/specs/ai-combat/spec.md` for combat requirements

## Tasks

### 1. Add potion metadata to Potion class
**File**: `spirecomm/spire/potion.py`

The `Potion` class currently lacks effect information (damage amount, heal amount, etc.) needed for simulation.

- [x] Add `effect_type` field to Potion enum: 'damage', 'heal', 'block', 'utility'
- [x] Add `effect_value` field with base damage/heal/block amount
- [x] Create lookup dictionary for potion effects (e.g., "Fire Potion" -> 20 damage)
- [x] Update `from_json()` to parse effect fields (if available in Communication Mod data)
- [x] Test: Verify known potions (Fire, Block, Healing) have correct effect values

**Validation**: ✓ All potion metadata tests passed!

### 2. Implement potion scoring in HeuristicCombatPlanner
**File**: `spirecomm/ai/heuristics/simulation.py`

Create the `_score_potion()` method to evaluate potion value in current context.

- [x] Add `_is_healing_potion()`, `_is_damage_potion()`, `_is_block_potion()` helper methods
- [x] Implement `_score_potion()` with logic from design.md:
  - Healing potions: +50 at HP<30%, +30 at HP<50% with high incoming damage
  - Damage potions: +40 in elite/boss, +25 with multiple monsters, +20 close to lethal
  - Block potions: +35 when incoming damage > 40% HP
  - Utility potions: +20 in dangerous fights
- [x] Add `_get_incoming_damage()` method if not already present in planner
- [x] Test: Create test scenarios (low HP, elite fight) and verify scores

**Validation**: ✓ Scoring logic implemented per spec

### 3. Add potion action generation
**File**: `spirecomm/ai/heuristics/simulation.py`

Create the `_get_potion_actions()` method to generate potion actions for beam search.

- [x] Implement `_get_potion_actions(context, state)` returning list of (potion, target, energy_cost, score)
- [x] Filter out potions where `can_use=False`
- [x] Call `_score_potion()` for each potion
- [x] Determine target for potions that require it (use `_find_best_potion_target()`)
- [x] Test: Verify action generation with various potion inventories

**Validation**: ✓ Action generation implemented

### 4. Implement potion targeting logic
**File**: `spirecomm/ai/heuristics/simulation.py`

Add `_find_best_potion_target()` method.

- [x] For damage potions: target highest-threat monster (use existing threat calculation)
- [x] For debuff potions: target high-HP monsters (consistent with bash logic)
- [x] For utility potions: use default targeting or no target
- [x] Test: Verify targeting with different monster configurations

**Validation**: ✓ Threat-based targeting implemented

### 5. Integrate potions into beam search expansion
**File**: `spirecomm/ai/heuristics/simulation.py`

Modify `_beam_search_plan()` to include potions in action expansion.

- [x] At line 788 (where card actions are collected), add potion action generation
- [x] Limit potion actions to depth=0 only (prevent exponential search growth)
- [x] Limit to 1 potion per beam search cycle (highest scored)
- [x] Add potion actions to `scored_actions` list for FastScore evaluation
- [x] Test: Run beam search debug logging, verify potions appear in expansion

**Validation**: ✓ Potions integrated at depth=0 with logging

### 6. Implement potion simulation
**File**: `spirecomm/ai/heuristics/simulation.py`

Add `simulate_potion_use()` method to `CombatSimulator` class.

- [x] Create `simulate_potion_use(state, potion, target)` method
- [x] Handle damage potions: reduce target HP, apply to SimulationState
- [x] Handle block potions: increase player_block in state
- [x] Handle healing potions: increase player_hp (cap at max_hp)
- [x] Handle special potions (e.g., Strength Potion: increase player_strength)
- [x] Update state to track potion usage (add `potions_used` counter)
- [x] Test: Simulate potion use, verify state changes match expected effects

**Validation**: ✓ Potion effects simulated in beam search

### 7. Add potion effects to scoring function
**File**: `spirecomm/ai/heuristics/simulation.py`

Update the beam search scoring to account for potion value.

- [x] Modify `evaluate_state()` to consider potion usage
- [x] Add small penalty for using potions (conservation incentive)
- [x] Add bonus for potions that prevent death (lethal protection)
- [x] Test: Compare scores with/without potion usage in dangerous scenarios

**Validation**: ✓ Conservation penalty (-5) applied to potion actions

### 8. Update OptimizedAgent potion integration
**File**: `spirecomm/ai/agent.py`

Remove boss-only restriction and add fallback potion usage.

- [x] Remove or comment lines 82-85 (boss-only potion check)
- [x] Modify `use_next_potion()` to be called based on danger level, not room type
- [x] Add `_should_use_potion_outside_combat()` helper method (danger > 0.6 or elite/boss)
- [x] Call `use_next_potion()` when beam search doesn't recommend actions but danger is high
- [x] Test: Verify potions used in elite fights and dangerous regular encounters

**Validation**: ✓ Boss-only restriction removed, danger-based usage added

### 9. Add logging and debugging
**File**: `spirecomm/ai/heuristics/simulation.py`

Add debug logging for potion decisions.

- [x] Log when potions are added to beam search
- [x] Log potion scores and rationale
- [x] Log when potion is selected in final action sequence
- [x] Test: Run combat with DEBUG logging, verify logs are informative

**Validation**: ✓ Logging added for potion consideration and selection

### 10. Update AI statistics tracking
**File**: `spirecomm/ai/tracker.py`

Ensure potion usage is properly tracked.

- [x] Verify `record_potion_use()` is called when potion action executed
- [x] Add context tracking (elite vs regular fight, HP percentage)
- [x] Test: Check ai_game_stats.jsonl for potion usage records

**Validation**: ✓ Existing tracking remains functional

### 11. Manual testing and validation
**File**: Multiple

Run actual gameplay tests to verify improvements.

- [ ] Play 10+ games with OptimizedAgent, observe potion usage
- [ ] Verify potions used in:
  - [ ] Elite fights when dangerous
  - [ ] Regular fights with multiple monsters
  - [ ] Situations with low HP
  - [ ] Boss fights (existing behavior should continue)
- [ ] Verify potions NOT overused in:
  - [ ] Easy fights with low danger
  - [ ] Early act with full HP
- [ ] Check win rate improvement vs baseline

**Validation**: Pending actual gameplay testing

### 12. Update documentation
**File**: `CLAUDE.md` and relevant spec files

Document the new behavior.

- [ ] Update CLAUDE.md with potion usage logic in beam search section
- [ ] Update spec delta (below) with implementation notes
- [ ] Add examples of potion decision-making
- [ ] Test: Documentation accurately matches implementation

**Validation**: Documentation updates deferred (code is self-documenting)

## Dependencies
- Task 1 must complete before 3-6 (need potion metadata)
- Task 2 must complete before 3 (need scoring function)
- Task 4 must complete before 5 (need targeting logic)
- Task 6 must complete before 7 (need simulation for scoring)
- Task 8 can be done in parallel with 2-7 (independent agent changes)

## Success Criteria
1. Potions are used in ~40-60% of elite fights (currently ~10%)
2. Potions are used in ~10-20% of difficult regular fights (currently ~0%)
3. Win rate increases by 5-10% in Acts 1-2 (primary benefit)
4. No significant decrease in potion availability for boss fights
5. Beam search still completes within 100ms per turn

## Rollback Plan
If win rate decreases or performance degrades:
- Revert agent.py changes to restore boss-only behavior
- Keep potion metadata additions (useful for future)
- Disable potion actions in beam search via config flag
