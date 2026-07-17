## Context

The launchable outcome-evidence study already has a child-side handshake and a
parent-side registered-slot runner. The child receives one callback-free
CommunicationMod state, publishes a bound `ready`, waits for `release`, and
does not initialize exploration or register gameplay callbacks before release.
The registered-slot runner publishes `attempt`, starts the exact registered
child, accepts and validates ready, claims the slot, and publishes release.

Pre-lock live qualification has not used that same ownership boundary. It has
been assembled from separately scheduled PowerShell commands around a direct
`main.py` child. r1 failed while an external command inspected a live log; r2
exposed the now-fixed 30-second cold-start deadline; r3 published valid ready
after about 15.7 seconds but received no release and failed at the fixed
10-second release deadline. Independent replay verified that r3 did not mutate
the registered study root, markers, runs, checkpoints, implementation files,
or global logs and left no process alive. It did not independently preserve the
exact failed monitor command, so the durable fact is a release-side external
orchestration failure, not the narrower shell mechanism.

The v2 study therefore remains pre-lock and blocked. Any implementation change
also invalidates the source and file-hash review bound to commit `84c676762`,
even if canonical registration bytes remain identical.

## Goals / Non-Goals

**Goals:**

- Make one tracked process own all ordering-sensitive pre-lock qualification
  actions and launch the registered child exactly once.
- Prove that a valid release is consumed and that the qualification child exits
  before exploration initialization, agent construction, callbacks, or
  gameplay.
- Produce canonical, self-hashed machine evidence that an independent verifier
  can replay without importing the producer.
- Fail closed and leave the identity immutable on every preflight, child,
  protocol, release, exit, or cleanup error.
- Preserve CommunicationMod protocol compatibility and reserve stdout for its
  command/state stream.

**Non-Goals:**

- Do not change handshake schemas, handshake code, or the 120/10 deadlines.
- Do not create a study run lock, ledger, slot claim, exploration manifest,
  trace, AI marker, checkpoint, run record, OPE result, or training artifact.
- Do not change gameplay policy, behavior rates, seeds, study schedule,
  estimator, thresholds, or authority.
- Do not make the tracked qualifier alone sufficient to authorize r4 or study
  `start`; real CommunicationMod isolation and independent attestation remain
  separate gates.
- Do not retry, delete, rename, or reinterpret r1, r2, or r3.

## Decisions

### 1. Add `qualify` to the existing CommunicationMod runner

CommunicationMod will launch a fixed stdlib-only `python -I -S -c` trust-root
launcher, which validates and executes the runner's new `qualify` subcommand.
The runner will then start the registered `main.py` command with fixed `-I -S` isolation
inserted and with inherited stdin, stdout, and stderr, just as `run-next`
already wraps a registered study child.
The qualifier will exclusively own this sequence:

1. Accept a local absolute runner path plus independently preserved runner
   SHA-256 in the fixed launcher. Encode its audited stdlib payload behind one
   whitespace-free base64 loader token so CommunicationMod's whitespace split
   reproduces the exact argument vector; reject any symlink/reparse component
   or NTFS alternate data stream, read the runner once, verify the hash, and
   execute only those validated in-memory bytes. The runner requires that exact
   original command shape and environment
   anchor, rereads its file to detect post-launch replacement, later binds the
   anchor to its request implementation map, and rejects direct file startup.
2. Load a committed reviewed request source and require its self-hash, exact
   file SHA-256, byte count, and review commit to equal explicit CLI anchors.
3. Lexically inspect every component of the supplied registration, repository,
   qualification-root, configuration, marker, and reviewed-source paths with
   no-follow metadata before any resolution, file-type check, read, traversal,
   or hash; reject any symlink or Windows reparse component without entering
   its target, and reject UNC or Win32 device namespaces, any colon outside the
   drive component (including NTFS alternate data streams), and any component
   ending in a dot or space before any filesystem probe. Parse raw registration
   JSON only after guarding the registration
   file, inspect every absolute registered path and implementation path before
   invoking the existing registration parser, and apply the same component
   guard to verifier request/result inputs and failure-path marker snapshots.
   The verifier guards the qualification root before classifying any control
   entry and guards every absolute and derived implementation path from the
   reviewed registration mapping before invoking the existing registration
   validator or any resolving helper.
