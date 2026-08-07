## Context

The first cross-fitted hierarchical execution is terminal and non-resumable.
It debited 12 scheduled positions, completed 11 environments, and produced no
complete 64-trajectory chunk because complete validation of its 63,171,200-byte
registration recurred at least 40 times per completed access. A later
source-only repair removed the amplification, completed exact elapsed-resource
accounting, bounded terminal publication, and hardened true-child lease
supervision. Those repairs passed synthetic and repository gates but have not
run against an actual-scale registration lifecycle.

The nearest comparable consumed simulator experiment completed 512 training
episodes, eight updates, and eight checkpoints in 2,165.452 charged seconds.
That is useful deterministic historical capacity evidence, not authority to
reuse its cohort, policy, or outcome. The old cross-fitted schedule contains
512 seed identities and is consumed as a whole even though only 12 were
debited.

A source-only implementation investigation rebuilt the full inventory at the
current pre-change `HEAD`: 1,676,494 provenance rows from 344 sources occupied
347,568,895 canonical JSON bytes and took 158.402 seconds. The complete
inventory therefore cannot fit a 128 MiB plain-JSON publication contract.

## Goals / Non-Goals

**Goals:**

- Decide whether the repaired control plane, a canonical fresh cohort, and the
  unchanged 14,400-second resource ceiling justify drafting a separate
  empirical successor registration proposal.
- Exercise actual registration-scale context ownership, one complete
  64-position control chunk, terminal closeout, and post-exit verification
  without importing Torch or native code and without constructing an
  environment.
- Bind the decision to exact pushed source and immutable historical evidence,
  make the budget formula deterministic, and permit only one typed `go` or
  `no_go` result.
- Preserve an independently checkable full candidate inventory and schedule so
  the complete old 512-seed cohort is demonstrably absent.

**Non-Goals:**

- Creating an empirical registration, execution request, approval, or
  authorization.
- Loading Torch, the native simulator, a production checkpoint, or a policy;
  accessing a seed through an environment; fitting, training, evaluating,
  running OPE, gameplay, CommunicationMod, qualification, or promotion.
- Changing estimator, folds, features, rewards, family objective, optimizer,
  chunk count, cohort size, resource limits, stop gates, or success criteria.
- Claiming policy quality, mechanism evidence, causal effect, formal-RL
  readiness, target-supported outcomes, or live value.

## Decisions

### Bind the audit to a pushed implementation commit

The auditor source and tests are committed and pushed before publication. The
audit then requires local `HEAD`, `origin/master`, and the requested source
commit to agree, requires a clean tracked worktree, and hashes every audited
source and immutable evidence input from that Git tree. Generated readiness
artifacts are committed only after the audit closes. Bound evidence is parsed
and shape-checked as part of `source_binding` before any cohort inventory work.
The consumed schedule must have exact fields, 512 ascending integer seeds,
eight exact 64-seed chunks whose entries are independently validated as
integers, and the required canonical seed digest; those
failures therefore cannot be mislabeled as cohort freshness.

Before the first source gate, the auditor atomically claims
`reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/<source_commit>`
by writing `attempt_started.json` in a hidden claim directory and atomically
renaming that complete directory. The source commit, not caller paths or the
audit id, is the one-shot key. If interruption occurs across the helper-return
boundary, the runner recovers only a byte-identical started receipt for its own
arguments and writes one typed, all-false `attempt_terminal.json`; a second
invocation for an existing source is rejected without modifying it. A verified
staging tree instead writes `attempt_verified.json` immediately before final
installation, including exact SHA-256 and size bindings for all three staged
files. There is no callable path that writes a validated artifact set
directly to a final publication directory. If interruption is observed after
the atomic staging rename, the runner recognizes the installed boundary only
when the exact verified receipt exists, the final directory validates against
that receipt, and the staging directory is absent; it never adds a contradictory
terminal `no_go` receipt to that installed `go`.

Alternative: audit an uncommitted tree. Rejected because later publication
could not prove which code produced the decision. Alternative: bind the report
commit to itself. Rejected because the report and seed inventory would change
the Git tree being inventoried.

### Publish the complete candidate inventory but grant it no execution role

The existing source-only seed inventory builder scans supported committed
report blobs from the pushed implementation tree. The audit publishes its
canonical full inventory plus the first 512 ascending nonexcluded candidates
as deterministic gzip (`mtime=0`, empty filename) over canonical JSON. The
stored artifact is limited to 64 MiB and its bounded decompressed canonical
form to 512 MiB; both byte identities and sizes are published.
It separately extracts all 512 seeds from the consumed cross-fitted
registration and requires an empty intersection. Independent verification
checks deterministic compression, bounded decompression, canonical ordering,
digests, counts, source bindings, fixed selection, and full-cohort
disjointness.

