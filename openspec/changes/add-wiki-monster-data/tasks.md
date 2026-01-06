# Tasks: Add Wiki Monster Data

## Phase 1: Data Extraction (Days 1-3)

### Task 1.1: Set up Wiki extraction infrastructure
- [ ] Create directory `scripts/wiki_extraction/`
- [ ] Create `extract_monster_data.py` script
- [ ] Implement helper functions:
  - `parse_hp_table(snapshot)` - Extract HP ranges
  - `parse_moves_section(snapshot)` - Extract move patterns
  - `parse_special_mechanics(snapshot)` - Extract abilities
  - `parse_ascension_modifiers(snapshot)` - Extract A10+ changes
- [ ] Test extraction on 3 sample monsters (Cultist, Hexaghost, Lagavulin)
- [ ] Validate extracted data against game behavior

**Validation**: Script successfully extracts data for 3 test monsters with accuracy > 95%

**Dependencies**: None

---

### Task 1.2: Extract Act 1 elite/boss data
- [ ] Navigate to and extract data for:
  - [ ] The Slaver (Blue/Red variants)
  - [ ] Gremlin Giant
  - [ ] Lagavulin
  - [ ] The Guardian
  - [ ] Slime Boss
  - [ ] Hexaghost
- [ ] Manual review and correction of extracted data
- [ ] Add strategy notes (e.g., "kill before 2nd Ritual")
- [ ] Format into JSON structure
- [ ] Save to `spirecomm/data/monster_wiki_data/act1_elites.json`

**Validation**: All 6 monsters extracted with move sequences, special mechanics, HP ranges

**Dependencies**: Task 1.1

---

### Task 1.3: Extract Act 2 elite/boss data
- [ ] Navigate to and extract data for:
  - [ ] Gremlin Leader
  - [ ] Centurion & Healer
  - [ ] Champ
  - [ ] Reptomancer
  - [ ] The Collector
- [ ] Manual review and correction
- [ ] Add strategy notes
- [ ] Save to `spirecomm/data/monster_wiki_data/act2_elites.json`

**Validation**: All 5 monsters extracted with complete data

**Dependencies**: Task 1.1

**Parallel with**: Task 1.2

---

### Task 1.4: Extract Act 3 elite/boss data
- [ ] Navigate to and extract data for:
  - [ ] Sentry (Construct/Beads/Invulnerable)
  - [ ] Chosen & Darkling
  - [ ] Time Eater
  - [ ] Donu & Deca
- [ ] Manual review and correction
- [ ] Add strategy notes
- [ ] Save to `spirecomm/data/monster_wiki_data/act3_elites.json`

**Validation**: All 4 monsters extracted with complete data

**Dependencies**: Task 1.1

**Parallel with**: Tasks 1.2, 1.3

---

### Task 1.5: Extract high-priority normal monsters
- [ ] Navigate to and extract data for:
  - [ ] Cultist
  - [ ] Jaw Worm
  - [ ] Fungi Beast
  - [ ] Louse
  - [ ] Shield & Spear
  - [ ] Sneaky Gremlin
  - [ ] Book of Stabbing
- [ ] Manual review and correction
- [ ] Save to `spirecomm/data/monster_wiki_data/priority_normals.json`

**Validation**: All 7 monsters extracted with complete data

**Dependencies**: Task 1.1

**Parallel with**: Tasks 1.2, 1.3, 1.4

---

## Phase 2: Enhanced Database (Day 4)

### Task 2.1: Create enhanced monster database module
- [ ] Create file `spirecomm/ai/heuristics/enhanced_monster_database.py`
- [ ] Implement `_load_monster_data()` function
  - Load all JSON files from `spirecomm/data/monster_wiki_data/`
  - Merge into single `ENHANCED_MONSTER_DATABASE` dict
  - Handle missing files gracefully (log info, continue)
  - Log success: "Loaded wiki data for X monsters"
- [ ] Implement `get_enhanced_monster_data(monster_id)` - lookup by ID
- [ ] Implement `get_move_pattern(monster_id, current_move_id)` - return sequence
- [ ] Implement `get_special_mechanics(monster_id)` - return mechanics dict
- [ ] Implement `get_threat_profile(monster_id)` - return threat profile
- [ ] Test: Load data for all 22 extracted monsters

**Validation**: All 22 monsters load successfully, lookup functions return correct data

**Dependencies**: Tasks 1.1-1.5

