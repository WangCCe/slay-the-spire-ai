# noncombat-outcome-evidence-expansion Specification

## Purpose
Define a pre-registered, source-bound, blinded, and fail-closed study lifecycle for expanding known-propensity non-combat outcome evidence without authorizing training or live promotion.

## Requirements

### Requirement: Immutable Outcome-Evidence Registration
The system SHALL require a committed, versioned registration that fixes the outcome-evidence study before any registered game starts.

#### Scenario: Registration is valid
- **WHEN** the study registration is created
- **THEN** it SHALL contain exactly 24 ordered slots of 25 games, deterministic session IDs and seeds, the fixed eval command contract, `card_reward=300` basis points, `shop=1000` basis points, a two-attempt per-run alternative budget, output naming rules, integrity rules, final evidence thresholds, and a canonical registration hash
- **AND** it SHALL fix deterministic Current, the committed calibration artifact path, the deterministic bootstrap seed, the 95 percent confidence level, and exactly 10,000 production bootstrap replicates
- **AND** it SHALL identify `card_reward:skip` and `shop:leave` as the only executable alternatives while event and route remain shadow-only

#### Scenario: Registration-controlled value changes
- **WHEN** any registered slot, seed, session ID, command field, exploration rate, budget, threshold, or output rule differs from the committed registration
- **THEN** the study SHALL reject the changed value
- **AND** it SHALL NOT silently regenerate or partially apply the schedule

### Requirement: Source-Bound Study Run Lock
The system SHALL bind all registered sessions to one immutable clean source and live-isolation lock created before the first slot launches.

#### Scenario: Study lock is created
- **WHEN** the start command runs from a tracked-clean source before slot one
- **THEN** it SHALL bind the registration bytes and hash, actual HEAD, hash-bound implementation files, Windows Python path, exact child command, CommunicationMod semantic configuration, and checkpoint isolation snapshot
- **AND** every generated slot configuration and session manifest SHALL reference the same run-lock hash

#### Scenario: Locked source or live state drifts
- **WHEN** a later slot observes a different source, registration, command, Python path, CommunicationMod semantic configuration, or checkpoint snapshot
- **THEN** the system SHALL record a global integrity stop before launching another game
- **AND** the affected study SHALL NOT qualify through later restoration or additional collection

### Requirement: Fixed Non-Replacement Slot Schedule
The system SHALL enforce the 24-slot registration as an outcome-independent upper bound of 600 game attempts.

#### Scenario: Registered slot launches normally
- **WHEN** the next ordered slot has not previously launched and the run lock remains valid
- **THEN** the runner SHALL launch it at most once with `--max-games 25` and `--eval`
- **AND** it SHALL reject training flags, model mutation flags, unregistered session IDs, and out-of-order replacement slots

#### Scenario: Slot exits before 25 complete trajectories
- **WHEN** a launched slot exits early for an operational reason without a global integrity failure
- **THEN** the ledger SHALL mark that slot terminally interrupted and preserve its complete eligible evidence
- **AND** the system SHALL NOT restart, replace, or add games to that slot

#### Scenario: Outcome evidence appears during collection
- **WHEN** a victory, supported victory, OPE estimate, or comparison result could be derived before slot 24 is terminal
- **THEN** that outcome SHALL NOT change the registered schedule, rates, thresholds, source, or continuation rule
- **AND** no success-based early stop or post-slot-24 extension SHALL be permitted

### Requirement: Blinded Structural Collection Monitor
The system SHALL provide a collection-time monitor that exposes integrity and progress without exposing study outcomes or policy evaluation.

#### Scenario: Study remains in collection phase
- **WHEN** at least one registered slot is not terminal and no global integrity closeout has started
- **THEN** monitor output MAY report slot lifecycle, process exit, artifact existence, manifest and configuration hashes, exact replay and confirmation counts, conservative run-join completeness, and isolation status
- **AND** it SHALL omit victory values and counts, floor reached, killed-by values, target weights, ESS, OPE estimates, bootstrap and influence results, and policy-comparison gates

#### Scenario: Blinded artifact is rendered
- **WHEN** a machine-readable or Markdown collection monitor artifact is written
- **THEN** its schema and rendered text SHALL contain none of the registered forbidden outcome or evaluation fields
- **AND** deterministic rendering SHALL be invariant to input enumeration order

### Requirement: Fail-Closed Study Integrity
The system SHALL stop registered collection when evidence can no longer be attributed to the frozen study contract.

