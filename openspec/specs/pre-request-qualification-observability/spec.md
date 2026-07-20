# pre-request-qualification-observability Specification

## Purpose
Define fail-closed, hash-linked observability from an exclusive qualification identity claim through active-request handoff and independent replay without granting live, study, training, or policy authority.

## Requirements

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
- **AND** before `source_verified`, the qualifier SHALL freeze the exact raw bytes and opened-file identities accepted by descriptor-bound no-follow reviewed-source reads and install both as immutable allowlists for subsequent project-source imports

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

### Requirement: Reviewed R7 Offline Preparation
The system SHALL prepare at most one previously absent r7 qualification candidate entirely offline before publishing its external root or changing CommunicationMod configuration.

#### Scenario: R7 preparation starts from an absent identity
- **WHEN** this amendment is approved and the exact r7 root, claim, stage, request, handoff, attempt, ready, release, terminal, failure, and attestation paths are all lexically absent
- **THEN** preparation SHALL freeze one clean implementation snapshot S, the unchanged canonical study registration, exact implementation and runner hashes, the registered no-action command, the current CommunicationMod bytes, protected marker/run/checkpoint/global-log inventories, and a zero-target-process observation
- **AND** it SHALL render one canonical qualification request-v3/bootstrap-v1 candidate with a fresh launch token, guarded root, fixed direct-child paths, exact restoration baseline, and uniformly false study, collection, OPE, policy, causal, training, and promotion authority
- **AND** all candidate bytes SHALL remain in a repository-local review area until the offline go/no-go gate passes

#### Scenario: Direct-child review material is frozen
- **WHEN** the candidate request, launcher vector, runner hash, source inventory, rollback material, and expected static-root inventory have been rendered deterministically
- **THEN** one direct-child review commit R SHALL contain only the exact inert allowlisted preparation and prelaunch-review paths declared by the request
- **AND** independent source-only replay SHALL prove `R` is the direct child of `S`, `HEAD == R`, the exact S-to-R diff matches the allowlist, every executable or importable path matches R, and all request/review/bootstrap hashes reproduce without trusting current mutable evidence

#### Scenario: Offline review rejects the candidate
- **WHEN** any source, Git, request, review, launcher, path, configuration, inventory, rollback, canonical-byte, hash, authority, or absence check fails before live publication
- **THEN** the system SHALL leave the external r7 root and CommunicationMod configuration unchanged and SHALL NOT launch Java, ModTheSpire, the qualifier, or a child
- **AND** it SHALL preserve the rejected preparation as obsolete and non-authorizing, stop this amendment, and route any implementation defect through a separate regression-backed source-fix change rather than modifying source and continuing with r7

#### Scenario: Offline go-no-go passes
- **WHEN** strict OpenSpec validation, focused and full regression evidence applicable to the frozen source, canonical rendering, exact diff review, independent source-only review, root absence, baseline capture, and rollback rehearsal all pass
- **THEN** the system MAY publish exactly the reviewed static r7 root and exact live launch configuration for one invocation
- **AND** no preparation byte, source byte, request anchor, runner hash, root path, baseline, or protected inventory MAY change between the recorded go decision and invocation
- **AND** every review transcript and go/no-go record created after R SHALL remain outside the guarded repository worktree and SHALL be bound by external path, size, and SHA-256 anchors so qualification still observes `HEAD == R` and a clean source inventory

### Requirement: At-Most-Once R7 Live Qualification
The system SHALL invoke r7 at most once through the reviewed v3 launcher and SHALL preserve either an immutable independently replayable result when the required anchors exist or an immutable independently attested external boundary when they do not.

#### Scenario: R7 is invoked through CommunicationMod
- **WHEN** the reviewed offline go/no-go record is current, the external static root exactly matches its request-bound inventory, protected live state still matches the baseline, no target process survives, and CommunicationMod contains the exact reviewed launcher literal and bounded initialization timeout
- **THEN** the operator SHALL invoke ModTheSpire exactly once with CommunicationMod launching `D:\anaconda\envs\stsai\python.exe` through the fixed stdlib bootstrap token
- **AND** the trusted launcher SHALL exclusively create the r7 claim before runner execution, the qualifier SHALL own the no-action handshake and child, and no second invocation, retry, replacement, repair, or timeout-only reinterpretation SHALL be permitted

