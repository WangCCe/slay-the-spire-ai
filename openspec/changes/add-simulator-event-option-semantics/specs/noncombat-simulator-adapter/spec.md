## ADDED Requirements

### Requirement: Source-Bound Event Option Semantics
The offline adapter layer SHALL resolve event-option semantics only from a versioned contract that binds the exact upstream event identity, phase, legal candidate indices, semantic labels and effects, simulator parent commit, and simulator source digest. Unsupported or drifted states SHALL fail closed.

#### Scenario: Supported Liars Game state is resolved
- **WHEN** a validated event snapshot identifies `Liars Game` at phase zero, the legal candidates have exactly indices zero and one, and simulator provenance matches the registered semantic contract
- **THEN** the resolver SHALL return ordered `Agree` and `Disagree` semantics whose text matches the upstream effects for the snapshot ascension
- **AND** it SHALL leave the source snapshot and candidate records byte-equivalent

#### Scenario: Event state is not exactly supported
- **WHEN** the event id, phase, candidate indices, candidate uniqueness, or simulator provenance differs from the registered semantic contract
- **THEN** the resolver SHALL fail with a field-specific reason
- **AND** it SHALL NOT return generic index labels or partial semantics

#### Scenario: Broader event coverage is requested
- **WHEN** an event has no explicitly registered semantic contract
- **THEN** the adapter SHALL report that event as unsupported
- **AND** the presence of a console display name or legal numeric action SHALL NOT imply semantic coverage
