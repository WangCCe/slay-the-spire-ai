# Proposal: Add Wiki Monster Data to Enhance Combat AI

## Summary

Enhance the AI's combat decision-making by integrating comprehensive monster data from the Slay the Spire Fandom Wiki. This will improve threat assessment, target selection, and combat mode selection through detailed knowledge of monster patterns, special mechanics, and weaknesses.

**Current Limitations:**
- Reactive threat calculation (only considers current intent)
- Hardcoded scaling logic for 3 monsters (Cultist, Gremlin Nob, Lagavulin)
- Limited monster database (~30 monsters with basic threat levels)
- No move pattern prediction or special ability handling

**Proposed Enhancements:**
- Proactive threat assessment (predict future moves, not just current)
- Intelligent target selection (handle summoners, hibernation, phase changes)
- Enhanced monster database (62+ monsters with move patterns, special mechanics)
- Combat simulation improvements (death splits, summoning, phase changes)

## Motivation

The AI currently makes combat decisions based primarily on immediate monster intent and basic threat levels. This reactive approach leads to suboptimal decisions:

1. **Cultist fights**: AI doesn't prioritize killing before 2nd Ritual (+6 Strength), allowing damage to double
2. **Reptomancer fights**: AI may target Reptomancer instead of killing Daggers first (which are more dangerous)
3. **Lagavulin fights**: AI doesn't recognize hibernation state, may wake it early with high-damage attacks
4. **Slime Boss fights**: AI doesn't prioritize AOE (Cleave) against monsters that split on death

By extracting detailed monster data from the Fandom Wiki (HP ranges, move patterns, special mechanics, weaknesses), the AI can make proactive, strategic decisions instead of reactive ones.

## Scope

### In Scope
1. Extract monster data from Fandom Wiki for 62+ monsters (all Act 1-3 enemies, elites, bosses)
2. Create enhanced monster database with:
   - Move patterns (sequence of moves by turn)
   - Special mechanics (summoning, hibernation, phase changes, death splits)
   - HP ranges and ascension modifiers
   - Weaknesses/resistances to status effects
3. Integrate enhanced data into:
   - Threat calculation (predictive, not reactive)
   - Target selection (special mechanic handling)
   - Combat mode selection (AGGRESSIVE/SEMI_AGGRESSIVE/BALANCED)
   - Combat simulation (move prediction, special ability effects)

### Out of Scope
- Machine learning or automated data extraction (manual extraction + organization)
- Real-time wiki updates (static data extraction)
- New combat mechanics or AI systems (enhancement only)
- Character-specific strategies (Ironclad-only focus)

## Proposed Solution

### Phase 1: Data Extraction (Days 1-3)
Use Playwright MCP to browse Fandom Wiki and extract data for priority monsters:
- **Act 1 Elites/Bosses** (6): Slaver, Gremlin Giant, Lagavulin, Guardian, Slime Boss, Hexaghost
- **Act 2 Elites/Bosses** (5): Gremlin Leader, Centurion, Champ, Reptomancer, Collector
- **Act 3 Elites/Bosses** (4): Sentry, Chosen, Time Eater, Donu & Deca
- **High-Priority Normals** (7): Cultist, Jaw Worm, Fungi Beast, Shield & Spear, Sneaky Gremlin, Book of Stabbing, Spiker

Data fields extracted per monster:
- HP ranges (min/max by act)
- Move patterns (move_id sequence by turn)
- Special mechanics (type: summoner/hibernation/phase_change/death_split)
- Weaknesses/resistances (status effect multipliers)

### Phase 2: Enhanced Database (Day 4)
Create `spirecomm/ai/heuristics/enhanced_monster_database.py` with:
```python
ENHANCED_MONSTER_DATABASE = {
    "Cultist": {
        "hp_ranges": {"normal": {"min": 42, "max": 46}},
        "moves": [
            {"move_id": 0, "name": "Ritual", "effect": "+3 Strength"},
            {"move_id": 1, "name": "Dark Strike", "damage": 6}
        ],
        "move_sequence": [0, 1, 2, 1, 1],  # Turn-by-turn pattern
        "special_mechanics": {
            "type": "summoner",
            "scaling": {"rate": "+3 Strength/turn", "threat_growth": 3.0}
        },
        "weaknesses": {"weak": 2.0},
        "threat_profile": {"base_threat": 15, "scaling_threat": 3.0}
    }
}
```

### Phase 3: Integration (Days 5-9)
Enhance existing systems:

1. **Threat Calculation** (`spirecomm/ai/decision/base.py`)
   - Add `compute_threat_v2()` with move pattern prediction
   - Predict next 2-3 moves from sequence
   - Account for scaling threat (Cultist Ritual, Lagavulin hibernation)