#### Scenario: Global integrity condition fails
- **WHEN** source or isolation drifts, a launched session is missing from the ledger, exact replay or confirmation fails, a manifest hash mismatches, or an unregistered session is presented as study evidence
- **THEN** the system SHALL append the exact global stop reason and prevent later slot launches
- **AND** finalization SHALL produce a blocked closeout without treating restoration or selective exclusion as a cure

#### Scenario: Gameplay diagnosis requires inspection
- **WHEN** an operationally stuck or failed process requires logs or a screenshot to diagnose safely
- **THEN** the operator MAY inspect the minimum evidence required to stop or recover the process
- **AND** any observed outcome SHALL NOT alter the registered experiment or authorize a replacement slot

### Requirement: Deterministic All-Slot Finalization
The system SHALL finalize the registered study exactly once from every registered slot after collection becomes terminal.

#### Scenario: All slots are terminal
- **WHEN** all 24 slots are completed or interrupted without a global integrity stop
- **THEN** finalization SHALL enumerate the committed slot table, verify every launched session, and include every structurally eligible trajectory from those sessions
- **AND** it SHALL write deterministic pool, target, readiness, estimate, verification, and closeout artifacts with complete inclusion and exclusion accounting

#### Scenario: Finalization is claimed exactly once
- **WHEN** finalization is ready to publish its registered artifacts
- **THEN** it SHALL atomically and exclusively create the registered finalization claim before replacing any final artifact
- **AND** an existing claim or final artifact SHALL reject the attempt before pool or outcome processing, while a failed artifact transaction SHALL retain the claim and fail closed

#### Scenario: Operator supplies a selective input set
- **WHEN** requested finalization omits a registered launched slot, adds an unregistered slot, duplicates a trajectory, or changes canonical input order
- **THEN** selective omission, addition, or duplication SHALL fail closed
- **AND** input reordering alone SHALL NOT change canonical output bytes or gates

#### Scenario: Study stopped globally
- **WHEN** a global integrity stop has made later collection invalid
- **THEN** finalization SHALL be allowed only as a blocked closeout that preserves collected source evidence
- **AND** it SHALL write no pool, target, readiness, estimate, bootstrap, influence, or comparison artifact and SHALL represent those unavailable source bindings as null
- **AND** it SHALL NOT emit a passing outcome-evidence gate

### Requirement: Outcome-Evidence Authority Boundary
The system SHALL report evidence expansion separately from policy comparison, formal training, reward design, causal claims, and live promotion.

#### Scenario: Outcome-evidence expansion passes
- **WHEN** every registered integrity and evidence-expansion condition passes
- **THEN** the report SHALL set only `outcome_evidence_expansion_ready` according to this study gate and SHALL run the existing OPE estimate and comparison gates unchanged
- **AND** causal uplift, formal non-combat RL training, reward design, and live policy promotion SHALL remain unauthorized

#### Scenario: Fixed evidence remains insufficient
- **WHEN** the registered limit is reached but any evidence-expansion threshold fails
- **THEN** the closeout SHALL report the observed shortfall as inconclusive or blocked
- **AND** it SHALL NOT lower thresholds, append replacement games, substitute floor reached for victory, or claim policy quality

### Requirement: Preclaim CommunicationMod Handshake
The system SHALL require the actual registered gameplay child to prove CommunicationMod state delivery before the study ledger claims a future slot.

#### Scenario: Preclaim attempt is durable
- **WHEN** the next slot passes run-lock and ordering validation and all registered handshake and gameplay output paths are absent
- **THEN** the parent SHALL capture the initial AI marker count and exclusively publish a bound attempt record before starting the child process
- **AND** any orphaned or duplicate attempt SHALL trigger one global stop without starting or retrying a child for that slot

#### Scenario: Registered child becomes ready
- **WHEN** a launchable registered slot has a valid run lock and the exact child receives and parses an initial CommunicationMod state within the registered deadline
- **THEN** the child SHALL publish an exclusive canonical ready record bound to the registration, run lock, slot, config, token, attempt, and child process while callbacks, exploration initialization, and gameplay actions remain disabled
- **AND** the parent SHALL verify that record and the live child, require unchanged marker count and absent gameplay outputs, and append `slot_started` with the original marker boundary

#### Scenario: Parent releases a claimed child
- **WHEN** the parent has appended `slot_started` for the verified ready child
- **THEN** it SHALL atomically publish the matching release record and the child SHALL validate it before initializing exploration, registering callbacks, or executing gameplay
- **AND** the already received state SHALL be retained for normal startup without being acted on before release or processed twice

