## Why

The third v2 pre-lock qualification produced a valid CommunicationMod `ready`
record within the 120-second deadline, but an independently scheduled external
monitor did not publish `release` before the fixed 10-second deadline. The
child failed closed with no gameplay or study contamination, yet r1 and r3 now
show that an untracked multi-command qualification procedure can consume
immutable identities even when the runtime handshake behaves correctly.

The independently replayed r3 failure record, final inventory, attempt, ready,
restored configuration, unchanged markers/runs/checkpoints/logs, and empty
process inventory establish a release-side orchestration failure and forbid
r3 retry or study `start`. The narrower monitor-command mechanism was not
captured independently, so this change addresses the demonstrated ownership
and ordering gap rather than treating an unpreserved shell assertion as fact.

## What Changes

- Add a tracked pre-lock `qualify` command to the existing outcome-evidence
  runner, entered only through a fixed stdlib-only `python -I -S -c` launcher
  encoded as one whitespace-free token compatible with CommunicationMod's
  command splitter.
  The launcher receives an externally preserved runner SHA-256, rejects a
  runner path with any symlink/reparse component or NTFS alternate data stream,
  reads and hashes the runner, and executes those validated bytes directly
  from memory. One parent process
  will exclusively own qualification preflight,
  attempt publication, one exact qualification-child launch derived from the
  registered command with fixed `-I -S` isolation added, ready validation,
  immediate release publication, qualification-child completion, cleanup, and
  deterministic result recording.
- Add a qualification-only child exit boundary after a valid release is
  consumed and before exploration initialization, callbacks, agent
  construction, gameplay, or study-slot claim. The boundary will require an
  explicit token bound to the loaded attempt and will be unavailable to normal
  gameplay or `run-next` children.
- Make qualification roots and child launches one-shot. Existing handshake or
  result artifacts, malformed bindings, timeout, early exit, release failure,
  or cleanup failure will fail closed without retrying the identity or creating
  a run lock, ledger, manifest, trace, marker, checkpoint, or gameplay record.
- Bind each invocation to a reviewed request source plus externally supplied
  request self-hash, exact file SHA-256, byte count, and review commit R. The
  request records implementation snapshot S; R must be its direct child, its
  exact diff must equal a non-executable request-declared allowlist, launch
  HEAD must equal R, and registration plus registered implementation bytes
  must remain unchanged across S and R. A pure-stdlib bootstrap runs before
  project imports, extracts the exact external R anchor without argparse,
  requires `HEAD == R`, hashes every tracked executable/importable worktree
  file against its R tree blob rather than trusting Git's stat cache, and
  rejects tracked drift, nonordinary index flags such as assume-unchanged or
  skip-worktree, unsafe Git attributes/filters, and untracked
  executable/importable paths through a fail-closed inert-format allowlist
  that treats unknown and extensionless forms as executable/importable. Stream
  non-inert bytes through guarded
  `git -c core.autocrlf=true hash-object --path --stdin` so Windows newline
  normalization is accepted without permitting binary drift, while allowing
  only R-tracked raw-byte-identical inert text/eol attributes and rejecting
  every other attributes source or configured filter,
  before exclusively publishing the reviewed
  bytes as the active request.
- Reject every symlink or Windows reparse component in externally supplied
  qualification paths lexically, before path resolution, file-type checks,
  reads, traversal, or hashing, so a junction alias cannot hide its target;
  reject UNC and Win32 device namespaces, any colon outside the drive
  component (including NTFS alternate data streams), and any component ending
  in a dot or space, lexically before any filesystem probe.
- Apply that qualification-only guard before the parent invokes the shared
  ready loader and, when the token is present, before `main.py` creates the
  coordinator or invokes the shared handshake/attempt loaders; preserve the
  shared handshake module and ordinary registered-study behavior.
- During independent replay, guard the qualification root before classifying
  any control entry and inspect every absolute path plus registered
  implementation path in the reviewed registration JSON before invoking the
  normal registration validator or any resolving helper.
- Purely bind the declared active request, attempt, ready, release, completion,
  and failure paths to fixed direct children of that guarded root before any
  path classification, inventory, existence probe, or read.
- Use the pinned trusted absolute Windows Git executable for every producer and
  verifier qualification Git call; never permit current-directory executable
  lookup before the untracked-source inventory runs.
- Require the qualifier to start under Python isolated mode through that exact
  externally reviewed launcher before argument parsing or project imports. The
  runner rechecks the original launcher command and external file anchor, then
  binds that anchor to its reviewed implementation hash; direct runner-file
  execution is rejected. Derive the owned child command
  from the registered executable, main path, and arguments with fixed
  `-I -S` inserted after the executable, remove every inherited `PYTHON*` and
  `GIT_*` variable, redirect qualification bytecode-cache lookups to the null
  device, allow only no-follow source modules from repository paths, and bind
  that exact derived command in request and result evidence. Qualification
  replay does not import ordinary registration-audit helpers before its
  reviewed-source checks.
