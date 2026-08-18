## ADDED Requirements

### Requirement: Frozen parent-action constrained warm-start training
The system SHALL optionally add the existing masked parent-policy cross-entropy objective to simulator-only warm-start training while leaving its weight zero by default.

#### Scenario: Zero-weight compatibility
- **WHEN** parent-policy anchor weight is `0.0`
- **THEN** fresh and warm-start training preserve their existing initialization, optimization, evaluation, and checkpoint behavior without creating an anchor network

#### Scenario: Positive-weight initialization
- **WHEN** a finite positive parent-policy anchor weight and a valid simulator-only warm-start checkpoint are supplied
- **THEN** the runner freezes the exact loaded parent state as the trainer anchor before replay optimization and uses the same state for held-out control evaluation

#### Scenario: Positive weight without parent
- **WHEN** a positive parent-policy anchor weight is supplied without a valid warm-start checkpoint
- **THEN** the runner fails before transition collection or model fitting

#### Scenario: Constrained optimizer evidence
- **WHEN** positive-weight replay optimization completes
- **THEN** the report records the configured weight, frozen-anchor parameter hash, and separate finite total, TD, and positive anchor loss summaries

#### Scenario: Constrained successor checkpoint
- **WHEN** a constrained simulator candidate is saved
- **THEN** its source binding includes the parent checkpoint hash, parent parameter hash, and configured anchor weight while retaining false production compatibility and promotion authority
