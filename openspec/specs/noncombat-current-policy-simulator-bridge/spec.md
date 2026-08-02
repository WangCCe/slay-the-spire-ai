# noncombat-current-policy-simulator-bridge Specification

## Purpose

Define an offline, fail-closed bridge from registered `sts_lightspeed`
non-combat snapshots to the exact Current policy path, with structural-only
evidence authority.

## Requirements

### Requirement: Source-bound offline bridge identity
The system SHALL run the Current-policy simulator bridge only from a registration that hash-binds the exact Current implementation, bridge and dependency files, simulator adapter identity, frozen evidence, external metadata, runtime, configuration, and expected outputs.

#### Scenario: A registered frozen POC is opened
- **WHEN** every bound source exists at the registered path and has the registered SHA-256 identity
- **THEN** the bridge SHALL record the resolved identities before evaluating a row
- **AND** it SHALL reject any missing, changed, fallback-resolved, or unregistered source

### Requirement: Exact snapshot hydration without mutation
The bridge SHALL validate and hydrate the minimum Communication Mod-compatible game and screen object graph required by the exact Current non-combat decision path, and it SHALL NOT mutate source snapshots or candidate records.

#### Scenario: A frozen row is hydrated
- **WHEN** every decision-relevant field is available from the registered snapshot or metadata source
- **THEN** the bridge SHALL create typed route, shop, event, or card-reward state with stable source-slot identity
- **AND** canonical hashes of the input snapshot and candidates SHALL remain unchanged after evaluation

#### Scenario: A decision-relevant field is absent
- **WHEN** Current can read a field whose exact value cannot be reconstructed from registered evidence
- **THEN** the row SHALL fail closed with a field-specific reason
- **AND** the bridge SHALL NOT insert a heuristic value that can affect the selected action

### Requirement: Exact Current policy execution
The bridge SHALL invoke the repository's exact `OptimizedAgent` non-combat screen path under a fixed Ironclad configuration with gameplay I/O and tracking disabled, and it SHALL reject optimized-component downgrade or SimpleAgent fallback.

#### Scenario: Current produces a target action
- **WHEN** a supported hydrated decision is evaluated
- **THEN** exactly one Current action object SHALL be emitted without gameplay callback, tracker write, or simulator mutation
- **AND** the report SHALL record the bound Current configuration and fallback status

#### Scenario: Current falls back or raises
- **WHEN** optimized components are unavailable, a fallback path is invoked, or evaluation raises an exception
- **THEN** the row SHALL fail closed
- **AND** no fallback action SHALL be accepted as Current evidence

### Requirement: Unique legal candidate mapping
The bridge SHALL map each emitted Current action to exactly one candidate from the row's validated legal candidate set using category-specific stable identity.

#### Scenario: Route action maps by coordinate
- **WHEN** Current emits a non-boss map-node action
- **THEN** exactly one `route:map_node` candidate with the same `x` and `y` SHALL be selected

#### Scenario: Card reward action maps by mode and slot
- **WHEN** Current takes a card, uses Singing Bowl, or skips
- **THEN** exactly one take candidate with the same source slot, bowl candidate, or skip candidate SHALL be selected respectively

#### Scenario: Shop action maps by kind and slot
- **WHEN** Current buys a card, relic, or potion, removes a card, or leaves
- **THEN** exactly one candidate with the same action kind and source slot SHALL be selected
- **AND** a name-only match SHALL NOT resolve duplicate inventory entries

#### Scenario: Event option semantics are unavailable
- **WHEN** the registered evidence lacks exact semantic labels for an event whose Current path reads option text
- **THEN** the event row SHALL fail with `missing_event_option_semantics`
- **AND** a generic index label SHALL NOT authorize an event action

#### Scenario: Mapping is absent or ambiguous
- **WHEN** zero or multiple legal candidates match the emitted action
- **THEN** the row SHALL fail closed and record the candidate identities considered

### Requirement: Frozen structural gate
The Stage 1 POC SHALL evaluate only the preregistered bounded selection of already-frozen rows and SHALL require schema validity, provenance closure, hydration, exact mapping, deterministic replay, non-mutation, fallback exclusion, and registered category coverage.

#### Scenario: Every Stage 1 gate passes
- **WHEN** all registered rows reproduce the same mapped action for the registered replay count and every structural check passes
- **THEN** the report SHALL emit `frozen_bridge_structurally_compatible`
- **AND** it MAY authorize only the registered Stage 2 compatibility check