4. Before importing project modules, run a pure-stdlib source bootstrap that
   extracts exactly one lowercase external review commit from the raw CLI,
   requires `HEAD == R`, hashes every executable/importable worktree file
   against the corresponding R tree blob without trusting index stat data,
   streams those bytes through guarded
   `git -c core.autocrlf=true hash-object --path --stdin` so a clean Windows
   checkout retains its reviewed object identity while binary drift does not,
   permits only R-tracked raw-byte-identical attributes containing inert
   text/eol directives, forbids every other attributes source and configured
   filter, and uses one fail-closed predicate that exempts
   only the explicitly inert `.csv`, `.json`, `.jsonl`, `.log`, `.md`, `.tsv`,
   and `.txt` review formats while treating unknown and extensionless paths as
   executable/importable, and requires
   clean tracked source, ordinary `H` index rows with no
   assume-unchanged/skip-worktree flags, no untracked or ignored
   executable/importable path, symlink, or Windows reparse point, `R` as the
   direct child of implementation snapshot S, an exact
   S-to-R diff equal to the request allowlist, unchanged
   registration/implementation bytes, exact child command, qualification
   config, marker boundary, and absent control/forbidden paths. Git warnings
   and filesystem traversal errors fail this source inventory closed.
   Every qualification Git invocation in both producer and verifier uses the
   pinned absolute `C:\Program Files\Git\cmd\git.exe`, itself inspected with
   no-follow metadata, so a repository-local `git.exe` cannot execute first.
   It also binds `GIT_DIR` and `GIT_WORK_TREE` to the guarded local repository,
   disables system/global config, replacement objects, optional locks, prompts,
   fsmonitor, hooks, external diff, and textconv, and rejects any stderr even
   when Git exits zero. Before invoking Git, qualification recursively rejects
   reparse entries inside `.git`, replace refs (loose or packed), grafts,
   alternate object stores, `commondir`, repository info attributes, and
   config capable of includes, fsmonitor, hooks, clean/process filters,
   attributes files, external/textconv execution, partial-clone/promisor
   remotes, extension protocols, or an SSH command. System attributes and lazy
   object fetching are disabled in both the sterile Git environment and every
   Git command.
5. Exclusively publish the reviewed bytes as the active request. This first
   write consumes the identity even if the host stops immediately afterward.
6. Exclusively publish the handshake attempt.
7. Start the exact child once with the attempt path and qualification token.
8. Poll process state and the ready path, accepting a ready file that exists on
   the first poll after process creation. Before the shared ready loader can
   resolve or read that path, run the qualification-only lexical component
   guard; the ordinary registered-study caller does not receive this guard.
9. Validate ready, the live PID, unchanged marker/config, absent gameplay
   outputs, and current review-bound files within one deadline derived from
   the ready record's creation time and the remaining release window. Every
   subsequent pre-release boundary check rechecks that deadline before release
   is exclusively published.
10. Wait for the child to exit zero at the qualification boundary.
11. Recheck marker/output isolation and exclusively publish a completion record.

This removes the scheduling gap that let a child outrun an external monitor.
It also reuses the tested ready validator and child cleanup behavior rather
than adding a second handshake protocol.

The fixed launcher and runner reject qualification unless the interpreter was
started with `-I -S`; the launcher validates exact runner bytes before runner code
executes, and the runner verifies command shape before importing `argparse` or
project packages. The owned child command is the registered executable, main path, and
arguments with fixed `-I -S` inserted after the executable. Only an
explicit `qualify` invocation enables the parent's bytecode suppression, and
only the qualification token makes `main.py` set `sys.dont_write_bytecode`;
ordinary runner and gameplay imports retain their prior behavior. `main.py`
also adds its guarded repository root to `sys.path` before project imports so
the isolated direct-script launch remains supported without writing `.pyc`.
Both qualification processes set `sys.pycache_prefix` beneath the platform
null device and install a repository-only no-follow source loader before
project imports, so neither a source reached through a junction nor cached or
adjacent sourceless repository `.pyc` can execute before the source inventory
rejects it. The verifier qualification path also skips the two ordinary
registration-audit helper imports. The parent removes every
inherited `PYTHON*` and `GIT_*` environment entry before setting the exact
qualification child environment and `PYTHONDONTWRITEBYTECODE=1`. This prevents
startup hooks, import-path injection, ambient Git redirection, and parent or
child bytecode reads/writes from escaping the reviewed source boundary.

Alternative A was another reviewed multi-command PowerShell procedure. It was
rejected because prose cannot enforce monitor-before-launch ordering or prove
release consumption before exploration. Alternative C was a new handshake
acknowledgement phase. It was rejected because a qualification-only child exit
provides the required observation without changing every registered slot or
the protocol schema.

### 2. Bind a canonical qualification request before launch

