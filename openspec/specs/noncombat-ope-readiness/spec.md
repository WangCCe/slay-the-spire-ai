# noncombat-ope-readiness Specification

## Purpose
Define the offline trajectory, target-policy, overlap, and audit contracts that must pass before non-combat OPE, formal RL training, or live policy promotion can be considered.

## Requirements

### Requirement: Complete Trajectory Audit Unit
The system SHALL treat one complete AI run trajectory, not one decision row, as the independent OPE-readiness audit unit.

#### Scenario: Consistent run rows form one trajectory
- **WHEN** confirmed known-propensity samples share one stable trajectory group and exactly one matched AI run outcome
- **THEN** the audit SHALL order their decisions deterministically and emit one trajectory record with one terminal outcome
- **AND** it SHALL report decision support separately from independent trajectory support

#### Scenario: Conflicting or incomplete outcome blocks trajectory
- **WHEN** rows in a trajectory have missing, ambiguous, floor-inconsistent, mixed, or conflicting run outcomes or provenance
- **THEN** the audit SHALL list the trajectory and exact blocking reasons
- **AND** it SHALL NOT count any row from that trajectory as an independent outcome observation

### Requirement: Versioned Terminal Outcome Contract
The system SHALL use a versioned terminal-run outcome contract with primary victory and secondary floor-reached channels without blending them into an RL reward.

#### Scenario: Complete outcome satisfies the contract
- **WHEN** one audited trajectory has an exact boolean victory, positive integer floor reached, non-negative integer playtime, stable run file, and matched included outcome
- **THEN** the audit SHALL preserve those fields once at trajectory level
- **AND** it SHALL evaluate victory and floor-reached variation separately

#### Scenario: Degenerate victory blocks candidate OPE readiness
- **WHEN** all complete audited trajectories have the same victory value
- **THEN** the report SHALL include `primary_outcome_degenerate`
- **AND** floor-reached variation SHALL remain diagnostic and SHALL NOT replace victory as reward truth

### Requirement: Exact Target Policy Manifest
The system SHALL require a versioned, source-hash-bound target-policy distribution for every audited decision before evaluating candidate-policy overlap.

#### Scenario: Exact target distribution is accepted
- **WHEN** a target entry binds the sample id, state hash, logged distribution hash, and non-negative rational probabilities over exactly the logged executable action ids that sum exactly to one
- **THEN** the audit SHALL accept the entry and preserve its target-policy provenance

#### Scenario: Labels or unsupported mass are rejected
- **WHEN** input supplies only a Current, Bottled, or model label, omits a decision, duplicates an action, changes logged support, assigns probability outside support, or fails exact normalization
- **THEN** target-policy readiness SHALL be false with explicit row-level reasons
- **AND** the audit SHALL NOT infer missing probabilities

#### Scenario: Built-in diagnostic targets remain explicit
- **WHEN** the developer requests behavior-identity or deterministic-Current diagnostics
- **THEN** the system SHALL materialize the same versioned target manifest with source hashes and exact distributions
- **AND** behavior identity SHALL be marked diagnostic-only rather than a candidate policy

### Requirement: Exact Trajectory Weight Reconstruction
The system SHALL reconstruct exact decision ratios and full-trajectory importance weights without clipping, capping, or treating decisions as independent outcomes.

#### Scenario: Supported selected actions produce exact weights
- **WHEN** every selected action has positive verified behavior probability and a valid target probability
- **THEN** the system SHALL compute each target-to-behavior ratio and their trajectory product as exact rational values
- **AND** it SHALL report finite display values without replacing the exact values

#### Scenario: Zero target probability preserves zero support
- **WHEN** the target policy assigns zero probability to any selected action in a trajectory
- **THEN** that trajectory's importance weight SHALL be exactly zero
- **AND** the system SHALL retain it in zero-weight and effective-support diagnostics rather than dropping or smoothing it

### Requirement: Overlap And Effective-Sample-Size Screens
The system SHALL report deterministic trajectory-level overlap diagnostics and SHALL apply conservative minimum screens without treating them as estimator validation.

#### Scenario: Overlap diagnostics are complete
- **WHEN** trajectory weights are reconstructed
- **THEN** the report SHALL include complete trajectory and decision counts, nonzero and zero-weight counts, weight sum, effective sample size, ESS fraction, maximum normalized weight, category-arm support, and outcome variation

#### Scenario: Minimum overlap screens are enforced
- **WHEN** there are fewer than 100 complete trajectories, fewer than 50 nonzero-weight trajectories, ESS below 50, ESS fraction below 0.5, maximum normalized weight above 0.1, or degenerate primary victory
- **THEN** overlap readiness SHALL be false
- **AND** the report SHALL list every failed screen using its observed and required value

### Requirement: Identity Policy Self-Check
The system SHALL provide a behavior-identity self-check that detects trajectory accounting or importance-weight implementation errors.

#### Scenario: Correct identity audit passes
- **WHEN** the target distribution exactly equals every logged behavior distribution
- **THEN** every decision ratio and trajectory weight SHALL equal one exactly
- **AND** ESS SHALL equal the complete trajectory count and weighted outcome summaries SHALL equal unweighted summaries

#### Scenario: Identity mismatch blocks audit integrity
- **WHEN** any identity ratio, trajectory weight, ESS, or outcome summary differs from its exact expected value
- **THEN** identity self-check SHALL be false with deterministic mismatch details
- **AND** OPE readiness SHALL remain false

### Requirement: Deterministic Fail-Closed Readiness Artifacts
The system SHALL emit deterministic JSON and Markdown OPE-readiness artifacts while keeping policy-value and deployment gates fail-closed.

#### Scenario: Valid but insufficient evidence emits blocked report
- **WHEN** inputs are structurally valid but any outcome, target, overlap, identity, or estimator gate is incomplete
- **THEN** the CLI SHALL successfully emit source hashes, effective contracts, diagnostics, blockers, and separate readiness booleans
- **AND** it SHALL report OPE, causal uplift, formal non-combat RL training, and live promotion as false

#### Scenario: Invalid input does not partially replace artifacts
- **WHEN** JSON, schema, hash, exact probability, duplicate identity, or provenance validation fails
- **THEN** the CLI SHALL exit nonzero
- **AND** it SHALL leave any previously complete output artifact pair unchanged

#### Scenario: B2 proof of concept remains no-promotion evidence
- **WHEN** the frozen B2 samples are audited with behavior-identity and deterministic-Current target manifests
- **THEN** both audits SHALL reconstruct exactly 25 trajectories and 230 decisions
- **AND** both SHALL remain blocked for OPE, causal uplift, formal non-combat RL training, and live promotion

### Requirement: Offline Gameplay Isolation
The OPE-readiness capability SHALL remain offline-only and SHALL NOT change production gameplay state.

#### Scenario: Audit leaves live state unchanged
- **WHEN** target-manifest generation or readiness auditing succeeds or fails
- **THEN** it SHALL NOT modify CommunicationMod configuration, live policy code, launcher defaults, run records, or checkpoints
- **AND** no live agent SHALL load an OPE-readiness artifact
