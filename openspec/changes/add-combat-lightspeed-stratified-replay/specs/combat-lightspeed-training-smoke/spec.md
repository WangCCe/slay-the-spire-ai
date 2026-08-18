## ADDED Requirements

### Requirement: Optional battle-index stratified replay preparation
The system SHALL optionally prepare the simulator training replay so every configured battle-index stratum has equal transition representation while preserving default unstratified behavior.

#### Scenario: Source transition identity
- **WHEN** a transition is collected from a `(seed, battle_index)` profile
- **THEN** the runner retains the requested battle index as analysis metadata and reports source transition counts by stratum

#### Scenario: Default replay preparation
- **WHEN** battle-index stratification is disabled
- **THEN** every source transition is inserted exactly once, prepared counts equal source counts, and duplicate counts are zero

#### Scenario: Deterministic stratified preparation
- **WHEN** battle-index stratification is enabled and every configured stratum has at least one source transition
- **THEN** the runner retains every source transition once, deterministically repeats rows in smaller strata to the largest source-stratum count, interleaves strata, and binds the preparation seed

#### Scenario: Missing stratum
- **WHEN** a configured battle index has no source transitions in stratified mode
- **THEN** the runner fails before replay insertion or model fitting, identifies the missing stratum, and does not substitute another stratum

#### Scenario: Replay preparation evidence
- **WHEN** a training report is published
- **THEN** it records the preparation mode, source counts, prepared counts, duplicate counts, target count, and total inserted replay rows

#### Scenario: Production isolation
- **WHEN** stratified replay preparation is used
- **THEN** it remains confined to the simulator-only runner and grants no production, live transfer, qualification, or promotion authority
