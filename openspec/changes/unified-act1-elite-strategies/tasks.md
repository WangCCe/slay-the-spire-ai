# Implementation Tasks

## Phase 1: Framework Setup

### 1.1 Create elite detection system
- [ ] Add `EliteType` enum to ironclad_combat.py
- [ ] Implement `_detect_elite_type()` method
- [ ] Test detection for all 4 elite types
- [ ] Add logging for detected elite type

### 1.2 Create unified integration point
- [ ] Implement `_apply_elite_strategy_override()` method
- [ ] Add call to integration point in `_score_sequence()`
- [ ] Ensure Gremlin Nob SKILL penalty still works
- [ ] Add framework-level logging

## Phase 2: Implement Individual Elite Strategies

### 2.1 Lagavulin progressive scaling
- [ ] Calculate siphon_count based on turn number
- [ ] Implement damage_weight scaling (4.0 → 8.0)
- [ ] Add low-damage penalty after turn 6
- [ ] Add pre-Siphon burst bonus (turns 5, 8, 11, ...)
- [ ] Test progressive scaling at turns 6, 9, 12

### 2.2 3 Sentries single-target focus
- [ ] Implement `_calculate_damage_distribution()` helper
- [ ] Add +50 bonus for 70%+ damage concentration
- [ ] Add -30 penalty for <50% concentration
- [ ] Test with concentrated vs spread damage

### 2.3 Slime Boss AOE priority
- [ ] Create AOE card list (Cleave, Thunderclap, etc.)
- [ ] Implement ×1.5 AOE damage multiplier
- [ ] Add +30 burst bonus near split threshold (40-60% HP)
- [ ] Test with AOE vs single-target attacks

## Phase 3: A20 Early Aggression

### 3.1 Implement early damage thresholds
- [ ] Turn 1: Require 8+ damage (-50 penalty if not)
- [ ] Turn 2: Require 15+ damage (-100 penalty if not)
- [ ] Turn 3+: Require 12+ HP per turn average (-150 penalty if not)
- [ ] Add ascension check (only apply if ascension >= 20)

### 3.2 Test early aggression impact
- [ ] Verify AI deals damage from turn 1
- [ ] Check that turn 2 has significant damage output
- [ ] Ensure preparation (Powers) still happens, but with damage

## Phase 4: Integration and Testing

### 4.1 Integration testing
- [ ] Test all 4 elites in mock combat scenarios
- [ ] Verify no interference between strategies
- [ ] Check that non-elite fights are unaffected

### 4.2 Validation
- [ ] Run AI vs Gremlin Nob (should still work)
- [ ] Run AI vs Lagavulin (check progressive scaling)
- [ ] Run AI vs 3 Sentries (check single-target focus)
- [ ] Run AI vs Slime Boss (check AOE priority)

### 4.3 Performance monitoring
- [ ] Check `ai_debug.log` for elite detection messages
- [ ] Verify strategy-specific logging works
- [ ] Monitor win rate in `ai_game_stats.csv`

## Phase 5: Documentation and Release

### 5.1 Update version and documentation
- [ ] Bump version to v3.4.0-unified-elite-strategies
- [ ] Update statistics.py with version comment
- [ ] Document all elite strategies in code comments

### 5.2 Create git commit and tag
- [ ] Commit all changes with descriptive message
- [ ] Create git tag v3.4.0-unified-elite-strategies
- [ ] Update OpenSpec proposal with implementation status

## Dependencies and Order

- **Phase 1** must complete before Phase 2
- **Phase 2.1, 2.2, 2.3** can be done in parallel after Phase 1
- **Phase 3** can be done in parallel with Phase 2
- **Phase 4** requires all previous phases to complete
- **Phase 5** happens after Phase 4 validation

## Estimated Complexity

- Phase 1: Low (framework setup)
- Phase 2: Medium (individual strategies)
- Phase 3: Low (threshold logic)
- Phase 4: Medium (testing and validation)
- Phase 5: Low (documentation)

**Total**: Medium complexity, ~500-700 lines of code added/modified
