# Implementation Tasks

## Phase 1: Critical Mechanics Fixes

### 1.1 Fix Debuff Multiplier Calculations
- [x] 1.1.1 Locate `_apply_vulnerable_damage()` in `simulation.py:196`
- [x] 1.1.2 Verify current implementation uses layer-based multiplier (incorrect)
- [x] 1.1.3 Replace with binary multiplier: `if vulnerable > 0: damage *= 1.5`
- [x] 1.1.4 Add `_apply_weak_damage()` method with binary 0.75x multiplier
- [x] 1.1.5 Add `_apply_frail_block()` method for block gain reduction
- [x] 1.1.6 Update `_apply_attack()` to call weak damage modifier
- [x] 1.1.7 Update `_apply_skill()` to use frail block modifier
- [x] 1.1.8 Add unit tests for debuff calculations (0 stacks, 1 stack, 3 stacks)
- [x] 1.1.9 Verify with test_combat_system.py combat scenarios

**Validation:** ✅ Complete - Unit tests pass (test_phase5_unit_tests.py)

---

### 1.2 Implement Survival-First Scoring
- [x] 1.2.1 Add `_estimate_incoming_damage(monsters)` method to FastCombatSimulator
- [x] 1.2.2 Parse monster intents to calculate expected damage (attack/strength attack/buff)
- [x] 1.2.3 Modify `calculate_outcome_score()` to accept current_act parameter
- [x] 1.2.4 Calculate `hp_loss = max(0, expected_incoming - player_block)`
- [x] 1.2.5 Add death check: `if hp_loss >= player_hp: return float('-inf')`
- [x] 1.2.6 Add survival penalty: `score -= hp_loss * W_DEATHRISK` (start with W_DEATHRISK=8.0)
- [x] 1.2.7 Add danger threshold penalty based on act
- [x] 1.2.8 Update `HeuristicCombatPlanner.plan_turn()` to pass current_act to scoring
- [x] 1.2.9 Test with manual combat scenarios (verify defensive play when low HP)

**Validation:** Monitor average HP loss per combat in ai_game_stats.csv (target: reduction)

---

### 1.3 Add Replan Triggers
- [x] 1.3.1 Create `TurnPlanSignature` class in `agent.py`
- [x] 1.3.2 Store hand card UUIDs, energy, monster states, random flags
- [x] 1.3.3 Add `current_plan_signature` field to OptimizedAgent
- [x] 1.3.4 Implement `should_replan(prev_sig, context)` method
- [x] 1.3.5 Compare hand/energy/monsters for strict equality
- [x] 1.3.6 Update `get_next_action_in_game()` to check replan triggers
- [x] 1.3.7 Invalidate cache and call `plan_turn()` when triggers fire
- [x] 1.3.8 Add logging for replan events (count per turn)
- [x] 1.3.9 Test with card draw scenarios (Battle Trance, Pommel Strike)

**Validation:** Run test_optimized_ai.py and verify replan frequency <3 per turn average

---

## Phase 2: Performance Optimization

### 2.1 Implement Transposition Table
- [x] 2.1.1 Add `state_key()` method to SimulationState class
- [x] 2.1.2 Include player stats (HP, block, energy, strength, debuffs)
- [x] 2.1.3 Include monster states (HP, block, debuffs, intent) as sorted tuple
- [x] 2.1.4 Include hand card multiset (card IDs, sorted)
- [x] 2.1.5 Create `seen_states = {}` dict in `_beam_search_plan()`
- [x] 2.1.6 Check state_key before adding to candidates
- [x] 2.1.7 Keep highest-scoring path for duplicate states
- [x] 2.1.8 Convert seen_states values back to beam list
- [x] 2.1.9 Profile decision time before/after (should not increase significantly)

**Validation:** Run with beam_width=15, verify effective beam width >15 (more states explored)

---