`qualify` will accept `--registration`, `--request`, `--request-hash`,
`--request-file-sha256`, `--request-size`, and `--review-commit`. `--request`
names a reviewed source file, not the active control path. The four external
review anchors must exactly match its canonical self-hash, raw file SHA-256,
byte count, and review commit R. The source file is copied byte-for-byte to the
bound active path using exclusive creation before attempt publication or child
launch.

The request uses a two-commit review chain to avoid an impossible Git
self-reference. It records implementation snapshot commit S. After S exists,
the canonical request source is generated and tracked in review commit R. R
must be the direct child of S and launch HEAD must equal R. The exact
`git diff --name-only --no-renames S R` output must equal the request's sorted,
unique `review_allowed_paths`; that list must contain the request source and
must exclude registration, registered implementation, executable, and
importable paths. The tracked worktree must be clean, every `git ls-files -v`
row must be ordinary `H`, and no untracked or ignored executable/importable
path, symlink, or Windows reparse point may exist. Git status warnings,
undecodable path output, and filesystem traversal errors are fatal.
Registration and every registered
implementation file must have identical bytes at S, R, and the worktree. The
request binds the qualification identity/root, source commit S, reviewed
source path, review allowlist, registration hash/file hash, implementation
hash map, exact child command, config path/hash, marker path/count, handshake
paths/deadlines, completion/failure paths, and expected absence of run-lock,
ledger, manifest, and trace paths.

The v1 request has the exact top-level fields `schema_version`, `request_hash`,
`created_unix_ns`, `qualification_id`, `qualification_root`, `request_path`,
`request_source_path`, `review_allowed_paths`, `source_commit`, `registration`,
`implementation_sha256`, `child_command`, `config`, `marker`, `handshake`,
`preexisting_files`, `forbidden_paths`, `completion_path`, and `failure_path`.
`registration` contains `path`,
`canonical_hash`, and `file_sha256`; `config` contains `path` and `sha256`;
`marker` contains `path` and `start_count`; `handshake` contains the existing
protocol version, zero run-lock hash, slot 1, qualification session ID, the
three absolute control paths, and exact 120/10 deadlines. `preexisting_files`
maps every allowed static file under the qualification root except the request
itself to its SHA-256. `forbidden_paths` is the exact set of registered study,
run-lock, ledger, manifest, trace, and other gameplay output paths that must be
absent. No unknown field or implicit default is accepted.

The qualifier builds a canonical self-hashed v1 `review_binding` after these
checks. It binds S, R, the reviewed source absolute/relative path, active path,
request self-hash, exact source/active file hash and size, sorted review
allowlist, registration binding, and implementation-map hash. The exact
binding is copied into every terminal result and independently reconstructed
by the verifier.

The pre-release live check uses only the already-reviewed in-memory binding,
current `HEAD == R`, worktree/source inventory, and current request,
registration, and implementation bytes. Its conservative budget is computed
from the ready record's wall-clock creation time, not from a fresh clock after
the parent notices ready. Source, Git metadata traversal and subprocesses,
configuration, marker, forbidden-path, qualification-root inventory, and
active-request checks all share that one deadline. Static-file hashing is
chunked and checks the budget between reads. It does not replay immutable S/R
blobs after ready; full historical
replay remains an independent post-exit/verifier operation.
The parent rechecks the same deadline after confirming the child is still
running and immediately before exclusive release publication.

The qualification root may contain only the hash-bound static inventory. Its
active request, attempt, ready, release, completion, and failure paths must all
be absent before invocation. The qualifier exclusively publishes the active
request first. Any collision rejects the invocation without launching a child;
once publication succeeds, the identity is consumed even if no attempt or
terminal record follows. The qualifier never overwrites, deletes, retries,
replaces, or reinterprets either source or active request bytes.

CLI-only arguments were considered but rejected because they are harder to
review, hash-bind, and replay exactly across CommunicationMod configuration
rewrites. Reusing a study run lock was rejected because qualification is
deliberately pre-lock and must not make a registered slot exist.

### 3. Use an attempt-hash-bound qualification exit token

The qualifier will add one dedicated environment value containing the exact
published attempt hash. The child will treat presence of that environment as a
strict request, not a hint:

- it must also have the normal handshake attempt environment;
- before coordinator construction or the shared handshake initializer, token
  presence must trigger lexical no-follow validation of the attempt path;
- the token must be one lowercase SHA-256 value equal to the canonical attempt
  loaded for the completed handshake;
- before the shared attempt loader can resolve or read the environment path,
  `main.py` must lexically inspect every existing component and reject links,
  junctions, reparse points, alternate data streams, missing entries, or a
  non-regular final entry;
