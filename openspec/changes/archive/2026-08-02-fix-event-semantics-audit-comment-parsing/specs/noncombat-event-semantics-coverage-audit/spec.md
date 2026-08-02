## MODIFIED Requirements

### Requirement: Four-Source Upstream Coverage Matrix
For every canonical Current event, the audit SHALL bind the upstream event identity and uniquely inventory its legal-action, display-label, and execution source cases, including statically visible phases, conditions, masks, indices, and labels. C++ comments SHALL NOT contribute case labels, conditions, phase signals, return expressions, display entries, or execution indices, while raw source spans and hashes SHALL remain exact.

#### Scenario: Upstream source surface is complete
- **WHEN** one enum and save-id identity plus unique legal-action, display-label, and execution cases exist and statically observed display indices cover the legal-index union
- **THEN** the event SHALL be classified `source_complete`
- **AND** the row SHALL retain all raw source paths, line spans, and conditional or phase-sensitive signals derived only from active code

#### Scenario: Commented source resembles active semantics
- **WHEN** a bound case span contains line-commented or block-commented case labels, conditions, returns, display output, or numeric execution cases
- **THEN** those commented tokens SHALL contribute no semantic evidence
- **AND** comment markers inside supported string or character literals SHALL remain literal content

#### Scenario: C++ lexical structure is unsupported or malformed
- **WHEN** a comment or supported literal is unterminated or the bounded masker encounters unsupported raw-string syntax
- **THEN** the audit SHALL fail with a field-specific parser blocker
- **AND** it SHALL NOT analyze the raw ambiguous span with regex fallback

#### Scenario: Upstream evidence is incomplete or ambiguous
- **WHEN** a mapping or active-code case is absent or duplicated, a legal index lacks a display label, or a dynamic construct exceeds the bounded parser
- **THEN** the event SHALL be classified `source_partial` or the audit SHALL fail closed when accounting cannot remain exact
- **AND** the exact missing proof SHALL be recorded without guessed semantics

### Requirement: Deterministic Coverage Artifacts
The audit SHALL publish a canonical configuration, event inventory, summary metrics, Markdown report, and manifest whose hashes and row counts can be recomputed byte-for-byte from the registered sources. A correction to published evidence SHALL use a fresh implementation-bound registration and output directory and SHALL preserve the predecessor artifacts unchanged.

#### Scenario: Audit publication succeeds
- **WHEN** identity and accounting gates pass for all Current-relevant events
- **THEN** every event SHALL appear exactly once in the sorted inventory and aggregate counts SHALL reconcile with the report and manifest
- **AND** recomputation SHALL reject any byte difference, missing artifact, or extra output file

#### Scenario: A corrected audit supersedes a predecessor
- **WHEN** a registered parser correction changes previously published semantic evidence
- **THEN** a deterministic predecessor-to-successor delta SHALL name every changed semantic field and prove all required invariant counts and authority values unchanged
- **AND** any unregistered delta SHALL block successor closeout