---

### Task 2.2: Add enhanced database to game data loader
- [ ] Modify `spirecomm/data/loader.py`:
  - Add `_load_monster_data()` method (similar to `_load_wiki_data()`)
  - Call `_load_monster_data()` in `load_data()` after wiki card data
  - Store in `self._monster_data` dict
  - Add `get_monster_data(monster_id)` method
- [ ] Test: Verify monster data loads on startup
- [ ] Test: Verify graceful handling when data files missing
- [ ] Update startup logging to include monster data count

**Validation**: Monster data loads automatically with game data, fallback works when missing

**Dependencies**: Task 2.1

---

## Phase 3: Threat Calculation Integration (Day 5)

### Task 3.1: Implement enhanced threat calculation
- [ ] Add method `compute_threat_v2(monster)` to `spirecomm/ai/decision/base.py`
- [ ] Implement threat components:
  - Immediate threat (current intent damage)
  - Future threat (predict next 2-3 moves from sequence)
  - Scaling threat (from threat_profile)
  - Special ability threat (summoning, phase changes)
  - Composition threat (minions, buffs)
- [ ] Add fallback: If enhanced data missing, call existing `compute_threat()`
- [ ] Add logging: Log threat calculation breakdown for debugging
- [ ] Test: Cultist threat increases by 3 per turn
- [ ] Test: Lagavulin threat: 5 (sleeping) vs 30 (awake)
- [ ] Test: Reptomancer summon threat (+20) > direct damage (+10)

**Validation**:
- Cultist turn 1: threat ≈ 18, turn 2: threat ≈ 21, turn 3: threat ≈ 24
- Lagavulin sleeping: threat ≈ 5, awake: threat ≈ 30
- Fallback to `compute_threat()` for unknown monsters

**Dependencies**: Task 2.1

---

### Task 3.2: Profile threat calculation performance
- [ ] Add timing instrumentation to `compute_threat_v2()`
- [ ] Measure execution time for 100 calls per monster type
- [ ] Verify < 5ms per monster (95th percentile)
- [ ] If > 5ms, optimize:
  - Cache enhanced_data lookup (access once, not multiple times)
  - Cache move_sequence lookups
  - Reduce dict access overhead
- [ ] Document final performance characteristics

**Validation**: 95th percentile < 5ms per monster

**Dependencies**: Task 3.1

---

## Phase 4: Target Selection Integration (Day 6)

### Task 4.1: Implement enhanced target selection
- [ ] Add method `_choose_target_for_card_v2(card, context, state)` to `spirecomm/ai/heuristics/ironclad_combat.py`
- [ ] Implement special mechanic handling:
  - Summoners: Reptomancer (kill Daggers), Cultist (kill Cultist)
  - Hibernation: Ignore Lagavulin while sleeping
  - Phase changes: Prioritize during burst windows (Hexaghost)
- [ ] Implement AOE efficiency detection:
  - Check for death split monsters (Slime Boss)
  - Check for similar HP groups
  - Return None to use AOE when efficient
- [ ] Implement card-specific targeting:
  - Bash → highest HP + threat
  - Body Slam → lowest HP + threat
- [ ] Add logging: Log target selection reasoning
- [ ] Test: Reptomancer + 2 Daggers → Bash targets Dagger
- [ ] Test: Lagavulin (sleeping) + Jaw Worm → Attack targets Jaw Worm
- [ ] Test: Cultist → Attack targets Cultist (kill before summon)

**Validation**:
- Reptomancer: Daggers targeted before Reptomancer
- Lagavulin (sleeping): Not targeted
- Cultist: Targeted for high-damage attacks
- Slime Boss: AOE cards prioritized

**Dependencies**: Task 2.1, Task 3.1

---

### Task 4.2: Profile target selection performance
- [ ] Add timing to `_choose_target_for_card_v2()`
- [ ] Measure execution time for 100 calls
- [ ] Verify < 2ms per call (95th percentile)
- [ ] Optimize if needed:
  - Cache enhanced_data lookups
  - Reduce loop iterations
- [ ] Document final performance

**Validation**: 95th percentile < 2ms per call

**Dependencies**: Task 4.1

---

## Phase 5: Combat Mode Integration (Day 7)

