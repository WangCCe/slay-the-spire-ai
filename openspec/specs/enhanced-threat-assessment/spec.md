# enhanced-threat-assessment Specification

## Purpose
TBD - created by archiving change add-wiki-monster-data. Update Purpose after archive.
## Requirements
### Requirement: Proactive Threat Calculation

The system SHALL provide a new `compute_threat_v2(monster)` method that calculates threat based on both current state and future predictions. The method SHALL:

1. Check for enhanced monster data first
2. Fall back to existing `compute_threat()` if enhanced data missing
3. Calculate threat from multiple components:
   - Immediate threat (current intent damage)
   - Future threat (predicted next 2-3 moves)
   - Scaling threat (from threat_profile.scaling_threat)
   - Special ability threat (summoning, phase changes, etc.)
   - Composition threat (minions, buffs)

#### Scenario: Cultist scaling threat prediction
- **GIVEN** a Cultist on turn 1 with 44 HP
- **AND** enhanced data: `threat_profile.scaling_threat = 3.0`
- **AND** move_sequence = [0 (Ritual), 1 (Dark Strike), 2 (Incite), 1, 1]
- **AND** estimated turns to death = 4
- **WHEN** calling `compute_threat_v2(cultist)`
- **THEN** threat SHALL be calculated as:
  - Immediate: 6 (Dark Strike damage)
  - Future: 4.8 (predicted Dark Strike damage × 0.8 discount)
  - Scaling: 12.0 (3.0 × 4 turns)
  - Total: ~23 (higher than reactive threat of ~15)

#### Scenario: Fallback to existing threat calculation
- **GIVEN** a monster without enhanced data
- **WHEN** calling `compute_threat_v2(monster)`
- **THEN** the method SHALL call existing `compute_threat(monster)`
- **AND** SHALL return the same result as before
- **AND** SHALL NOT raise an exception

#### Scenario: Lagavulin hibernation state threat
- **GIVEN** a Lagavulin with intent = SLEEP
- **AND** enhanced data: `threat_profile.hibernation_threat = 5`, `awakened_threat = 30`
- **WHEN** calling `compute_threat_v2(lagavulin)`
- **THEN** threat SHALL be 5 (low while sleeping)
- **AND** WHEN intent changes to ATTACK
- **THEN** threat SHALL be 30 (high when awake)

---

### Requirement: Future Move Prediction

The system SHALL predict the next N moves for a monster based on its move_sequence from enhanced data.

**Algorithm:**
1. Get move_sequence from enhanced monster data
2. Find current move_id position in sequence
3. Return next N move_ids from sequence
4. Handle sequence cycling (repeat patterns)
5. Handle missing data (return current move only)

#### Scenario: Predict Cultist moves
- **GIVEN** a Cultist with move_sequence = [0, 1, 2, 1, 1]
- **AND** current move_id = 0 (Ritual)
- **AND** look_ahead = 2
- **WHEN** calling `predict_monster_moves(cultist, 2)`
- **THEN** the function SHALL return moves [1 (Dark Strike), 2 (Incite)]
- **AND** each move SHALL include damage, intent, effect

#### Scenario: Predict moves with cycling
- **GIVEN** a Cultist with move_sequence = [0, 1, 2, 1, 1]
- **AND** current move_id = 2 (Incite, turn 3)
- **AND** look_ahead = 3
- **WHEN** predicting moves
- **THEN** the function SHALL return [1 (Dark Strike), 1 (Dark Strike), 1 (Dark Strike)]
- **AND** SHALL cycle through the repeat pattern [1, 1]

#### Scenario: Predict moves for unknown monster
- **GIVEN** a monster without enhanced data
- **WHEN** calling `predict_monster_moves(monster, 2)`
- **THEN** the function SHALL return [current_move] (single move, no prediction)
- **AND** SHALL NOT raise an exception

#### Scenario: Current move not in sequence
- **GIVEN** a monster with enhanced data
- **AND** current move_id = 99 (not in move_sequence)
- **WHEN** calling `predict_monster_moves(monster, 2)`
- **THEN** the function SHALL log a warning
- **AND** SHALL return [current_move]
- **AND** SHALL NOT crash

