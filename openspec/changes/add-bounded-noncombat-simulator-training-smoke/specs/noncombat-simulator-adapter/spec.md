## MODIFIED Requirements

### Requirement: Deterministic Non-Combat Environment API
The adapter SHALL expose deterministic Ironclad reset, deep clone, canonical snapshot, legal-action enumeration, action execution, and terminal outcome through JSON-compatible values.

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

### Requirement: Simulator POC Has No Training Authority
Simulator adapter readiness SHALL authorize only a separate reviewed proposal for a bounded simulator-training smoke; an accepted smoke change MAY invoke only its pre-registered bounded execution and SHALL NOT authorize formal training or live use.

#### Scenario: POC report passes
- **WHEN** a fit report returns `adapter_poc_ready`
- **THEN** live study launch, formal RL training, OPE reinterpretation, live policy loading, and promotion authority SHALL all remain false

#### Scenario: Reviewed bounded smoke executes
- **WHEN** an accepted simulator-training-smoke change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY run only within that change's registered cohorts and resource bounds
- **AND** formal RL, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Bottled labels are attached
- **WHEN** Bottled labels are compared with simulator transitions
- **THEN** they SHALL remain auxiliary annotations
- **AND** they SHALL NOT become direct reward, terminal truth, or simulator correctness evidence