#### Scenario: Preclaim handshake fails
- **WHEN** the child times out, exits early, emits malformed readiness, presents an attempt, binding, or PID mismatch, creates duplicate handshake artifacts, grows the AI marker count, or creates a manifest or trace before claim
- **THEN** the parent SHALL terminate the child, append one exact global stop, and leave the registered slot unlaunched
- **AND** it SHALL NOT retry, replace, release, or attribute a manifest, trace, decision, trajectory, or AI marker to that slot

#### Scenario: Failure occurs after claim but before release
- **WHEN** the parent or host fails after `slot_started` but before a valid release is consumed
- **THEN** recovery SHALL preserve the slot as launched and mark it interrupted before globally stopping the study
- **AND** it SHALL NOT roll the slot back to unlaunched or permit another child for that slot

#### Scenario: Ordinary gameplay has no study handshake
- **WHEN** the explicit registered-study handshake environment is absent
- **THEN** coordinator, exploration, and agent startup SHALL retain their existing behavior without creating handshake artifacts
- **AND** no ordinary gameplay or bounded eval command SHALL be treated as a registered slot

### Requirement: Versioned Launchable Handshake Contract
The system SHALL hash-bind the preclaim handshake contract into every future launchable outcome-evidence registration and run lock while preserving historical evidence bytes.

#### Scenario: Future registration is launchable
- **WHEN** a new outcome-evidence registration is generated after this capability is implemented
- **THEN** it SHALL use the new schema version and fix the handshake protocol version, readiness and release deadlines, attempt/ready/release artifact names, implementation files, and fail-closed continuation rule
- **AND** `start` and `run-next` SHALL reject a registration that lacks or changes any required handshake binding

#### Scenario: Historical v1 evidence is inspected
- **WHEN** an existing v1 registration is loaded for read-only verification
- **THEN** the verifier SHALL preserve its original schema and artifact interpretation without rewriting any byte
- **AND** the runner SHALL refuse to launch or resume a v1 registered slot after this change

### Requirement: Independent Blocked-Closeout Verification
The standalone outcome-evidence verifier SHALL independently replay a registered blocked closeout without importing the study finalizer or requiring normal OPE artifacts.

#### Scenario: Ledger selects blocked verification
- **WHEN** the validated append-only ledger contains exactly one global stop and no active slot and the validated claim mode is `integrity_stop`
- **THEN** the verifier SHALL select the blocked branch from those frozen facts rather than a CLI option, report status, or artifact-presence guess
- **AND** it SHALL require a valid terminal slot prefix followed only by registered unlaunched slots

#### Scenario: Blocked closeout is exact
- **WHEN** the claim and closeout are bound to the registration, run lock, source, ledger slot table, and exact global-stop reason
- **THEN** the verifier SHALL independently reconstruct and match the deterministic JSON and Markdown closeout, null unavailable source bindings, blockers, limitations, and all-false authority gates
- **AND** it SHALL require every registered pool, target, readiness, estimate, bootstrap, influence, and comparison artifact to be absent

#### Scenario: Blocked evidence is tampered
- **WHEN** the ledger, claim mode, stop reason, slot accounting, closeout hash, source binding, blocker, authority gate, limitation, Markdown rendering, or forbidden-artifact absence differs from independent replay
- **THEN** the verifier SHALL exit nonzero at the first deterministic mismatch
- **AND** it SHALL NOT fall through to normal verification or report partial success

#### Scenario: Historical blocked artifact is replayed
- **WHEN** the frozen 2026-07-15 v1 registration and blocked artifact root are supplied read-only
- **THEN** the standalone verifier SHALL pass the blocked branch and report its independently checked registration, run-lock, ledger, claim, closeout, and forbidden-artifact facts
- **AND** that pass SHALL NOT authorize OPE, policy comparison, training, reward design, gameplay-policy edits, or live promotion

#### Scenario: Normal closeout remains normal
- **WHEN** the validated ledger has no global stop, all registered slots are terminal, and claim mode is `complete`
- **THEN** the verifier SHALL run the existing full pool, target, readiness, estimate, influence, and closeout replay without weakening any check
- **AND** a mixed normal/blocked claim or artifact set SHALL fail closed

### Requirement: Observable Future Qualification Gate
The system SHALL require every future replacement outcome-evidence qualification to pass the versioned pre-request observability contract before it can support a later reviewed `start` decision.

