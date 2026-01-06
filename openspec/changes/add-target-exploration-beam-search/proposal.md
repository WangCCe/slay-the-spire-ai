# Proposal: Add Target Exploration to Beam Search

## Change ID
`add-target-exploration-beam-search`

## Status
**PROPOSED** - Ready for review

## Problem Statement

The current beam search implementation in `OptimizedAgent` only explores **card sequences**, not **target choices**. For each card that requires targeting, the agent deterministically selects a single target using `_find_best_target()` before beam search evaluates the sequence. This approach misses optimal combat sequences where target distribution matters.

### Current Behavior

From `spirecomm/ai/heuristics/simulation.py:1150-1152`:
```python
# Determine target (deterministic, not explored)
target = self._find_best_target(card, context) if card.has_target else None
```

This means:
- **Beam search explores**: Which cards to play, in what order
- **Beam search does NOT explore**: Which monster to target with each attack

### Example Scenario

**Setup**: 3 monsters [Boss(20HP), MinionA(10HP), MinionB(10HP)], Hand: [Iron Wave(5 dmg), Heavy Blade(14 dmg)]

**Current (deterministic) approach**:
1. Iron Wave: `_find_best_target()` → Boss (highest threat)
2. Heavy Blade: `_find_best_target()` → Boss (highest threat)
   - **Result**: Boss at 1 HP, both minions at full HP ✗

**Optimal approach** (target exploration would find):
1. Iron Wave: Target MinionA → Kill (5 dmg)
2. Heavy Blade: Target MinionB → Kill (14 dmg)
   - **Result**: Two minions dead, Boss at full HP (but -20 incoming damage) ✓

### Impact

This limitation causes:
1. **Missed kill opportunities**: Focusing fire on one target when spreading damage could kill multiple
2. **Inefficient debuff usage**: Applying Vulnerable to monsters that aren't the highest damage dealers
3. **Suboptimal AOE vs single-target decisions**: Not evaluating whether spreading damage is better
4. **Reduced beam search effectiveness**: The algorithm explores a smaller decision tree than intended

## Root Causes

From code analysis:

1. **`simulation.py:1152`**: Target selection happens **inside** the beam search loop, not as a branching factor
2. **Performance concern**: Full target exploration would explode search space:
   - Current: `(card_count)^depth` candidates
   - Full target exploration: `(card_count × monster_count)^depth` candidates
   - Example: 5 cards × 3 monsters × 3 depth = 3375 candidates (27x increase)

3. **Design assumption**: The original design assumed `_find_best_target()` was "good enough" to avoid explosion

## Proposed Solution

### Phase 1: Smart Target Pruning (Conservative)

Add **target space pruning** before beam search expansion to limit the number of targets explored per card:

**Pruning Strategy**:
- For **attack cards**: Only explore:
  1. Killable targets (damage >= monster HP + block)
  2. Highest threat target (fallback)
- For **debuff cards**: Only explore:
  1. Top 2 threat targets
  2. Skip if target count > 4 (fall back to deterministic)

**Result**: At most 2-3 targets per card instead of all alive monsters

### Phase 2: Conditional Target Exploration

Add a **target exploration toggle** that's enabled only when beneficial:

**Enable target exploration when**:
- 2-3 monsters alive (not overwhelming)
- Hand size <= 5 cards (manageable complexity)
- At least one single-target attack card
- NOT in timeout danger (beam search < 60ms so far)

**Otherwise**: Use deterministic `_find_best_target()` (current behavior)

### Phase 3: Lazy Target Expansion

Implement **progressive target expansion** similar to progressive card expansion:

- **Depth 0**: Explore top 2 targets (M_targets = 2)
- **Depth 1**: Explore top 1-2 targets (M_targets = 1-2)
- **Depth 2+**: Use deterministic (M_targets = 1)

This focuses exploration on the first action (most impactful) while avoiding explosion.

## Impact

### Expected Benefits

