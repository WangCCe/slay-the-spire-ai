## ADDED Requirements

### Requirement: Explicit shadow registration
The runtime SHALL enable latent-gated combat shadowing only from an explicit tracked and unmodified registration that binds an ancestor source commit with unchanged behavior-affecting files, the candidate artifact, production parent checkpoint, parent parameter state, trace destination, event budget, and readiness gates.

#### Scenario: No registration is configured
- **WHEN** RL v2 starts without the shadow registration environment variable
- **THEN** checkpoint loading and action selection remain unchanged and no shadow artifact is loaded

#### Scenario: A bound input differs
- **WHEN** a configured registration, source file, candidate artifact, production checkpoint, parent parameter state, or output path differs from its binding
- **THEN** startup fails before gameplay begins and no shadow event is published

### Requirement: Deterministic inference-only eligibility
The shadow runtime SHALL require a loaded RL v2 parent in inference mode with epsilon zero and expert mix disabled.

#### Scenario: Training or exploration is enabled
- **WHEN** shadowing is configured for training, nonzero epsilon, or expert-mixed action selection
- **THEN** initialization rejects the configuration before gameplay begins

### Requirement: Behavior-neutral candidate observation
The shadow runtime SHALL evaluate the adapter on the same encoded state and legal-action mask as the deterministic parent decision, SHALL bind the final guard-processed action through the existing execution callback, and SHALL have no authority to replace either action.

#### Scenario: Candidate differs from parent
- **WHEN** the gate opens and the candidate selects a different legal action
- **THEN** the RL agent still returns the original parent-selected proposal and records the disagreement together with the final guard-processed action

#### Scenario: Parent parity differs
- **WHEN** the adapter's frozen parent action differs from the action selected by the active parent network
- **THEN** the event records the parity failure, shadowing is disabled for later decisions, and the already selected parent action is preserved

#### Scenario: Guard requests a transient state refresh
- **WHEN** the final callback emits `WaitAction` to refresh stale combat state without changing gameplay state
- **THEN** the runtime records a transient-discard event, does not treat the wait as a policy action, and does not consume the policy-decision budget

### Requirement: Bounded structured telemetry
The runtime SHALL append schema-versioned JSONL decision and transient-discard events with candidate, parent and source identities, session and sequence identity, compact game context, legal action indices, action indices, gate telemetry, derived action relations, and adapter-inference latency until the registered policy-decision budget is reached.

#### Scenario: Valid shadow decision
- **WHEN** one eligible combat decision is observed
- **THEN** exactly one parseable decision event is appended with a contiguous session sequence number

#### Scenario: Event budget is exhausted
- **WHEN** the registered maximum decision count has been written in the current or an earlier valid process session
- **THEN** later decisions skip candidate inference and trace publication while parent gameplay continues

### Requirement: Runtime failure isolation
After successful initialization, shadow inference and publication failures SHALL NOT change the parent-selected gameplay action.

#### Scenario: Shadow evaluation raises
- **WHEN** adapter inference or event publication fails after action selection
- **THEN** the runtime logs the failure, attempts to record one error event, disables shadowing, and returns control without replacing the parent action

### Requirement: Read-only readiness summary
The summarizer SHALL validate trace identity, source identity, event schema, derived-field consistency and contiguous events and SHALL report preregistered completeness, parity, candidate and final-action legality, error, budget, gate-open, disagreement, and adapter-inference latency metrics without making a gameplay-quality claim.

#### Scenario: Every readiness gate passes
- **WHEN** the trace reaches the minimum decision count with valid and internally consistent events, exact parent parity, only legal candidate and final actions, zero errors, and p95 adapter-inference latency within the registered ceiling
- **THEN** the report marks the cohort eligible only for a separately bounded matched gameplay evaluation

#### Scenario: Any readiness gate fails
- **WHEN** trace identity, sequence continuity, minimum count, parity, legality, error, budget, or latency validation fails
- **THEN** the report marks the cohort not ready and does not authorize candidate action takeover
