# Proposal: Fix Lethal Detection Failure

## Problem Statement

The AI sometimes plays defensive cards (block/skills) even when it has lethal damage available to kill all monsters this turn. This wastes damage output and extends combat unnecessarily, increasing the risk of taking damage or losing the fight.

**Observed Behavior**: AI prioritizes defensive cards (e.g., Defend, Iron Wave) over attack cards when lethal is available, resulting in:
- Wasted turn (monsters not killed when they could be)
- Unnecessary damage taken from surviving monsters
- Suboptimal win rate due to poor combat decisions

**Root Cause Analysis Needed**:
1. Is `CombatEndingDetector.can_kill_all()` correctly detecting lethal?
2. Is the lethal detection being called before beam search?
3. Are the scoring weights favoring defense over kills?
4. Is the greedy lethal sequence finder (`find_lethal_sequence()`) failing to construct valid sequences?
5. Is beam search exploring defensive sequences despite lethal being available?

## Context

**Current Implementation**:
- `IroncladCombatPlanner.plan_turn()` (line 82-87) checks `combat_ending_detector.can_kill_all(context)` before beam search
- If lethal detected, it calls `find_lethal_sequence()` to get the kill sequence
- If lethal sequence found, it returns immediately (skipping beam search)
- `CombatEndingDetector.can_kill_all()` uses a conservative 20% margin requirement (line 51: `total_possible_damage >= total_monster_hp * 1.2`)
- Beam search scoring weights: `KILL_BONUS = 100`, `DAMAGE_WEIGHT = 2.0`, `BLOCK_WEIGHT = 1.5`

**Potential Issues**:
1. **False negatives in lethal detection**: The 20% margin may be too conservative, causing valid lethal lines to be missed
2. **Greedy sequence construction failure**: `find_lethal_sequence()` uses a greedy approach that may not construct valid sequences with energy/targeting constraints
3. **Scoring weight imbalance**: Even when lethal detection fails, beam search might score defensive sequences higher than kill sequences
4. **SimpleAgent fallback**: For non-Ironclad characters, `SimpleAgent` has no lethal detection at all

## Goals

### Primary Goal
Fix the AI to consistently prioritize lethal damage over defensive plays when killing all monsters is possible this turn.

### Success Criteria
1. AI correctly identifies when lethal is available (95%+ accuracy in test scenarios)
2. AI executes lethal sequences instead of defensive plays (100% when lethal detected)
3. No regression in survival rate (defensive decisions when lethal is NOT available remain sound)
4. Coverage extends to all character classes (Ironclad, Silent, Defect)

## Scope

### In Scope
1. **Investigation**: Analyze game logs and code to identify why lethal detection fails
2. **Fix lethal detection**: Improve `CombatEndingDetector` accuracy
3. **Fix sequence construction**: Ensure `find_lethal_sequence()` returns valid executable sequences
4. **Adjust beam search scoring**: Increase kill priority to ensure lethal sequences outscore defensive ones
5. **Add lethal detection to SimpleAgent**: Extend basic lethal detection to Silent and Defect
6. **Logging**: Add debug logs to track lethal detection decisions

### Out of Scope
1. General combat optimization (separate concern)
2. Potion usage optimization (handled by existing combat-potion-usage spec)
3. Map routing changes (unrelated to combat)
4. New AI architectures (keep existing beam search)

## Non-Goals

1. Make the AI more aggressive overall (only fix lethal detection, not general aggression)
2. Optimize for speed (current 100ms budget is acceptable)
3. Add new combat mechanics (stick to existing game mechanics)

## Risks

### High Risk
- **Over-aggression**: Fixing lethal detection might make the AI too aggressive, attacking when it should defend
  - **Mitigation**: Keep the 20% margin or adjust to 10% after validation
  - **Mitigation**: Add HP threshold check (only go for lethal if player HP > 30%)

### Medium Risk
- **Performance impact**: More accurate lethal detection might be slower
  - **Mitigation**: Profile detection function, optimize if needed
  - **Mitigation**: Cache lethal detection result per turn

