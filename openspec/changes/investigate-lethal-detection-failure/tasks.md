# Tasks: Fix Lethal Detection Failure

## Phase 1: Investigation and Instrumentation

- [ ] **Task 1.1**: Add detailed logging to `CombatEndingDetector.can_kill_all()`
  - Log total affordable damage calculated
  - Log total monster HP calculated
  - Log margin check result (pass/fail)
  - Log energy constraint check (pass/fail)
  - Log HP safety threshold check (pass/fail)
  - Log final decision with reasoning
  - **Validation**: Run 5 games, check ai_debug.log for [LETHAL_DETECTION] messages

- [ ] **Task 1.2**: Add logging to `CombatEndingDetector.find_lethal_sequence()`
  - Log sequence construction attempt
  - Log number of cards in sequence
  - Log sequence validation result
  - Log fallback to beam search if construction fails
  - **Validation**: Run 5 games, check ai_debug.log for [LETHAL_SEQUENCE] messages

- [ ] **Task 1.3**: Analyze existing logs for failure patterns
  - Search ai_debug.log for examples where defense was played despite lethal availability
  - Categorize failures: detection failure vs construction failure vs scoring failure
  - Document specific test cases (monster HP, player hand, energy available)
  - **Validation**: Document at least 3 specific failure cases from logs

- [ ] **Task 1.4**: Review current combat scoring weights
  - Check KILL_BONUS, DAMAGE_WEIGHT, BLOCK_WEIGHT values
  - Verify if defensive cards are outscoring kill sequences
  - Test scoring with manual examples
  - **Validation**: Create document with scoring analysis

## Phase 2: Fix Lethal Detection Logic

