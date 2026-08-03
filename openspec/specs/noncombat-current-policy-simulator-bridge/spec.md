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

#### Scenario: A native shop has consumed card removal
- **WHEN** a validated shop snapshot reports `remove_cost == -1` and its legal candidate set contains no `remove_card` action
- **THEN** the bridge SHALL hydrate removal as unavailable with a policy-inert nonnegative typed cost
- **AND** it SHALL preserve the source snapshot and candidates byte-for-byte

#### Scenario: A shop remove-cost sentinel is inconsistent
- **WHEN** `remove_cost == -1` is paired with a legal `remove_card` candidate, or the reported cost is below `-1`, missing, boolean, or non-integer
- **THEN** the bridge SHALL fail with a field-specific structural blocker before Current executes
- **AND** it SHALL NOT infer removal availability or replace an unproven negative value

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
The bridge SHALL map each emitted Current action to exactly one candidate from the row's validated legal candidate set using category-specific stable identity, and event actions SHALL translate through the validated Current-position-to-simulator-index observation rather than direct integer equality.

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

#### Scenario: Event action maps through two coordinates
- **WHEN** Current emits `ChooseAction` for a validated event observation
- **THEN** its choice index SHALL select exactly one contiguous Current-position row and that row's simulator choice index SHALL select exactly one legal event candidate
- **AND** a sparse simulator index SHALL NOT be compared directly with the Current position

#### Scenario: Event option semantics are unavailable
- **WHEN** registered evidence lacks an exact total observation for an event whose Current path reads option text
- **THEN** the event row SHALL fail with the resolver's field-specific blocker
- **AND** a generic index label SHALL NOT authorize an event action

#### Scenario: Mapping is absent or ambiguous
- **WHEN** zero or multiple legal candidates match the stable category identity or validated event observation row
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
Stateful evaluation SHALL retain one configured Current agent per registered episode and SHALL process decisions in monotonic episode order. Historical Stage 2 SHALL remain limited to its fixed reused-seed registration, while any API v3 total-event native compatibility run SHALL use an independent pushed registration and untouched fixed cohort without inheriting historical authorization.

#### Scenario: An episode has multiple decisions
- **WHEN** ordered snapshots from one episode are evaluated
- **THEN** route history, shop transition state, and other Current session state SHALL be retained within that episode
- **AND** no state SHALL leak to another episode or deterministic replay

#### Scenario: Historical Stage 2 is authorized
- **WHEN** its frozen Stage 1 passes and the Stage 2 registration names only its previously consumed seeds
- **THEN** one bounded deterministic own-trajectory compatibility run MAY execute under that historical registration
- **AND** it SHALL report legality and reproducibility without interpreting terminal policy quality

#### Scenario: API v3 total-event compatibility is requested
- **WHEN** the completed total event implementation is evaluated on native own trajectories
- **THEN** a separate registration SHALL bind the API v3 module, total observation identity, implementation, new fixed cohort, replay count, limits, publication contract, and all-false authority
- **AND** neither the historical Stage 1 verdict nor its consumed Stage 2 seeds SHALL grant or transfer execution authority

#### Scenario: A native event action is evaluated
- **WHEN** Current returns a position for an event observation during the registered API v3 cohort
- **THEN** the episode SHALL record the exact total-contract source, Current position, simulator choice index, and uniquely mapped legal action
- **AND** state SHALL remain episode-local across every event phase and follow-up decision

#### Scenario: Unregistered or previously reserved seed is requested
- **WHEN** execution contains an extra, changed, selected, consumed, training, validation, or reserved final-test seed
- **THEN** execution SHALL stop before simulator rollout
- **AND** the evaluator SHALL NOT substitute another seed

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

### Requirement: Implementation-Only Event Bridge Boundary
The total event observation implementation change SHALL prove code-level structural behavior without executing a native simulator cohort or granting evaluation, gameplay, policy-quality, baseline-floor, reward, formal-RL, training, or promotion authority.

#### Scenario: Implementation verification passes
- **WHEN** focused regressions, strict OpenSpec validation, and the repository commit gate pass
- **THEN** the implementation MAY be recorded as ready for a separately preregistered compatibility evaluation
- **AND** no seed, native environment, gameplay process, model, or trainer SHALL run within this change

