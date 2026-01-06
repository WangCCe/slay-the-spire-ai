# combat-simulation-enhancement Specification Delta

## Purpose

Enhance the combat simulation system to predict monster moves and handle special abilities (death splits, summoning, phase changes) for more accurate beam search evaluation.

## ADDED Requirements

### Requirement: Monster Move Prediction

The system SHALL provide `predict_monster_moves(monster, look_ahead=2)` that predicts the next N moves for a monster.

**Prediction algorithm:**
1. Get move_sequence from enhanced monster data
2. Find current move_id position in sequence
3. Return next N move_ids with associated move data
4. Handle missing data, invalid current_id, sequence cycling

#### Scenario: Predict next moves for Cultist
- **GIVEN** Cultist with move_sequence = [0, 1, 2, 1, 1]
- **AND** current_move_id = 0 (Ritual, turn 1)
- **AND** look_ahead = 2
- **AND** moves = [{id:0, name:"Ritual", damage:0}, {id:1, name:"Dark Strike", damage:6}, {id:2, name:"Incite", damage:0}]
- **WHEN** calling `predict_monster_moves(cultist, 2)`
- **THEN** the function SHALL return:
  - [{id:1, name:"Dark Strike", damage:6}, {id:2, name:"Incite", damage:0}]
- **AND** SHALL correctly predict the next 2 turns

#### Scenario: Predict moves with cycling
- **GIVEN** Cultist with move_sequence = [0, 1, 2, 1, 1]
- **AND** current_move_id = 2 (Incite, turn 3)
- **AND** look_ahead = 3
- **WHEN** predicting moves
- **THEN** the function SHALL return:
  - [{id:1, damage:6}, {id:1, damage:6}, {id:1, damage:6}]
- **AND** SHALL cycle through the repeat pattern [1, 1]

#### Scenario: Unknown monster - no prediction
- **GIVEN** a monster without enhanced data
- **WHEN** calling `predict_monster_moves(monster, 2)`
- **THEN** the function SHALL return [current_move]
- **AND** SHALL NOT raise an exception

#### Scenario: Invalid current_move_id
- **GIVEN** a monster with enhanced data
- **AND** current_move_id = 99 (not in move_sequence)
- **WHEN** calling `predict_monster_moves(monster, 2)`
- **THEN** the function SHALL log a warning
- **AND** SHALL return [current_move]

---

### Requirement: Future Monster Damage Calculation

The system SHALL provide `calculate_future_monster_damage(state, context)` that estimates total monster damage over the next 2-3 turns.

**Algorithm:**
1. For each monster, predict next 2-3 moves
2. Sum damage from predicted moves
3. Add Strength scaling to damage
4. Return total expected damage

#### Scenario: Calculate future damage for single monster
- **GIVEN** 1 Cultist with 6 Strength
- **AND** predicted next moves: [Dark Strike (6 dmg), Incite (0 dmg)]
- **WHEN** calling `calculate_future_monster_damage(state, context)`
- **THEN** the function SHALL calculate:
  - Turn 1: 6 + 6(Strength) = 12 damage
  - Turn 2: 0 damage (Incite, no damage)
  - Total: 12 damage

#### Scenario: Calculate future damage for multiple monsters
- **GIVEN** 2 Jaw Worms, each predicting [Attack (7 dmg), Attack (7 dmg)]
- **WHEN** calculating future damage
- **THEN** the function SHALL calculate:
  - Monster 1: 7 + 7 = 14
  - Monster 2: 7 + 7 = 14
  - Total: 28 damage

#### Scenario: Future damage with Weak debuff
- **GIVEN** 1 monster with Weak (2 stacks)
- **AND** predicted move: Attack (12 dmg)
- **WHEN** calculating future damage
- **THEN** the function SHALL apply Weak multiplier (0.75×)
  - Adjusted damage: 12 × 0.75 = 9

---

### Requirement: Enhanced Combat Simulation

The `simulate_card_play()` method SHALL be enhanced to handle special monster abilities:

1. **Death splits**: When monster dies (HP ≤ 0), add split monsters to simulation state
2. **Summoning**: When summon move occurs, add new monsters to simulation state
3. **Phase changes**: When HP threshold crossed, update monster's move_pool

#### Scenario: Death split simulation
- **GIVEN** Slime Boss (140 HP) in simulation state
- **AND** playing attack dealing 150 damage (kills Slime Boss)
- **AND** enhanced data: `special_mechanics.splits = [{"hp_threshold": 0, "splits_into": [{"name": "Acid Slime (M)", "count": 2}]}]`
- **WHEN** calling `simulate_card_play(state, attack_card, slime_boss)`
- **THEN** the function SHALL:
  - Set Slime Boss HP to 0 (dead)
  - Add 2 "Acid Slime (M)" monsters to state.monsters
  - Each with HP from enhanced data (e.g., 28 HP each)