2. **Target Selection** (`spirecomm/ai/heuristics/ironclad_combat.py`)
   - Add `_choose_target_for_card_v2()` with special mechanic handling:
     - Summoners: Reptomancer (kill Daggers), Cultist (kill Cultist)
     - Hibernation: Ignore Lagavulin while sleeping
     - Phase changes: Burst during vulnerable windows (Hexaghost)
     - AOE efficiency: Prioritize against Slime Boss (splits)

3. **Combat Mode** (`spirecomm/ai/agent.py`)
   - Add `select_combat_mode_with_monster_data()`
   - AGGRESSIVE: Summoners, phase-change bosses, high scaling
   - SEMI_AGGRESSIVE: Elites, hibernating monsters
   - BALANCED: Normal monsters

4. **Combat Simulation** (`spirecomm/ai/heuristics/simulation.py`)
   - Add `predict_monster_moves()` for move pattern prediction
   - Enhance `simulate_card_play()` to handle death splits, phase changes, summoning

### Phase 4: Full Database (Days 10-12)
Extract remaining 40+ normal monsters and add ascension modifiers (A10+, A15+).

### Phase 5: Testing & Documentation (Days 13-15)
Integration tests, performance benchmarks, documentation updates.

## Alternatives Considered

### Alternative 1: Automated Wiki Scraping
**Pros**: Faster, scalable to game updates
**Cons**: Complex parsing, error-prone, requires maintenance when Wiki format changes
**Decision**: Manual extraction + organization (mixed approach as requested by user)

### Alternative 2: Extend Current MONSTER_DATABASE Only
**Pros**: Simpler, less code
**Cons**: Limited enhancement, no move patterns or special mechanics
**Decision**: Create separate enhanced database for richer data structure

### Alternative 3: Machine Learning for Threat Prediction
**Pros**: Learns optimal play from game data
**Cons**: Requires large training dataset, overkill for current needs
**Decision**: Manual data extraction with explicit rules (more transparent, debuggable)

## Impact

**Expected Benefits:**
- Win rate: +5-10% improvement
- Damage taken: -10-20% reduction (better defensive decisions)
- Turn efficiency: -0.5 to -1 turn per combat
- Decision quality: Visibly smarter targeting (kill Daggers first, ignore sleeping Lagavulin)

**Performance:**
- Beam search time: Maintain < 100ms (95th percentile)
- Threat calculation: < 5ms per monster
- Memory overhead: < 50MB for enhanced database

**Risks:**
- Wiki data accuracy: Manual review mitigates errors
- Performance degradation: Lazy loading, caching, early timeout fallback
- Backward compatibility: Keep existing `compute_threat()` as fallback
- Maintenance burden: Clear documentation for adding new monsters

## Success Metrics

### Quantitative
- Win rate improvement: +5-10% over baseline
- Damage taken reduction: -10-20% per combat
- Turn reduction: -0.5 to -1 turn average
- Performance: Beam search < 100ms (95th percentile)

### Qualitative
- Decision quality: visibly better targeting (e.g., killing Daggers first vs Reptomancer)
- Adaptiveness: Adjusts combat mode based on monster composition
- Robustness: Handles edge cases (hibernation, phase changes, death splits)

## Dependencies

**External:**
- Slay the Spire Fandom Wiki (https://slay-the-spire.fandom.com)
- Playwright MCP (for data extraction)

**Internal:**
- Existing monster database (`spirecomm/ai/heuristics/monster_database.py`)
- Threat calculation (`spirecomm/ai/decision/base.py:compute_threat()`)
- Target selection (`spirecomm/ai/heuristics/ironclad_combat.py`)
- Combat simulation (`spirecomm/ai/heuristics/simulation.py`)

**Blocking:**
- None (can proceed independently)

## Related Changes

- `scaling-threat-evaluation`: Enhances with detailed monster data
- `ai-combat`: Improves threat-based targeting with move prediction
- `game-data-loading`: Pattern for data loading (similar to card data from wiki-card-data.txt)

## Open Questions

1. **Data format**: Should monster data be stored as JSON files (like wiki-card-data.txt) or hardcoded in Python?
   - **Recommendation**: JSON files for maintainability, similar to existing wiki card data

2. **Extraction priority**: Should we extract all 62 monsters at once, or prioritize elites/bosses first?
   - **Recommendation**: Phased approach - elites/bosses (22) for maximum impact, then normal monsters (40+)

3. **Performance budget**: What is the acceptable overhead for enhanced threat calculation?
   - **Recommendation**: < 5ms per monster, maintain overall < 100ms beam search time

4. **Fallback behavior**: How should the AI behave when enhanced data is missing?
   - **Recommendation**: Graceful degradation to existing `compute_threat()` logic