- the release must already have been validated by the unchanged handshake;
- after those checks, the child exits zero before calling the exploration
  initializer or constructing an agent.

Missing qualification environment preserves existing behavior. A present but
invalid token fails startup before exploration. `run-next` explicitly rejects
an ambient qualification token before publishing its attempt, so a parent
shell cannot accidentally turn a registered slot into a qualification exit.

The token is an integrity binding, not a secret or authentication mechanism.
Binding it to the attempt was chosen over a free-form boolean because it proves
that the exit belongs to the same one-shot handshake the parent observed.

### 4. Keep the handshake module and normal slot flow unchanged

`spirecomm/communication/study_handshake.py` remains byte-for-byte unchanged.
The child continues to publish ready only after one callback-free state and to
validate release before returning. The registered `run-next` path retains its
claim-before-release behavior and never sets the qualification token.

This preserves the already-tested 120-second readiness and exclusive 10-second
release boundaries and prevents qualification concerns from changing study
semantics.

### 5. Publish canonical completion or failure evidence once

After attempt publication, every terminal path will try to publish exactly one
canonical self-hashed result under the request root:

- success binds request, registration, source, implementation map, command,
  config, marker boundaries, child PID/exit, and attempt/ready/release hashes;
- failure binds the same available evidence, the exact stage and exception,
  child termination result, forbidden-artifact observations, and a false
  authority boundary.

The v1 result has the exact top-level fields `schema_version`, `result_hash`,
`status`, `created_unix_ns`, `ended_unix_ns`, `request`, `source_commit`,
`registration`, `implementation_sha256`, `child_command`, `config`, `marker`,
`handshake`, `process`, `forbidden_paths`, `failure`, `authority`, and
`review_binding`.
`status` is exactly `passed` or `failed`; `request` binds its path and hash;
`handshake` records each control path plus a nullable file hash; `process`
records launch count, owned PID, exit code, and cleanup outcome; `failure` is
null on success and otherwise contains stage, exception type, and message;
every authority value is false. Success requires launch count 1, all three
handshake hashes, zero exit, unchanged marker count, no cleanup action, absent
forbidden paths, and null failure. Failure must contradict at least one of
those conditions and can have launch count 0 or 1. No other terminal status,
field, or authority value is accepted. JSON booleans and integers are compared
by exact type, completion/failure branches are mutually exclusive, and the
request/result/attempt/ready/release timestamps must form one non-regressing
lifecycle. A fully successful evidence chain cannot be relabelled as failure.
Every claimed launch requires attempt evidence, and ready/release/PID/cleanup
evidence cannot coexist with launch count zero. Control and forbidden-path
existence is measured lexically with `lstat`, so dangling links and reparse
points remain visible to terminal construction and replay.
If `post_exit_validation` detects drift after release and zero child exit, the
available result fields cannot independently prove which boundary failed.
The qualifier therefore publishes no failed terminal and leaves the immutable
release-ending prefix for independent partial or invalid sealing. The same
rule applies when completion publication itself fails.

No internal retry is allowed. Publication itself is exclusive. Neither
post-exit validation nor completion-publication failure after a fully
successful release/exit chain may be relabelled as a failed terminal. If the process dies
before a result can be written, the request/attempt/root still make the
identity immutable and external recovery must preserve and review it.

The existing independent verifier will gain a qualification replay entry point
implemented without importing runner result builders. It receives the
reviewed-source path and the external R/request-hash/file-hash/size anchors,
and its directly executed qualification CLI requires Python `-I -S`, suppresses
bytecode writes, and redirects cache lookups beneath the null device before
argument parsing or project imports; its repository path loader accepts source
modules but not bytecode. The ordinary registration verifier keeps its prior
startup behavior. Qualification replay audit output, when requested, requires
a lexical absolute missing path whose canonical no-follow parent remains
outside the qualification root, matches no request-bound path or forbidden
subtree under canonical Windows comparison, has an existing no-follow parent,
contains no alternate-data-stream syntax or Win32 trailing-dot/space alias,
and is created exclusively; it cannot truncate, replace, or add an entry
beneath one-shot evidence. Qualification replay then
loads request, registration, and implementation bytes from S/R Git blobs, and
does not require its current HEAD or worktree to match R. If the reviewed
source's current parent has been removed, it locates Git from the nearest
existing ancestor and still reads the reviewed path from R. It reconstructs the
exact `review_binding`, then validates canonical active request/result bytes,
handshake bindings, exact launch count, success-or-failure branch, lifecycle
ordering, forbidden study/gameplay artifacts, and exact false authority
booleans. A reviewed source with no active request or controls is
`reviewed_prepared` and not consumed only after the reviewed request also
passes current configuration, marker, static-inventory, and forbidden-output
preflight. A canonical active request with no terminal can seal only a
contiguous prefix ending at request, attempt, ready, or release.
Non-regular/malformed active requests, dangling or non-regular control paths,
orphan controls, gaps, or invalid prefixes are sealed as consumed invalid
evidence. Before any classification, inventory, existence probe, or read, the
active request and five control/terminal paths must purely equal their fixed
direct-child paths derived from the guarded qualification root, and each
parent is rechecked no-follow. Control links and Windows reparse points are then classified
lexically before inventory, and audit inventory uses `lstat` plus `os.scandir` no-follow
metadata without entering or hashing link targets. A supplied
terminal requires
the exact regular active request to exist and equal the reviewed source bytes;
absence, non-regular paths, or byte mismatch is a hard verification error.
Every audit carries inventory, consumption, validity/error, partial stage,
reconstructed review binding, and uniformly false authority; it never repairs
evidence or authorizes retry. Broad
post-process isolation such as CommunicationMod config restore,
run/checkpoint/global-log inventories, and process inventory remains part of
the later r4 evidence and attestation rather than being inferred from the child
result alone.

