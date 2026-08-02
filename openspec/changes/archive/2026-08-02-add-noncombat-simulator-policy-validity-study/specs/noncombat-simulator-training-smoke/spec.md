## ADDED Requirements

### Requirement: Canonical Smoke Model Is A Frozen Evaluation Candidate
The completed simulator-training smoke SHALL permit its canonical final model and exact seeded initialization to be consumed only as immutable inputs to a separately reviewed offline policy-validity study.

#### Scenario: Policy-validity study binds the smoke
- **WHEN** an accepted policy-validity registration references the smoke model
- **THEN** it SHALL bind the smoke registration, model, trajectories, manifest, implementation identity, feature version, model seed, and canonical hashes
- **AND** it SHALL validate exact published action and policy-input compatibility before new evaluation

#### Scenario: Prior smoke holdout is replayed for compatibility
- **WHEN** a bounded subset of smoke holdout seeds verifies adapter and policy identity
- **THEN** those rows SHALL be used only as a byte-exact compatibility gate
- **AND** their outcomes SHALL NOT enter policy selection, a new quality estimate, or promotion evidence

#### Scenario: Frozen candidate would change
- **WHEN** loading, feature projection, adapter semantics, or evaluation would alter the canonical model or its published compatible actions
- **THEN** the policy-validity study SHALL block before fresh seeds
- **AND** it SHALL NOT retrain, translate, or repair the frozen model in place
