## ADDED Requirements

### Requirement: Normalized Decision-Signature Diagnostics
The system SHALL provide a read-only, versioned normalized decision signature for eligible operating-decision disagreements in addition to the existing full-context fingerprint. A normalized signature SHALL retain every input that selects a Bottled-style adapter branch for its category and SHALL exclude only incidental serialization, ordering, identifier, or retry information. It SHALL NOT replace the exact-context ranking used by the repair gate.

#### Scenario: Group comparable complete disagreements
- **GIVEN** two non-fixture, complete, high-confidence comparison rows with the same category, oracle mode, current/reference decisions, reference-policy branch inputs, and distinct decision occurrences
- **AND** their full-context fingerprints differ only in fields outside the documented normalized signature
- **WHEN** the diagnostic ranker evaluates the rows
- **THEN** it SHALL emit one deterministic normalized review group with both members
- **AND** it SHALL preserve each member's full-context fingerprint and occurrence identity in the report
- **AND** it SHALL leave the exact-context “Most Worth Fixing” ranking unchanged

#### Scenario: Keep material context differences separate
- **GIVEN** two otherwise similar rows that differ in an offered card, enabled event option, purge affordability, adapter HP-threshold side, adapter-relevant relic flag, route feature vector, oracle mode, or reference-policy branch
- **WHEN** the diagnostic ranker evaluates the rows
- **THEN** it SHALL assign different normalized signatures
- **AND** it SHALL NOT represent the rows as repeated support for one review group

#### Scenario: Exclude unsupported or non-independent evidence
- **GIVEN** fixture, partial-evidence, low- or medium-confidence, matched, unsupported, or duplicate-retry rows
- **WHEN** the diagnostic ranker evaluates the rows
- **THEN** it SHALL exclude them from normalized review-group support
- **AND** it SHALL report the exclusion reason or count without presenting the rows as repair evidence

#### Scenario: Preserve the no-repair-first boundary
- **GIVEN** a normalized review group contains two or more eligible distinct occurrences
- **WHEN** the comparator renders its report
- **THEN** it SHALL label the group as diagnostic review evidence rather than a gameplay repair recommendation
- **AND** it SHALL state that an operator must inspect its member contexts and add a failing regression before selecting any gameplay change
- **AND** it SHALL NOT modify gameplay strategy code, training state, model parameters, Communication Mod configuration, or a live run

#### Scenario: Produce reproducible audit output
- **GIVEN** the same ordered fixture and trace inputs with the same signature version
- **WHEN** the comparator is run twice
- **THEN** it SHALL emit the same normalized signature values, grouping, ordering, and exclusion summaries
- **AND** it SHALL include the signature version and source/occurrence identities needed to audit each displayed group
