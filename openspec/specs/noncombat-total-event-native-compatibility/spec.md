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