### 2.2 Add Timeout Protection
- [x] 2.2.1 Import `time` module in simulation.py
- [x] 2.2.2 Record `start_time = time.time()` at start of `plan_turn()`
- [x] 2.2.3 Add timeout check in beam search loop: `if time.time() - start_time > 0.08: break`
- [x] 2.2.4 Return best_sequence found when timeout triggers
- [x] 2.2.5 Add fallback to cached plan if available and beam search times out
- [x] 2.2.6 Log timeout events for monitoring
- [x] 2.2.7 Test with complex combats (4+ monsters, 10+ cards)

**Validation:** Ensure all decisions complete in <100ms (p99) in ai_debug.log

---

### 2.3 Implement Two-Stage Action Expansion
- [x] 2.3.1 Create `fast_score_action(action, state)` method in HeuristicCombatPlanner
- [x] 2.3.2 Add zero-cost bonus (+20), attack bonus (+10), low-HP block bonus (+15)
- [x] 2.3.3 Add base damage estimate (+2 per damage point)
- [x] 2.3.4 Define `M_values = [12, 10, 7, 5, 4]` for progressive widening
- [x] 2.3.5 Update beam search to call fast_score on all actions
- [x] 2.3.6 Sort actions by fast_score descending
- [x] 2.3.7 Select top M actions based on current depth
- [x] 2.3.8 Run full simulation only on selected actions
- [x] 2.3.9 Compare decision time before/after (target: 20-30% reduction)

**Validation:** Profile decision time, verify <100ms p99 maintained

---

## Phase 3: Advanced Decision Quality

### 3.1 Implement Threat-Based Targeting
- [x] 3.1.1 Create `compute_threat(monster, state)` in DecisionContext (decision/base.py)
- [x] 3.1.2 Add expected damage from intent (ATTACK, ATTACK_BUFF, ATTACK_DEBUFF, ATTACK_DEFEND)
- [x] 3.1.3 Add debuff threat (+10 for Weak/Vulnerable intents)
- [x] 3.1.4 Add scaling threat (+15 for elites/bosses with growth)
- [x] 3.1.5 Add AOE threat (+8 for buffs affecting other monsters)
- [x] 3.1.6 Update `find_best_target()` to use threat scores
- [x] 3.1.7 Implement kill detection: if damage >= monster HP + block
- [x] 3.1.8 Prioritize killable targets by threat (highest threat first)
- [x] 3.1.9 If no killable targets, return highest threat target
- [x] 3.1.10 Test with multi-elite scenarios (verify threat priority over HP)

**Validation:** Manually verify targeting choices in elite fights (Gremlin Nob, Slavers)

---

### 3.2 Add Engine Event Tracking
- [x] 3.2.1 Add event counters to SimulationState (`exhaust_events`, `cards_drawn`, `skills_played`, `attacks_played`, `damage_instances`, `energy_gained`, `energy_saved`)
- [x] 3.2.2 Update `_apply_attack()` to track attack cards and damage instances
- [x] 3.2.3 Update `_apply_skill()` to track skill cards
- [x] 3.2.4 Update `_apply_power()` to detect energy-related events (Corruption, Feel No Pain)
- [x] 3.2.5 Add energy tracking in simulate_card_play (cost vs cost_for_turn)
- [x] 3.2.6 Define synergy values: `FNP_value=3`, `DE_value=2`, `draw_value=3`, `energy_value=4`
- [x] 3.2.7 Update `calculate_outcome_score()` to include event bonuses
- [x] 3.2.8 Test with Feel No Pain deck (exhaust cards should score higher)
- [x] 3.2.9 Test with Corruption deck (free skills should score higher)

**Validation:** Run test_optimized_ai.py and verify combo cards get selected

---

## Phase 4: Integration and Tuning

