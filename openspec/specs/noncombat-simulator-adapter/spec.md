# noncombat-simulator-adapter Specification

## Purpose

Define an optional, provenance-bound offline simulator interface and its strict
separation from live gameplay, evaluation evidence, training, and promotion.

## Requirements

### Requirement: Offline External Simulator Isolation
The system SHALL use `sts_lightspeed` only through an explicitly requested offline adapter and SHALL NOT import it from the CommunicationMod gameplay runtime.

#### Scenario: Adapter is absent during live gameplay
- **WHEN** the production agent starts through CommunicationMod
- **THEN** it SHALL NOT import, build, or invoke the simulator adapter
- **AND** simulator availability SHALL NOT change live action selection

#### Scenario: External checkout is explicit
- **WHEN** a developer builds or audits the simulator adapter
- **THEN** the command SHALL require an explicit external checkout and caller-selected build location
- **AND** it SHALL NOT modify or vendor the external checkout

### Requirement: Provenance-Bound Simulator Environment
The adapter SHALL bind every transition report to the physical simulator source, dependency, build, adapter, and fixture identities used to produce it.

#### Scenario: Complete provenance is recorded
- **WHEN** a simulator fit audit succeeds
- **THEN** the report SHALL record the simulator parent commit, source-diff digest, submodule commits, module hash, Python and compiler identities, adapter commit, and fixture hash

#### Scenario: Registered identity drifts
- **WHEN** any required source, dependency, module, or fixture identity differs from the registered input
- **THEN** the audit SHALL fail closed with an explicit provenance blocker
- **AND** it SHALL NOT reuse a prior readiness result

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

### Requirement: Four-Category Simulator Transitions
The adapter SHALL emit versioned simulator transitions for route, shop, event, and card-reward decisions while declaring all baseline-controlled screens and follow-up semantics.

#### Scenario: Target category transition is emitted
- **WHEN** the environment reaches a supported target decision and applies one reported candidate
- **THEN** it SHALL emit source state, candidate set, selected action, successor state or terminal outcome, category, and simulator provenance

#### Scenario: Combat is baseline controlled
- **WHEN** a selected non-combat action leads to combat before the next target decision
- **THEN** the adapter SHALL resolve combat with the declared simulator baseline
- **AND** the transition SHALL record that baseline rather than attributing combat control to the learned policy

#### Scenario: Unsupported screen remains explicit
- **WHEN** the environment reaches Neow, boss relic, campfire, treasure, or a follow-up selection outside the POC action space
- **THEN** the adapter SHALL either resolve it with the declared baseline and record that fact or stop with an unsupported reason
- **AND** it SHALL NOT silently relabel the screen as one of the four target categories

### Requirement: Historical Prefix And Category Fit Audit
The system SHALL publish a deterministic, fail-closed fit report before simulator transitions can support a training proposal.

#### Scenario: Adapter POC fit is demonstrated
- **WHEN** exact source provenance passes, repeated seeds are deterministic, clone branches are isolated, every reported action executes legally, all four target categories have bounded smoke coverage, terminal outcomes are produced, and every frozen historical prefix candidate set matches
- **THEN** the report MAY classify the result as `adapter_poc_ready`
- **AND** it SHALL list remaining simulator-divergence and action-scope limitations

#### Scenario: Any fit prerequisite fails
- **WHEN** any required provenance, determinism, clone, legality, category, terminal, or historical-prefix check fails
- **THEN** the report SHALL classify the result as `blocked`
- **AND** it SHALL identify the exact failed prerequisite

### Requirement: Simulator POC Has No Training Authority
Simulator adapter readiness SHALL authorize only separately reviewed bounded simulator smoke, policy-validity, or baseline-warm-start work and SHALL NOT authorize formal training or live use.

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

#### Scenario: Reviewed baseline warm start executes
- **WHEN** an accepted baseline-warm-start change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY collect native demonstrations, train one bounded supervised candidate ranker, and evaluate frozen policies only within that change's registered cohorts and limits
- **AND** formal RL, simulator RL training, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Bottled labels are attached
- **WHEN** Bottled labels are compared with simulator transitions
- **THEN** they SHALL remain auxiliary annotations
- **AND** they SHALL NOT become direct reward, terminal truth, or simulator correctness evidence

