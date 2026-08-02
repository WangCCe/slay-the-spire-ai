## ADDED Requirements

### Requirement: Reachable-Surface Successor Isolation
The compatibility system SHALL evaluate the reachable-surface v3 resolver only through new versioned evaluator, registration, ledger, output, and artifact identities while preserving the predecessor `7000..7007` registration, journal, failure, and contract identity unchanged.

#### Scenario: Successor evidence is prepared
- **WHEN** the new evaluator binds its predecessor evidence
- **THEN** the predecessor SHALL be recorded only as consumed negative history and SHALL grant no seed, execution, verdict, or retry authority
- **AND** the successor SHALL use distinct schemas, paths, hashes, and output bytes

#### Scenario: Historical bytes or status drift
- **WHEN** the predecessor registration, journal, manifest, closeout, consumed seeds, or failure identity differs from its bound value
- **THEN** successor registration and execution SHALL stop before native environment construction
- **AND** no historical artifact SHALL be rewritten or upgraded

### Requirement: Exhaustive Successor Seed Isolation
Before naming the successor cohort, the system SHALL inventory every seed-bearing path in tracked repository registrations and seed ledgers and SHALL conservatively exclude every consumed, selected, reserved, training, validation, compatibility, smoke, qualification, final-test, or ambiguously classified seed.

#### Scenario: Seed inventory is complete
- **WHEN** the inventory is generated from the pushed implementation and tracked repository files
- **THEN** every retained row SHALL name the source path, JSON path, integer seed, and role or conservative exclusion reason
- **AND** canonical recomputation SHALL reject a changed source set, missing declaration, duplicate conflict, or byte drift

#### Scenario: The fixed successor cohort is registered
- **WHEN** exactly eight sorted candidate seeds are absent from every excluded inventory row
- **THEN** the seed ledger and registration SHALL bind those exact seeds, two replays per seed, at most 500 target decisions per replay, and a 120-second whole-run bound
- **AND** no caller SHALL override membership, order, replay count, decision limit, wall-time limit, or ascension

#### Scenario: A candidate seed is declared or ambiguous
- **WHEN** a proposed seed appears in any prior seed-bearing path or the inventory cannot prove how a relevant source was parsed
- **THEN** registration SHALL fail before publication
- **AND** the system SHALL NOT accept proximity, naming convention, or lack of observed gameplay as proof of isolation

### Requirement: Pushed Reachable-Surface Native Preregistration
The successor registration SHALL hash-bind the pushed evaluator and dependencies, API v3 module and build fields, adapter and simulator physical identity, reachable-surface resolver and contract, Current policy and metadata, runtime, exact seed ledger, predecessor evidence, output contract, and all-false authority before any native seed is read.

#### Scenario: Build-only identity is collected
- **WHEN** the evaluator implementation is committed and pushed and an API v3 module must be identified
- **THEN** the module MAY be built or loaded only for API and build-info discovery
- **AND** no native `Environment` SHALL be constructed, no seed SHALL be passed, and no canonical execution journal or output directory SHALL be created

#### Scenario: First environment is requested
- **WHEN** every registered identity reproduces exactly
- **THEN** the tracked tree SHALL be clean, registration and ledger bytes SHALL equal their blobs at `HEAD`, and `HEAD` SHALL equal `origin/master`
- **AND** any mismatch SHALL stop before journal creation and seed access

### Requirement: One-Shot Reachable-Surface Compatibility Gate
The successor evaluator SHALL consume its whole fixed cohort before constructing the first environment and SHALL classify only exact legal, mutation-free, deterministic, terminal native Current trajectories using the reachable-surface v3 semantic identity.

#### Scenario: Whole-cohort execution starts
- **WHEN** all pre-seed gates pass
- **THEN** the evaluator SHALL atomically persist a started journal naming the complete cohort as consumed before constructing the first environment
- **AND** any later blocker, crash, timeout, interruption, or partial result SHALL forbid retry, replacement seed, limit change, or continuation under the same registration

#### Scenario: An event decision is evaluated
- **WHEN** a registered native trajectory reaches an explicit or generic event target
- **THEN** the bridge SHALL report the reachable v3 semantic source, upstream and Current event ids, event data, Current position, simulator choice index, and selected legal action id
- **AND** predecessor semantics, inline fallback, unsupported identity, ambiguous candidate mapping, or source drift SHALL fail the cohort closed

#### Scenario: The structural gate passes
- **WHEN** both fresh replays for all eight seeds have identical canonical trajectories, only legal mapped actions, no mutation or fallback, valid terminal completion, and aggregate nonzero route, shop, event, and card-reward counts
- **THEN** the verdict SHALL be `reachable_event_native_compatibility_passed`
- **AND** terminal outcomes and floors SHALL remain diagnostics rather than policy-quality or reward evidence

#### Scenario: A structural gate fails
- **WHEN** identity, legality, mapping, determinism, terminal, limit, coverage, mutation, or semantic validation fails
- **THEN** the verdict SHALL preserve the first field-specific blocker as a consumed negative
- **AND** execution SHALL NOT continue to improve category counts or policy outcomes

### Requirement: Successor Canonical Publication Has Structural-Only Authority
The successor SHALL publish a finalized journal and hash-closed canonical artifacts that can be verified without native loading, while gameplay, baseline-floor, target-supported outcome, reward, model, OPE, formal-RL, training, qualification, loading, and promotion authority remain false for pass or failure.

#### Scenario: Execution returns a handled result
- **WHEN** the one-shot cohort passes or fails through a handled blocker
- **THEN** configuration, journal, rows or failure, metrics, report, and manifest SHALL bind every registered and execution identity
- **AND** the no-native verifier SHALL reproduce deterministic artifacts byte-for-byte without importing the module or constructing an environment

#### Scenario: Compatibility passes
- **WHEN** the successor verdict is `reachable_event_native_compatibility_passed`
- **THEN** the project MAY reassess whether to propose a separate non-teacher baseline-floor study
- **AND** it SHALL NOT start gameplay, model fitting, reward selection, formal RL, training, loading, qualification, or promotion

#### Scenario: Execution stops unexpectedly
- **WHEN** a started journal exists without finalized canonical artifacts
- **THEN** the cohort SHALL remain consumed and require read-only failure closeout
- **AND** recovery SHALL NOT load the native module or construct another environment