#### Scenario: R7 publication fails closed without an issued invocation
- **WHEN** the external static root and reviewed CommunicationMod launch configuration have been published, a final comparison fails before the operator issues the ModTheSpire invocation, target-process inventory remains zero, and every control and result path remains absent
- **THEN** the operator SHALL NOT launch ModTheSpire, Java, the qualifier, or a child and SHALL preserve the published static root without deletion, repair, replacement, or reuse
- **AND** the exact CommunicationMod baseline SHALL be restored and independently attested together with protected-state equality, unchanged zero-target-process inventory, absent control/result paths, and evidence that the operator invocation command was not issued
- **AND** r7 SHALL be classified as `retired_after_publication_without_invocation`, with no claim about a live protocol boundary and every study, collection, OPE, policy, causal, training, and promotion authority false

#### Scenario: R7 publication encounters a possible live boundary
- **WHEN** the external static root and reviewed CommunicationMod launch configuration have been published but a target process, control path, launch observation, or uncertainty appears before the planned operator invocation
- **THEN** the operator SHALL NOT issue that invocation and SHALL preserve the root and exact observed evidence without inferring whether the trusted launcher executed
- **AND** controlled cleanup SHALL stop owned or target processes when required, restore the exact CommunicationMod baseline, independently recollect protected isolation, and classify r7 as `retired_after_live_boundary` without retry or current authority

#### Scenario: R7 reaches a valid terminal
- **WHEN** claim, every ordered pre-request stage, active request, handoff, attempt, ready, release, child zero exit, request-owned restoration, terminal, external result anchors, and zero-surviving-process evidence all validate
- **THEN** the standalone verifier SHALL independently reproduce the complete v3 lifecycle and emit one canonical attestation bound to the exact request, result, root inventory, restored configuration, protected inventory comparison, source anchors, and terminal hashes
- **AND** r7 SHALL be classified as qualified only for a later separately reviewed study `start` decision, with every current authority field still false
- **AND** the qualified handoff and closeout SHALL remain externally anchored without any tracked write, task update, commit, sync, archive, or checkout change after R until the later `start` decision declines launch or the frozen-study run-lock no-write window closes

#### Scenario: R7 stops at a partial or invalid boundary
- **WHEN** the observed root contains a claim or later evidence but lacks a complete valid terminal and attestation, contains malformed or unexpected evidence, or any source, process, configuration, inventory, cleanup, or external-anchor fact is uncertain
- **THEN** independent replay SHALL classify only the exact supported partial, invalid, abrupt, or failed boundary and SHALL mark r7 consumed and retired
- **AND** the system SHALL preserve every root byte and recorded absence, terminate owned and target processes when controlled cleanup requires it, restore the exact request-bound CommunicationMod baseline, and independently recollect isolation without deleting, repairing, retrying, or relabeling r7

#### Scenario: No valid claim is externally observable after launch attempt
- **WHEN** external process or CommunicationMod evidence proves the reviewed launch was attempted but the r7 root contains neither a valid nor malformed claim entry
- **THEN** the closeout SHALL report only the externally supported launch-attempt boundary and SHALL NOT infer that the trusted launcher never executed
- **AND** r7 SHALL be conservatively retired, the exact baseline SHALL be restored and attested, and no second invocation SHALL occur

#### Scenario: Live qualification remains no-action
- **WHEN** any r7 live branch executes or closes
- **THEN** no study root, run lock, ledger, slot, gameplay action, run record, AI marker, checkpoint, model, policy, training artifact, or OPE output SHALL be created or mutated
- **AND** the final closeout SHALL leave study `start`, collection, outcome interpretation, policy change, causal claim, training, and promotion authority false
