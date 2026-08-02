## MODIFIED Requirements

### Requirement: Deterministic Non-Combat Environment API
The adapter SHALL expose deterministic Ironclad reset, deep clone, canonical snapshot, legal-action enumeration, action execution, native SimpleAgent target-action query, and terminal outcome through JSON-compatible values.

#### Scenario: Same seed resets identically
- **WHEN** two environments reset with the same seed and ascension under the same bound identities
- **THEN** their canonical snapshots and legal actions SHALL be byte-equivalent at every corresponding policy decision

#### Scenario: Clone branches are isolated
- **WHEN** an environment is cloned at a target decision and an action executes on only one branch, including an action that enters a new Act
- **THEN** the untouched branch snapshot and map SHALL remain unchanged
- **AND** the changed branch SHALL return a legal successor or terminal outcome

#### Scenario: Reported candidates execute legally
- **WHEN** the adapter reports legal candidates at a target decision
- **THEN** every candidate SHALL execute successfully on a fresh clone of that decision state
- **AND** no unreported action SHALL be accepted as a target-category action

#### Scenario: Upstream screen field lacks current semantics
- **WHEN** an upstream screen-info field is uninitialized, stale, or not defined for the current target screen
- **THEN** the adapter SHALL omit it or emit an explicit canonical unavailable value
- **AND** process memory contents SHALL NOT enter snapshots or policy features

#### Scenario: Native baseline target action is queried
- **WHEN** a baseline-following environment reaches a route, shop, event, or card-reward decision
- **THEN** the adapter SHALL map the corresponding upstream SimpleAgent decision to exactly one currently reported candidate
- **AND** repeated queries SHALL leave source snapshot and candidate bytes unchanged

#### Scenario: Native baseline continuation is broken
- **WHEN** an environment previously applies a target action different from its queried SimpleAgent action
- **THEN** a later native-baseline query on that trajectory SHALL fail closed
- **AND** the adapter SHALL NOT present a stale route path as a counterfactual baseline action

### Requirement: Simulator POC Has No Training Authority
Simulator adapter readiness SHALL authorize only separately reviewed bounded simulator smoke or policy-validity work and SHALL NOT authorize formal training or live use.

#### Scenario: POC report passes
- **WHEN** a fit report returns `adapter_poc_ready`
- **THEN** live study launch, formal RL training, OPE reinterpretation, live policy loading, and promotion authority SHALL all remain false

#### Scenario: Reviewed bounded smoke executes
- **WHEN** an accepted simulator-training-smoke change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY run only within that change's registered cohorts and resource bounds
- **AND** formal RL, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Reviewed policy-validity study executes
- **WHEN** an accepted simulator-policy-validity change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY run only frozen policies within that change's registered compatibility and fresh-evaluation bounds
- **AND** training, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Bottled labels are attached
- **WHEN** Bottled labels are compared with simulator transitions
- **THEN** they SHALL remain auxiliary annotations
- **AND** they SHALL NOT become direct reward, terminal truth, or simulator correctness evidence