- [ ] **Task 2.1**: Implement `_calculate_affordable_damage()` method
  - Calculate total damage from cards playable with available energy
  - Respect card costs (use cost_for_turn for Snecko Eye support)
  - Add Strength to attack damage
  - Account for Vulnerable debuff if present
  - **Validation**: Unit test with [Strike(6), Strike(6), Heavy Blade(14)] and 2 energy → returns 20 damage (can't afford Heavy Blade)

- [ ] **Task 2.2**: Implement `_can_target_all_monsters()` helper method
  - Check if single-target attacks can reach all monsters (energy constraint)
  - Check if AOE attacks are available when needed
  - Return False if targeting constraints prevent lethal
  - **Validation**: Unit test with 2 monsters (12 HP each) and hand [Strike(6), Strike(6)] → returns False (need AOE or more attacks)

- [ ] **Task 2.3**: Add HP safety threshold to `can_kill_all()`
  - Check player HP > 30 OR player HP percentage > 30%
  - Return False if HP too low (even if damage sufficient)
  - Log reason when HP check fails
  - **Validation**: Unit test with player at 10 HP, lethal available → returns False

- [ ] **Task 2.4**: Reduce margin requirement from 20% to 10%
  - Change line 51 in combat_ending.py from `* 1.2` to `* 1.1`
  - Update docstring to reflect new margin
  - **Validation**: Unit test with 100 monster HP, 105 damage available → returns True (would have returned False with 1.2 margin)

- [ ] **Task 2.5**: Integrate all checks into `can_kill_all()`
  - Call `_calculate_affordable_damage()` instead of `_calculate_max_damage()`
  - Add `_can_target_all_monsters()` check
  - Add HP safety threshold check
  - Update logging to include all check results
  - **Validation**: Run 10 games, verify lethal detection works correctly

## Phase 3: Fix Lethal Sequence Construction

- [ ] **Task 3.1**: Rewrite `find_lethal_sequence()` to use beam search
  - Create HeuristicCombatPlanner with AGGRESSIVE mode
  - Set small beam_width (10) for speed
  - Set max_depth (5) for sequence length
  - Call `plan_turn()` to get sequence
  - **Validation**: Unit test with hand [Strike, Strike, Bash], monster 12 HP → returns [Strike, Strike]

- [ ] **Task 3.2**: Implement `_verify_lethal()` helper method
  - Simulate playing the sequence using FastCombatSimulator
  - Check if all monsters are dead after simulation
  - Return True if lethal validated, False otherwise
  - **Validation**: Unit test with lethal sequence → returns True, with non-lethal sequence → returns False

- [ ] **Task 3.3**: Add validation to `find_lethal_sequence()`
  - Call `_verify_lethal()` on constructed sequence
  - Return empty list if validation fails
  - Log validation failure
  - **Validation**: Run 5 games, verify no invalid lethal sequences are executed

- [ ] **Task 3.4**: Add fallback to greedy approach if beam search fails
  - If beam search returns empty sequence, try original greedy logic
  - Log when fallback is triggered
  - **Validation**: Test with edge case where beam search times out

## Phase 4: Beam Search Scoring Improvements

- [ ] **Task 4.1**: Add ALL_LETHAL_BONUS constant to simulation.py
  - Define constant: `ALL_LETHAL_BONUS = 500`
  - Add comment explaining exponential bonus for killing all monsters
  - **Validation**: Read code to verify constant is defined

- [ ] **Task 4.2**: Implement all-kill bonus in scoring function
  - Check if `final_alive == 0` (all monsters killed)
  - Add `ALL_LETHAL_BONUS` to score if condition met
  - Log when bonus is applied
  - **Validation**: Unit test with all monsters killed → score includes +500

- [ ] **Task 4.3**: Implement block penalty when lethal available
  - Create `lethal_is_possible()` helper (call `can_kill_all()`)
  - In scoring function, reduce BLOCK_WEIGHT by 70% if lethal is possible
  - Log when block penalty is applied
  - **Validation**: Unit test with lethal available, block card played → score reduced by 70%

- [ ] **Task 4.4**: Test scoring with manual examples
  - Create test case: all-kill (3 monsters) vs heavy defense
  - Verify all-kill sequence scores higher
  - Create test case: partial kill (2/3) vs no kill
  - Verify partial kill scores higher
  - **Validation**: All test cases pass

## Phase 5: Extend to SimpleAgent (Silent/Defect)

- [ ] **Task 5.1**: Implement `_has_lethal_damage()` in SimpleAgent
  - Calculate total damage from all attack cards in hand
  - Add player Strength if available
  - Check if total damage >= total monster HP + block
  - Return True if lethal available
  - **Validation**: Unit test with hand [Strike(6), Strike(6)], monster 12 HP → returns True

- [ ] **Task 5.2**: Implement `_get_lethal_action()` in SimpleAgent
  - Sort attack cards by damage (highest first)
  - Create PlayCardAction for highest-damage card
  - Set target to lowest HP monster
  - Return action
  - **Validation**: Unit test returns correct PlayCardAction

- [ ] **Task 5.3**: Integrate lethal check into `get_play_card_action()`
  - Call `_has_lethal_damage()` at start of method
  - If lethal detected, call `_get_lethal_action()` and return
  - Log when lethal is detected for SimpleAgent
  - **Validation**: Run 5 games with Silent, verify lethal is prioritized

- [ ] **Task 5.4**: Test with Silent and Defect
  - Run 10 games with Silent
  - Run 10 games with Defect
  - Monitor ai_debug.log for lethal detection
  - Verify win rate is not degraded
  - **Validation**: Win rate maintained (±5% of baseline)

## Phase 6: Integration Testing and Validation

- [ ] **Task 6.1**: Run comprehensive tests with Ironclad
  - Play 20 games with Ironclad
  - Monitor ai_debug.log for lethal detection messages
  - Track success rate: (lethal detected) / (lethal actually available)
  - Target: 95%+ detection accuracy
  - **Validation**: Document detection accuracy rate

- [ ] **Task 6.2**: Verify no regression in survival rate
  - Compare win rate before and after changes
  - Compare average HP lost per combat
  - Compare death rate
  - Target: No more than 5% regression in win rate
  - **Validation**: Statistics documented in CSV

- [ ] **Task 6.3**: Test edge cases
  - Low HP lethal (player at 15-30 HP): Should skip risky lethal
  - AOE lethal (Cleave, Whirlwind): Should prioritize AOE over single-target
  - Energy-constrained lethal (exactly enough energy): Should work
  - Multi-monster lethal (3+ monsters): Should construct valid sequence
  - **Validation**: All edge cases handled correctly

- [ ] **Task 6.4**: Performance validation
  - Measure time for lethal detection (should be <10ms)
  - Measure time for sequence construction (should be <50ms)
  - Verify no timeouts in Communication Mod
  - **Validation**: Add timing logs, confirm within budget

- [ ] **Task 6.5**: Code review and cleanup
  - Review all changes for code quality
  - Remove debug logging if excessive
  - Update docstrings
  - Add comments for complex logic
  - **Validation**: Code is clean and documented

## Phase 7: Documentation and Rollout

- [ ] **Task 7.1**: Update README/CLAUDE.md if needed
  - Document new lethal detection behavior
  - Add troubleshooting section if issues arise
  - **Validation**: Documentation is clear and accurate

- [ ] **Task 7.2**: Create rollback plan
  - Document how to revert changes if needed
  - Add feature flag to disable lethal detection
  - **Validation**: Rollback procedure is documented

- [ ] **Task 7.3**: Final validation
  - Run final test suite (all character classes)
  - Check all log files for errors
  - Verify ai_game_stats.csv shows acceptable performance
  - **Validation**: All checks pass, ready for deployment

## Dependencies

- **Task 2.1** depends on Task 1.4 (need to understand current scoring first)
- **Task 2.5** depends on Tasks 2.1, 2.2, 2.3, 2.4 (integrate all components)
- **Task 3.1** depends on Task 2.5 (need fixed detection first)
- **Task 3.3** depends on Task 3.2 (need verification helper first)
- **Task 4.3** depends on Task 2.5 (need lethal detection helper)
- **Task 5.3** depends on Tasks 5.1, 5.2 (need helpers first)
- **Task 6.1** depends on all Phase 2-5 tasks (need complete implementation)
- **Task 6.2** depends on Task 6.1 (need test data first)

## Estimated Effort

- **Phase 1**: 2-3 hours (investigation and logging)
- **Phase 2**: 3-4 hours (detection logic fixes)
- **Phase 3**: 2-3 hours (sequence construction fixes)
- **Phase 4**: 1-2 hours (scoring improvements)
- **Phase 5**: 2-3 hours (SimpleAgent extension)
- **Phase 6**: 3-4 hours (testing and validation)
- **Phase 7**: 1-2 hours (documentation and rollout)

**Total**: 14-21 hours