#### Scenario: A future replacement is prepared
- **WHEN** the observability implementation has passed regression, full-suite, strict OpenSpec, byte, and independent source-only review and a separate amendment prepares a previously absent qualification identity
- **THEN** that identity SHALL use qualification request/result/review-binding v3 and bootstrap-evidence v1 with a fresh source snapshot, review commit, request anchors, launch token, root, and exact CommunicationMod baseline
- **AND** no v1/v2 request, retired root, copied prefix, timeout increase, or cleanup operation SHALL substitute for a fresh v3 identity

#### Scenario: A future replacement supports start review
- **WHEN** a future v3 identity has one exact claim/stage/active-request/handoff/attempt/ready/release/zero-exit/terminal chain, restored request-bound isolation, no surviving child, externally pinned terminal anchors, and passing independent attestation
- **THEN** that evidence SHALL remain input only to a separate later review of whether to create the registered study run lock
- **AND** it SHALL NOT itself create the run lock, start collection, interpret OPE, change gameplay policy, make causal claims, train a model, or promote a policy

#### Scenario: Historical r1 through r6 evidence is verified within its preserved boundary
- **WHEN** the preserved r1-r6 roots, requests, terminals, reports, audits, and recorded absences are inspected after v3 observability is implemented
- **THEN** every available historical byte SHALL retain its exact path, size, and SHA-256 and every unavailable artifact SHALL remain explicitly absent
- **AND** evidence-derived classification SHALL remain distinct from any separately reviewed consumed, failed, obsolete, prepared, partial, or retired governance disposition
- **AND** complete public v1/v2 replay SHALL be required only when the preserved bundle contains every request, review, and Git anchor required by that verifier path
- **AND** no missing request, result, review commit, audit byte, Git anchor, bootstrap field, or root artifact SHALL be synthesized to make an incomplete historical bundle replayable
- **AND** no historical v1/v2 identity SHALL be retried, upgraded in place, or used to authorize a future launch or `start`

#### Scenario: Observability implementation is complete but no replacement exists
- **WHEN** this change passes all offline implementation and review gates but no separate replacement amendment has been approved
- **THEN** the registered v2 study root SHALL remain absent and collection SHALL remain blocked
- **AND** completion of observability alone SHALL NOT authorize r7 preparation, a live game launch, study evidence collection, OPE interpretation, training, or policy change

### Requirement: Tracked Pre-Lock Qualification Orchestration
The system SHALL provide a tracked, owner-controlled, one-shot pre-lock qualifier for future launchable outcome-evidence studies without creating a run lock, ledger, or registered slot.

#### Scenario: Qualification request passes preflight
- **WHEN** a canonical request records implementation snapshot S, externally supplied request self-hash/file-SHA/size/review-commit anchors match its exact reviewed source bytes, every component of each externally supplied qualification path passes lexical no-follow inspection before resolution, file-type checks, reads, traversal, or hashing, R is the direct child of S, launch HEAD equals R, the exact S-to-R diff equals the request's non-executable review allowlist, a pre-project-import bootstrap proves tracked source is clean with only ordinary `H` index rows and no assume-unchanged/skip-worktree flags, untracked or ignored executable/importable paths, symlinks, or Windows reparse points, every Git/source-inventory warning or traversal error fails closed, registration and registered implementation bytes are unchanged across S/R/worktree, and the reviewed qualification root has no active control or forbidden output paths
- **THEN** the qualifier SHALL exclusively publish the reviewed bytes as the active request and then publish the matching attempt before starting exactly one child process
- **AND** it SHALL pass the exact attempt path and attempt-hash-bound qualification token only to that owned child
- **AND** terminal evidence SHALL carry a canonical self-hashed review binding for S, R, source/active paths and exact bytes, registration, implementation map, and review allowlist
- **AND** CommunicationMod SHALL enter the parent only through a fixed stdlib-only `python -I -S -c` launcher encoded as one whitespace-free token whose externally preserved runner SHA-256 and local absolute no-follow runner path are independently reviewed; CommunicationMod-equivalent whitespace splitting SHALL reproduce the exact command vector, the launcher SHALL read, hash, and execute only the validated in-memory runner bytes, and direct runner-file qualification SHALL be rejected
- **AND** before argument parsing or project imports the runner SHALL verify that exact original launcher command and environment anchor, bind the anchor to its reviewed implementation map, extract exactly one lowercase external R anchor, prove `HEAD == R`, and hash every tracked executable/importable worktree file against its R tree blob without trusting index stat data; one shared fail-closed predicate SHALL treat unknown and extensionless paths as executable/importable and exempt only explicitly inert review formats, worktree bytes SHALL be streamed through guarded `git -c core.autocrlf=true hash-object --path --stdin` and match the R object ID while every attributes source must be tracked in R, raw-byte identical, and limited to inert text/eol directives and all configured filters remain forbidden, and the child command SHALL equal the registered executable, main path, and arguments with fixed `-I -S` inserted immediately after the executable
- **AND** the parent SHALL remove every inherited `PYTHON*` and `GIT_*` environment entry before setting the exact qualification child environment, and both qualification processes SHALL disable bytecode writes, redirect cache lookups beneath the platform null device, and permit only no-follow source modules from repository paths before project imports so startup hooks, import-path injection, ambient Git redirection, junction-backed source, cached bytecode, or adjacent sourceless repository `.pyc` files cannot execute, escape, or mutate the reviewed boundary
- **AND** every producer or verifier qualification Git command SHALL invoke one pinned trusted absolute executable that passes no-follow inspection, never a bare executable name subject to current-directory lookup
- **AND** every qualification Git process SHALL bind `GIT_DIR` and `GIT_WORK_TREE` to the guarded ordinary local repository, disable system/global configuration and attributes, replacement objects, lazy object fetching, optional locks, prompts, fsmonitor, hooks, external diff, and textconv, and fail closed on any stderr
- **AND** qualification SHALL reject reparse entries inside `.git`, common directories, alternate object stores, grafts, loose or packed replacement refs, repository info attributes, partial-clone/promisor remotes, extension protocols, and include/fsmonitor/hooks/filter/attributes/external/textconv/SSH-command configuration before Git reads reviewed evidence

