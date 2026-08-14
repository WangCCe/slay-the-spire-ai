## ADDED Requirements

### Requirement: Explicit bounded canary configuration
The system SHALL enable card-uplift intervention only from a source-bound
canary configuration that is mutually exclusive with shadow mode and limits
execution to three fresh games.

#### Scenario: Canary is not configured
- **WHEN** ordinary gameplay starts without the canary environment variable
- **THEN** card-uplift intervention remains inert

#### Scenario: Conflicting modes are configured
- **WHEN** shadow and canary configurations are both present
- **THEN** startup fails before CommunicationMod gameplay begins

### Requirement: Eligible card action substitution
The canary SHALL substitute the frozen candidate action only for an eligible
three-card, skippable, non-combat reward whose selected action maps uniquely to
the live offer.

#### Scenario: Candidate differs on an eligible reward
- **WHEN** projection and scoring succeed and the candidate action differs from Current
- **THEN** the wrapper returns the uniquely mapped live card or skip action and records the substitution

#### Scenario: Candidate agrees
- **WHEN** the candidate action equals Current
- **THEN** the wrapper returns Current unchanged and records agreement

### Requirement: Fail-closed Current fallback
The canary MUST retain Current for every ineligible decision and MUST disable
later interventions after any runtime error.

#### Scenario: Decision is ineligible
- **WHEN** the live card reward violates any eligibility rule
- **THEN** the wrapper returns Current and records the ineligibility without disabling later eligible decisions

#### Scenario: Runtime error occurs
- **WHEN** projection, scoring, binding, or action construction raises an error
- **THEN** the wrapper returns Current, records the error, and disables all later substitutions

### Requirement: Operational evidence and rollback
The canary SHALL publish canonical decision rows and three fresh run records,
then restore ordinary gameplay without modifying production checkpoints.

#### Scenario: Operational gate passes
- **WHEN** exactly three runs complete with at least eight substitutions, zero invalid actions, zero runtime errors, intact bindings, unique rows, and maximum latency at most 200 ms
- **THEN** the report permits only a separate policy-value experiment proposal

#### Scenario: Operational gate fails
- **WHEN** any operational check is unmet
- **THEN** Current remains the rollback and no retry, tuning, or promotion is authorized
