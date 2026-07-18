## ADDED Requirements

### Requirement: Exclusive Pre-Request Identity Claim
The system SHALL consume every future launchable qualification identity through one guarded, exclusive, durable bootstrap claim before publishing any later pre-request stage or active request.

#### Scenario: Trusted launcher creates the first claim
- **WHEN** the reviewed trusted launcher begins a future v3 qualification with the exact local no-follow root, claim path, runner SHA-256, request anchors, review commit, and deterministic launch token
- **THEN** it SHALL exclusively create the canonical bootstrap claim before executing the reviewed runner
- **AND** any claim-path entry SHALL make the identity permanently consumed and ineligible for overwrite, deletion, completion, retry, replacement, or reinterpretation

#### Scenario: Claim creation collides or is interrupted
- **WHEN** the claim path already exists, changes identity during publication, becomes malformed or partial, or cannot be published durably
- **THEN** the launcher SHALL fail closed without publishing a later stage, active request, attempt, child, study artifact, gameplay artifact, or authority
- **AND** any existing claim entry SHALL remain consumed and SHALL NOT be repaired or retried

#### Scenario: An observed launch has no claim
- **WHEN** external evidence proves that CommunicationMod attempted the reviewed qualification launch but no valid or malformed claim entry exists
- **THEN** the evidence SHALL remain non-authorizing and SHALL NOT be represented as proof that the launcher never executed
- **AND** the observed identity SHALL be conservatively retired without retry

### Requirement: Immutable Hash-Linked Pre-Request Stages
The system SHALL publish only one contiguous immutable stage chain from trusted-launcher verification through request-bound isolation validation.

#### Scenario: Pre-request validation advances normally
- **WHEN** launcher, runner-entry, source, request/review-chain, and prelaunch-isolation checks complete in order
- **THEN** the qualifier SHALL exclusively publish canonical self-hashed `launcher_verified`, `runner_entered`, `source_verified`, `request_reviewed`, and `isolation_verified` records in that order
- **AND** every record SHALL bind the same qualification identity, launch token, request anchors, review commit, runner SHA-256, process PID, positive timestamp, stage index/name, and previous-record hash

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

### Requirement: Request-Bound Bootstrap Handoff
The system SHALL bind one complete pre-request stage chain to the exact reviewed active request before attempt publication or child launch.

#### Scenario: Active request handoff succeeds
- **WHEN** the exact reviewed v3 request passes source, review-chain, registration, implementation, command, and request-bound isolation checks after `isolation_verified`
- **THEN** the qualifier SHALL exclusively publish those reviewed bytes as the active request and then exclusively publish one handoff binding the claim hash, ordered final stage hash, active-request byte SHA-256, request self-hash, and launch token
- **AND** it SHALL reject attempt publication and child launch until that handoff validates

#### Scenario: Host stops during handoff
- **WHEN** active-request publication succeeds but the host stops before a valid handoff is published
- **THEN** the root SHALL remain an immutable active-request partial that cannot be repaired, retried, or relabeled as a pre-request failure
- **AND** later replay SHALL keep every study, gameplay, policy, causal, and training authority false

#### Scenario: Terminal evidence follows a valid handoff
- **WHEN** the existing attempt, ready, release, child-exit, restoration, and terminal lifecycle proceeds after a valid handoff
- **THEN** result v3 and its review binding SHALL include the independently reconstructable bootstrap inventory, final stage hash, and handoff hash
- **AND** a v3 terminal that omits or changes any bootstrap binding SHALL fail verification

### Requirement: Independent Pre-Request Evidence Replay
The standalone qualification verifier SHALL replay v3 bootstrap evidence without importing producer result builders or trusting current worktree bytes.

#### Scenario: Verifier replays a valid pre-request prefix
- **WHEN** external S/R/request anchors and one guarded qualification root contain a valid claim plus a contiguous stage prefix
- **THEN** the verifier SHALL independently reconstruct the deterministic launch token, expected direct-child paths, canonical records, static anchors, self-hashes, and stage chain
- **AND** it SHALL report the exact last completed stage, `consumed=true`, no retry, and all authority fields false

#### Scenario: Verifier replays a complete v3 lifecycle
- **WHEN** claim, every stage, active request, handoff, attempt, ready, release, terminal, external result anchors, restored isolation, and child-death evidence all match
- **THEN** the verifier SHALL report the existing verified qualification terminal status
- **AND** qualification alone SHALL still leave study `start`, run-lock, collection, OPE interpretation, policy, causal, training, and promotion authority false until their separate reviewed gates pass

#### Scenario: Verifier observes corrupt or extra evidence
- **WHEN** any guarded root entry, record byte, path identity, schema, stage order, hash, anchor, failure class, handoff, terminal, or external anchor differs from independent replay
- **THEN** the verifier SHALL reject positive verification and deterministically classify the supported invalid or partial boundary
- **AND** it SHALL NOT delete evidence, fill gaps, prefer a later record, or return a retryable state

### Requirement: CommunicationMod And Isolation Preservation
Pre-request observability SHALL remain diagnostic-only and SHALL preserve the existing CommunicationMod protocol and live-isolation ownership boundaries.

#### Scenario: Qualification writes bootstrap evidence
- **WHEN** the trusted launcher or qualifier publishes a claim, stage, failure, or handoff
- **THEN** it SHALL write only guarded qualification-root artifacts and SHALL keep CommunicationMod stdout/stderr free of diagnostic and result text
- **AND** it SHALL NOT mutate the AI marker, run records, checkpoints, global AI logs, registered study root, run lock, ledger, manifest, trace, model, or policy

#### Scenario: Failure precedes qualifier-owned restoration
- **WHEN** the process stops before the reviewed request makes exact CommunicationMod restoration and terminal isolation recollection qualifier-owned
- **THEN** bootstrap evidence SHALL claim only the last completed internal stage
- **AND** an external controlled cleanup SHALL stop Java, restore the exact request-bound baseline, recollect isolation, and independently prove no surviving target process before any later candidate decision

#### Scenario: Ordinary gameplay starts without qualification
- **WHEN** the exact v3 qualification launcher and bootstrap anchors are absent
- **THEN** ordinary gameplay, bounded evaluation, registered slot execution, and training commands SHALL preserve their existing startup and artifact behavior
- **AND** they SHALL NOT create or consume bootstrap qualification evidence
