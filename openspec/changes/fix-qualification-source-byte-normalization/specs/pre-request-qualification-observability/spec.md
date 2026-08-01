## MODIFIED Requirements

### Requirement: Immutable Hash-Linked Pre-Request Stages
The system SHALL publish only one contiguous immutable stage chain from trusted-launcher verification through request-bound isolation validation.

#### Scenario: Pre-request validation advances normally
- **WHEN** launcher, runner-entry, source, request/review-chain, and prelaunch-isolation checks complete in order
- **THEN** the qualifier SHALL exclusively publish canonical self-hashed `launcher_verified`, `runner_entered`, `source_verified`, `request_reviewed`, and `isolation_verified` records in that order
- **AND** every record SHALL bind the same qualification identity, launch token, request anchors, review commit, runner SHA-256, process PID, positive timestamp, stage index/name, and previous-record hash
- **AND** before `source_verified`, the qualifier SHALL freeze the exact raw bytes and opened-file identities accepted by descriptor-bound no-follow reviewed-source reads and install both as immutable allowlists for subsequent project-source imports

#### Scenario: Reviewed source uses an exact or normalized checkout representation
- **WHEN** descriptor-bound no-follow source reads produce raw bytes whose Git blob object ID exactly matches the reviewed tree object
- **THEN** the qualifier SHALL accept and freeze those exact raw bytes without requiring line-ending conversion
- **AND** when the raw object ID does not match, the qualifier MAY accept the bytes only when the existing fixed-environment Git text conversion reproduces the reviewed tree object
- **AND** `.gitattributes` SHALL remain raw-byte exact, SHALL permit only the existing safe text directives plus Git's literal built-in `binary` token, and SHALL reject every custom macro, filter, external conversion, substantive or binary tamper, path, identity, or inventory mismatch before `source_verified`

#### Scenario: Reviewed source changes after validation
- **WHEN** a project source is replaced, linked, changed, restored, or newly introduced after reviewed-source validation and before or during a later import
- **THEN** the source-only loader SHALL re-read the requested path through a no-follow descriptor with opened-file identity checks and require exact matches to both the immutable validated raw bytes and validation-time opened-file identity before compilation
- **AND** any unbound path, unsafe identity, or byte mismatch SHALL stop before module code executes and SHALL NOT publish `request_reviewed`, an active request, an attempt, or a child

#### Scenario: Controlled validation fails before active request
- **WHEN** a controlled failure occurs after claim creation and before active-request publication
- **THEN** the qualifier SHALL attempt to exclusively publish one canonical failure record bound to the last completed stage with a fixed failure code, exception type, optional numeric OS code, and bounded sanitized detail
- **AND** it SHALL remain silent on CommunicationMod stdout/stderr and SHALL NOT include environment values, arbitrary process output, gameplay outcomes, secrets, or authority

#### Scenario: Process stops without a failure record
- **WHEN** the qualification process stops after a valid claim or stage prefix without publishing a valid failure record or active request
- **THEN** independent replay SHALL classify only `abrupt_after_<last-stage>` or an invalid claim boundary supported by the existing bytes
- **AND** it SHALL NOT infer the in-progress operation, use offline timing as live proof, or permit another invocation

#### Scenario: Stage evidence is malformed or non-contiguous
- **WHEN** a stage is missing, duplicated, reordered, non-canonical, hash-disconnected, anchor-inconsistent, non-regular, linked, replaced, partially published, or accompanied by an unexpected root entry
- **THEN** the evidence SHALL be consumed and fail closed as invalid
- **AND** no later valid-looking stage, request, handoff, terminal, or audit SHALL repair or promote it
