# Non-Combat Total Event Native Compatibility Specification

## Purpose

Define the immutable API v3 native compatibility gate for Current-policy
non-combat trajectories while preserving structural-only evidence authority.

## Requirements

### Requirement: Staged Native Preregistration Boundary
The compatibility system SHALL separate evaluator implementation, build-only native identity collection, pushed preregistration, and seed execution so that no native environment exists before the exact execution contract is committed and available at `origin/master`.

#### Scenario: API v3 module identity is collected before registration
- **WHEN** the verified evaluator implementation has been committed and pushed
- **THEN** the adapter MAY be built out of tree and loaded only for API and build-info identity collection
- **AND** no `Environment` SHALL be constructed and no seed SHALL be read

#### Scenario: Execution is requested
- **WHEN** the evaluator is asked to construct the first native environment
- **THEN** the tracked tree SHALL be clean, the registration bytes SHALL equal the blob at `HEAD`, and `HEAD` SHALL equal `origin/master`
- **AND** any mismatch SHALL stop before journal creation or seed access

### Requirement: Complete Physical Compatibility Identity
The registration SHALL hash-bind every source and runtime surface that can affect the native Current trajectory, including the API v3 module, adapter, simulator physical sources, dependencies, total observation contract, bridge and Current policy code, metadata, runtime, seed ledger, limits, output contract, and all-false authority.

#### Scenario: Bound identity matches
- **WHEN** registration validation and pre-execution discovery reproduce every registered field
- **THEN** compatibility execution MAY proceed to journal creation
- **AND** the validated identity SHALL be copied into canonical configuration and metrics

#### Scenario: Any identity field drifts
- **WHEN** a module hash or size, build field, adapter source, simulator commit, dirty flag, source digest or count, dependency commit, contract identity, implementation source, metadata, runtime, seed ledger, or output field differs
- **THEN** execution SHALL fail before the first environment is constructed
- **AND** no prior compatibility result SHALL be reused

### Requirement: Fixed Isolated One-Shot Cohort
The registration SHALL use exactly seeds `7000..7007`, two replays per seed, at most 500 target decisions per replay, and a 120-second total execution bound, with no caller override.

#### Scenario: Seed isolation is validated
- **WHEN** the registration is prepared or opened for execution
- **THEN** its bound seed ledger SHALL prove the cohort disjoint from every consumed, training, validation, compatibility, and reserved final-test seed named by prior registrations
- **AND** seed order and membership SHALL equal the preregistered sequence exactly

#### Scenario: First environment is about to be constructed
- **WHEN** every pre-seed identity check has passed
- **THEN** the evaluator SHALL atomically persist a journal marking the complete cohort consumed before constructing `Environment(7000, 0)`
- **AND** any later blocker, partial run, timeout, crash, or failure SHALL NOT permit a same-identity retry, replacement seed, or limit change

### Requirement: Deterministic Structural Compatibility Gate
The evaluator SHALL classify API v3 native compatibility only from legal, terminal, mutation-free Current trajectories whose two preregistered replays match exactly and whose aggregate target decisions cover route, shop, event, and card reward.

#### Scenario: One registered seed passes
- **WHEN** both fresh sessions for that seed select only reported candidates, receive matching transitions, avoid fallback and tracker activity, preserve source bytes, and reach a valid terminal outcome within the decision and time limits
- **THEN** their canonical trajectory bytes SHALL be identical
- **AND** the preserved row SHALL record action, policy-input, category, event-observation, terminal, and physical identity diagnostics

#### Scenario: Event decisions are encountered
- **WHEN** a native trajectory reaches an event target decision
- **THEN** Current SHALL hydrate and reverse-map it through the hash-bound total observation contract with explicit Current position and simulator choice index
- **AND** missing, inline-fallback, ambiguous, unsupported, or drifted semantics SHALL fail the cohort closed

#### Scenario: Aggregate gate passes
- **WHEN** all eight seeds pass two-replay equality and terminate and aggregate counts for all four target categories are nonzero
- **THEN** the verdict SHALL be `total_event_native_compatibility_passed`
- **AND** encountered event identities and sparse mappings SHALL be reported without requiring a selected rare event

#### Scenario: Any structural gate fails
- **WHEN** legality, transition identity, determinism, terminal completion, limits, source immutability, fallback exclusion, event observation, or aggregate category coverage fails
- **THEN** the verdict SHALL preserve the first field-specific blocker as a valid consumed negative
- **AND** the evaluator SHALL NOT continue for policy-quality sample size or tune around the result

### Requirement: Canonical Publication And No-Native Verification
The system SHALL publish an operational journal plus hash-closed canonical configuration, rows or failure, metrics, report, and manifest, and SHALL verify deterministic artifacts without constructing another native environment.

#### Scenario: Execution returns normally
- **WHEN** the one-shot cohort passes or fails through a handled blocker
- **THEN** the journal SHALL be finalized and every published artifact SHALL be bound by path, size, and SHA-256
- **AND** a separate verifier SHALL recompute deterministic artifacts from the registration and preserved rows without loading the module

#### Scenario: Execution process stops unexpectedly
- **WHEN** a started journal exists without a finalized canonical result
- **THEN** the registration SHALL remain consumed and require read-only failure closeout
- **AND** recovery SHALL NOT construct another environment for any registered seed

### Requirement: Structural-Only Evidence Authority
The native compatibility result SHALL keep gameplay, baseline-floor, target-supported outcome, reward, model, OPE, formal-RL, training, qualification, loading, and promotion authority false regardless of terminal floors or victories observed.

#### Scenario: Compatibility passes
- **WHEN** the verdict is `total_event_native_compatibility_passed`
- **THEN** the project MAY consider a separately preregistered non-teacher baseline-floor study
- **AND** it SHALL NOT treat this cohort as a baseline comparison or training go

#### Scenario: Compatibility fails or remains partial
- **WHEN** the verdict is negative or only a started journal survives
- **THEN** the exact structural blocker SHALL remain the active bridge boundary
- **AND** the cohort SHALL NOT be expanded, retried, or reinterpreted as policy evidence

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