### Task 5.1: Implement monster-aware combat mode selection
- [ ] Add function `select_combat_mode_with_monster_data(context)` to `spirecomm/ai/agent.py`
- [ ] Implement monster composition analysis:
  - Detect summoners (has_summoner flag)
  - Detect phase changes (has_phase_change flag)
  - Detect hibernation (has_hibernating flag)
  - Calculate total scaling threat
- [ ] Implement mode selection logic:
  - AGGRESSIVE: summoners, phase-change bosses, high scaling (>10)
  - SEMI_AGGRESSIVE: elites, hibernating monsters
  - BALANCED: normal monsters
- [ ] Add logging: Log mode selection reasoning
- [ ] Test: Cultist → AGGRESSIVE
- [ ] Test: 3 Jaw Worms → BALANCED
- [ ] Test: Hexaghost (boss) → AGGRESSIVE
- [ ] Test: Lagavulin + 2 Gremlins → SEMI_AGGRESSIVE

**Validation**:
- Cultist: AGGRESSIVE mode selected
- 3 Jaw Worms: BALANCED mode selected
- Hexaghost: AGGRESSIVE mode selected
- Lagavulin + Gremlins: SEMI_AGGRESSIVE mode selected

**Dependencies**: Task 2.1

---

### Task 5.2: Integrate mode selection into combat flow
- [ ] Modify `spirecomm/ai/agent.py`:
  - Replace `select_combat_mode()` call with `select_combat_mode_with_monster_data()`
  - Update combat mode decision logging
  - Ensure backward compatibility (fallback to old selection)
- [ ] Test: Run full combat with various monster compositions
- [ ] Verify mode changes based on monster data

**Validation**: Combat mode adapts to monster composition, fallback works for unknown monsters

**Dependencies**: Task 5.1

---

## Phase 6: Combat Simulation Enhancement (Days 8-9)

### Task 6.1: Implement monster move prediction
- [ ] Add method `predict_monster_moves(monster, look_ahead=2)` to `spirecomm/ai/heuristics/simulation.py`
- [ ] Implement prediction logic:
  - Get move_sequence from enhanced database
  - Find current move in sequence
  - Return next N moves
  - Handle missing data: Return current move only
- [ ] Add error handling:
  - Handle missing move_sequence
  - Handle current_move not in sequence
- [ ] Test: Cultist predicts [Dark Strike, Incite] after Ritual
- [ ] Test: Hexaghost predicts phase-specific moves

**Validation**:
- Cultist: Correctly predicts next 2 moves
- Hexaghost: Correctly predicts phase-specific moves
- Fallback works for unknown monsters

**Dependencies**: Task 2.1

---

### Task 6.2: Enhance combat simulation with special abilities
- [ ] Modify `simulate_card_play()` in `spirecomm/ai/heuristics/simulation.py`:
  - Detect monster deaths (HP <= 0)
  - Handle death splits: Add split monsters to state (Slime Boss)
  - Handle summoning: Add summoned monsters to state (Reptomancer, Cultist)
  - Handle phase changes: Update move_pool when HP threshold crossed (Hexaghost)
- [ ] Add logging: Log special ability triggers
- [ ] Test: Slime Boss death → 2 Acid Slime (M) added to state
- [ ] Test: Reptomancer summon → 2 Daggers added to state
- [ ] Test: Hexaghost phase change → move_pool updated

**Validation**:
- Slime Boss: Splits correctly on death
- Reptomancer: Summons correctly
- Hexaghost: Phase changes at correct HP thresholds
- Beam search accounts for new monsters in future turns

**Dependencies**: Task 6.1

---

### Task 6.3: Integrate future damage into beam search
- [ ] Add method `calculate_future_monster_damage(state, context)` to simulation.py
- [ ] Use `predict_monster_moves()` to estimate damage over next 2 turns
- [ ] Integrate into beam search scoring:
  - Modify `_score_sequence()` to include future damage
  - Apply discounted weight: `future_damage * W_DEATHRISK * 0.5`
- [ ] Test: Beam search avoids over-blocking for low-damage future turns
- [ ] Test: Beam search prioritizes killing high-damage monsters

**Validation**:
- Beam search accounts for future damage in scoring
- Sequences that kill high-damage monsters prioritized
- Performance: Beam search still < 100ms

**Dependencies**: Task 6.2

---

### Task 6.4: Profile enhanced simulation performance
- [ ] Add timing to beam search with enhanced simulation
- [ ] Measure execution time for 100 combats
- [ ] Verify < 100ms (95th percentile)
- [ ] If > 100ms, optimize:
  - Reduce move prediction depth (look_ahead=2 → look_ahead=1)
  - Cache move predictions per monster per turn
  - Skip special ability simulation for simple fights
