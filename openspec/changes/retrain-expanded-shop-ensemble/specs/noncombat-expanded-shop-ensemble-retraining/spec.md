## ADDED Requirements

### Requirement: Exact Expanded Training Corpus
The system SHALL bind five canonical shop datasets by byte hash and SHALL aggregate exactly 496 compatible, globally unique source states while retaining cohort identity.

#### Scenario: Expanded corpus loads
- **WHEN** the original four datasets and the 384-source expansion match their registered identities
- **THEN** the training corpus SHALL contain exactly 496 unique sources with 1024-wide state and candidate features

#### Scenario: Expanded corpus differs
- **WHEN** any file hash, row count, source identity, feature boundary, or cohort binding differs
- **THEN** retraining SHALL fail before model fitting

### Requirement: Unchanged OOF Retraining Contract
The system MUST reuse five deterministic source folds, model seeds, epochs `8/16/32`, vote quorums `3/4/5`, Current-relative objective, and all existing OOF eligibility checks without widening or replacement.

#### Scenario: OOF configuration is eligible
- **WHEN** one registered configuration improves Current mean regret, is noninferior on maximum regret, corrects at least three decisions, makes at least five overrides, and worsens no more decisions than it corrects
- **THEN** the system SHALL freeze the deterministic best eligible epoch and quorum

#### Scenario: No OOF configuration is eligible
- **WHEN** every registered configuration fails at least one gate
- **THEN** the system SHALL publish a terminal no-go
- **AND** it SHALL NOT load native runtime or access the reserved fresh schedule

### Requirement: One Reserved Fresh Gate
The system SHALL access the reserved `95492..95555` schedule only after OOF selection and source commit, collecting exactly 32 new source states for one frozen evaluation.

#### Scenario: Fresh gate passes
- **WHEN** the gated ensemble improves Current mean regret, remains noninferior on maximum regret, corrects at least one decision, and worsens no more decisions than it corrects
- **THEN** it SHALL be marked ready only for a separate live-shadow proposal

#### Scenario: Fresh gate fails or errors
- **WHEN** any fresh check fails or execution errors after source access
- **THEN** execution SHALL terminate without retry, refit, quorum change, seed replacement, or policy integration

### Requirement: Thin Wrapper Isolation
The wrapper SHALL delegate model and evaluation behavior to the exact-bound cross-validation implementation and SHALL keep gameplay, CommunicationMod, production checkpoint access, formal RL, qualification, and promotion authority false.

#### Scenario: Retraining artifacts publish
- **WHEN** preflight or fresh execution completes
- **THEN** source identity SHALL include the wrapper and delegated implementation
- **AND** artifact hashes and operation disclosures SHALL be verifiable
