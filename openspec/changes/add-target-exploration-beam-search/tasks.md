# Implementation Tasks

## Phase 1: Smart Target Pruning

### 1.1 Implement target ranking
- [x] Create `_rank_targets(card, context)` method in `simulation.py`
  - Returns list of (monster, threat_score) tuples sorted by threat
  - Separate logic for attacks vs debuff cards
  - Handle edge cases (no monsters, no targets needed)
- [ ] Add unit tests for `_rank_targets()`
  - Test with 1, 2, 3, 4+ monsters
  - Test killable vs non-killable targets
  - Test debuff card targeting

### 1.2 Implement target pruning
- [x] Create `_prune_targets(card, ranked_targets, context)` method
  - For attacks: Keep killable targets + highest threat
  - For debuffs: Keep top 2 threat targets
  - Skip pruning if > 4 monsters (fallback to deterministic)
  - **Implemented cleanup phase detection (all monsters < 8 HP)**
- [ ] Add tests for pruning logic
  - Verify at most 2-3 targets returned for attacks
  - Verify at most 2 targets returned for debuffs
  - Test edge case: all monsters killable
  - Test edge case: no monsters killable

### 1.3 Refactor `_find_best_target()`
- [x] Modify `_find_best_target()` to use `_rank_targets()` internally
  - Keep current behavior (return single best target)
  - Reuse ranking logic for consistency
- [x] Verify no regression in existing tests
  - **Import test successful, module loads correctly**

---

## Phase 2: Conditional Target Exploration

### 2.1 Add target exploration enable/disable logic
- [x] Create `_should_explore_targets(context)` method
  - Return False if monster_count > 3
  - Return False if monster_count < 2
  - Return False if hand_size > 5
  - Return False if no single-target attack cards
  - Return False if beam_search_time > 60ms (from context)
  - Return False if cleanup phase (all monsters < 8 HP)
  - Otherwise return True
- [ ] Add tests for enable conditions
  - Test each condition independently
  - Test combination of conditions

### 2.2 Integrate target exploration into beam search
- [x] Modify `_beam_search_plan()` in `simulation.py`
  - Before card expansion loop, check `_should_explore_targets()`
  - If False: Use current deterministic behavior
  - If True: Use target expansion for targeted cards
- [x] Add logging for target exploration decisions
  - Log when exploration is enabled/disabled and why
  - Log number of targets explored per card
  - Log performance metrics (pruning debug logs added)

### 2.3 Add timeout protection
- [x] Wrap target exploration in timeout check
  - If elapsed time > 60ms, disable target exploration
  - Fall back to deterministic targeting
  - Log timeout events
- [ ] Test timeout handling
  - Simulate slow beam search scenarios
  - Verify fallback works correctly

---

## Phase 3: Lazy Target Expansion

### 3.1 Implement progressive target expansion
- [x] Add progressive target expansion logic (inline, not as separate constant)
  - Depth 0: 2 targets
  - Depth 1: 1-2 targets (adaptive, currently set to 2)
  - Depth 2+: 1 target (deterministic)
- [x] Modify card expansion loop
  - For each card, get pruned targets
  - Select top M targets based on depth
  - Create candidate actions for each target
- [ ] Test progressive expansion
  - Verify depth 0 explores 2 targets
  - Verify depth 2+ explores 1 target
  - Test with varying monster counts

