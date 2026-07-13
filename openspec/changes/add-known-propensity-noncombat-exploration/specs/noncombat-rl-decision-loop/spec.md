## ADDED Requirements

### Requirement: Verified Known-Propensity Evidence
The system SHALL accept behavior probabilities as evaluation evidence only when they come from a confirmed, replay-valid exploration record with an exact candidate distribution.

#### Scenario: Confirmed exploration sample supplies behavior probability
- **WHEN** a canonical non-combat sample joins to a confirmed exploration decision and the validator reproduces its state hash, candidate distribution, draw, selected action, and selected-action probability
- **THEN** the sample SHALL record the verified behavior policy and known selected-action probability
- **AND** it SHALL preserve the exact candidate probabilities and exploration provenance

#### Scenario: Unverified probability remains unsupported
- **WHEN** an exploration record is missing, shadow-only, rejected, unresolved, ambiguous, or not replay-valid
- **THEN** the sample SHALL NOT treat its selected-action probability as verified behavior evidence
- **AND** it SHALL retain an explicit unsupported reason instead of inferring a probability

### Requirement: Exploration Data Does Not Unlock Policy Claims
The system SHALL keep known-propensity data qualification separate from OPE, causal outcome, formal non-combat RL, and live-promotion readiness.

#### Scenario: Exploration data gate passes
- **WHEN** `known_propensity_exploration_data_ready` is true
- **THEN** the readiness report SHALL continue to evaluate reward design, estimator-specific overlap and variance, OPE validation, formal training, and live promotion as separate gates
- **AND** it SHALL NOT report causal uplift or authorize formal non-combat RL solely from the exploration-data result

#### Scenario: Bottled or pilot labels join exploration rows
- **WHEN** offline Current, Bottled, or pilot-model labels are attached to known-propensity exploration samples
- **THEN** those labels SHALL remain auxiliary policy comparisons
- **AND** they SHALL NOT change the recorded behavior distribution or become reward truth
