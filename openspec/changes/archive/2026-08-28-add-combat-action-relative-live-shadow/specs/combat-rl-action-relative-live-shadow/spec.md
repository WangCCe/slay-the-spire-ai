## ADDED Requirements

### Requirement: Explicit deferred-shadow registration

The runtime SHALL enable action-relative live shadowing only from an explicit
tracked and unmodified registration that binds unchanged source files, the
candidate artifact and corpus identities, production parent checkpoint and
parameter state, trace destination, decision budget, and readiness gates.

#### Scenario: No registration is configured
- **WHEN** RL v2 starts without the action-relative shadow environment variable
- **THEN** checkpoint loading and action selection remain unchanged and no candidate artifact is loaded

#### Scenario: A bound input differs
- **WHEN** source, registration, artifact, corpus, parent checkpoint, parent state, or trace binding differs
- **THEN** startup fails before gameplay begins and no shadow event is published

### Requirement: Inference-only mutually exclusive eligibility

The shadow runtime SHALL require production-r16 inference with epsilon zero and
expert mix disabled and SHALL be mutually exclusive with every candidate or
other combat shadow runtime.

#### Scenario: Training, exploration, or another live runtime is configured
- **WHEN** action-relative shadowing is combined with training, nonzero epsilon, expert mix, latent shadow, or latent candidate authority
- **THEN** initialization rejects the configuration before gameplay begins

### Requirement: Deferred post-guard observation

The runtime SHALL cache the encoded proposal state and SHALL defer inference
until the execution callback supplies the final guard-processed action. It SHALL
evaluate only decisions where raw parent action 90 became a legal non-90
executed action and SHALL have no authority to replace that action.

#### Scenario: Real guard replacement is eligible
- **WHEN** the parent proposal is action 90 and the committed legal executed action is not 90
- **THEN** the scorer evaluates legal non-guard alternatives relative to the executed guard while production execution remains unchanged

#### Scenario: Decision is not a guard replacement
- **WHEN** parent or executed action does not meet the fixed eligibility condition
- **THEN** the runtime records the support reason without candidate inference or behavior change

#### Scenario: Transient wait is committed
- **WHEN** the final callback emits a wait used only to refresh state
- **THEN** the runtime discards the pending proposal without consuming the committed-decision budget

### Requirement: Constrained behavior-neutral candidate inference

Eligible inference SHALL remove action 90 and the executed guard from the legal
alternative mask before maximization, apply the registered advantage threshold,
and record candidate intent without replacing the executed action.

#### Scenario: Candidate would intervene
- **WHEN** the highest allowed predicted advantage reaches the threshold
- **THEN** the event records the legal candidate and predicted advantage while the executed production guard remains unchanged

#### Scenario: No candidate is allowed or clears threshold
- **WHEN** constraints remove every alternative or every prediction is below threshold
- **THEN** the event records an exact candidate abstention and preserves production execution

### Requirement: Bounded structured live telemetry

The runtime SHALL append one schema-versioned event per committed decision until
the 512-decision budget is reached, with source and artifact identities, state
identity, compact game context, parent, guard, legal and candidate actions,
support reason, constraints, predicted advantage, intervention intent,
execution neutrality, inference latency, session sequence, and errors.

#### Scenario: Valid committed decision
- **WHEN** a cached proposal is committed to a gameplay action
- **THEN** exactly one parseable event is appended with a contiguous session decision sequence

#### Scenario: Event budget is exhausted
- **WHEN** 512 valid committed events already exist across current or prior sessions
- **THEN** later decisions skip shadow inference and publication while production gameplay continues

### Requirement: Read-only live readiness summary

The summarizer SHALL validate registration and trace identity, sequence,
derived fields, behavior neutrality, support, legality, EndTurn safety, errors,
budget, and latency without making a gameplay-quality claim.

#### Scenario: Every readiness gate passes
- **WHEN** at least 100 eligible events occur within 512 committed decisions, all events preserve execution, candidate actions are legal and non-EndTurn, errors are zero, and p95 inference latency is at most 20ms
- **THEN** the report marks the artifact eligible only for a separately registered matched live evaluation

#### Scenario: Any readiness gate fails
- **WHEN** identity, continuity, neutrality, support, legality, safety, error, budget, or latency validation fails
- **THEN** the report marks the artifact not ready and does not authorize candidate action takeover