### Low Risk
- **Breaking existing combat logic**: Changes might introduce bugs in non-lethal scenarios
  - **Mitigation**: Add comprehensive logging to track decision-making
  - **Mitigation**: Test on variety of combat scenarios before deploying

## Alternatives Considered

### Alternative 1: Increase Kill Bonus in Beam Search
**Description**: Increase `KILL_BONUS` from 100 to 500 to make beam search naturally favor lethal

**Pros**:
- Simple change (one line)
- No new code to maintain

**Cons**:
- Doesn't fix root cause (lethal detection failure)
- May cause over-aggression in non-lethal scenarios
- Beam search is expensive; lethal detection is cheap

**Decision**: **Rejected** - This is a band-aid, not a fix. The issue is that lethal detection fails, not that scoring is wrong.

### Alternative 2: Remove Defensive Cards When Lethal Available
**Description**: Filter out defensive cards from beam search when lethal is detected

**Pros**:
- Ensures lethal sequences are explored
- Simple logic change

**Cons**:
- Still relies on lethal detection (which may be broken)
- May miss edge cases where defense is needed even with lethal (e.g., Thorns)

**Decision**: **Partially accepted** - This is a good secondary safeguard, but lethal detection must be fixed first.

### Alternative 3: Hybrid Approach (Chosen)
**Description**:
1. Fix `CombatEndingDetector` accuracy
2. Improve greedy sequence construction
3. Add defensive card filtering when lethal detected
4. Extend to all character classes

**Pros**:
- Comprehensive fix
- Defense-in-depth (multiple safeguards)
- Fair to all characters

**Cons**:
- More complex than single-line fixes
- Requires testing across characters

**Decision**: **Accepted** - This is the most robust solution.

## Dependencies

### Code Dependencies
- `spirecomm/ai/heuristics/combat_ending.py` - Core lethal detection logic
- `spirecomm/ai/heuristics/simulation.py` - Beam search scoring
- `spirecomm/ai/heuristics/ironclad_combat.py` - Ironclad combat planner
- `spirecomm/ai/agent.py` - SimpleAgent combat logic

### Spec Dependencies
- `openspec/specs/ai-combat/spec.md` - Combat requirements (may need modification)

### External Dependencies
- Slay the Spire game logs (D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log)
- Communication Mod (for testing)

## Implementation Outline

### Phase 1: Investigation (1-2 hours)
1. Add detailed logging to `CombatEndingDetector`
2. Replay game logs to identify specific failure cases
3. Categorize failures (detection vs construction vs scoring)
4. Document root cause

### Phase 2: Fix Lethal Detection (2-3 hours)
1. Adjust margin requirement (1.2 → 1.1 or 1.05)
2. Add energy constraint validation to `can_kill_all()`
3. Fix `find_lethal_sequence()` to respect targeting constraints
4. Add sequence validation before returning

### Phase 3: Beam Search Scoring (1 hour)
1. Increase `KILL_BONUS` if needed (100 → 150)
2. Add lethal bonus to scoring function
3. Filter defensive cards when lethal detected (safeguard)

### Phase 4: Extend to All Characters (2 hours)
1. Extract lethal detection into shared utility
2. Add to `SimpleAgent.get_play_card_action()`
3. Test with Silent and Defect

### Phase 5: Validation (1-2 hours)
1. Run test games and collect statistics
2. Verify no regression in survival rate
3. Check ai_debug.log for correct lethal decisions
4. Tune parameters if needed

## Rollout Plan

1. **Staged rollout**: Test with Ironclad first, then extend to Silent/Defect
2. **Monitoring**: Watch ai_debug.log for `[COMBAT] Lethal detected!` messages
3. **Rollback**: If win rate drops or crashes increase, revert changes immediately

## Open Questions

1. **What is the actual failure rate?** Need to analyze logs to determine if this affects 10% of combats or 50%
2. **Is the 20% margin appropriate?** May need to adjust based on test results
3. **Should we add a minimum HP threshold?** Only go for lethal if player HP > 30% to avoid risky plays
4. **How to handle AOE vs single-target?** Greedy sequence finder may not optimize AOE usage

**Question for user**: Can you provide a specific example from the logs where the AI played defense despite having lethal? This will help us identify the exact failure mode.
