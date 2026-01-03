# Change: Optimize Beam Search Combat for A20 Ironclad

## Why

The current OptimizedAgent uses beam search for combat planning but has several critical issues limiting A20 performance:

1. **Mechanic simulation bugs**: Vulnerable/Weak/Frail use incorrect multiplier formulas (layer-based instead of duration-based), causing systematic over/underestimation
2. **Damage-focused scoring**: Prioritizes damage output over survival, leading to avoidable HP loss in A20
3. **Stale cache execution**: Doesn't replan when hand/energy/monsters change (draws, card generation, deaths)
4. **No state deduplication**: Beam search explores duplicate game states, wasting computational budget
5. **Inefficient action space**: Expands all playable cards equally instead of pruning low-value actions early

These issues cause suboptimal decisions in elite/boss fights and reduce A20 win rates.

## What Changes

### Phase 1: Critical Fixes (High Impact, Low Risk)
- Fix debuff multipliers: Vulnerable/Weak/Frail apply fixed multipliers when present (1.5x/0.75x/0.75x) instead of layer-based scaling
- Add next-turn survival scoring: Estimate enemy incoming damage and penalize HP loss heavily
- Add replan triggers: Detect when cached plan becomes invalid (card draws, energy changes, monster deaths)

### Phase 2: Performance & Quality
- Add transposition table: Deduplicate identical game states to widen effective beam width
- Implement two-stage action expansion: FastScore filter → FullSim evaluation with progressive widening (M decreases with depth)

### Phase 3: Advanced Decision Quality
- Add engine event tracking: Count exhaust/draw/energy events for implicit combo evaluation
- Implement threat-based targeting: Prioritize high-threat enemies and kill targets over lowest-HP

## Impact

**Affected specs:**
- `ai-combat` (new capability for beam search combat planning)

**Affected code:**
- `spirecomm/ai/heuristics/simulation.py` - Fix debuff mechanics, add transposition table
- `spirecomm/ai/heuristics/card.py` - Add engine event tracking
- `spirecomm/ai/agent.py` - Add replan triggers to OptimizedAgent
- `spirecomm/ai/decision/base.py` - Enhance DecisionContext with threat evaluation

**Expected outcomes:**
- Higher A20 Ironclad win rate (primary success metric)
- Reduced average HP loss per combat
- Better elite/boss fight performance
- Maintained or improved decision speed (<100ms per turn)
- More robust handling of complex combat scenarios

**Migration:**
No breaking changes. OptimizedAgent behavior improves incrementally with each phase. SimpleAgent remains unchanged.