Actual-scale candidate JSON is encoded directly through a canonical JSON
iterator into deterministic gzip while canonical and stored hashes are updated.
The independent verifier reconstructs Git blobs one at a time through one
`git cat-file --batch` process, streams its expected candidate gzip to a
temporary sibling, and compares the expected and staged files in bounded
chunks. The large candidate is never deep-copied or fully decompressed into a
second in-memory representation during publication verification.

The candidate seed integers are data only. No access journal, environment,
native adapter, runtime, policy, or checkpoint may consume them in this
change. A later registration may adopt them only by binding the same pushed
tree and passing its own independent inventory review.

Alternative: exclude only the 12 debited seeds. Rejected because that would be
an evidence-driven retry of the remaining old cohort. Alternative: reserve an
arbitrary new numeric range. Rejected because canonical inventory selection is
already deterministic and auditable.

### Rehearse one actual-scale control chunk in an isolated scratch root

The auditor derives an ephemeral registration from the consumed 63 MB
registration by changing only its synthetic identity and scratch output path,
then recomputing an internal synthetic identity. It creates one validated
context, initializes the lease/journal/resource lifecycle, records one full
64-position debit/terminal control chunk with synthetic terminal payloads, and
closes a typed synthetic failure bundle. It never calls dependency loading,
environment construction, runtime fitting, or checkpoint encoding.

The rehearsal runs in a child process with imports of Torch and the native
adapter blocked. Each of context setup, the 64-position control chunk, and
terminal closeout has a fixed 300-second watchdog. Only pass/fail stage outcomes
enter the canonical decision; observed wall times are optional diagnostics and
cannot turn a failed ceiling into `go`. Scratch artifacts are independently
verified, summarized by hashes/counts, then excluded from the published
readiness artifact inventory. The child owns a separate process group; timeout
or malformed output terminates the complete process tree and must confirm the
child exit before the audit closes.

Alternative: run all 512 synthetic positions. Rejected because one exact chunk
plus structural constant-validation evidence exercises the recurring boundary
without making the source-only audit unnecessarily long. Alternative: run a
native smoke episode. Rejected because that would consume empirical authority
before the go/no-go decision exists.

### Use a fixed conservative budget equation

The decision reserves 3,600 seconds for repaired source-control overhead:
300 seconds for context/setup, eight times 300 seconds for chunk control, 300
seconds for terminal closeout, and a fixed 600-second contingency. It then
binds the historical artifact's raw charged field exactly as
`2165.4520000000193`, uses the pre-registered three-place workload term
`2,165.452s`, and multiplies that term by `3.0`. The fixed readiness equation is:

`3600.0 + 3.0 * 2165.452 <= 14400.0`

The resulting upper projection is `10,096.356s` with `4,303.644s` margin. The
auditor verifies the raw historical value, artifact hash, and arithmetic rather
than estimating a coefficient from the new rehearsal. Both the auditor and the
independent verifier parse that bound JSON number as an exact decimal before
any binary-float conversion and reject a quoted string even when its characters
match. Any raw value, input, ceiling, multiplier, or
arithmetic drift is `no_go`.

The source gate binds the historical artifact's bytes but does not interpret
its budget terms. Content validation is deferred until candidate freshness and
rehearsal/scaling have passed, preserving the fixed fail-fast gate order.

Alternative: decide from measured mean milliseconds per helper. Rejected
because machine timing is noisy and invites threshold tuning. Alternative:
increase the empirical wall-time budget. Rejected because readiness must be
shown under the unchanged registered resource class.

### Make the verifier independent and the authority one-way

The verifier is a separate standard-library module that never imports the
auditor, Torch, runtime, or native adapter. It validates canonical schemas,
all-false authority, Git/source/evidence bindings, candidate inventory and
schedule arithmetic, consumed-cohort disjointness, stage ceiling results, the
fixed budget equation, and JSON/Markdown agreement. It emits only verified
summaries or a verification failure. The auditor converts the first safely
observed failure into the source attempt's typed `no_go` receipt and does not
continue into downstream gates after their prerequisites become untrusted.

The auditor first writes the three publication artifacts to a hidden sibling
staging directory. On Windows it starts rehearsal and verifier processes behind
a named startup handshake, assigns them to a kill-on-close Job Object before
release, and confirms every enumerated process handle is signaled on cleanup;
other platforms use an isolated process group. The independent publication
verifier has an immutable 900-second ceiling. A timeout or nonzero/mismatched
summary terminates the process tree and writes only the attempt's typed
`no_go_artifact_binding` receipt, regardless of earlier-gate tokens quoted in
verifier diagnostics. Gate typing honors only a leading structured
`no_go_<gate>` marker in the raw exception string; normalization, a hyphenated
lookalike, or a nested token cannot create a gate. Scratch-verifier stderr is
first parsed as canonical JSON and only a literal leading marker in its `error`
field may select `control_plane_scaling`; every other structured gate remains
`rehearsal_boundary`. Untyped exception text falls back to
the currently executing gate and cannot be influenced by a caller path.