### 4.1 Adaptive Beam Width by Act
- [x] 4.1.1 Update `HeuristicCombatPlanner.__init__()` to accept act parameter
- [x] 4.1.2 Implement adaptive beam_width: Act 1→12, Act 2→18, Act 3→25
- [x] 4.1.3 Update OptimizedAgent to pass current_act to planner initialization
- [x] 4.1.4 Profile decision time in each act (ensure <100ms maintained)
- [x] 4.1.5 Tune values if necessary (reduce if timeouts increase)

**Validation:** Monitor ai_debug.log for decision times by act

---

### 4.2 Adaptive Depth by Hand Size
- [x] 4.2.1 Update `plan_turn()` to calculate base_max_depth
- [x] 4.2.2 Calculate `playable_count = len(playable_cards)`
- [x] 4.2.3 Add bonus for zero-cost cards: `extra_zero_cost = sum(1 for c in playable_cards if c.cost_for_turn == 0)`
- [x] 4.2.4 Add bonus for extra energy: `extra_energy = energy_available - 3`
- [x] 4.2.5 Set `max_depth = min(playable_count, 3 + extra_energy + extra_zero_cost // 2)`
- [x] 4.2.6 Cap max_depth at 5 (avoid excessive search)
- [x] 4.2.7 Test with large hand scenarios (10+ cards)

**Validation:** Verify depth adapts: 3 energy/2 cards→depth=2, 6 energy/8 cards→depth=5

---

### 4.3 Tune Scoring Weights
- [x] 4.3.1 Run baseline A20 games with current weights (record win rate, HP loss)
- [x] 4.3.2 Adjust W_DEATHRISK if too aggressive (>30 HP loss/act) or too passive (<10 HP loss/act)
- [x] 4.3.3 Tune kill bonus (currently 100) if excessive overkill or insufficient kill priority
- [x] 4.3.4 Tune damage weight (currently 2) if damage output too low
- [x] 4.3.5 Tune block weight (currently 1.5) if block under/over-utilized
- [x] 4.3.6 Run 10+ A20 games per weight configuration
- [x] 4.3.7 Select weights maximizing win rate while maintaining acceptable HP loss

**Validation:** Compare win rates in ai_game_stats.csv before/after tuning

---

### 4.4 Add Comprehensive Logging
- [x] 4.4.1 Log beam search parameters (beam_width, max_depth, M values)
- [x] 4.4.2 Log replan events (trigger reason, frequency per turn)
- [x] 4.4.3 Log transposition table stats (states seen, states merged)
- [x] 4.4.4 Log scoring breakdown (damage component, survival penalty, kill bonus)
- [x] 4.4.5 Log decision time (ms) per turn
- [x] 4.4.6 Log timeout events and fallback usage
- [x] 4.4.7 Update ai_debug.log format for readability
- [x] 4.4.8 Add stats summary at game end (avg decision time, max time, replan count)

**Validation:** Review logs from test games, verify all expected data present

---

## Phase 5: Testing and Validation

### 5.1 Unit Testing
- [x] 5.1.1 Test debuff multipliers (0, 1, 3 stacks of vulnerable/weak/frail)
- [x] 5.1.2 Test survival scoring (death penalty, HP loss penalty, danger threshold)
- [x] 5.1.3 Test state_key uniqueness (different states → different keys)
- [x] 5.1.4 Test transposition table (duplicate states merged correctly)
- [x] 5.1.5 Test threat calculation (different monster types/intents)
- [x] 5.1.6 Test fast_score_action (zero-cost prioritization, block bonus)
- [x] 5.1.7 Test replan triggers (card draw, monster death, energy change)
- [x] 5.1.8 Test timeout protection (returns best sequence when time exceeded)

**Validation:** All unit tests pass (create test_simulation.py if needed)

---

### 5.2 Integration Testing
- [x] 5.2.1 Run test_combat_system.py and verify no regressions
- [x] 5.2.2 Run test_optimized_ai.py and verify all tests pass
- [x] 5.2.3 Run 5 complete A20 Ironclad games (monitor for crashes/freeze)
- [x] 5.2.4 Verify decision times in ai_debug.log (<100ms p99)
- [x] 5.2.5 Check ai_game_stats.csv for reasonable win rate (>50% for A20)
- [x] 5.2.6 Verify average HP loss per act (target: 15-25 HP)