---

### Requirement: Scaling Threat Calculation

The system SHALL calculate future scaling threat based on the threat_profile.scaling_threat parameter.

**Formula:**
```
scaling_threat = threat_profile.scaling_threat × estimated_turns_to_death
estimated_turns_to_death = monster.current_hp // estimated_dps_per_turn
estimated_dps_per_turn = 20 (default, or player-specific)
```

#### Scenario: Cultist scaling threat
- **GIVEN** a Cultist with `threat_profile.scaling_threat = 3.0`
- **AND** current_hp = 44
- **AND** estimated_dps_per_turn = 20
- **WHEN** calculating scaling threat
- **THEN** estimated_turns_to_death = 44 // 20 = 2.2 ≈ 2
- **AND** scaling_threat = 3.0 × 2 = 6
- **AND** this SHALL be added to total threat

#### Scenario: Gremlin Nob scaling threat
- **GIVEN** a Gremlin Nob with `threat_profile.scaling_threat = 4.5`
- **AND** current_hp = 82
- **AND** estimated_dps_per_turn = 20
- **WHEN** calculating scaling threat
- **THEN** estimated_turns_to_death = 82 // 20 = 4.1 ≈ 4
- **AND** scaling_threat = 4.5 × 4 = 18
- **AND** Gremlin Nob SHALL be prioritized over lower-scaling monsters

#### Scenario: No scaling threat
- **GIVEN** a monster with `threat_profile.scaling_threat = 0` (or not specified)
- **WHEN** calculating scaling threat
- **THEN** scaling_threat = 0
- **AND** no scaling component SHALL be added to total threat

---

### Requirement: Special Ability Threat

The system SHALL add threat based on special_mechanics type:

- **Summoner**: +20 threat if allowed to summon
- **Death split**: +8 threat per split monster
- **Phase change**: +10 threat during vulnerable phases
- **Hibernation**: Use hibernation_threat (5) or awakened_threat (30) based on state

#### Scenario: Summoner threat
- **GIVEN** a Reptomancer with `special_mechanics.type = "summoner"`
- **AND** `threat_profile.summon_threat = 20`
- **AND** summons = [{"turn": 1, "count": 2}]
- **WHEN** calculating threat
- **THEN** threat SHALL include +20 for summoning
- **AND** threat SHALL include +20 for minions (2 × 10)
- **AND** total special ability threat = 40

#### Scenario: Death split threat
- **GIVEN** a Slime Boss with `special_mechanics.type = "death_split"`
- **AND** splits = [{"splits_into": [{"count": 2}]}]
- **WHEN** calculating threat
- **THEN** threat SHALL include +16 for death split (2 splits × 8)
- **AND** this SHALL encourage AOE attacks

#### Scenario: Phase change burst window
- **GIVEN** a Hexaghost with `special_mechanics.type = "phase_change"`
- **AND** current HP ratio = 0.55 (just crossed 60% threshold)
- **AND** next phase has vulnerable moves
- **WHEN** calculating threat
- **THEN** threat SHALL include +10 for burst window opportunity
- **AND** the AI SHALL prioritize high-damage attacks

#### Scenario: Hibernation state threat
- **GIVEN** a Lagavulin with intent = SLEEP
- **AND** `threat_profile.hibernation_threat = 5`
- **WHEN** calculating threat
- **THEN** special ability threat SHALL use hibernation_threat = 5
- **AND** WHEN intent changes to ATTACK
- **THEN** special ability threat SHALL use awakened_threat = 30

---

### Requirement: Future Damage Discount

When calculating future threat from predicted moves, the system SHALL apply a discount factor to account for uncertainty.

**Discount factors:**
- Next turn: 1.0 (no discount)
- 2 turns ahead: 0.8
- 3 turns ahead: 0.6
- 4+ turns ahead: 0.5

