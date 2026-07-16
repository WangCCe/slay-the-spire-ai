## ADDED Requirements

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
