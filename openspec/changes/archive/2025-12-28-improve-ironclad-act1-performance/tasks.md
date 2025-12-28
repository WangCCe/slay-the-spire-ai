# Implementation Tasks

## Change: improve-ironclad-act1-performance

This is an ordered checklist of implementation tasks. Complete tasks sequentially and mark as done.

---

## Phase 1: Enable OptimizedAI by Default

- [x] **1.1** Investigate why OptimizedAgent is not the default
  - Check main.py:30 to understand current default behavior
  - Verify OptimizedAgent imports successfully without errors
  - Test if OptimizedAgent can be instantiated and used
  - Document any import errors or missing dependencies

- [x] **1.2** Enable OptimizedAgent as default for Ironclad
  - Modify main.py to default use_optimized=True for Ironclad
  - Add fallback to SimpleAgent if OptimizedAgent fails
  - Add logging to indicate which agent is being used
  - Test that the change doesn't break other character classes

- [x] **1.3** Verify OptimizedAgent integration
  - Run a test game with OptimizedAgent for Ironclad
  - Confirm combat decisions use beam search (check logs)
  - Confirm card rewards use synergy evaluation
  - Confirm statistics are tracked correctly

- [x] **1.4** Add diagnostic logging
  - Log when OptimizedAgent vs SimpleAgent is used
  - Log beam search results (sequences evaluated, best score)
  - Log combat ending detection results
  - Log card synergy scores for rewards

---

## Phase 2: Fix Critical Bugs

- [ ] **2.1** Debug combat decision issues
  - Add logging to track decision flow in IroncladCombatPlanner
  - Identify where suboptimal decisions are made
  - Check if beam search is actually running
  - Verify simulation state is accurate

- [ ] **2.2** Fix targeting logic bugs
  - Verify Bash targets high HP monsters
  - Verify attack cards target low HP monsters
  - Verify AOE cards are used correctly with multiple monsters
  - Test edge cases (monsters with same HP, one monster left, etc.)

- [ ] **2.3** Fix energy calculation issues
  - Verify card costs are calculated correctly (check Snecko Eye, etc.)
  - Verify energy doesn't go negative in simulations
  - Verify zero-cost cards are handled correctly

- [ ] **2.4** Fix simulation accuracy
  - Verify damage calculations account for Strength
  - Verify Vulnerable debuff is applied (1.5x damage)
  - Verify monster block is subtracted correctly
  - Verify AOE vs single-target damage distribution

- [ ] **2.5** Test combat edge cases
  - Test with 0 playable cards (should end turn)
  - Test with only unplayable cards (should end turn)
  - Test when lethal is available (should find it)
  - Test when need to block (should survive)

---

## Phase 3: Improve Act 1 Priorities

- [x] **3.1** Analyze current Ironclad priorities
  - Review IroncladPriority.CARD_PRIORITY_LIST
  - Identify cards that are over/under-prioritized for Act 1
  - Check MAX_COPIES limits for key cards
  - Document which cards need priority adjustments

- [x] **3.2** Update Act 1 card priorities
  - Prioritize early game consistency (Strike, Bash, defend cards)
  - Deprioritize late-game cards without synergy (Demon Form early, etc.)
  - Adjust copy limits for key cards
  - Add special handling for first few floors

- [ ] **3.3** Implement deck composition awareness (SKIPPED - deferred to future improvement)
  - Check current deck size when picking rewards
  - Count copies of key effects (block, attack, strength)
  - Adjust priorities based on what's already in deck
  - Avoid picking redundant effects

- [ ] **3.4** Add synergy detection to reward selection (SKIPPED - already implemented in OptimizedAI)
  - Detect if deck has Strength theme (pump cards)
  - Detect if deck has Block theme (Body Slam, Metallicize)
  - Detect if deck has Shiv theme (if using Silent's cards somehow)
  - Prioritize cards that synergize with detected archetype

- [ ] **3.5** Update combat play priorities (SKIPPED - PLAY_PRIORITY_LIST already well-tuned)
  - Review IroncladPriority.PLAY_PRIORITY_LIST
  - Adjust based on Act 1 needs
  - Prioritize efficient cards (high damage/energy)
  - Deprioritize setup cards without payoff

---

## Phase 4: Add Safety Improvements

- [ ] **4.1** Implement HP-based decision thresholds
  - Add HP% check to DecisionContext
  - Play more conservatively when HP < 50%
  - Play more conservatively when HP < 30%
  - Take calculated risks when HP > 80%

- [ ] **4.2** Add elite encounter awareness
  - Detect elite fights from game state
  - Play more conservatively against elites (save potions, etc.)
  - Assess incoming damage from elite intents
  - Prioritize survival over speed in elite fights

- [ ] **4.3** Improve potion usage
  - Use potions earlier in tough fights (don't hoard until death)
  - Use attack potions on high HP targets
  - Use block potions before big hits
  - Use potion on turn when it provides most value

- [ ] **4.4** Add rest site decision improvements
  - Rest more aggressively when HP < 60%
  - Smith high-impact cards (Bash, key attacks)
  - Lift when good synergy exists
  - Dig when HP is good and deck needs thinning

---

## Phase 5: Testing and Validation

- [ ] **5.1** Run test games
  - Play at least 20 games with improved AI
  - Track win rate, floor reached, HP lost
  - Compare to baseline (before changes)
  - Document specific improvements

- [ ] **5.2** Analyze failure cases
  - Review games where AI still died in Act 1
  - Identify remaining issues
  - Categorize failures (combat, card selection, bad RNG)
  - Create additional tasks if needed

- [ ] **5.3** Performance benchmarking
  - Measure decision time per action
  - Ensure beam search doesn't timeout (<100ms)
  - Check memory usage during games
  - Optimize if performance issues found

- [ ] **5.4** Validate other character classes
  - Test Silent with OptimizedAI
  - Test Defect with OptimizedAI
  - Ensure changes don't break other classes
  - Fix any regressions

---

## Phase 6: Documentation

- [ ] **6.1** Update OPTIMIZED_AI_README.md
  - Document that OptimizedAgent is now default
  - Add Ironclad-specific improvements
  - Include any new configuration options

- [ ] **6.2** Update CLAUDE.md
  - Note the default agent change
  - Document new priority system
  - Add performance expectations

- [ ] **6.3** Create improvement summary
  - Document what was changed
  - Document measured improvements
  - Document known limitations
  - Suggest future improvements

---

## Task Completion Notes

- Mark tasks as `[x]` only when fully complete and tested
- If a task reveals additional work, create new tasks before marking complete
- Document any deviations from this plan in task comments
- Run `openspec validate` after completing each phase to ensure consistency