- Bind every qualification Git process to the guarded local repository and its
  ordinary `.git` directory with a sterile Git environment and command line.
  Reject metadata reparse points, replace refs, grafts, alternate object
  stores, common directories, repository info attributes, partial-clone or
  promisor remotes, extension protocols,
  include/fsmonitor/hooks/filter/external/textconv/SSH configuration, or any
  Git stderr, while explicitly disabling replacement, optional locks, prompts,
  fsmonitor, hooks, external diff, textconv, system attributes, and lazy fetch.
- Bind request source, active request, S, R, the registration identity,
  implementation-map hash, exact file hash/size, and review allowlist in one
  canonical self-hashed `review_binding` carried by terminal and audit
  evidence. Independent historical replay reads S/R Git blobs using the same
  external anchors and does not depend on the verifier's current HEAD or
  worktree bytes.
- Require direct qualification replay to start the standalone verifier with
  Python `-I -S` before argument parsing or project imports and redirect its
  bytecode-cache lookups to the null device while allowing only source modules
  from repository paths; disable long-option abbreviation so a shortened
  qualification option cannot bypass the pre-argument isolation gate; preserve
  ordinary registration audit startup.
- Publish optional qualification audit output only through no-follow,
  exclusive creation at a lexical absolute path whose canonical parent remains
  outside the qualification root and which matches no request-bound path or
  forbidden subtree; reject alternate-data-stream syntax and Win32 trailing
  dot/space aliases before canonical comparison or creation, and never
  truncate, replace, or add verifier output beneath one-shot evidence. Preserve ordinary
  registration-audit `--output` behavior.
- Bound every pre-release Git metadata traversal, Git subprocess, source and
  configuration read, and qualification-root inventory hash by the one release
  deadline derived from the ready timestamp. File hashing is chunked so the
  budget is checked throughout large-file reads.
- Keep CommunicationMod stdout reserved for the child protocol and avoid live
  log reads while the qualification child is running. Qualification diagnostics
  will use canonical files or stderr, with post-exit isolation checked
  separately.
- Add red-first regressions for the r3 ordering race, the post-release exit
  boundary, stale artifacts, exact-command launch count, token binding and
  leakage, timeout and malformed ready cases, release/cleanup/publication
  failure, external-anchor and review-chain drift, and independent terminal or
  partial-prefix replay. Distinguish a reviewed source that was never consumed
  from valid consumed prefixes and malformed/orphaned consumed evidence.
- Require independently preserved result self-hash/file-SHA/size anchors for
  terminal replay. A self-hashed completion or failure file without those
  external anchors remains untrusted and cannot become verified evidence.
- Preserve the handshake protocol, 120-second readiness deadline, 10-second
  release deadline, study schedule, behavior rates, seeds, estimator,
  thresholds, policy, checkpoints, and training authority.

Success means the tracked qualifier accepts a valid ready record even when it
appears immediately after the owned child starts, publishes release within the
child deadline, observes a bound success exit before exploration or agent
creation, leaves every study/gameplay artifact absent, and passes focused plus
full pytest and strict OpenSpec validation. A successful offline test does not
authorize r4 or `start`; the study still requires a separate reviewed binding
refresh, a previously absent qualification identity, real CommunicationMod
isolation, an independently reviewed CommunicationMod command that preserves
the exact launcher literal and runner SHA-256, and independent attestation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-outcome-evidence-expansion`: require a tracked, owner-controlled,
  one-shot pre-lock qualification orchestrator and a child-verifiable exit
  boundary before any future qualification can authorize a study run lock.

## Impact

- Runtime and CLI: `scripts/run_noncombat_outcome_evidence_expansion.py`,
  `main.py`, and the independent qualification replay path in
  `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`; the
  handshake implementation and protocol remain unchanged.
- Tests: outcome-evidence runner, main startup/runtime errors, study handshake,
  committed registration review, and independent qualification-result replay.
- Planning: the active v2 study remains blocked. Its r3 evidence must stay
  immutable, and a later amendment must refresh source/implementation bindings
  and name a previously absent r4 root before any live qualification.
- Registration: both modified runtime files are already registered
  implementation paths. Canonical registration bytes may remain unchanged if
  path and contract fields stay fixed, but source commit and file hashes must be
  regenerated and independently reviewed; any actual registration-byte change
  must preserve the current registration as superseded.
- Non-goals: no gameplay-policy change, no RL training, no parameter tuning, no
  study collection, no run lock, no ledger, no CommunicationMod Java change,
  and no retry or reinterpretation of r1, r2, or r3.
- Rollback boundary: before a newly reviewed qualification identity is created,
  this source change can be reverted normally. After an r4 identity is
  attempted, its artifacts are immutable and recovery must use a separately
  reviewed identity rather than source rollback, deletion, or retry.
