# combat-lightspeed-checkpoint-interpolation Specification

## Purpose
TBD - created by archiving change add-combat-lightspeed-conservative-step-screen. Update Purpose after archive.
## Requirements
### Requirement: Bound simulator checkpoint inputs
The system SHALL construct interpolations only from two explicitly hash-bound, structurally compatible, production-incompatible simulator training checkpoints.

#### Scenario: Valid input pair
- **WHEN** both files match their declared hashes, checkpoint kind, production flag, and tensor structure
- **THEN** the utility accepts their online network states as parent and candidate endpoints

#### Scenario: Invalid input pair
- **WHEN** either hash differs or either checkpoint is production-compatible, malformed, or structurally incompatible
- **THEN** the utility fails before creating any candidate output

### Requirement: Deterministic floating-point interpolation
The system SHALL construct each declared alpha state as `parent + alpha * (candidate - parent)` for every floating-point online-network tensor.

#### Scenario: Interior alpha
- **WHEN** a unique finite alpha strictly inside `(0, 1)` is declared
- **THEN** every output tensor equals the deterministic interpolation cast to the parent tensor dtype

#### Scenario: Invalid alpha
- **WHEN** an alpha is duplicated, non-finite, or outside the open interval `(0, 1)`
- **THEN** the utility rejects the complete request before publishing outputs

### Requirement: Simulator-only output provenance
The system SHALL atomically publish every interpolation as a production-incompatible simulator checkpoint with a manifest binding its construction.

#### Scenario: Successful publication
- **WHEN** all interpolated states are constructed and validated
- **THEN** each checkpoint records its alpha, parent and candidate file hashes, endpoint parameter hashes, output parameter hash, source commit, and false production authority

#### Scenario: Frozen comparison consumption
- **WHEN** a generated checkpoint is supplied to the existing frozen LightSTS comparator
- **THEN** it passes the same simulator-only checkpoint validation as an ordinary training-smoke candidate

### Requirement: No selection or live authority
The construction utility SHALL not rank alpha values, fit parameters, access production checkpoints, or authorize gameplay transfer.

#### Scenario: Construction report
- **WHEN** interpolation artifacts are published
- **THEN** the report states that selection requires a separate frozen comparison and that all gameplay, qualification, promotion, and transfer authority remains false

