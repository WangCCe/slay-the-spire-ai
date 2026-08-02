## ADDED Requirements

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

## MODIFIED Requirements

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