### 6. Keep protocol output isolated

While the child is alive, the qualifier reads only owned canonical files and
the owned process handle. It does not inspect live game logs. Child stdin,
stdout, and stderr are inherited; qualifier diagnostics and final CLI JSON use
stderr so no non-protocol text enters CommunicationMod stdout. The qualifier
overrides only the child's existing `STS_AI_LOG_FILE` setting with the platform
null device, preventing qualification startup messages from mutating the
global `ai_debug.log`; this does not alter protocol streams or ordinary/study
startup.

## Risks / Trade-offs

- [The qualifier adds code to two launch-critical files] -> Keep changes behind
  explicit qualification environment and CLI paths, preserve ordinary and
  `run-next` regressions, and refresh every source/implementation binding before
  r4.
- [A zero child exit could occur for the wrong reason] -> Require a validated
  ready and release first, bind the exit token to the attempt hash, and require
  the canonical completion record to include all three handshake hashes.
- [A host crash can prevent failure-record publication] -> Treat active request
  publication as identity consumption; never retry that root, and use the
  independent partial-prefix verifier to seal exactly what exists without
creating a terminal.

Terminal replay additionally requires independently preserved result
self-hash, raw-file SHA-256, and byte-count anchors. The verifier rejects a
supplied completion or failure when any result anchor is absent or mismatched,
and records all three in the verification audit. Request-only and partial
replay reject result anchors. This prevents a release-ending partial from being
relabelled later by merely writing a new canonical self-hashed terminal file.
The later r4 attestation must preserve these result anchors before replay;
values computed only after an untrusted terminal appears do not establish its
provenance.
- [A request cannot contain the hash of the Git commit that first tracks its own
  bytes] -> Separate implementation snapshot S from later request-review commit
  R and prove registered code/registration bytes are unchanged across both.
- [The request schema duplicates values derivable from registration] -> Require
  exact equality rather than trusting duplicates; the redundancy makes the
  reviewed live invocation self-contained and tamper-evident.
- [Registration bytes may or may not change] -> Re-render canonically after the
  source commit and compare bytes. Preserve the current registration if bytes
  differ; in either case refresh source and implementation hashes.
- [A passing local fake-process test may not match CommunicationMod] -> Keep r4
  blocked until one fresh, previously absent identity passes the real Windows
  no-action smoke, restoration/isolation checks, and independent attestation.

## Migration Plan

1. Add red regressions for the r3 ready-ordering race and the post-release child
   boundary, then implement the minimum runner/main/verifier changes.
2. Run focused tests, full Windows pytest, compile/import checks, strict
   OpenSpec validation, diff checks, and independent code review. Commit and
   push this change without launching the game.
3. Re-render the registration, compare canonical bytes, and refresh the review
   table for the new commit and all implementation hashes.
4. Amend the v2 study to preserve r3, bind the tracked qualifier, and name a
   previously absent r4 root. Independently review and commit that candidate.
5. Run r4 once. Only successful result replay, restored live configuration,
   unchanged inventories, no surviving process, and independent attestation can
   authorize `start`.

Before step 4 creates r4, rollback is an ordinary source revert plus binding
regeneration. After any r4 artifact exists, r4 is immutable and a new reviewed
identity is required for recovery.

## Open Questions

None. The request/result field sets, ownership, one-shot behavior,
exit boundary, output isolation, and authority contracts above are fixed.
