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

### Requirement: Hash-Bound Estimator Validation Handoff
The readiness system SHALL accept estimator validation only through a versioned calibration artifact bound to the exact estimator implementation, configuration, fixtures, and source evidence.

#### Scenario: Passing calibration advances only estimator readiness
- **WHEN** an independently verified calibration artifact passes every required exactness, coverage, bias, and determinism gate
- **THEN** `estimator_validation_ready` SHALL be true for estimate artifacts bound to that calibration hash
- **AND** overlap readiness SHALL remain an independently evaluated prerequisite

#### Scenario: Missing or mismatched calibration remains blocked
- **WHEN** the calibration artifact is missing, failed, stale, malformed, or bound to different estimator bytes or configuration
- **THEN** estimator validation and OPE estimate readiness SHALL be false with explicit blockers
- **AND** the system SHALL NOT infer validation from unit-test status or an unbound report label

### Requirement: Estimator And Policy Readiness Separation
The readiness system SHALL report estimate generation, candidate comparison, causal uplift, formal training, and live promotion as distinct gates.

#### Scenario: Estimate is complete but comparison is inconclusive
- **WHEN** estimator validation and dataset estimation are ready but the primary victory comparison interval or influence conditions fail
- **THEN** OPE estimate readiness SHALL be true while policy comparison readiness SHALL be false
- **AND** causal uplift, formal non-combat RL training, and live policy promotion SHALL remain false

#### Scenario: Comparison success does not authorize training
- **WHEN** the pre-specified primary interval, estimator-direction, and leave-one-trajectory-out gates all pass
- **THEN** policy comparison readiness SHALL be true
- **AND** causal uplift, formal non-combat RL training, and live policy promotion SHALL remain false until separately specified and approved

### Requirement: Frozen B3-B7 Estimator Proof Of Concept
The system SHALL apply the validated estimator pipeline to the frozen B3-B7 pool without changing its source evidence or gameplay policy.

#### Scenario: B3-B7 inputs remain exact
- **WHEN** the B3-B7 estimator proof of concept runs
- **THEN** it SHALL bind the canonical pool SHA-256 `aa61da25c93cdfa24ec57f787fbd41b5e4921c1a1a2bf9cb75f799133159b292`
- **AND** it SHALL independently reconstruct 125 trajectories, 1,253 decisions, 87 nonzero deterministic-Current weights, and the existing overlap-ready diagnostics

#### Scenario: One victory remains an explicit limitation
- **WHEN** B3-B7 estimates and intervals are rendered
- **THEN** the report SHALL preserve the one-victory outcome count and the number of zero-victory bootstrap replicates
- **AND** it SHALL apply the pre-specified comparison gates without substituting floor reached or changing thresholds after observing the result

### Requirement: Registered Deterministic-Current Outcome-Evidence Screen
The OPE readiness system SHALL apply the pre-registered outcome-evidence thresholds to the complete registered pool without changing the existing estimator or policy-comparison contracts.

#### Scenario: Supported victory is counted
- **WHEN** a complete uniquely joined trajectory has `victory=true` and its exact deterministic-Current trajectory weight is greater than zero
- **THEN** the system SHALL count it once as a deterministic-Current-supported victory
- **AND** it SHALL report the trajectory identifier and exact weight only after the study is unblinded

#### Scenario: Outcome-evidence expansion qualifies
- **WHEN** all registered slots are accounted for without a global integrity stop, at least 575 complete uniquely joined trajectories exist, each executable category has at least 50 confirmed baseline and 50 confirmed alternative decisions, deterministic-Current nonzero-weight trajectories are at least half of complete trajectories, deterministic-Current ESS fraction is at least 0.5, maximum normalized deterministic-Current weight is at most 0.05, and at least three distinct deterministic-Current-supported victories exist
- **THEN** `outcome_evidence_expansion_ready` SHALL be true
- **AND** each observed value and required threshold SHALL be emitted in the unblinded readiness artifact

#### Scenario: Outcome-evidence threshold fails
- **WHEN** any registered integrity, completeness, arm-support, nonzero-weight, ESS, maximum-weight, or supported-victory condition is not met
- **THEN** `outcome_evidence_expansion_ready` SHALL remain false with every failed condition listed
- **AND** floor reached, additional unregistered runs, or a favorable point estimate SHALL NOT substitute for the failed condition

#### Scenario: Expanded evidence reaches existing OPE gates
- **WHEN** the registered pool is unblinded regardless of whether `outcome_evidence_expansion_ready` passes
- **THEN** the system SHALL run the existing exact target construction, readiness, validated estimation, 10,000-replicate bootstrap, leave-one-trajectory-out, and victory-only comparison gates without changing their thresholds
- **AND** evidence expansion, estimate readiness, policy comparison, causal uplift, formal training, and live promotion SHALL remain separate booleans
