## ADDED Requirements

### Requirement: Verified Complete-Trajectory Estimator Input
The system SHALL estimate policy values only from a hash-bound canonical sample, target manifest, and readiness artifact that pass independent replay and the existing complete-trajectory overlap gate.

#### Scenario: Verified overlap-ready input is accepted
- **WHEN** all source hashes, target probabilities, exact trajectory weights, terminal outcomes, and overlap screens independently replay successfully
- **THEN** the estimator SHALL accept exactly one weighted terminal observation per complete trajectory
- **AND** it SHALL preserve zero-weight trajectories in support and uncertainty accounting

#### Scenario: Invalid or unsupported input fails closed
- **WHEN** independent replay fails, overlap is not ready, a source hash changes, or a required trajectory outcome or denominator is invalid
- **THEN** dataset estimation readiness SHALL be false with explicit reasons
- **AND** no prior complete estimate artifact SHALL be partially replaced

### Requirement: Exact OIS And Self-Normalized Estimates
The system SHALL compute ordinary and self-normalized importance-sampling estimates at complete-run trajectory granularity using exact arithmetic before rendering finite display values.

#### Scenario: Supported target produces separate outcome estimates
- **WHEN** verified trajectory weights have a positive total
- **THEN** the system SHALL compute exact OIS, SNIS, behavior, and target-minus-behavior values separately for victory and floor reached
- **AND** it SHALL identify SNIS as primary and OIS as a variance diagnostic

#### Scenario: Estimation never changes observed support
- **WHEN** a trajectory has zero target weight or an extreme positive weight
- **THEN** the system SHALL retain its exact weight without clipping, capping, smoothing, or dropping it
- **AND** it SHALL NOT treat decisions from that trajectory as independent outcomes

### Requirement: Deterministic Paired Trajectory Bootstrap
The system SHALL construct uncertainty intervals by resampling complete trajectories with replacement using a versioned deterministic hash-draw contract.

#### Scenario: Repeated bootstrap is byte reproducible
- **WHEN** identical input hashes, seed, replicate count, and confidence level are used
- **THEN** every sampled trajectory index, exact replicate estimate, percentile endpoint, and rendered artifact SHALL be identical
- **AND** reordering input rows SHALL NOT change the result

#### Scenario: Paired uplift preserves dependence
- **WHEN** a bootstrap replicate is evaluated
- **THEN** behavior value and target OIS/SNIS value SHALL use the same sampled trajectory multiset
- **AND** target-minus-behavior intervals SHALL be computed from paired replicate differences rather than independent intervals

#### Scenario: Undefined replicate blocks the required interval
- **WHEN** any required primary replicate has an undefined target denominator or invalid outcome
- **THEN** the artifact SHALL report the exact replicate and reason
- **AND** estimate readiness SHALL remain false rather than silently discarding the replicate

### Requirement: Synthetic Estimator Calibration Gate
The system SHALL require a versioned deterministic calibration artifact covering identity, known-truth estimation, exact bootstrap enumeration, ordering invariance, repeated-sample coverage, and bias before estimator validation is ready.

#### Scenario: Complete calibration passes
- **WHEN** identity and synthetic exactness checks pass, hash bootstrap equals exact enumeration, ordering invariance holds, 95 percent SNIS target and uplift coverage each fall between 0.90 and 0.99 on the fixed experiment, and absolute mean bias is at most 0.02
- **THEN** estimator validation readiness SHALL be true
- **AND** the artifact SHALL record the fixture, seed, sample, replicate, threshold, and implementation hashes

#### Scenario: Any calibration dimension fails
- **WHEN** an exact invariant, enumeration check, ordering check, coverage bound, bias bound, source hash, or deterministic rerun check fails
- **THEN** estimator validation readiness SHALL be false with every failed dimension listed
- **AND** no real-data estimate SHALL be marked OPE-estimate-ready from that artifact

### Requirement: Candidate Comparison And Influence Gate
The system SHALL distinguish a complete OPE estimate from evidence that a target policy is better than its logged behavior policy.

#### Scenario: Candidate superiority gate passes
- **WHEN** estimator and dataset gates pass, the 95 percent primary SNIS uplift interval has a lower endpoint strictly above zero, full-sample OIS and SNIS primary uplifts are positive, and every defined leave-one-trajectory-out SNIS primary uplift is positive
- **THEN** policy comparison readiness SHALL be true
- **AND** the artifact SHALL preserve all interval and influence evidence supporting that result

#### Scenario: Inconclusive candidate remains a valid estimate
- **WHEN** estimation succeeds but any interval, estimator-direction, or leave-one-trajectory-out comparison condition fails
- **THEN** OPE estimate readiness SHALL remain true while policy comparison readiness SHALL be false
- **AND** floor-reached estimates SHALL NOT substitute for the failed victory comparison

### Requirement: Deterministic Fail-Closed Estimator Artifacts
The system SHALL emit deterministic JSON and Markdown calibration and estimate artifacts with separately named estimator, dataset, estimate, comparison, causal, training, and promotion gates.

#### Scenario: Successful offline estimate keeps downstream gates closed
- **WHEN** a complete estimate artifact is emitted
- **THEN** it SHALL report exact point estimates, intervals, influence diagnostics, source hashes, effective contracts, blockers, and limitations
- **AND** causal uplift, formal non-combat RL training, and live policy promotion SHALL remain false

#### Scenario: Tampered artifact is rejected independently
- **WHEN** source bytes, calibration evidence, point estimates, bootstrap draws, interval endpoints, influence rows, or gate booleans are changed
- **THEN** the independent verifier SHALL exit nonzero with the first deterministic mismatch
- **AND** it SHALL NOT import the main estimator implementation

### Requirement: Offline Estimator Isolation
The estimator-validation capability SHALL remain offline-only and SHALL NOT modify production gameplay state.

#### Scenario: Calibration and estimation leave live state unchanged
- **WHEN** calibration, estimation, rendering, or independent verification succeeds or fails
- **THEN** the system SHALL NOT modify CommunicationMod configuration, live policy code, launcher defaults, run records, or checkpoints
- **AND** no live agent SHALL import or auto-load estimator artifacts