#### Scenario: Active request publication is interrupted
- **WHEN** the qualifier exclusively publishes the active request but the host stops before attempt or terminal publication
- **THEN** the qualification identity SHALL remain consumed and ineligible for retry, deletion, replacement, or reinterpretation
- **AND** a later invocation SHALL reject the existing active request before starting a child

#### Scenario: Child becomes ready immediately after start
- **WHEN** the owned child publishes a valid bound ready record at any time after process creation and before the exclusive readiness deadline, including before the qualifier's first poll
- **THEN** the qualifier SHALL validate the already-present record and live child without applying a post-launch absence assertion
- **AND** it SHALL lexically reject any ready-path symlink or Windows reparse component before invoking the shared handshake loader or any resolving helper
- **AND** after revalidating unchanged marker/configuration and absent gameplay outputs it SHALL exclusively publish the matching release immediately
- **AND** the ready creation time SHALL define one conservative remaining-release deadline shared by every subsequent source, Git metadata traversal/subprocess, configuration, marker, forbidden-path, chunked root-inventory hash, active-request, child-running, and immediately-before-release check, and validation SHALL NOT repeat immutable S/R blob replay after ready

#### Scenario: Qualification owns the CommunicationMod stream
- **WHEN** CommunicationMod launches the qualifier and the qualifier launches the registered child
- **THEN** child stdin, stdout, and stderr SHALL remain connected to CommunicationMod as required by the existing protocol
- **AND** the qualifier SHALL route only that child's file logger to the platform null device so qualification startup does not mutate the global AI debug log
- **AND** qualifier diagnostics and result output SHALL use canonical files or stderr and SHALL NOT read live game logs while the child is running or write non-protocol text to CommunicationMod stdout

#### Scenario: Qualification preflight or handshake fails
- **WHEN** the request or binding is malformed, a control or forbidden artifact already exists, the child fails to start, times out, exits early, emits malformed or mismatched ready evidence, changes a protected boundary, or release publication fails
- **THEN** the qualifier SHALL fail closed, terminate the owned child if one exists, and SHALL NOT retry or replace it under the same qualification identity
- **AND** it SHALL NOT create or authorize a run lock, ledger, slot claim, manifest, trace, AI marker, checkpoint, run record, gameplay action, training action, or study `start`

### Requirement: Qualification Child Post-Release Exit Boundary
The registered child SHALL support an explicit qualification-only success exit after consuming a valid release and before exploration initialization, callback registration, agent construction, or gameplay.

#### Scenario: Bound qualification child consumes release
- **WHEN** the unchanged child handshake validates release and the dedicated qualification token is one lowercase SHA-256 value equal to the loaded attempt hash
- **THEN** the child SHALL exit successfully before initializing exploration, constructing an agent, registering callbacks, or acting on the retained state
- **AND** token presence SHALL make `main.py` lexically validate every attempt-path component and its regular final entry before coordinator construction or invocation of the shared handshake and attempt loaders, while ordinary no-token startup remains unchanged
- **AND** the parent SHALL treat success as valid only after it has validated ready and release and observed that zero exit from the owned PID
- **AND** isolated direct-script startup SHALL establish the guarded repository import root before any project import without consulting ambient Python path or startup customization

