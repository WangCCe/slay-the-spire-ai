# Implementation Tasks

## Task 1: Add Multi-Monster Detection to Outcome Score
**Priority**: Critical
**Estimated Time**: 1-2 hours
**Dependencies**: None

Modify `spirecomm/ai/heuristics/simulation.py` to add multi-monster detection to `calculate_outcome_score()`:

1. Count alive monsters from `initial_state.monsters`
2. Apply adaptive damage multiplier based on monster count:
   - 1 monster: 1.0× (baseline)
   - 2 monsters: 1.3× (moderate bonus)
   - 3+ monsters: 1.8× (significant bonus)
3. Add logging to track multiplier application

**Success Criteria**: Outcome Score now applies damage multiplier based on monster count

---

## Task 2: Add AOE Card Bonus in Multi-Monster Scenarios
**Priority**: High
**Estimated Time**: 1 hour
**Dependencies**: Task 1

Enhance scoring to recognize AOE cards specifically:

1. Detect when AOE cards are played in sequence (Cleave, Whirlwind, Thunderclap, Immolate)
2. Apply bonus points when AOE used in multi-monster fights:
   - 2 monsters: +20 points
   - 3+ monsters: +40 points
3. Log AOE bonus application

**Success Criteria**: AOE card plays receive explicit scoring bonuses in multi-monster fights

---

## Task 3: Add Floor 6-7 Special AOE Priority
**Priority**: Medium
**Estimated Time**: 1 hour
**Dependencies**: Task 2

Add extra AOE priority during highest death floor (Floor 6-7):

1. Detect Floor 6-7 from context
2. Apply additional AOE multiplier:
   - Floor 6-7, 3+ monsters: 2.2× (extra priority)
   - Floor 6-7, 2 monsters: 1.5×
3. Add debug logging for Floor 6-7 special handling

**Success Criteria**: Floors 6-7 multi-monster fights receive highest AOE priority

---

## Task 4: Update AI Version
**Priority**: Low
**Estimated Time**: 15 minutes
**Dependencies**: Tasks 1-3

Update version string in `spirecomm/ai/statistics.py`:

```python
# Version 3.5.1: Multi-monster scoring fix
#   - Added monster count detection to calculate_outcome_score()
#   - Applied adaptive damage weight: 1.0× (1 monster), 1.3× (2 monsters), 1.8× (3+ monsters)
#   - Added AOE card bonus in multi-monster scenarios
#   - Added Floor 6-7 special AOE priority
#   - Fixed scoring mismatch between FastScore and Outcome Score
return "3.5.1-multi-monster-scoring"
```

**Success Criteria**: Version string reflects multi-monster scoring improvements

---

## Task 5: Testing and Validation
**Priority**: Critical
**Estimated Time**: 2-3 hours (50 games)
**Dependencies**: Task 4

Run validation games to verify improvements:

1. Run 50 games with v3.5.1
2. Track metrics:
   - Floor 6 death rate (target: <15%, down from 24.5%)
   - AOE card usage in multi-monster fights
   - Average HP loss in Floor 6-7
   - Win rate (target: 5-10%)
3. Review logs to confirm AOE prioritization
4. Compare baseline metrics (v3.4.7) vs v3.5.1

**Success Criteria**:
- Floor 6 death rate decreases from 24.5% to <15%
- AOE cards prioritized in 3-monster fights
- No increase in early-game (Floors 1-3) deaths

---

## Task 6: Documentation Update
**Priority**: Low
**Estimated Time**: 30 minutes
**Dependencies**: Task 5

Update project documentation:

1. Add `CHANGELOG.md` entry for v3.5.1
2. Update `CLAUDE.md` with multi-monster scoring details
3. Document scoring weights in comments

**Success Criteria**: Documentation reflects scoring changes accurately