- **AND** subsequent beam search candidates SHALL account for 2 additional monsters

#### Scenario: Summoning simulation
- **GIVEN** Reptomancer in simulation state
- **AND** Reptomancer uses move_id 0 (Summon)
- **AND** enhanced data: `moves[0].summon = {"name": "Dagger", "count": 2}`
- **WHEN** simulating Reptomancer's turn
- **THEN** the function SHALL add 2 "Dagger" monsters to state.monsters
- **AND** each Dagger SHALL have HP from enhanced data (e.g., 12 HP)
- **AND** subsequent calculations SHALL account for 2 additional damage sources

#### Scenario: Phase change simulation
- **GIVEN** Hexaghost (150/250 HP, 60% HP) in simulation state
- **AND** playing attack dealing 40 damage
- **AND** enhanced data: `special_mechanics.phases = [{"hp_threshold": 0.6, "move_pool": [4, 5, 6]}]`
- **WHEN** simulating the attack
- **THEN** HP drops to 110/250 (44%)
- **AND** 44% < 60% threshold, so phase change triggers
- **AND** the function SHALL update monster's move_pool to [4, 5, 6]
- **AND** future move predictions SHALL use new move_pool

#### Scenario: No enhanced data - simulate normally
- **GIVEN** a monster without enhanced data
- **WHEN** simulating card play
- **THEN** the function SHALL simulate normally (no special ability handling)
- **AND** SHALL NOT add split monsters, summoned monsters, or change move_pools

---

### Requirement: Future Damage in Beam Search Scoring

The beam search scoring function SHALL incorporate future monster damage estimates.

**Integration:**
```python
def _score_sequence(state, context):
    # ... existing scoring ...

    # NEW: Include future damage
    future_damage = calculate_future_monster_damage(new_state, context)
    score -= future_damage * W_DEATHRISK * 0.5  # Discount future damage
```

#### Scenario: Beam search avoids over-blocking
- **GIVEN** current incoming damage: 20
- **AND** predicted future damage (next turn): 8
- **AND** W_DEATHRISK = 10.0
- **WHEN** scoring a sequence with 12 block
- **THEN** the function SHALL calculate:
  - Current HP loss: max(0, 20 - 12) = 8
  - Future damage penalty: 8 × 10.0 × 0.5 = 40
  - Total penalty: (8 × 10.0) + 40 = 120
- **AND** SHALL prefer sequences that kill high-damage monsters early

#### Scenario: Killing high-damage monster prioritized
- **GIVEN** Monster A (18 damage next turn, 15 HP) and Monster B (6 damage next turn, 40 HP)
- **AND** playing attack for 15 damage
- **WHEN** scoring two sequences:
  - Sequence 1: Kill Monster A (15 damage) - Future damage: 6
  - Sequence 2: Damage Monster B (15 damage) - Future damage: 24
- **THEN** Sequence 1 SHALL score higher (lower future damage penalty)

---

### Requirement: Simulation Performance Constraints

Enhanced combat simulation SHALL maintain performance targets:

- **Move prediction**: < 1ms per monster (95th percentile)
- **Enhanced simulation**: Total beam search still < 100ms (95th percentile)
- **Adaptive complexity**: Use simpler simulation for simple fights

#### Scenario: Performance target met
- **GIVEN** 4 monsters in combat
- **AND** beam search with 100 candidates
- **WHEN** timing enhanced simulation
- **THEN** 95th percentile beam search time SHALL be < 100ms

#### Scenario: Adaptive complexity
- **GIVEN** simple fight: 2 normal monsters, no special mechanics
- **WHEN** running beam search
- **THEN** the system MAY skip move prediction (use current intent only)
- **AND** MAY skip special ability simulation
- **AND** performance SHALL improve (< 50ms typical)

#### Scenario: Complex fight - full simulation
- **GIVEN** complex fight: 1 elite + 2 monsters, with special mechanics
- **WHEN** running beam search
- **THEN** the system SHALL use full enhanced simulation
- **AND** SHALL predict moves, handle special abilities
- **AND** performance SHALL still be < 100ms

---

## Cross-References

This specification extends:
- **ai-combat** - Enhances beam search simulation with move prediction and special abilities

This specification depends on:
- **monster-data-loading** - Requires move_sequence, moves, special_mechanics data
- **enhanced-threat-assessment** - Uses predict_monster_moves() for future threat calculation

This specification enables:
- **intelligent-targeting** - Provides accurate monster state predictions for targeting decisions