**Validation:** All integration tests pass, no game crashes

---

### 5.3 Performance Benchmarking
- [x] 5.3.1 Record baseline decision time (before optimization)
- [x] 5.3.2 Measure decision time after Phase 1 (critical fixes)
- [x] 5.3.3 Measure decision time after Phase 2 (transposition + pruning)
- [x] 5.3.4 Measure decision time after Phase 3 (threat + engine events)
- [x] 5.3.5 Compare p50, p95, p99 latencies across phases
- [x] 5.3.6 Verify no phase exceeds 100ms p99

**Validation:** Performance maintained or improved across all phases

---

### 5.4 Win Rate Validation
- [x] 5.4.1 Run 20+ A20 Ironclad games with optimized agent
- [x] 5.4.2 Compare win rate against baseline (from git history)
- [x] 5.4.3 Analyze lost games (cause of death: elite, boss, or attrition)
- [x] 5.4.4 Check if specific combats cause repeated losses
- [x] 5.4.5 Compare average HP loss per act (target: <25 HP/act)
- [x] 5.4.6 Verify elite/boss win rate improvement

**Validation:** Target 10-15% improvement in A20 win rate

---

## Phase 6: Documentation and Deployment

### 6.1 Update Documentation
- [x] 6.1.1 Update COMBAT_SYSTEM_IMPLEMENTATION_SUMMARY.md with new mechanics
- [x] 6.1.2 Add section on debuff multipliers (correct game formulas)
- [x] 6.1.3 Add section on survival-first scoring philosophy
- [x] 6.1.4 Add section on transposition table and state deduplication
- [x] 6.1.5 Add section on replan triggers and cache invalidation
- [x] 6.1.6 Update CLAUDE.md with new capabilities

**Validation:** Documentation accurately reflects implementation

---

### 6.2 Code Cleanup
- [x] 6.2.1 Remove debug print statements (use logging instead)
- [x] 6.2.2 Remove commented-out code
- [x] 6.2.3 Add docstrings to new methods (state_key, compute_threat, fast_score_action)
- [x] 6.2.4 Ensure consistent code style (snake_case, type hints)
- [x] 6.2.5 Run pylint/flake8 if available (fix warnings)

**Validation:** Code passes style checks

---

### 6.3 Final Validation
- [x] 6.3.1 Run `openspec validate optimize-beam-search-combat --strict`
- [x] 6.3.2 Fix any validation errors
- [x] 6.3.3 Verify all tasks in this file are completed
- [x] 6.3.4 Run final test suite (all tests pass)
- [x] 6.3.5 Generate summary document of changes
- [x] 6.3.6 Submit for review and approval

**Validation:** OpenSpec validation passes with no errors

---

## Dependencies and Parallelization

**Can be done in parallel:**
- Phase 1 tasks (1.1, 1.2, 1.3) - independent mechanics fixes
- Phase 2 tasks (2.1, 2.2, 2.3) - independent performance features
- Tasks 5.1 (unit tests) can be written alongside implementation

**Must be sequential:**
- Phase 1 → Phase 2 → Phase 3 (each phase builds on previous)
- Task 4.3 (tune weights) must wait until Phase 3 complete
- Phase 5 (testing) must wait until all implementation complete
- Phase 6 (deployment) must wait until testing complete

**Estimated completion order:**
1. Phase 1: Critical Fixes (1-2 days)
2. Phase 2: Performance (1-2 days)
3. Phase 3: Decision Quality (2-3 days)
4. Phase 4: Integration (1 day)
5. Phase 5: Testing (2-3 days)
6. Phase 6: Deployment (1 day)

**Total estimated time: 8-12 days**
