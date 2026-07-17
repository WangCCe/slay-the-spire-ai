## ADDED Requirements

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
