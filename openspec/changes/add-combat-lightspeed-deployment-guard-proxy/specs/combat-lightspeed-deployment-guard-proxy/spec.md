## ADDED Requirements

### Requirement: Opt-in evaluation-only deployment guard proxy
The LightSTS combat runner SHALL preserve direct raw-policy action execution by default and SHALL support a registered evaluation-only proxy for wasteful raw end-turn actions.

#### Scenario: Default compatibility
- **WHEN** the deployment guard proxy mode is `none`
- **THEN** paired evaluation executes the selected raw policy action without proxy substitution

#### Scenario: Training isolation
- **WHEN** a non-default deployment guard proxy is configured
- **THEN** transition collection, replay preparation, optimizer updates, and checkpoint parameters remain independent of the proxy

#### Scenario: Invalid mode
- **WHEN** an unregistered deployment guard proxy mode is configured
- **THEN** validation fails before native trajectory collection or model fitting

### Requirement: Deterministic wasteful-end-turn replacement
The registered proxy SHALL consider replacement only for a raw end-turn selected with positive player energy and at least one legal card-play action.

#### Scenario: Eligible end-turn
- **WHEN** the raw policy selects end-turn with positive energy and legal card-play actions
- **THEN** the proxy evaluates each card action on an independent environment clone, excludes unsupported successors, and executes the supported action with the greatest existing immediate native reward using RL action index as the deterministic tie-break

#### Scenario: Ineligible end-turn
- **WHEN** the raw action is not end-turn, player energy is zero, or no legal card-play action exists
- **THEN** the proxy executes the raw action unchanged

#### Scenario: No supported replacement
- **WHEN** every legal card-play candidate produces an unsupported successor
- **THEN** the proxy executes the raw end-turn and records that no supported replacement was available

### Requirement: Symmetric paired-policy application
The runner SHALL apply the configured proxy independently and identically to the frozen control and fitted candidate during paired held-out evaluation.

#### Scenario: Paired evaluation
- **WHEN** control and candidate are evaluated on the same reachable held-out profile
- **THEN** each policy's raw action is transformed only from its own current snapshot and legal actions under the same proxy mode

### Requirement: Guard proxy evidence and authority
The report SHALL bind the configured mode and separate raw-policy actions from proxy interventions without expanding simulator evidence authority.

#### Scenario: Evaluation telemetry
- **WHEN** an evaluation completes
- **THEN** its per-policy and aggregate evidence includes raw end-turn, eligible, replacement, and no-supported-replacement counts

#### Scenario: Counterfactual authority
- **WHEN** a proxy-enabled report is published
- **THEN** gameplay, transfer, mechanics-equivalence, live-policy-quality, qualification, and promotion authority remain false
