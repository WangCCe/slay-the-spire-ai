## ADDED Requirements

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
