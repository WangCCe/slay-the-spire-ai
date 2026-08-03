## ADDED Requirements

### Requirement: Immutable V1 Lineage And Versioned R2 Profile
The diagnostic SHALL preserve the consumed v1 registration, zero-row failure,
closeout, journal, manifest, and canonical artifacts byte-for-byte while using
one explicit immutable profile boundary for any separately registered r2
identity. The r2 profile MUST change only publication identity and lineage; it
MUST preserve v1 cohort, policy, support, transition, row, and verdict semantics.

#### Scenario: Historical v1 artifacts are verified after profile extraction
- **WHEN** the no-native verifier selects the v1 profile and reads the committed
  v1 registration and canonical output directory
- **THEN** it SHALL recompute every v1 artifact and the failed verdict
  byte-for-byte
- **AND** it SHALL NOT validate v1 as a reusable source-bound execution identity

#### Scenario: R2 profile is internally consistent
- **WHEN** an r2 registration uses the exact r2 schemas, paths,
  preimplementation lineage, implementation sources, cohort, limits, and
  all-false authority
- **THEN** every registration, result, journal, publication, and verification
  helper SHALL use only the r2 profile
- **AND** v1 evidence SHALL remain unchanged

#### Scenario: Profile identities are mixed or unsupported
- **WHEN** a registration, schema, path, preimplementation record, output root,
  or artifact from one profile is supplied to another profile, or an unknown
  profile is requested
- **THEN** the diagnostic SHALL fail before environment construction
- **AND** it SHALL publish no structural result

### Requirement: R2 Binds The Consumed Failure And Independent Fix
The r2 preregistration SHALL bind a canonical tracked lineage record containing
the exact consumed v1 identity and failure boundary, anti-retry eligibility
decision, completed candidate-schema fix, current implementation sources,
predecessor evidence, native module, adapter and simulator provenance,
metadata, runtime, unchanged seed rationale, and all-false authority.

#### Scenario: Complete r2 lineage is validated
- **WHEN** every bound repository and external file matches its registered path,
  byte size, SHA-256, expected Git identity, and semantic value
- **THEN** r2 preparation MAY publish a canonical registration
- **AND** it SHALL construct no native environment or access a seed

#### Scenario: Consumed evidence or fix lineage drifts
- **WHEN** any v1 artifact, closeout, failure coordinate, anti-retry decision,
  source-fix archive, implementation byte, module, provenance, metadata,
  runtime, or authority field differs
- **THEN** r2 preparation and execution SHALL fail before environment
  construction
- **AND** neither v1 nor r2 evidence SHALL be rewritten

### Requirement: Exactly One Pushed R2 Successor Attempt
The diagnostic SHALL permit at most one r2 execution from a clean pushed
registration with an absent r2 output root. It MUST use exactly ordered seeds
`7000`, `7100`, `2000`, and `10`, two replays per seed, 500 target decisions per
replay, a 600-second whole-run deadline, and the existing declared Courier
support boundary, without runtime overrides or replacement.

#### Scenario: R2 execution reaches the native boundary
- **WHEN** the r2 registration and every offline gate pass, local `HEAD` equals
  the pushed registration commit, the output root is absent, and the started
  journal is durable
- **THEN** the runner MAY construct the first environment and execute the fixed
  cohort once
- **AND** the existing deterministic row and verdict requirements SHALL apply
  unchanged

#### Scenario: R2 completes with a structural pass
- **WHEN** all fixed rows satisfy the existing pass requirements and canonical
  no-native recomputation matches every artifact
- **THEN** r2 SHALL establish only a completed Current own-trajectory structural
  row and permit a separate read-only baseline-floor readiness refresh
- **AND** every baseline-floor, fresh-evidence, outcome, gameplay, OPE, model,
  reward, formal-RL, training, qualification, loading, and promotion authority
  SHALL remain false

#### Scenario: R2 fails, blocks, or is interrupted
- **WHEN** r2 publishes a failure or support-limited result, leaves a started or
  partial journal, exceeds a bound, or cannot be recomputed exactly
- **THEN** the r2 identity SHALL be terminal and non-retryable
- **AND** this change SHALL NOT repair r2, change controls, or prepare r3

### Requirement: Offline Gates Precede R2 Preregistration
Before publishing an r2 registration, the implementation SHALL prove exact v1
historical recomputation, production-shaped candidate handling through the
complete pre-step boundary, evaluator action-metadata rejection before
`step()`, profile isolation, r2 lineage validation, focused regression success,
partitioned commit-gate success, strict OpenSpec validity, and exact consumed
evidence byte identity without native loading or environment construction.

#### Scenario: Every offline gate passes
- **WHEN** the implementation and its complete registered test inputs are clean,
  committed, pushed, and all required checks reproduce
- **THEN** one later commit MAY publish the r2 registration
- **AND** native execution SHALL remain blocked until that registration commit
  is independently validated and pushed

#### Scenario: An offline gate fails
- **WHEN** historical recomputation, profile isolation, production candidate
  coverage, lineage, tests, source identity, strict validation, or byte identity
  fails
- **THEN** no r2 registration or output root SHALL be created
- **AND** the lane SHALL stop without native loading, seed access, gameplay, or
  training
