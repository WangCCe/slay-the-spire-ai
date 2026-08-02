# Non-Combat Event Option Observation Contract Specification

## Purpose

Define a provenance-bound, total, and fail-closed mapping from simulator event
choice indices and dynamic context to Current-visible event option positions and
labels without granting resolver, evaluation, gameplay, or training authority.

## Requirements

### Requirement: Provenance-Bound Observation Contract
The event-option observation contract SHALL run only from an explicit registration that binds its implementation, the corrected r2 audit registration and artifacts, exact Current and upstream identities, reviewed event rules, expected outputs, and all-false authority.

#### Scenario: Every registered identity matches
- **WHEN** the validator opens the contract registration and every bound source and predecessor artifact has its registered path, size, and SHA-256
- **THEN** it SHALL validate the contract from those exact bytes
- **AND** it SHALL NOT import or execute the native simulator, bridge resolver, gameplay runtime, model, or trainer

#### Scenario: Any identity or authority drifts
- **WHEN** a bound input is missing, changed, outside its declared root, or any authority flag is true
- **THEN** validation SHALL fail before publishing contract evidence
- **AND** no prior contract result SHALL be reused

### Requirement: Total Current Event Identity Coverage
The contract SHALL account exactly once for every one of the 25 canonical events and all 47 aliases in the corrected r2 inventory and SHALL bind each upstream enum, event id, event name, and Current hydration id.

#### Scenario: Identity coverage is total
- **WHEN** registered event rules reconcile with the corrected r2 inventory
- **THEN** every canonical event and alias SHALL have one unambiguous observation rule
- **AND** upstream `Mindbloom` SHALL map to the Current-recognized `MindBloom` hydration id

#### Scenario: Event identity is unknown or ambiguous
- **WHEN** an event, alias, upstream identity, or Current hydration id is missing, duplicated, or differs from the registered rule
- **THEN** the contract SHALL fail with an identity-specific blocker
- **AND** it SHALL NOT fuzzy-match or select a default event

### Requirement: Reversible Position And Simulator-Index Mapping
For every validated legal event candidate set, the contract SHALL produce an ordered observation row for each candidate containing a contiguous Current position, the original simulator choice index, and a non-empty Current-facing label.

#### Scenario: Legal candidates use contiguous indices
- **WHEN** simulator choice indices are `0..n-1` and every index has a registered label
- **THEN** each Current position SHALL map reversibly to the equal simulator index
- **AND** labels SHALL retain the registered source order

#### Scenario: Legal candidates are sparse
- **WHEN** a legal candidate set contains sparse simulator indices such as Cleric Leave at index 2 or Cursed Tome Continue at index 3
- **THEN** Current positions SHALL remain contiguous from zero while preserving each sparse simulator index in the mapping
- **AND** a future Current action SHALL be translatable through that mapping rather than direct integer equality

#### Scenario: Candidate mapping is invalid
- **WHEN** candidate indices are duplicate, unordered, unknown for the event, event-mismatched, or lack a registered non-empty label
- **THEN** the contract SHALL fail closed with the exact candidate blocker
- **AND** it SHALL NOT synthesize a generic index label

### Requirement: Explicit Dynamic Observation Rules
The contract SHALL represent every decision-relevant dynamic event label or phase with a named schema and SHALL reject missing, extra, or inconsistent dynamic context.

#### Scenario: Cursed Tome phase is supported
- **WHEN** `event_data` is 0, 1, 2, 3, or 4 and the legal candidate indices match the registered phase table
- **THEN** the contract SHALL map phase 0 to Read/Leave at indices 0/1, phases 1/2/3 to Continue at index 2/3/4, and phase 4 to Take/Stop at indices 5/6
- **AND** each visible option SHALL receive its contiguous Current position

#### Scenario: Cursed Tome phase or candidates drift
- **WHEN** `event_data` is outside 0 through 4 or its candidate set differs from the registered phase table
- **THEN** the contract SHALL fail with a phase-specific blocker
- **AND** it SHALL NOT infer a phase from a label or choose a nearby index

#### Scenario: N'loth offered relics are complete
- **WHEN** indices 0 and 1 have distinct offered-relic records whose slots, ids, and names match the bound snapshot relic list
- **THEN** their labels SHALL be `Offer <relic name>` and index 2 SHALL retain `Leave`
- **AND** the contract SHALL record the offered-relic context schema required from a future adapter snapshot

#### Scenario: N'loth offered relics are unavailable or inconsistent
- **WHEN** an offered slot, id, or name is absent, duplicated, out of range, or differs from the snapshot relic record
- **THEN** the contract SHALL report that runtime observation as unresolved
- **AND** resolver and adapter readiness SHALL remain false

### Requirement: Deterministic Contract Evidence Without Runtime Authority
The validator SHALL publish canonical configuration, contract, metrics, report, and manifest artifacts that recompute byte-for-byte and SHALL describe observation coverage only, not policy quality or RL readiness.

#### Scenario: Contract publication succeeds
- **WHEN** all identity, coverage, mapping, dynamic-rule, provenance, and authority checks pass
- **THEN** the artifacts SHALL report 25 events, 47 aliases, zero unaccounted surfaces, and every required dynamic context field
- **AND** recomputation SHALL reject any byte difference, missing artifact, or extra managed file

#### Scenario: Contract evidence is complete
- **WHEN** every registered observation rule is structurally validated
- **THEN** resolver implementation and adapter readiness SHALL remain false until a separate reviewed change implements the contract
- **AND** simulator execution, seed use, compatibility evaluation, baseline measurement, gameplay, reward, model fitting, formal RL, training, and promotion SHALL remain unauthorized
