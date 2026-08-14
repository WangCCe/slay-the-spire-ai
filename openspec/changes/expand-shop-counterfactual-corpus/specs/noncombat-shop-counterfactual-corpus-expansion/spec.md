## ADDED Requirements

### Requirement: Fixed Independent Shop Expansion Cohort
The system SHALL collect exactly 384 complete supported shop source states from the fixed `95556..96323` seed schedule and SHALL stop after the source target or fixed resource bound is reached.

#### Scenario: Source target is reached
- **WHEN** 384 supported source states have complete outcomes for every legal shop action
- **THEN** collection SHALL stop without consuming later scheduled seeds
- **AND** every source SHALL retain its exact state tensor, candidate tensors, Current action, candidates, and branch outcomes

#### Scenario: Source target is not reached
- **WHEN** the fixed seed schedule or resource bound ends before 384 complete sources
- **THEN** the run SHALL emit a terminal no-go
- **AND** it SHALL NOT retry, replace seeds, widen limits, or authorize retraining

### Requirement: Historical Independence And Compatibility
The expansion collector MUST bind the four historical shop datasets by byte hash and MUST reject a new source hash that overlaps any of their 112 unique sources or differs from their feature and partition schema.

#### Scenario: Expansion sources are independent
- **WHEN** all new source hashes are unique and absent from the historical corpus
- **THEN** the report SHALL record `112` historical and `384` new unique sources

#### Scenario: Source or schema overlap occurs
- **WHEN** a new source hash already exists or its state/candidate feature boundary differs
- **THEN** execution SHALL fail before publication

### Requirement: Expansion Signal Gate
The system SHALL authorize only a separate retraining proposal when the expansion contains 384 complete sources, at least 192 informative sources, at least four action kinds, 16 matching deterministic replays, and no historical overlap.

#### Scenario: Expansion gate passes
- **WHEN** every support, diversity, replay, identity, and time check passes
- **THEN** the report SHALL mark the combined 496-source support ready for a separate retraining proposal
- **AND** it SHALL NOT claim policy quality, qualification, or promotion

#### Scenario: Expansion gate fails
- **WHEN** any preregistered check fails
- **THEN** Current SHALL remain the rollback and no training or fresh evaluation SHALL run

### Requirement: Source-Only Native Isolation
The collector SHALL use the registered native simulator and frozen Current-policy continuation while keeping gameplay, CommunicationMod, production checkpoint access, model fitting, learned-model loading, training, and protected seed access false.

#### Scenario: Native collection executes
- **WHEN** the expansion run starts
- **THEN** no game or CommunicationMod process SHALL be active before or after execution
- **AND** operation disclosures and artifact identities SHALL be published with the canonical dataset and manifest