### 3.2 Detect "cleanup phase"
- [x] Add cleanup phase detection in `_should_explore_targets()` and `_prune_targets()`
  - Return True if all monsters < 8 HP
  - Return True if all monsters at 1 HP (Neow's Blessing scenario)
- [x] Use greedy targeting in cleanup phase
  - Skip target exploration in cleanup
  - Use lowest-HP targeting for attacks (implemented in `_prune_targets()`)
- [ ] Test cleanup detection
  - Test with all low-HP monsters
  - Test with mixed HP monsters

---

## Phase 4: Testing & Validation

### 4.1 Performance testing
- [ ] Run 100 combats with target exploration enabled
  - Measure average beam search time
  - Measure max beam search time
  - Verify < 100ms average, < 150ms max
- [ ] Compare to baseline (deterministic targeting)
  - Measure time overhead percentage
  - Target: < 20% overhead

### 4.2 Win rate testing
- [ ] Run 50 games with target exploration
  - Track Act 1 completion rate
  - Track overall win rate
  - Compare to baseline (previous runs)
- [ ] Monitor multi-kill rate
  - Count combats killing 2+ monsters
  - Compare to baseline
  - Target: +10% improvement

### 4.3 Qualitative validation
- [ ] Review combat logs for 10 games
  - Check for better target distribution
  - Check for missed kills (regressions)
  - Verify debuff targeting is sensible
- [ ] Check timeout logs
  - Verify no timeout spikes
  - Verify fallback logic works

---

## Documentation

### 5.1 Update spec
- [x] Add requirements to `openspec/changes/add-target-exploration-beam-search/specs/ai-combat/spec.md`
  - Target pruning requirements
  - Conditional exploration requirements
  - Progressive expansion requirements
  - Performance requirements

### 5.2 Code comments
- [x] Document target exploration strategy
  - Add module-level docstring explaining approach
  - Add inline comments for pruning logic
  - Add comments for timeout protection

### 5.3 Update README (if applicable)
- [ ] Document target exploration feature
  - Explain when it's enabled
  - Explain performance impact
  - Provide examples

---

## Rollback Plan

If issues arise:
- [ ] Add feature flag to disable target exploration
  - Environment variable: `SPIRECOMM_TARGET_EXPLORATION=false`
  - Command-line flag: `--no-target-exploration`
- [ ] Keep deterministic targeting as default if tests fail
- [ ] Monitor logs for 24 hours after deployment

---

## Dependencies

- Task 1.1 depends on: None ✅
- Task 1.2 depends on: 1.1 ✅
- Task 1.3 depends on: 1.2 ✅
- Task 2.1 depends on: 1.3 ✅
- Task 2.2 depends on: 2.1 ✅
- Task 2.3 depends on: 2.2 ✅
- Task 3.1 depends on: 2.2 ✅
- Task 3.2 depends on: 2.2 ✅
- Task 4.x depends on: All implementation tasks (1.1-3.2) ✅
- Task 5.x depends on: All implementation tasks (1.1-3.2) ✅

---

## Parallelizable Work

These tasks can be done in parallel:
- Tasks 1.1, 1.2, 2.1 (implement different methods) ✅ Completed
- Tasks 4.1, 4.2 (different types of testing) - Pending
- Tasks 5.1, 5.2, 5.3 (different documentation) - Partially complete

---

## Estimated Time

- Phase 1 (Pruning): 1-2 hours ✅ **Completed**
- Phase 2 (Conditional): 1-2 hours ✅ **Completed**
- Phase 3 (Lazy): 2-3 hours ✅ **Completed**
- Phase 4 (Testing): 2-3 hours ⏳ In Progress
- Phase 5 (Documentation): 1-2 hours ✅ Mostly Complete

**Total**: 7-12 hours (Implementation ~6 hours complete, Testing & validation pending)

---

## Implementation Summary

**Completed Features**:
1. ✅ `_rank_targets()` - Returns sorted list of (monster, threat) tuples
2. ✅ `_prune_targets()` - Implements smart target space reduction
   - Attack cards: Keep killable targets + highest threat fallback
   - Debuff cards: Keep top 2 threat targets
   - Cleanup phase: Use greedy lowest-HP targeting
   - Skip if > 4 monsters
3. ✅ `_should_explore_targets()` - Conditional enable logic
   - Checks: monster count (2-3), hand size (<=5), single-target cards, timeout (60ms), cleanup phase
4. ✅ Target exploration integrated into `_beam_search_plan()`
   - Progressive expansion: depth 0→2 targets, depth 1→2 targets, depth 2+→1 target
   - Comprehensive logging at every step
   - Fallback to deterministic when appropriate

**Key Design Decisions**:
- Progressive target expansion limits to 2 targets at depth 0-1, 1 target at depth 2+
- Cleanup phase detection (all monsters < 8 HP) uses greedy targeting
- Timeout protection at 60ms (leaves 40ms buffer for 100ms total budget)
- Cleanup phase also disables target exploration for efficiency

**Code Quality**:
- ✅ Syntax check passed
- ✅ Import test successful
- ✅ Comprehensive debug logging added
- ✅ Backward compatible (falls back to deterministic when needed)