#### Scenario: Qualification token is malformed or mismatched
- **WHEN** the dedicated qualification environment is present without a handshake attempt, is malformed, or differs from the loaded attempt hash
- **THEN** child startup SHALL fail closed before exploration initialization, agent construction, callbacks, or gameplay
- **AND** it SHALL NOT silently ignore, normalize, or reinterpret the token

#### Scenario: Ordinary gameplay has no qualification exit
- **WHEN** the qualification environment is absent
- **THEN** ordinary gameplay and registered study children SHALL preserve their existing post-handshake behavior
- **AND** `run-next` SHALL reject any ambient qualification environment before publishing a registered-slot attempt and SHALL never add that environment to its child

### Requirement: One-Shot Qualification Evidence
The qualifier SHALL publish exclusive canonical evidence for its single terminal outcome and an independent verifier SHALL replay that evidence without importing producer result builders.

#### Scenario: Qualification child exits at the success boundary
- **WHEN** attempt, ready, release, child exit, marker boundary, configuration, and forbidden-output checks all pass
- **THEN** the qualifier SHALL exclusively publish one canonical self-hashed completion record binding the request, registration, source, implementation map, exact command, configuration, owned PID and exit code, and all handshake hashes
- **AND** terminal forbidden-path observations SHALL use no-follow entry existence so dangling symlinks or Windows reparse points cannot be recorded as absent
- **AND** every authority field for study `start`, run lock, collection, training, policy change, and causal claim SHALL remain false until the separate reviewed live qualification and attestation gates pass

#### Scenario: Qualification terminates unsuccessfully
- **WHEN** a terminal qualification condition fails after the request identity exists, except for post-exit boundary validation after release/zero exit or completion publication itself
- **THEN** the qualifier SHALL attempt to exclusively publish one canonical self-hashed failure record with the failure stage, available bindings, cleanup result, forbidden-artifact observations, and false authority fields
- **AND** the root SHALL remain immutable and ineligible for retry even if a host crash prevents terminal-record publication

#### Scenario: Completion publication fails after successful release and exit
- **WHEN** attempt, ready, release, isolation, and child zero-exit evidence are complete but exclusive completion publication fails
- **THEN** the qualifier SHALL NOT relabel the successful lifecycle as a failed terminal
- **AND** it SHALL leave the consumed release-ending prefix immutable for independent partial sealing

#### Scenario: Post-exit boundary validation fails
- **WHEN** release and zero child exit are complete but the subsequent source, configuration, marker, forbidden-path, root-inventory, or active-request recheck fails
- **THEN** the qualifier SHALL NOT publish a failed terminal because the otherwise successful process/handshake fields do not independently prove the observed drift
- **AND** it SHALL leave the consumed release-ending prefix immutable for independent partial or invalid sealing, exactly as for completion-publication failure

#### Scenario: Independent qualification replay succeeds
- **WHEN** the standalone verifier receives a reviewed-source path, external R/request-hash/file-hash/size anchors, a terminal record, and independently preserved result-self-hash/file-SHA/size anchors
- **AND** direct qualification replay starts under Python isolated no-site mode (`-I -S`), redirects bytecode-cache lookups beneath the platform null device, permits only no-follow source modules from repository paths, skips ordinary registration-audit helper imports, and rejects abbreviated long options before argument parsing or project imports, while ordinary registration audit startup remains unchanged
- **THEN** it SHALL independently load S/R Git blobs without relying on current HEAD, current worktree bytes, or continued existence of the reviewed source's current parent directory and validate the direct-parent/exact-diff review chain, canonical bytes, duplicate-key rejection, self-hashes, reconstructed review binding, source/registration/implementation/command/configuration bindings, launch-count/PID/cleanup consistency including one attempt for every claimed launch, regular no-follow attempt/ready/release entries, lifecycle timestamp ordering, terminal branch, no-follow forbidden artifact existence, and exact JSON authority booleans
- **AND** it SHALL reject missing, additional, reordered, malformed, mismatched, non-canonical, retried, or tampered evidence
- **AND** it SHALL reject any success-looking failed terminal even when its claimed stage is `post_exit_validation`
- **AND** it SHALL bind the three result anchors into its audit and reject terminal replay when any result anchor is absent or mismatched
- **AND** historical Git replay SHALL use the same guarded local `.git` binding, sterile environment and command controls, metadata-indirection rejection, and stderr-fail-closed rules as producer validation
- **AND** when qualification replay publishes an audit file, the output SHALL be a lexical absolute path with no colon outside its drive component and no component ending in a dot or space, its canonical no-follow parent SHALL remain outside the guarded qualification root, it SHALL match no request-bound path or forbidden subtree under canonical Windows path comparison, its existing parent SHALL pass no-follow inspection, its final entry SHALL be absent, and publication SHALL use exclusive creation without truncating or replacing any evidence; ordinary registration-audit output behavior remains unchanged