1. **Better kill efficiency**: Find sequences that kill multiple monsters instead of over-damaging one
2. **Smarter debuff targeting**: Apply Vulnerable/Weak to monsters that maximize the effect
3. **Improved AOE evaluation**: Beam search can compare "Cleave all for 8" vs "Bash highest threat for 12 + Vulnerable"
4. **Minimal performance impact**: Pruning keeps search space manageable

### Scope

- **Modified**:
  - `spirecomm/ai/heuristics/simulation.py`:
    - `_beam_search_plan()`: Add target exploration logic
    - `_find_best_target()`: Refactor to return ranked target list
    - Add `_prune_targets()` method for target space reduction
  - `openspec/specs/ai-combat/spec.md`: Add target exploration requirements
- **Testing**: Verify decision time remains < 100ms, monitor win rate improvements

### Risks

1. **Performance degradation**: If pruning isn't aggressive enough, beam search could timeout
   - **Mitigation**: Add timeout protection (80ms budget), fall back to deterministic if slow
   - **Mitigation**: Monitor beam search expansion count, abort if > 500 candidates

2. **Complexity increase**: More code paths = more potential bugs
   - **Mitigation**: Thorough logging of target selection, unit tests for pruning logic
   - **Mitigation**: Gradual rollout with feature flags

3. **Over-exploration**: Exploring targets that don't matter (e.g., all monsters at 1 HP)
   - **Mitigation**: Skip target exploration when all monsters are low HP (< 8 HP)
   - **Mitigation**: Detect "cleanup phase" and use greedy lowest-HP targeting

## Success Metrics

1. **Quantitative**:
   - Beam search decision time: Still < 100ms average (target: < 80ms with pruning)
   - Multi-kill combat rate: Increase by 10% (more combats killing 2+ monsters)
   - HP loss per combat: Decrease by 2-3 HP (better target distribution)
   - Win rate: Maintain or improve (target: +2-3% overall)

2. **Qualitative**:
   - Better target choices observed in logs (killing minions instead of over-damaging boss)
   - No timeout spikes (beam search consistently completing in time)
   - Improved debuff targeting (Vulnerable on highest damage dealers)

## Dependencies

- **Existing beam search infrastructure**: Must be working (from `ai-combat` spec)
- **Threat calculation**: `compute_threat()` from `decision/base.py` must be accurate
- **Performance budget**: 100ms timeout from Communication Mod
- **No external packages**: Must use standard library only

## Timeline

- **Phase 1** (Pruning): 1-2 hours - Implement target ranking and pruning logic
- **Phase 2** (Conditional): 1-2 hours - Add conditional enable/disable logic
- **Phase 3** (Lazy): 2-3 hours - Implement progressive target expansion
- **Testing**: 2-3 hours - Verify performance, monitor win rates
- **Total**: 6-10 hours

## Alternatives Considered

1. **Full target exploration (no pruning)**: Rejected - Would cause 27x search space explosion, timeouts
2. **Random target sampling**: Rejected - Non-deterministic, hard to test, might miss optimal targets
3. **Improve `_find_best_target()` only**: Rejected - Doesn't solve the core issue (target distribution matters)
4. **Post-hoc target reassignment**: Rejected - Too complex, breaks beam search assumptions
5. **Machine learning for targeting**: Rejected - External dependencies, overkill for this problem

## Open Questions

1. What's the maximum number of targets to explore per card before performance degrades? (Suggested: 2-3)
2. Should target exploration be character-specific? (Ironclad has more AOE, Silent has more single-target)
3. How do we handle "cleanup phase" when all monsters are low HP? (Greedy lowest-HP makes sense here)
4. Should debuff cards get different target exploration rules than attacks? (Explore more targets for debuffs?)

## References

- `openspec/specs/ai-combat/spec.md` - Current beam search requirements
- `spirecomm/ai/heuristics/simulation.py:1352-1412` - `_find_best_target()` implementation
- `spirecomm/ai/decision/base.py:189-273` - `compute_threat()` implementation
- User question: "OptimizedAgent 选目标的时候用beam search了吗"
