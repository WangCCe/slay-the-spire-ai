## ADDED Requirements

### Requirement: Source-bound action-relative candidate registration

The runtime SHALL enable action-relative candidate takeover only from an
explicit committed candidate registration that binds source, artifact and
corpus identities, production-parent checkpoint and parameter state, CPU
inference, trace destination, finite decision budget, and the fixed late safety
policy.

#### Scenario: Candidate registration is valid
- **WHEN** eval mode loads a committed candidate registration whose source and all bound identities match the active checkout and production r16
- **THEN** a distinct frozen CPU residual may initialize without changing the production parent

#### Scenario: Candidate registration differs
- **WHEN** mode, schema, source, artifact, corpus, checkpoint, parent state, device, trace boundary, budget, or safety-policy identity differs
- **THEN** initialization fails before candidate-controlled gameplay or trace publication

### Requirement: Mutually exclusive eval-only candidate mode

Candidate mode MUST require training disabled, epsilon exactly zero, expert mix
disabled, and a production-parent checkpoint, and SHALL be mutually exclusive
with every latent or action-relative live shadow or candidate runtime.

#### Scenario: Training or exploration is requested
- **WHEN** action-relative candidate mode is combined with training, nonzero epsilon, or expert mix
- **THEN** initialization fails before gameplay

#### Scenario: Another combat live runtime is configured
- **WHEN** latent shadow, latent candidate, action-relative shadow, or action-relative candidate registrations overlap
- **THEN** agent initialization fails before any candidate artifact is loaded

#### Scenario: No candidate argument is supplied
- **WHEN** the batch wrapper launches an ordinary parent arm
- **THEN** ambient action-relative candidate registration is removed from the child environment

### Requirement: Guard-relative late takeover with fixed safety veto

The candidate runtime SHALL evaluate only a raw parent EndTurn proposal that a
completed outer guard changed to a legal non-EndTurn action. It SHALL apply a
candidate only after the fixed source-bound safety veto passes and MUST retain
the guard action on abstention, veto, or error.

#### Scenario: Safe candidate clears the threshold
- **WHEN** the decision is eligible, the constrained candidate is legal and non-EndTurn, its predicted advantage reaches the registered artifact threshold, and every safety-veto condition passes
- **THEN** the candidate becomes the selected action before the ordinary final-action commit

#### Scenario: Candidate is ineligible or vetoed
- **WHEN** parent or guard support differs, the candidate abstains, or any legality or safety-veto condition fails
- **THEN** the completed guard action remains selected and gameplay continues without candidate takeover

#### Scenario: Candidate processing fails
- **WHEN** late inference, decoding, safety validation, tracing, or commit processing raises or produces inconsistent identity
- **THEN** candidate authority is disabled, the arm becomes ineligible, and the guard action is retained for recoverability

### Requirement: Complete late-action provenance

Each candidate decision SHALL record parent, guard, candidate, advantage,
safety policy and veto, selected action, takeover status, final action,
identity, legality, latency, and runtime-error evidence. Transient control
actions SHALL be audited without consuming the candidate decision budget.

#### Scenario: Candidate decision is committed
- **WHEN** the final boundary emits an encodable combat action
- **THEN** one contiguous event records whether the safe selected action matches the final action and whether candidate takeover occurred

#### Scenario: Transient wait is emitted
- **WHEN** a stale-state refresh emits `WaitAction`
- **THEN** the pending proposal becomes a transient-discard event without consuming the candidate decision budget

### Requirement: Preregistered matched gameplay cohort

The evaluation SHALL use exactly ten fresh Ironclad A0 seeds in identical order
for candidate and production-r16 parent arms, with conservative routing, eval
mode, epsilon zero, training disabled, and production configuration restored
between arms.

#### Scenario: Both arms complete
- **WHEN** candidate and parent each complete ten natural runs on the registered seed order
- **THEN** run records, logs, traces, seed identities, and exact configuration restoration are reconciled before scoring

#### Scenario: Execution boundary changes after start
- **WHEN** source, checkpoint, artifact, seed order, threshold, routing, safety policy, or evaluation settings change after the first completed game
- **THEN** the gate is invalid and is not reinterpreted as matched evidence

### Requirement: Conservative qualification and promotion boundary

The candidate SHALL qualify only when paired floor wins exceed losses, at least
one pair differs, total floors and Act 2, Act 2 boss, Act 3, and victory counts
are non-worse, at least one safe takeover occurs, both arms complete, and every
technical condition passes. Passing SHALL NOT automatically promote it.

#### Scenario: Every registered condition passes
- **WHEN** the complete reconciled report satisfies every paired outcome, identity, safety, legality, completion, error, seed, and restoration condition
- **THEN** the candidate is eligible only for a separate promotion decision

#### Scenario: All pairs tie or any condition fails
- **WHEN** all floor pairs tie or any registered technical or outcome condition fails
- **THEN** production r16 remains authoritative and the cohort is closed to tuning or retry