#### Scenario: A partial prefix is given a later self-hashed terminal
- **WHEN** a release-ending partial is followed by a canonical self-hashed completion or failure that lacks the independently preserved result-self-hash/file-SHA/size anchors
- **THEN** the verifier SHALL reject terminal verification rather than promote the new file to `verified`
- **AND** request-only or partial replay SHALL reject supplied result anchors rather than reinterpret them as provenance

#### Scenario: Qualification paths use a junction alias
- **WHEN** a registration, registered absolute path, reviewed source, qualification root, verifier result or audit output, Git executable, or failure marker path contains a symlink or Windows reparse component, uses a UNC or Win32 device namespace, contains a colon outside its drive component such as an NTFS alternate data stream, or has a component ending in a dot or space
- **THEN** the producer or verifier SHALL reject it before invoking the normal parser, resolving, reading, hashing, traversing, executing Git, or constructing terminal marker evidence
- **AND** the verifier SHALL guard the qualification root before classifying any control entry and SHALL guard every absolute and derived implementation path in reviewed registration bytes before normal registration validation
- **AND** before any classification, inventory, existence probe, or read, it SHALL purely bind the declared active request, attempt, ready, release, completion, and failure paths to fixed direct children of the guarded root and recheck their parent components no-follow
- **AND** a missing historical reviewed-source suffix MAY still locate Git from its nearest existing ordinary ancestor, but no existing reparse prefix may be followed

#### Scenario: Reviewed source has not been consumed
- **WHEN** the externally anchored reviewed source passes current configuration, marker, static-inventory, and forbidden-output preflight and neither active request nor any control or terminal artifact exists
- **THEN** the verifier SHALL report `reviewed_prepared`, `consumed=false`, and `qualification_status=not_attempted`
- **AND** every study, run-lock, collection, policy, causal, and training authority SHALL remain false

#### Scenario: Malformed or orphaned evidence consumed the identity
- **WHEN** an active request path is malformed/non-regular, any control path is dangling, non-regular, a symlink, or a Windows reparse point, or control/terminal artifacts exist without the exact reviewed active request
- **THEN** the verifier SHALL emit a self-hashed `sealed_invalid` audit with `consumed=true`, an explicit invalid stage/error, artifact inventory, reconstructed review binding, and no authority
- **AND** it SHALL classify symlinks and Windows reparse points before inventory and SHALL use `lstat` plus no-follow traversal without hashing or entering link targets
- **AND** it SHALL NOT reinterpret that root as prepared, retryable, or terminally verified

#### Scenario: Terminal replay lacks the reviewed active request
- **WHEN** a terminal record is supplied but the active request is absent, non-regular, or differs byte-for-byte from the externally anchored reviewed source
- **THEN** the verifier SHALL fail terminal verification rather than returning a verified or recoverable audit
- **AND** it SHALL NOT use terminal fields to replace or reinterpret the missing reviewed active identity

#### Scenario: Independent replay seals a partial host-crash prefix
- **WHEN** the active request exists, both terminal branches are absent, and the available handshake evidence is one contiguous canonical prefix ending at request, attempt, ready, or release
- **THEN** the verifier SHALL emit a self-hashed partial audit that identifies the final observed stage and proves the reviewed root remains consumed
- **AND** every study, run-lock, collection, policy, causal, and training authority SHALL remain false
- **AND** the verifier SHALL reject gaps, reordered timestamps, tampering, either terminal branch, or any attempt to repair or promote the prefix

#### Scenario: Broad live isolation remains external
- **WHEN** the tracked qualifier reports a successful local terminal result
- **THEN** that result alone SHALL NOT claim CommunicationMod configuration restoration, unchanged run/checkpoint/global-log inventories, empty process inventory, independent attestation, or authorization to create a study run lock
- **AND** a later reviewed qualification identity SHALL prove those live conditions separately before `start`
- **AND** that later review SHALL preserve and attest the exact CommunicationMod launcher literal and runner SHA-256 before invocation

