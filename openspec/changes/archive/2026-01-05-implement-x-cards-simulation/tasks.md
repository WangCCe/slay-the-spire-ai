# implement-x-cards-simulation Tasks

## Phase 1: Add X-Card Helper Methods

### 1.1 Create _calculate_x_damage() method
- [x] Add method in simulation.py to calculate X-damage for special cards
- [x] Implement Body Slam: `damage = state.player_block`
- [x] Implement Bludgeon: `damage = min(30, 12 + state.player_block // 10)`
- [x] Implement Whirlwind: `damage = context.energy_available`
- [x] Return 0 for unrecognized cards (fallback)
- [x] Add docstring with examples

**Validation**: Method returns correct damage for each X-card

### 1.2 Create _calculate_x_block() method
- [x] Add method in simulation.py to calculate X-block for special cards
- [x] Implement Rage: `block = context.max_energy` (total energy, not available)
- [x] Return 0 for unrecognized cards (fallback)
- [x] Add docstring with examples

**Validation**: Method returns correct block for Rage

---

## Phase 2: Integrate into Attack Simulation

### 2.1 Update _apply_attack() to use X-calculation
- [x] Detect when base_damage == 0 and card might be X-damage
- [x] Call `_calculate_x_damage()` for X-damage cards
- [x] Use calculated value in damage formula
- [x] Ensure Strength/Dex bonuses apply correctly
- [x] Test with Body Slam (should use player_block)

**Validation**: Body Slam deals damage equal to player block

### 2.2 Handle AOE X-cards (Whirlwind)
- [x] Ensure Whirlwind's base_damage = energy_available
- [x] Verify AOE logic applies this damage to each monster
- [x] Check that total damage = energy × num_monsters
- [x] Test with 2-4 monsters

**Validation**: Whirlwind deals energy damage to each enemy

### 2.3 Handle Bludgeon edge case
- [x] Implement Bludgeon scaling: `min(30, 12 + block // 10)`
- [x] Test with 0 block (should be 12)
- [x] Test with 50 block (should be 17)
- [x] Test with 200 block (should be 30, capped)

**Validation**: Bludgeon damage scales correctly with block

---

## Phase 3: Integrate into Skill Simulation

### 3.1 Update _apply_skill() to use X-calculation
- [x] Detect when block gain might be X-block
- [x] Call `_calculate_x_block()` for X-block cards
- [x] Apply calculated block to SimulationState
- [x] Test with Rage (should gain max_energy block)

**Validation**: Rage gains block equal to max energy

### 3.2 Handle Frail/Weak on X-cards
- [x] Ensure Body Slam damage affected by Weak
- [x] Ensure Rage block affected by Frail
- [x] Test with debuffs active

**Validation**: Debuffs apply to X-card values

---

## Phase 4: Update Beam Search Scoring

### 4.1 Update FastScore for X-cards
- [x] Modify `_fast_score_card()` to detect X-cards
- [x] Call `_calculate_x_damage()` / `_calculate_x_block()` for X-cards
- [x] Use calculated values in score formula
- [x] Ensure X-cards score higher when conditions favorable

**Validation**: Body Slam gets high score when player has high block

### 4.2 Update FullSim for X-cards
- [x] Ensure full simulation uses X-calculation
- [x] Verify beam search explores X-card sequences
- [x] Test Body Slam in beam search (should prioritize after block-building)

**Validation**: Beam search includes Body Slam in optimal sequences

---

## Phase 5: Testing & Validation

### 5.1 Unit tests for _calculate_x_damage()
- [x] Test Body Slam with 0 block → 0 damage
- [x] Test Body Slam with 20 block → 20 damage
- [x] Test Body Slam with 50 block → 50 damage
- [x] Test Bludgeon with 0 block → 12 damage
- [x] Test Bludgeon with 50 block → 17 damage
- [x] Test Bludgeon with 200 block → 30 damage (capped)
- [x] Test Whirlwind with 3 energy → 3 damage

**Validation**: All unit tests pass

### 5.2 Unit tests for _calculate_x_block()
- [x] Test Rage with max_energy=2 → 2 block
- [x] Test Rage with max_energy=3 → 3 block
- [x] Test Rage with max_energy=1 → 1 block

**Validation**: All unit tests pass

### 5.3 Integration test with combat simulation
- [x] Run simulation with Body Slam in deck
- [x] Verify damage equals player_block
- [x] Run simulation with Rage in deck
- [x] Verify block gain equals max_energy
- [x] Run simulation with Whirlwind in deck
- [x] Verify total damage equals energy × monsters

**Validation**: Combat simulation uses X-card values correctly

### 5.4 Beam search integration test
- [x] Create scenario: Player has 20 block, hand has Body Slam
- [x] Run beam search
- [x] Verify Body Slam is high in action ranking
- [x] Create scenario: 3 enemies, 3 energy, Whirlwind in hand
- [x] Verify Whirlwind prioritized (9 total damage)

**Validation**: Beam search correctly evaluates X-cards

### 5.5 Edge case testing
- [x] Test X-cards with 0 state (0 block, 0 energy)
- [x] Test X-cards with extreme values (100 block, etc.)
- [x] Test X-cards with debuffs (Weak, Frail)
- [x] Test upgraded versions (Body Slam+, Rage+)

**Validation**: No crashes, reasonable behavior in all cases

---

## Phase 6: Documentation

### 6.1 Update CLAUDE.md
- [x] Document X-card calculation behavior
- [x] Add examples (Body Slam, Rage, Whirlwind)
- [x] Explain where calculations happen
- [x] Note limitations (only Ironclad cards initially)

**Validation**: CLAUDE.md explains X-card system

### 6.2 Add code comments
- [x] Comment X-card logic in _calculate_x_damage()
- [x] Comment X-card logic in _calculate_x_block()
- [x] Document formulas (e.g., Bludgeon scaling)
- [x] Note where to add new X-cards

**Validation**: Code is well-documented

---

## Dependencies & Ordering

**Critical Path**:
1. Phase 1 (add helpers) → Phase 2 (integrate attacks) → Phase 3 (integrate skills) → Phase 4 (update scoring) → Phase 5 (test) → Phase 6 (document)

**Parallelizable**:
- Phase 2.2 and 2.3 can be done in parallel (different X-cards)
- Phase 5.1 and 5.2 can be done in parallel (different test suites)

**Blocking**:
- Phase 2 blocks on Phase 1 (need helper methods first)
- Phase 3 blocks on Phase 1
- Phase 4 blocks on Phase 2 and 3 (need integration complete)
- Phase 5 blocks on Phase 4 (need scoring updates)
- Phase 6 blocks on Phase 5 (document working code)
