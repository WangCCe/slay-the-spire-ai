## ADDED Requirements
### Requirement: RL reward shaping for combat and progression
The system SHALL calculate combat rewards using effective damage (no overkill) and target-level debuff context, and SHALL align combat-win vs run-victory signals.

#### Scenario: Effective damage without overkill
- **GIVEN** a monster at 5 HP and a 12-damage action is taken
- **WHEN** calculating combat reward
- **THEN** damage reward SHALL be computed from 5 damage (no overkill)

#### Scenario: Vulnerable bonus applies only to vulnerable targets
- **GIVEN** two monsters where only one has Vulnerable
- **WHEN** damage is dealt to the non-vulnerable target
- **THEN** the vulnerable bonus SHALL NOT be applied

#### Scenario: Combat win vs run victory
- **GIVEN** combat ends and the game transitions to COMBAT_REWARD
- **WHEN** calculating rewards
- **THEN** the combat-win bonus SHALL be applied
- **AND** the run-victory bonus SHALL NOT be applied

### Requirement: Diminishing kill rewards per combat
The system SHALL apply a diminishing kill reward per combat using the formula base / (1 + kill_index), where kill_index starts at 0 for the first kill in the combat.

#### Scenario: Diminishing reward for second kill
- **GIVEN** base kill reward of 10
- **WHEN** the second monster in the same combat is killed (kill_index=1)
- **THEN** the kill reward SHALL be 5

### Requirement: Relaxed per-turn penalty
The system SHALL apply a per-turn penalty of -0.05 during combat and SHALL NOT apply any additional end-turn penalty beyond this per-turn penalty.

#### Scenario: End turn penalty
- **GIVEN** the player ends their turn with available actions
- **WHEN** calculating combat rewards for the turn
- **THEN** the total turn penalty SHALL be -0.05

### Requirement: Enemy strength gain penalty without cap
The system SHALL apply an enemy strength gain penalty equal to -1.0 times total strength gained in the step, with no cap.

#### Scenario: Strength gain penalty applies in full
- **GIVEN** enemies gain a total of 4 Strength in a step
- **WHEN** calculating rewards
- **THEN** the penalty SHALL be -4.0