#### Scenario: Future damage discount
- **GIVEN** a monster with predicted moves: [12 dmg (turn 2), 15 dmg (turn 3), 10 dmg (turn 4)]
- **WHEN** calculating future threat
- **THEN** threat SHALL be:
  - Turn 2: 12 × 0.8 = 9.6
  - Turn 3: 15 × 0.6 = 9.0
  - Turn 4: 10 × 0.5 = 5.0
  - Total future: 23.6

#### Scenario: Immediate damage no discount
- **GIVEN** a monster with current intent dealing 10 damage
- **AND** predicted next move dealing 12 damage
- **WHEN** calculating threat
- **THEN** immediate threat: 10 × 1.0 = 10
- **AND** future threat: 12 × 0.8 = 9.6
- **AND** total: 19.6

---

### Requirement: Threat Calculation Logging

The system SHALL log threat calculation breakdown at DEBUG level for monitoring and debugging.

**Log format:**
```
[THREAT] {monster_id}: {total_threat} = immediate:{imm} + future:{fut} + scaling:{scl} + special:{spc}
```

#### Scenario: Threat calculation logging
- **GIVEN** logging level = DEBUG
- **AND** a Cultist on turn 1
- **WHEN** calling `compute_threat_v2(cultist)`
- **THEN** the system SHALL log: "[THREAT] Cultist: 22.8 = immediate:6 + future:4.8 + scaling:12 + special:0"
- **AND** the log SHALL help diagnose threat scoring decisions

#### Scenario: Logging disabled at INFO level
- **GIVEN** logging level = INFO (not DEBUG)
- **WHEN** calling `compute_threat_v2(monster)`
- **THEN** the system SHALL NOT log threat breakdown
- **AND** performance SHALL NOT be impacted by logging

---

### Requirement: Performance Constraints

The enhanced threat calculation SHALL meet performance targets:

- **Per-monster calculation**: < 5ms (95th percentile)
- **Cache enhanced data lookups**: Access enhanced_data dict once, not multiple times
- **Early fallback**: Skip prediction if enhanced data missing

#### Scenario: Performance target met
- **GIVEN** 100 monsters with enhanced data
- **WHEN** timing `compute_threat_v2()` calls
- **THEN** 95th percentile execution time SHALL be < 5ms
- **AND** SHALL NOT impact beam search performance

#### Scenario: Performance optimization
- **GIVEN** `compute_threat_v2()` taking 8ms per monster (> 5ms target)
- **WHEN** profiling reveals multiple dict lookups
- **THEN** optimize by caching enhanced_data lookup:
```python
# Before (multiple lookups)
threat = enhanced_data['threat_profile']['base_threat']
scaling = enhanced_data['threat_profile']['scaling_threat']

# After (single lookup)
threat_profile = enhanced_data.get('threat_profile', {})
threat = threat_profile.get('base_threat', 0)
scaling = threat_profile.get('scaling_threat', 0)
```

#### Scenario: Fallback performance
- **GIVEN** a monster without enhanced data
- **WHEN** calling `compute_threat_v2(monster)`
- **THEN** fallback to `compute_threat()` SHALL be fast (< 2ms)
- **AND** SHALL NOT significantly impact overall performance

---

### Requirement: Backward Compatibility

The existing `compute_threat()` method SHALL remain unchanged and continue to work as before. The new `compute_threat_v2()` method SHALL be opt-in for callers that want enhanced threat calculation.

#### Scenario: Existing code unchanged
- **GIVEN** existing code calling `compute_threat(monster)`
- **WHEN** the code is run
- **THEN** it SHALL continue to work exactly as before
- **AND** SHALL NOT require any modifications

#### Scenario: Opt-in to enhanced threat
- **GIVEN** new code wanting enhanced threat calculation
- **WHEN** calling `compute_threat_v2(monster)`
- **THEN** it SHALL get predictive threat when enhanced data available
- **AND** SHALL fallback to reactive threat when enhanced data missing

#### Scenario: Gradual migration
- **GIVEN** the codebase with both methods available
- **WHEN** migrating callers to `compute_threat_v2()`
- **THEN** migration CAN be gradual (one caller at a time)
- **AND** old code CAN continue using `compute_threat()`
- **AND** new code CAN use `compute_threat_v2()`

---