After verification, the runner streams the predictable staging files into a
cryptographically random hidden sibling, checking every copied SHA-256 and size
against the pre-verifier binding. It rebinds the sealed files, retires the
original staging tree, and atomically renames only that sealed snapshot to the
caller's final output path. Thus an unverified
authoritative-looking `go` directory is never exposed.

The runner generates and owns the exact random sealed path before invoking the
sealing helper, so ownership survives interruption across the helper-return
boundary. Any failure or interruption before the final rename removes only
that exact path. A failed final rename performs the same bounded cleanup. If
an output entry appeared but does not validate against the verified receipt,
recovery fails closed as `no_go_artifact_binding` rather than leaving a
started/verified attempt with no terminal outcome.

A verified `go` changes one state only:
`empirical_successor_registration_proposal_eligible=true`. Every execution,
training, evaluation, gameplay, formal-RL, qualification, and promotion flag
remains false. A `no_go` is terminal for this source identity; changing a gate
requires a new proposal and source commit, not an in-place rerun.

## Final Outcome

The single canonical audit for pushed source
`863ae5a4046df110e4f9028bb3c56d556a7c6a43` closed as terminal
`no_go_source_binding` before inventory reconstruction or rehearsal. The bound
registration's schedule correctly retained eight fields, while the readiness
implementation's exact-field validator omitted `canonical_search_start`,
`inventory_sha256`, and `selection_schema_version`. No output publication was
installed, every authority and empirical-operation flag remained false, and
independent receipt review confirmed canonical bytes, matching identities,
valid digests, and absent output/scratch/staging paths. This source is consumed
and SHALL NOT be retried. Any correction requires a new source-only OpenSpec
change, exact bound-schema regressions, and a new pushed source identity; this
outcome does not make an empirical registration proposal eligible.

## Risks / Trade-offs

- [One source-only chunk may miss later journal/checkpoint scaling] -> Use
  structural validation-count checks, eightfold fixed control reservation, a
  600-second contingency, and a 3x historical workload multiplier; keep the
  later empirical request separately reviewable.
- [The seed builder and report verifier could share a defect] -> Publish the
  complete deterministically compressed inventory, independently validate its canonical structure and Git
  source bindings, and require the later registration workflow to rebuild it
  again before any authority exists.
- [Actual-scale evidence can multiply memory use across producer and verifier]
  -> Use shallow mapping validation, iterator-based canonical gzip, streamed
  Git blobs, bounded file comparison, and a small-payload-only in-memory helper.
- [Wall-clock watchdogs vary by machine] -> Use generous fixed 300-second stage
  ceilings and include only pass/fail in the decision. A timeout is `no_go`, not
  a reason to tune or retry.
- [A crash could leave a partial or apparently valid final report] -> Consume
  the source identity before work, retain a durable started/terminal or
  started/verified receipt, and install only an independently verified staging
  directory by atomic rename.
- [A readiness `go` could be mistaken for training approval] -> Keep every
  authority field false except proposal eligibility and require a new exact
  human-approved request before native loading or seed access.
- [Publishing candidate seeds exposes them to later analysis] -> Treat the full
  candidate schedule as bound to this readiness identity; any inspection or
  source change that could influence the mechanism requires a fresh inventory
  and explicit cohort decision.

## Migration Plan

1. Add RED schema, binding, disjointness, stage-ceiling, budget, authority, and
   import-isolation tests.
2. Implement the auditor and independent verifier without native/Torch imports.
3. Run focused source-only tests and an independent review; commit and push the
   implementation source after the repository commit gate passes once.
4. Run the one bounded readiness audit against that pushed commit, verify it in
   a fresh process, and publish deterministic gzip inventory, JSON, and Markdown.
5. Publish the project-direction decision, sync/archive the change, run required
   final checks, then commit and push the evidence. Do not create an empirical
   registration in this change.

Rollback before evidence publication removes the additive code/tests. Rollback
after publication reverts those files and the readiness artifacts. In both
cases consumed terminal bundles, candidate seed identities, checkpoints, and
game configuration remain unchanged.

## Open Questions

None. A later empirical proposal must decide whether to adopt the exact
candidate schedule; this readiness change deliberately cannot decide or
authorize that step.
