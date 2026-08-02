## ADDED Requirements

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
