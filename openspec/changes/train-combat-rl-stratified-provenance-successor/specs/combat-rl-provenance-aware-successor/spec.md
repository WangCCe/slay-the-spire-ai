## ADDED Requirements

### Requirement: Recipe-before-corpus parity collection
The system MUST freeze the optimizer recipe, split rule, provenance-stratified eligibility thresholds, seed-generation rule, and production-r16 collection behavior before collecting a new training replay. The new replay MUST pass zero-update, trace, inventory, boundary, action legality, provenance reconciliation, and direct eval-parent parity checks before fitting.

#### Scenario: Registered fresh cohort passes
- **WHEN** exactly the registered games complete on the registered seeds and every parity check passes
- **THEN** the immutable replay hash may be bound as training-only input for the registered recipe

#### Scenario: Collection or parity check fails
- **WHEN** game count, seed order, zero-update state, trace binding, inventory identity, boundary integrity, action legality, provenance reconciliation, or direct eval-parent agreement fails
- **THEN** the cohort remains diagnostic-only and no candidate is fitted

## MODIFIED Requirements

### Requirement: Fixed downstream eligibility gate
The system SHALL permit only a separately registered fresh holdout when all preregistered technical, fit, materiality, direct-policy stability, override-label uplift, provenance, and serialization checks pass. It MUST NOT grant gameplay, qualification, promotion, or production authority.

#### Scenario: Every stratified development condition passes
- **WHEN** validation TD loss improves, overall parent disagreement is at least 5%, direct parent disagreement is at most 10%, override executed-label agreement improves by at least 0.10 absolute, positive-energy End Turn count increases by at most two, both validation provenance strata are nonempty, and all integrity checks pass
- **THEN** the frozen candidate hash is eligible only for a separate fresh holdout

#### Scenario: Any stratified development condition fails
- **WHEN** one or more fixed conditions fail
- **THEN** production r16 remains authoritative and no alternate recipe is fitted on the same corpus
