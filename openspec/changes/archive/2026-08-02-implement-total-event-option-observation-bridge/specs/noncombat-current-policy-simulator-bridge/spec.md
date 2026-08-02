## ADDED Requirements

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

## MODIFIED Requirements

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
