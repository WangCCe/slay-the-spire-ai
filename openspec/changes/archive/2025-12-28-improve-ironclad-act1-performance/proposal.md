# Proposal: Improve Ironclad Act 1 Performance

## Change ID
`improve-ironclad-act1-performance`

## Status
**PROPOSED** - Ready for review

## Problem Statement

The AI's Ironclad performance is currently suboptimal, frequently failing to complete Act 1. Based on user feedback and code analysis, the following issues have been identified:

1. **Inefficient Combat Decisions**: The current `SimpleAgent` uses greedy single-card selection without looking ahead, leading to suboptimal sequences (e.g., over-defending when lethal is available, wasting energy on inefficient card combinations)

2. **Suboptimal Card Reward Selection**: The priority lists in `IroncladPriority` don't adequately account for:
   - Act 1 specific needs (early game scaling vs consistency)
   - Deck synergies (e.g., picking up Strength cards without other Strength cards)
   - Current deck composition (picking cards that duplicate effects already abundant in deck)

3. **Lack of Risk Assessment**: The AI doesn't properly assess:
   - When to take risky plays for lethal
   - When to conserve HP vs resources
   - Elite fight difficulty assessment

4. **Underutilization of Optimized AI**: Despite having an `OptimizedAgent` with beam search combat planning and synergy detection:
   - It's not enabled by default (requires `--optimized` flag or environment variable)
   - The SimpleAgent is still the default in main.py
   - The OptimizedAgent exists but may have integration issues or bugs preventing its use

## Root Causes

From code analysis:

1. **main.py:30**: Default behavior is to use `SimpleAgent` unless explicitly requested
2. **agent.py:118-154**: `get_play_card_action()` uses greedy selection - picks one "best" card without simulating the full turn
3. **priorities.py:458-558**: Static priority lists that don't adapt to:
   - Current deck composition
   - Act progression
   - Relic synergies
4. **Missing context**: SimpleAgent doesn't use the `DecisionContext`, `IroncladCombatPlanner`, or `SynergyCardEvaluator` from the heuristics system

## Proposed Solution

### Phase 1: Enable Optimized AI by Default
Make `OptimizedAgent` the default choice for Ironclad, as it already includes:
- Beam search combat planning (`IroncladCombatPlanner`)
- Synergy-based card evaluation (`SynergyCardEvaluator`)
- Combat ending detection (`CombatEndingDetector`)
- Deck archetype detection

### Phase 2: Fix Critical Bugs in Optimized AI
Investigate and fix any bugs preventing OptimizedAI from working correctly:
- Verify beam search is finding optimal sequences
- Fix targeting logic (high HP for Bash, low HP for attacks)
- Ensure energy calculations are correct
- Validate simulation accuracy

### Phase 3: Improve Act 1 Priorities
Update `IroncladPriority` for better Act 1 performance:
- Prioritize early game consistency over late-game scaling
- Adjust card reward selection based on deck composition
- Improve defensive card assessment (when to block vs when to attack)

### Phase 4: Add Safety Improvements
Enhance risk assessment:
- HP-based decision thresholds (play safer when low HP)
- Elite encounter detection (play around big hits)
- Potion timing improvements

## Impact

### Expected Benefits
- **Win Rate Improvement**: Target 50%+ Act 1 completion rate for Ironclad at A20
- **Better Combat Decisions**: Beam search will find lethal lines and avoid wasting resources
- **Smarter Card Selection**: Synergy-aware evaluation reduces anti-picks
- **Reduced Deaths**: Better defensive assessment prevents unnecessary damage

### Scope
- **Modified**:
  - `main.py` - Enable OptimizedAgent by default
  - `spirecomm/ai/priorities.py` - Update Ironclad priorities for Act 1
  - `spirecomm/ai/heuristics/ironclad_combat.py` - Fix any bugs in combat planner
  - `spirecomm/ai/heuristics/simulation.py` - Ensure simulation accuracy
- **Testing**: Monitor win rates in `ai_game_stats.csv`

### Risks
- **Performance**: Beam search is slower than greedy (mitigation: adaptive beam width/depth)
- **Complexity**: More code paths = more potential bugs (mitigation: thorough testing)
- **Regression**: Changes might affect other character classes (mitigation: test all classes)

## Success Metrics

1. **Quantitative**:
   - Ironclad Act 1 completion rate at A20: >50%
   - Average turns per combat: <15 (efficient kills)
   - Average HP lost per combat: <20

2. **Qualitative**:
   - No obvious misplays (wasting potions, passing with lethal)
   - Better card reward choices (observed via logging)
   - Stable performance across multiple runs

## Dependencies

- **Communication Mod**: Must be installed and configured
- **No external Python packages**: All improvements must use standard library
- **Statistics tracking**: Should be enabled to measure improvements

## Timeline

- **Phase 1** (Enable OptimizedAI): Quick - change default in main.py, verify it works
- **Phase 2** (Bug Fixes): Medium - depends on what issues are found
- **Phase 3** (Priority Tuning): Medium - requires iteration and testing
- **Phase 4** (Safety): Low-Medium - incremental improvements

## Alternatives Considered

1. **Keep SimpleAgent, add improvements**: Rejected - would duplicate OptimizedAgent functionality
2. **Create new IroncladAgent**: Rejected - unnecessary complexity, OptimizedAgent already exists
3. **Only tune priorities**: Rejected - doesn't fix the fundamental greedy decision-making flaw
4. **Machine Learning approach**: Rejected - requires external dependencies, more complex than heuristic improvements

## Open Questions

1. What specific issues is the user experiencing? (Which combats? Which floor?)
2. Is the OptimizedAgent failing due to bugs, or is it just not being used?
3. What ascension level is the user playing at? (Lower ascension needs different strategy)
4. Are there specific card rewards the AI is picking that are problematic?

## References

- `IRONCLAD_IMPROVEMENTS.md` - Existing documentation on Ironclad optimizations
- `OPTIMIZED_AI_README.md` - Documentation on the OptimizedAgent system
- `COMBAT_SYSTEM_IMPLEMENTATION_SUMMARY.md` - Beam search implementation details