- [ ] Document final performance characteristics

**Validation**: Beam search < 100ms (95th percentile)

**Dependencies**: Task 6.3

---

## Phase 7: Complete Database (Days 10-12)

### Task 7.1: Extract remaining Act 1 normal monsters
- [ ] Extract data for:
  - [ ] All Gremlin types (Thief, Face, Wizard, Fat, Sneaky, Mad)
  - [ ] Acid Slime (S/M/L)
  - [ ] Spike Slime (S/M/L)
  - [ ] Slavers
  - [ ] Fungi Beast
  - [ ] Louse variants
  - [ ] Other Act 1 normals
- [ ] Manual review and correction
- [ ] Save to `spirecomm/data/monster_wiki_data/act1_normals.json`

**Validation**: All Act 1 normal monsters extracted (~15)

**Dependencies**: Task 1.1

---

### Task 7.2: Extract remaining Act 2 normal monsters
- [ ] Extract data for:
  - [ ] Shield and Spear variants
  - [ ] Mugger
  - [ ] Book of Stabbing
  - [ ] Snake Plant
  - [ ] Sentries
  - [ ] Other Act 2 normals
- [ ] Manual review and correction
- [ ] Save to `spirecomm/data/monster_wiki_data/act2_normals.json`

**Validation**: All Act 2 normal monsters extracted (~12)

**Dependencies**: Task 1.1

**Parallel with**: Task 7.1

---

### Task 7.3: Extract remaining Act 3 normal monsters
- [ ] Extract data for:
  - [ ] Spiker
  - [ ] Slag Slime
  - [ ] Transient
  - [ ] Other Act 3 normals
- [ ] Manual review and correction
- [ ] Save to `spirecomm/data/monster_wiki_data/act3_normals.json`

**Validation**: All Act 3 normal monsters extracted (~8)

**Dependencies**: Task 1.1

**Parallel with**: Tasks 7.1, 7.2

---

### Task 7.4: Add ascension modifiers
- [ ] Revisit all extracted monsters
- [ ] Extract ascension modifier data from Wiki:
  - A10+ changes (HP, damage, effects)
  - A15+ changes
  - A18+ changes
- [ ] Add `ascension_modifiers` field to enhanced database
- [ ] Test: Verify A10+ data is used when ascension >= 10

**Validation**: All monsters have ascension modifiers where applicable

**Dependencies**: Tasks 7.1, 7.2, 7.3

---

### Task 7.5: Verify database completeness
- [ ] Compare against `items.json` creature list (66 enemies)
- [ ] Check for missing monsters:
  ```python
  from spirecomm.data.loader import game_data_loader
  all_enemies = game_data_loader.get_all_enemies()
  enhanced_monsters = set(ENHANCED_MONSTER_DATABASE.keys())
  missing = set(all_enemies.keys()) - enhanced_monsters
  ```
- [ ] Extract data for missing monsters
- [ ] Verify count: 62+ monsters in enhanced database

**Validation**: 62+ monsters in enhanced database (matches items.json)

**Dependencies**: Task 7.4

---

## Phase 8: Integration Testing (Days 13-14)

### Task 8.1: Create unit tests
- [ ] Create `tests/test_enhanced_monster_data.py`:
  - `test_threat_calculation_cultist_scaling()` - Verify threat +3/turn
  - `test_threat_calculation_lagavulin_hibernation()` - Verify 5 (sleep) vs 30 (awake)
  - `test_threat_calculation_reptomancer_summon()` - Verify summon threat > damage
  - `test_target_selection_reptomancer()` - Verify Daggers targeted first
  - `test_target_selection_lagavulin_sleeping()` - Verify ignored while sleeping
  - `test_target_selection_cultist()` - Verify aggressive targeting
  - `test_combat_mode_cultist()` - Verify AGGRESSIVE mode
  - `test_combat_mode_multi_enemy()` - Verify SCALING/AGGRESSIVE mode
- [ ] Run tests and verify all pass

**Validation**: All unit tests pass

**Dependencies**: Tasks 3.1, 4.1, 5.1

---

