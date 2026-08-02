## ADDED Requirements

### Requirement: Reachable-Surface Successor Contract
The system SHALL publish a versioned successor observation contract whose explicit policy-sensitive rules and audited generic-default identities are disjoint and whose union equals the complete registered reachable event-option target surface.

#### Scenario: The successor partition is valid
- **WHEN** the source-only reachable audit and frozen predecessor contract are loaded under their exact identities
- **THEN** the successor SHALL retain all 25 explicit rules and register all 23 generic-default event identities without overlap or an unaccounted target
- **AND** it SHALL bind the 2 disabled and 1 direct-transition pool identities as excluded evidence rather than event-option rules

#### Scenario: A predecessor or audit identity drifts
- **WHEN** the predecessor contract, reachable audit, simulator source, Current source, or partition hash differs
- **THEN** successor contract validation SHALL fail before resolver use
- **AND** no generic event SHALL be admitted from an unregistered runtime observation

### Requirement: Audited Generic Default Rule
For a registered generic event, the successor resolver SHALL derive Current-visible options from exact ordered native candidates while preserving separate contiguous Current positions and simulator choice indices.

#### Scenario: A registered generic event is resolved
- **WHEN** event id and name match one generic identity and candidates are non-empty, ordered, unique, source-bound event options with valid indices and labels
- **THEN** the resolver SHALL assign Current positions `0..n-1`, retain each candidate simulator index, and use the candidate label as non-empty label and text
- **AND** the semantic source SHALL identify the reachable-surface successor contract

#### Scenario: Generic evidence is ambiguous or unsupported
- **WHEN** identity is unknown, explicit and generic sets overlap, candidate order or indices are invalid, labels are empty, or Current AST evidence is absent or drifted
- **THEN** resolution SHALL fail with a field-specific blocker
- **AND** it SHALL NOT use inline fallback, fuzzy identity, a guessed label, or position-equals-index assumptions

### Requirement: Explicit And Historical Semantics Remain Isolated
The successor SHALL preserve explicit static, phased, and dynamic rules without converting them to generic semantics and SHALL preserve the frozen predecessor contract and its historical readers byte-for-byte.

#### Scenario: An explicit event is resolved
- **WHEN** an event identity has a predecessor explicit rule
- **THEN** that explicit rule SHALL take precedence and retain all phase, context, candidate, and dual-coordinate checks
- **AND** the event SHALL NOT be eligible for generic resolution

#### Scenario: Historical evidence is verified
- **WHEN** a frozen registration names the predecessor semantic identity
- **THEN** schema-aware verification SHALL require that exact predecessor identity
- **AND** it SHALL NOT silently upgrade the registration or authorize a consumed cohort retry