### Requirement: R7 Qualification Handoff Boundary
The outcome-evidence study SHALL treat the independently attested r7 result only as input to a later study-launch review and SHALL remain blocked throughout this amendment.

#### Scenario: R7 is independently qualified
- **WHEN** the complete request-v3/bootstrap-v1 lifecycle, terminal anchors, restored request-bound isolation, protected inventory comparison, and independent attestation all pass for r7
- **THEN** the study SHALL record r7 as the sole current qualification candidate eligible for a later review of whether to invoke `start`
- **AND** this amendment SHALL NOT create the run lock, ledger, registered slot configuration, collection artifact, OPE artifact, model, checkpoint, policy change, causal claim, training run, or promotion authority
- **AND** the repository SHALL remain tracked-clean at the exact qualified R with no intervening write or commit; the r7 handoff, attestation, and provisional closeout SHALL remain externally anchored until the later `start` decision or run-lock no-write window releases that freeze

#### Scenario: R7 is retired
- **WHEN** r7 is obsolete before publication, retired after publication without an issued invocation, consumed without a complete valid attestation, or retired for any observed, uncertain, partial, invalid, failed, abrupt, or cleanup-uncertain live boundary
- **THEN** the registered study root SHALL remain absent and every remaining `run-v2-known-propensity-outcome-evidence-study` live task SHALL remain blocked
- **AND** a published r7 root SHALL remain immutable even when no invocation occurred, and no r7 byte MAY be retried, repaired, deleted, upgraded in place, or used to justify `start`

#### Scenario: R7 amendment closes deterministically
- **WHEN** offline review rejects r7, live qualification retires r7, or independent replay qualifies r7
- **THEN** the amendment closeout SHALL bind the exact source range, request/review/root/result/attestation hashes or declared absences, CommunicationMod before/after bytes, protected inventory comparison, process observations, disposition, limitations, and all-false authority
- **AND** an obsolete or retired branch MAY commit, sync, and archive that closeout immediately because no qualified `start` handoff exists
- **AND** a qualified branch SHALL keep the closeout external and the amendment active until a later reviewed decision declines `start` or the complete frozen-study tracked-write prohibition has ended, after which the exact externally anchored closeout MAY be imported without changing historical r7 evidence
- **AND** preparing r8, invoking study `start`, collecting trajectories, interpreting OPE, changing rewards or gameplay policy, training, and promotion SHALL each require separately reviewed authority outside this amendment

### Requirement: R8 Qualification Handoff Boundary
The outcome-evidence study SHALL treat an independently attested r8 result only as input to a separate study `start` review and SHALL remain blocked throughout this amendment.

#### Scenario: R8 is independently qualified
- **WHEN** the complete bootstrap-v1/request-v3 lifecycle, terminal anchors, request-bound restoration, protected inventory comparison, process-death evidence, and standalone verifier all pass for r8
- **THEN** the study SHALL record r8 as the sole current qualification candidate eligible for a separate review of whether to invoke `start`
- **AND** this amendment SHALL NOT create a run lock, ledger, slot configuration, gameplay or collection artifact, OPE artifact, checkpoint, model, reward, policy change, causal claim, training run, or promotion authority
- **AND** the repository SHALL remain tracked-clean at exact reviewed R while the r8 handoff and provisional closeout remain externally anchored until the later `start` decision or existing run-lock no-write window releases that freeze

#### Scenario: R8 is obsolete or retired
- **WHEN** offline review rejects r8 or any publication, invocation, qualification, verification, restoration, inventory, cleanup, or process boundary fails to produce a complete independently attested terminal
- **THEN** the registered study root SHALL remain absent and every remaining live task in `run-v2-known-propensity-outcome-evidence-study` SHALL remain blocked
- **AND** every published r8 byte SHALL remain immutable and no r8 retry, repair, deletion, reuse, or r9 preparation SHALL be authorized

#### Scenario: R8 amendment closes by disposition
- **WHEN** r8 becomes obsolete, retires, or qualifies for a later `start` review
- **THEN** its closeout SHALL bind exact source, request, review, root, result, verifier, attestation, configuration, inventory, process, disposition, limitation, and authority evidence
- **AND** an obsolete or retired branch MAY commit, sync, and archive immediately
- **AND** a qualified branch SHALL preserve tracked-clean R and external closeout anchors until a separate `start` decision declines launch or the study's tracked-write prohibition ends