### Task 8.2: Create integration tests
- [ ] Create `tests/test_enhanced_combat.py`:
  - `test_cultist_combat_aggressive()` - Full combat, verify kill before turn 3
  - `test_reptomancer_kill_daggers_first()` - Full combat, verify minion priority
  - `test_lagavulin_ignore_while_sleeping()` - Full combat, verify hibernation handling
  - `test_hexaghost_aggressive_burst()` - Full combat, verify phase change handling
  - `test_slime_boss_aoe_efficiency()` - Full combat, verify AOE prioritization
- [ ] Run tests in live game with Communication Mod
- [ ] Verify win conditions met for each test

**Validation**: All integration tests pass, AI behavior visibly improved

**Dependencies**: Task 8.1

---

### Task 8.3: Performance benchmarking
- [ ] Run performance tests:
  - Beam search time (95th percentile) with enhanced database
  - Threat calculation time (95th percentile)
  - Target selection time (95th percentile)
  - Memory usage (enhanced database size)
- [ ] Compare against baseline (existing implementation)
- [ ] Verify targets met:
  - Beam search < 100ms
  - Threat calculation < 5ms
  - Target selection < 2ms
  - Memory < 50MB
- [ ] Document performance characteristics

**Validation**: All performance targets met

**Dependencies**: Tasks 3.2, 4.2, 6.4

---

### Task 8.4: A/B testing
- [ ] Run 50 games with existing AI (baseline)
- [ ] Run 50 games with enhanced AI
- [ ] Compare metrics:
  - Win rate
  - Average damage taken per combat
  - Average turns per combat
  - Elite/Boss win rate
- [ ] Verify improvements:
  - Win rate: +5-10%
  - Damage taken: -10-20%
  - Turns: -0.5 to -1
- [ ] Document results

**Validation**: Measurable improvements in win rate, damage taken, turns

**Dependencies**: Task 8.3

---

## Phase 9: Documentation (Day 15)

### Task 9.1: Update CLAUDE.md
- [ ] Add section "Enhanced Monster Database" to CLAUDE.md
- [ ] Document:
  - File location and structure
  - Data fields and their meaning
  - How to add new monsters to database
  - Integration points (threat, targeting, combat mode)
- [ ] Add examples:
  - Example monster entry (Cultist)
  - Example threat calculation
  - Example target selection

**Validation**: CLAUDE.md updated with comprehensive documentation

**Dependencies**: Task 8.4

---

### Task 9.2: Add inline code documentation
- [ ] Add docstrings to all new functions:
  - `compute_threat_v2()` - Explain threat components
  - `_choose_target_for_card_v2()` - Explain priority logic
  - `select_combat_mode_with_monster_data()` - Explain mode selection
  - `predict_monster_moves()` - Explain move prediction
  - Helper functions in enhanced_monster_database.py
- [ ] Add inline comments for complex logic:
  - Move sequence prediction
  - Special mechanic handling
  - Threat calculation breakdown
- [ ] Verify documentation is clear and helpful

**Validation**: All new code documented

**Dependencies**: Task 9.1

---

### Task 9.3: Create user guide for monster data
- [ ] Create `docs/monster_data_guide.md`:
  - How to extract data from Wiki
  - JSON file format specification
  - Step-by-step example: Adding a new monster
  - Common pitfalls and how to avoid them
  - Validation checklist
- [ ] Include examples:
  - Simple monster (Jaw Worm)
  - Complex monster (Hexaghost with phases)
  - Summoner (Reptomancer)
- [ ] Review and verify guide is complete and accurate

**Validation**: User guide is comprehensive and actionable

**Dependencies**: Task 9.2

---

## Summary

**Total Tasks**: 42
**Estimated Duration**: 15 days
**Key Deliverables**:
- Enhanced monster database (62+ monsters)
- Enhanced threat calculation (predictive)
- Enhanced target selection (special mechanics)
- Enhanced combat mode selection (monster-aware)
- Enhanced combat simulation (move prediction)
- Comprehensive tests and documentation

**Parallelizable Work**:
- Tasks 1.2-1.5 (data extraction for different acts)
- Tasks 7.1-7.3 (normal monster extraction)
- Tasks 8.1-8.4 (testing can run in parallel once implementation complete)

**Critical Path**:
1. Task 1.1 (extraction infrastructure) → Tasks 1.2-1.5 (data extraction)
2. Task 2.1 (database creation) → Tasks 3.1, 4.1, 5.1, 6.1 (integration)
3. Task 8.4 (A/B testing) → Task 9.1-9.3 (documentation)
