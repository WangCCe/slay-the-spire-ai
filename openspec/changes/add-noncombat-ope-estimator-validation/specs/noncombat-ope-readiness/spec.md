## ADDED Requirements

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
