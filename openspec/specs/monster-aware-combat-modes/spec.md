# monster-aware-combat-modes Specification

## Purpose
TBD - created by archiving change add-wiki-monster-data. Update Purpose after archive.
## Requirements
### Requirement: Monster-Aware Combat Mode Selection

The system SHALL provide `select_combat_mode_with_monster_data(context)` that analyzes monster composition and selects appropriate combat mode.

**Mode selection logic:**
1. Analyze all monsters in combat
2. Detect special mechanics (summoners, phase changes, hibernation)
3. Calculate total scaling threat
4. Select mode based on detected threats

#### Scenario: Summoner detected - AGGRESSIVE mode
- **GIVEN** 1 Cultist (44 HP) with `special_mechanics.type = "summoner"`
- **AND** `threat_profile.scaling_threat = 3.0`
- **WHEN** selecting combat mode
- **THEN** the system SHALL detect has_summoner = True
- **AND** SHALL return CombatMode.AGGRESSIVE
- **AND** log: "AGGRESSIVE: Summoner present - kill before more adds"

#### Scenario: Phase change boss - AGGRESSIVE mode
- **GIVEN** 1 Hexaghost (250 HP) with `special_mechanics.type = "phase_change"`
- **AND** `threat_profile.scaling_threat = 2.0`
- **AND** monster_type = "boss"
- **WHEN** selecting combat mode
- **THEN** the system SHALL detect has_phase_change = True, has_boss = True
- **AND** SHALL return CombatMode.AGGRESSIVE
- **AND** log: "AGGRESSIVE: Phase change boss - burst during windows"

#### Scenario: High scaling threat - AGGRESSIVE mode
- **GIVEN** 2 Cultists, each with `threat_profile.scaling_threat = 3.0`
- **AND** total_scaling_threat = 6.0 (> 5 threshold)
- **WHEN** selecting combat mode
- **THEN** the system SHALL calculate total_scaling_threat = 6.0
- **AND** SHALL return CombatMode.AGGRESSIVE
- **AND** log: "AGGRESSIVE: High scaling threats (6.0) - kill before they scale"

#### Scenario: Elite present - SEMI_AGGRESSIVE mode
- **GIVEN** 1 Lagavulin (87 HP) with monster_type = "elite"
- **AND** `special_mechanics.type = "hibernation"`
- **WHEN** selecting combat mode
- **THEN** the system SHALL detect has_elite = True, has_hibernating = True
- **AND** SHALL return CombatMode.SEMI_AGGRESSIVE
- **AND** log: "SEMI-AGGRESSIVE: Elite present - need good damage but some defense"

#### Scenario: Hibernating monster - SEMI_AGGRESSIVE mode
- **GIVEN** 1 Lagavulin (intent = SLEEP) + 2 Jaw Worms
- **AND** Lagavulin has `special_mechanics.type = "hibernation"`
- **WHEN** selecting combat mode
- **THEN** the system SHALL detect has_hibernating = True
- **AND** SHALL return CombatMode.SEMI_AGGRESSIVE
- **AND** log: "SEMI-AGGRESSIVE: Hibernating monster - aggressive when it wakes"

#### Scenario: Normal monsters - BALANCED mode
- **GIVEN** 3 Jaw Worms with monster_type = "normal"
- **AND** no special mechanics
- **AND** total_scaling_threat = 0
- **WHEN** selecting combat mode
- **THEN** the system SHALL detect no special threats
- **AND** SHALL return CombatMode.BALANCED
- **AND** log: "BALANCED: Normal monster composition"

---

### Requirement: Monster Composition Analysis

The system SHALL analyze the composition of monsters in combat to detect threat patterns.

**Analysis components:**
1. Count total monsters
2. Detect special mechanic types
3. Calculate total scaling threat
4. Identify monster types (normal/elite/boss)

#### Scenario: Multi-monster fight analysis
- **GIVEN** 3 Jaw Worms + 1 Cultist
- **WHEN** analyzing monster composition
- **THEN** the system SHALL detect:
  - total_monsters = 4
  - has_summoner = True (Cultist)
  - total_scaling_threat = 3.0 (from Cultist)
  - monster_types = [3×normal, 1×normal]

#### Scenario: Elite + normal fight analysis
- **GIVEN** 1 Lagavulin (elite) + 2 Fungi Beasts (normal)
- **WHEN** analyzing monster composition
- **THEN** the system SHALL detect:
  - has_elite = True
  - has_hibernating = True (Lagavulin)
  - total_scaling_threat = 1.5 (from Fungi Beasts)
  - has_boss = False

#### Scenario: Boss fight analysis
- **GIVEN** 1 Hexaghost (boss) + 2 Acid Slimes (normal)
- **WHEN** analyzing monster composition
- **THEN** the system SHALL detect:
  - has_boss = True
  - has_phase_change = True (Hexaghost)
  - total_scaling_threat = 2.0 (from Hexaghost)
  - monster_types = [1×boss, 2×normal]

---

### Requirement: Combat Mode Integration

The existing combat mode selection SHALL be replaced with `select_combat_mode_with_monster_data()` in the combat flow.

**Integration points:**
- OptimizedAgent combat decision flow
- Beam search combat planning
- Combat state management

#### Scenario: Integration into OptimizedAgent
- **GIVEN** OptimizedAgent handling combat
- **WHEN** selecting combat mode at start of turn
- **THEN** the agent SHALL call `select_combat_mode_with_monster_data(context)`
- **AND** SHALL use the returned mode for beam search scoring

#### Scenario: Backward compatibility
- **GIVEN** old code using `select_combat_mode()`
- **WHEN** running with enhanced system
- **THEN** old code SHALL continue to work
- **AND** new code CAN use `select_combat_mode_with_monster_data()`
- **AND** both methods SHALL return valid CombatMode values

#### Scenario: Fallback for missing monster data
- **GIVEN** monsters without enhanced data
- **WHEN** calling `select_combat_mode_with_monster_data(context)`
- **THEN** the system SHALL fallback to existing logic (name-based, count-based)
- **AND** SHALL still return a valid CombatMode

---

### Requirement: Combat Mode Logging

The system SHALL log combat mode selection reasoning at INFO level.

**Log format:**
```
[COMBAT_MODE] {MODE}: {reason}
```

#### Scenario: Mode selection logging
- **GIVEN** 1 Cultist in combat
- **WHEN** selecting AGGRESSIVE mode
- **THEN** the system SHALL log: "[COMBAT_MODE] AGGRESSIVE: Summoner present - kill before more adds"

#### Scenario: Mode selection with multiple factors
- **GIVEN** Reptomancer + 2 Daggers
- **WHEN** selecting AGGRESSIVE mode
- **THEN** the system SHALL log: "[COMBAT_MODE] AGGRESSIVE: Summoner present - kill minions before more summoned"

---

