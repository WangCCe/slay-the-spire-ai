## MODIFIED Requirements

### Requirement: Exploration Data Does Not Unlock Policy Claims
The system SHALL keep known-propensity data qualification separate from outcome-contract, target-policy, overlap, estimator-validation, OPE, causal outcome, formal non-combat RL, and live-promotion readiness.

#### Scenario: Exploration data gate passes
- **WHEN** `known_propensity_exploration_data_ready` is true
- **THEN** the readiness report SHALL route the qualified dataset through the versioned trajectory, outcome, target-policy, overlap, effective-sample-size, and estimator-validation gates
- **AND** it SHALL NOT report causal uplift or authorize OPE, formal non-combat RL, or live promotion solely from the exploration-data result

#### Scenario: OPE readiness audit remains separate
- **WHEN** an offline readiness audit reconstructs valid trajectory weights and passes its minimum overlap screens
- **THEN** it SHALL report outcome-contract, target-policy, overlap, identity, and estimator-validation readiness separately
- **AND** OPE readiness SHALL remain false until an independently specified estimator-validation gate is implemented and passes

#### Scenario: Bottled or pilot labels join exploration rows
- **WHEN** offline Current, Bottled, or pilot-model labels are attached to known-propensity exploration samples
- **THEN** those labels SHALL remain auxiliary policy comparisons until converted into a complete versioned target-policy distribution
- **AND** they SHALL NOT change the recorded behavior distribution or become reward truth
