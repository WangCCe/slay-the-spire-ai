## ADDED Requirements

### Requirement: Source-Bound Historical Shop Corpus
The system SHALL load the registered historical shop partitions only when every file matches its expected byte hash, every row has compatible finite state and candidate feature tensors, and all source hashes are globally unique.

#### Scenario: Four compatible cohorts are loaded
- **WHEN** the registered train, development, robust-evaluation, and Current-relative fresh datasets match their bound identities
- **THEN** the system SHALL aggregate exactly 112 unique source rows
- **AND** it SHALL retain each row's cohort identity for reporting and fold construction

#### Scenario: Historical support differs
- **WHEN** a file hash, source hash, feature width, candidate alignment, or expected row count differs
- **THEN** the system SHALL fail before model fitting
- **AND** it SHALL NOT recollect, repair, omit, or replace historical rows

### Requirement: Grouped Out-Of-Fold Ensemble Selection
The system SHALL assign historical rows to five deterministic source-level folds and SHALL select the epoch count and vote quorum using only ensemble predictions made by models that did not fit the predicted row.

#### Scenario: OOF predictions are produced
- **WHEN** cross-validation runs for a registered epoch candidate
- **THEN** every historical source SHALL receive exactly one held-out ensemble prediction
- **AND** no model contributing to that prediction SHALL have trained on that source

#### Scenario: A configuration is selected
- **WHEN** an OOF configuration improves Current mean regret, is noninferior on maximum regret, corrects at least three rows, performs at least five overrides, and worsens no more rows than it corrects
- **THEN** the system SHALL select the eligible configuration with the lowest mean regret using deterministic tie breaks
- **AND** it SHALL freeze the selected epoch and vote quorum before fresh source access

#### Scenario: No configuration is eligible
- **WHEN** every registered OOF configuration fails at least one selection condition
- **THEN** the system SHALL emit a terminal no-go without collecting a fresh cohort

### Requirement: Frozen Multi-Initialization Shop Ensemble
The system SHALL fit five CPU models with distinct registered initialization seeds on the complete historical corpus using the frozen epoch count, and SHALL serialize enough identity and state to reproduce their centered-score ensemble predictions.

#### Scenario: Final ensemble is fit
- **WHEN** OOF selection succeeds
- **THEN** all five models SHALL train on exactly the 112 registered historical sources
- **AND** the serialized ensemble SHALL reproduce identical candidate ordering for the same tensors

### Requirement: One-Shot Fresh Shop Evaluation Gate
The system SHALL evaluate the frozen ensemble and vote-quorum override rule on exactly 32 new source states from a disjoint registered seed schedule, with no model or quorum modification after fresh access begins.

#### Scenario: Fresh gate passes
- **WHEN** the gated ensemble improves Current mean regret, remains noninferior on maximum regret, corrects at least one Current decision, and worsens no more decisions than it corrects
- **THEN** the report SHALL mark the ensemble ready only for a separate live-shadow proposal
- **AND** it SHALL NOT integrate or promote the model

#### Scenario: Fresh gate fails or execution errors
- **WHEN** any fresh metric fails or an error occurs after fresh access begins
- **THEN** the run SHALL terminate without retry, seed replacement, quorum change, model refit, or policy integration

### Requirement: Bounded Authority And Artifacts
The runner SHALL emit configuration, corpus audit, OOF metrics, ensemble state, fresh dataset, final metrics, report, and artifact manifest while keeping gameplay, CommunicationMod, production checkpoint access, formal RL, qualification, and promotion authority false.

#### Scenario: Experiment artifacts are published
- **WHEN** the one-shot run completes
- **THEN** every declared artifact SHALL have a recorded byte size and SHA-256 identity
- **AND** the report SHALL disclose native loading, model fitting, historical access, and fresh evaluation operations separately