#### Scenario: Any Stage 1 gate fails
- **WHEN** a row, category quota, identity, deterministic replay, or non-mutation check fails
- **THEN** the report SHALL emit `frozen_bridge_not_compatible`
- **AND** Stage 2 SHALL remain unauthorized

### Requirement: Episode-local state and bounded compatibility
Stateful evaluation SHALL retain one configured Current agent per registered episode and SHALL process decisions in monotonic episode order. Stage 2 SHALL use only a fixed subset of previously consumed seeds and only after Stage 1 authorization.

#### Scenario: An episode has multiple decisions
- **WHEN** ordered snapshots from one episode are evaluated
- **THEN** route history, shop transition state, and other Current session state SHALL be retained within that episode
- **AND** no state SHALL leak to another episode or deterministic replay

#### Scenario: Stage 2 is authorized
- **WHEN** Stage 1 passes and the Stage 2 registration names only previously consumed seeds
- **THEN** one bounded deterministic own-trajectory compatibility run MAY execute
- **AND** it SHALL report legality and reproducibility without interpreting terminal policy quality

#### Scenario: Fresh or unregistered seed is requested
- **WHEN** Stage 2 contains an untouched, changed, extra, or unregistered seed
- **THEN** execution SHALL stop before simulator rollout

### Requirement: Structural-only evidence authority
Every bridge report SHALL separate structural compatibility from policy quality and SHALL keep baseline-floor, reward, formal-training, fresh-evidence, gameplay, and promotion authority false.

#### Scenario: The bridge POC passes
- **WHEN** Stage 1 and optional Stage 2 both pass
- **THEN** the report SHALL state that a separate preregistered baseline-floor study is required
- **AND** it SHALL NOT update formal RL readiness, select a reward, fit a model, launch gameplay, or authorize training

#### Scenario: The bridge POC fails
- **WHEN** either authorized stage fails
- **THEN** the report SHALL preserve the failure and rollback boundary
- **AND** it SHALL NOT broaden the cohort or repair gameplay policy within this change

### Requirement: Registered Event Semantic Enrichment
The bridge SHALL use a registered adapter semantics contract to enrich a deep copy of an event snapshot only when exact inline option semantics are absent. Existing valid inline semantics SHALL remain authoritative, and original evidence SHALL remain unchanged.

#### Scenario: Missing semantics have exact registered coverage
- **WHEN** a frozen event row lacks inline `option_semantics` and the registered adapter resolver returns complete semantics for exactly the legal candidate indices
- **THEN** the bridge SHALL hydrate Current from an enriched deep copy
- **AND** it SHALL retain canonical equality of the original snapshot and candidates before and after evaluation

#### Scenario: Missing semantics lack exact registered coverage
- **WHEN** the resolver rejects the event identity, phase, legal indices, or provenance
- **THEN** the bridge SHALL fail the row with the resolver's structural blocker
- **AND** it SHALL NOT invoke Current with generic or partial event labels

#### Scenario: Inline semantics already exist
- **WHEN** a frozen event row contains valid complete `option_semantics`
- **THEN** the bridge SHALL use those semantics without resolver replacement
- **AND** it SHALL still require exact equality with the legal candidate indices

### Requirement: Immutable Successor Registration
A bridge recomputation performed by changed implementation code SHALL use a successor registration that binds its predecessor and proves the frozen cohort and evaluation contract unchanged before row execution.

#### Scenario: Successor preserves the predecessor contract
- **WHEN** the successor binds the predecessor registration and canonical output manifest and all registered immutable fields compare equal
- **THEN** the bridge MAY recompute the same frozen Stage 1 rows into a new output directory
- **AND** the report SHALL publish the predecessor binding and immutable-field comparison

#### Scenario: Successor changes an immutable field
- **WHEN** any frozen row or snapshot hash, category minimum, replay count, Current configuration, authority flag, metadata binding, runtime, prior-seed binding, or Stage 2 seed or limit differs from the predecessor
- **THEN** execution SHALL stop before evaluating a row
- **AND** the successor SHALL NOT inherit Stage 1 or Stage 2 authorization

#### Scenario: Stage 1 successor passes
- **WHEN** every unchanged frozen Stage 1 row passes under the registered semantic and implementation identities
- **THEN** the report SHALL emit `frozen_bridge_structurally_compatible`
- **AND** it MAY authorize only the unchanged, already-consumed Stage 2 compatibility check