### Requirement: Versioned Event Observation Snapshot Context
New native adapter modules SHALL identify the decision-relevant event snapshot extension as adapter API v3, while offline validators SHALL preserve explicit read compatibility for historical registered v2 snapshots without upgrading or filling their contents.

#### Scenario: N'loth snapshot is emitted by a v3 module
- **WHEN** the native adapter reaches an N'loth event decision
- **THEN** `state.decision_context.offered_relics` SHALL contain exactly two records sourced from `GameContext.info.relicIdx0` and `GameContext.info.relicIdx1`
- **AND** each record SHALL contain its simulator choice index, relic slot, relic id, and relic name matching the corresponding `state.relics` entry

#### Scenario: Another event snapshot is emitted by a v3 module
- **WHEN** the native adapter reaches an event other than N'loth
- **THEN** it SHALL retain the event id, event name, and event data required by the total observation contract
- **AND** it SHALL NOT synthesize N'loth offered-relic context

#### Scenario: Historical v2 evidence is inspected
- **WHEN** an immutable registered snapshot or provenance record declares adapter API v2
- **THEN** the offline validator SHALL preserve and validate that declared identity
- **AND** it SHALL NOT treat missing v3-only context as present or rewrite historical evidence

#### Scenario: A newly loaded native module has the wrong API
- **WHEN** runtime discovery loads a native module that does not declare adapter API v3
- **THEN** module loading SHALL fail before an environment is constructed
- **AND** historical read compatibility SHALL NOT authorize execution of that module

### Requirement: Source-Bound Event Option Semantics
The offline adapter layer SHALL resolve event-option observations only from the canonical versioned contract that binds all 25 Current-relevant event identities, 47 aliases, legal simulator indices, Current positions, semantic labels, dynamic context, simulator parent commit, and simulator source digest. Unsupported, ambiguous, or drifted inputs SHALL fail closed.

#### Scenario: A static event state is resolved
- **WHEN** a validated event snapshot and its ordered legal candidates match one exact static rule in the hash-checked canonical contract and simulator provenance matches the registered identity
- **THEN** the resolver SHALL return ordered rows with contiguous Current positions, original simulator choice indices, and non-empty contract labels
- **AND** it SHALL leave the source snapshot, candidates, provenance, and contract bytes unchanged

#### Scenario: A Cursed Tome phase is resolved
- **WHEN** event data is 0, 1, 2, 3, or 4 and legal simulator indices exactly match the registered phase row
- **THEN** the resolver SHALL emit Read/Leave for phase 0, the corresponding single Continue row for phases 1 through 3, or Take/Stop for phase 4
- **AND** each emitted Current position SHALL remain contiguous even when the simulator index is sparse

#### Scenario: N'loth offered relics are resolved
- **WHEN** legal indices are 0, 1, and 2 and both offered-relic records have distinct in-range slots whose ids and names equal the corresponding snapshot relics
- **THEN** the resolver SHALL emit `Offer <relic name>` for indices 0 and 1 and `Leave` for index 2
- **AND** any missing, duplicate, out-of-range, or mismatched offered-relic field SHALL block resolution

#### Scenario: Upstream event identity needs Current normalization
- **WHEN** the exact upstream rule uses an event id such as `Mindbloom` or `Nloth` whose Current hydration id differs
- **THEN** the observation SHALL carry the registered Current id such as `MindBloom` or `N'loth`
- **AND** it SHALL NOT fuzzy-match an unregistered identity

#### Scenario: Contract or event input is not exactly supported
- **WHEN** the contract path, hash, schema, counts, event id, event name, phase, candidate kind, candidate order, candidate index, dynamic context, or simulator provenance differs from the registered boundary
- **THEN** the resolver SHALL fail with a field-specific reason
- **AND** it SHALL NOT return generic index labels, partial semantics, cached prior rules, or a default event