#### Scenario: A compatibility result is requested
- **WHEN** a caller asks this implementation change to prove own-trajectory compatibility or policy quality
- **THEN** the request SHALL remain blocked pending a separate registration and change
- **AND** historical consumed seeds SHALL NOT be retried as an implementation test

### Requirement: Registered Event Semantic Enrichment
The bridge SHALL use the hash-bound total event observation contract to enrich a deep copy of an event snapshot only when exact inline option semantics are absent. It SHALL normalize every accepted event option to distinct Current-position and simulator-index coordinates while leaving original evidence unchanged.

#### Scenario: Missing semantics have exact total contract coverage
- **WHEN** an event row lacks inline semantics and the registered resolver returns a complete observation for exactly the legal candidates
- **THEN** the bridge SHALL hydrate Current using the observation's Current event id, labels, and contiguous positions
- **AND** it SHALL retain the simulator indices only for reverse candidate mapping

#### Scenario: Missing semantics lack exact contract coverage
- **WHEN** the resolver rejects contract identity, event identity, phase, legal candidates, dynamic context, or provenance
- **THEN** the bridge SHALL fail the row with the resolver's structural blocker
- **AND** it SHALL NOT invoke Current with generic, partial, or stale event labels

#### Scenario: Versioned inline semantics already exist
- **WHEN** an event row contains complete inline semantics with explicit Current positions and simulator choice indices matching the legal candidates
- **THEN** the bridge SHALL preserve their labels and normalize them in a deep copy without resolver replacement
- **AND** hydration and reverse mapping SHALL use their separate coordinates

#### Scenario: Legacy inline semantics are unambiguous
- **WHEN** legacy inline semantics contain only choice indices, labels, and text and both those choice indices and legal simulator indices are exactly `0..n-1`
- **THEN** the bridge MAY normalize each legacy index as both Current position and simulator choice index in its deep copy
- **AND** it SHALL preserve the original snapshot and candidates byte-for-byte

#### Scenario: Legacy inline semantics are ambiguous
- **WHEN** legacy semantics or legal candidates are sparse, reordered, duplicate, partial, extra, or otherwise cannot prove both coordinates
- **THEN** the bridge SHALL fail before Current executes
- **AND** it SHALL NOT infer which coordinate a legacy index represents

#### Scenario: Current returns an invalid event position
- **WHEN** Current returns a negative, non-integer, out-of-range, or otherwise unregistered position
- **THEN** reverse mapping SHALL fail with a position-specific blocker
- **AND** no nearest or default simulator candidate SHALL be selected

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

### Requirement: Audited Generic Event Enrichment
For new code-level sessions, the bridge SHALL enrich a native event without inline option semantics through the reachable-surface successor resolver, while preserving source snapshot and candidate bytes and retaining historical registration validation by schema.

#### Scenario: A generic native event is hydrated
- **WHEN** the event is in the audited generic set and its candidates satisfy the successor contract
- **THEN** the bridge SHALL hydrate contiguous Current options, call Current with the registered event identity, and reverse-map the selected Current position to the exact simulator choice index
- **AND** diagnostics SHALL record upstream and Current event ids, event data, semantic source, Current position, simulator choice index, and selected action id

#### Scenario: An explicit native event is hydrated
- **WHEN** the event is covered by an explicit static, phased, or dynamic rule
- **THEN** the bridge SHALL use the explicit successor rule and preserve its stronger checks
- **AND** generic enrichment SHALL NOT shadow or relax that rule

#### Scenario: Event enrichment cannot prove its source
- **WHEN** the event is outside the explicit and generic sets or any identity, candidate, mutation, mapping, or Current-handling proof fails
- **THEN** the bridge SHALL stop before issuing a simulator action
- **AND** it SHALL NOT fall back to candidate position zero merely because Current's present default would select it

### Requirement: Successor Bridge Has Structural-Only Authority
The reachable-surface bridge extension SHALL establish only code-level observation and action-mapping behavior and SHALL grant no native execution or policy-quality authority.

#### Scenario: All source-only bridge regressions pass
- **WHEN** explicit, generic, sparse-index, phase, dynamic-context, mutation, unknown-event, and historical-isolation tests pass
- **THEN** the extension MAY be recorded as ready for a separate compatibility preregistration
- **AND** gameplay, baseline-floor, outcome, reward, model, OPE, formal-RL, training, qualification, loading, and promotion authority SHALL remain false
