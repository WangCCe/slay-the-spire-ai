## Context

The API v3 event observation implementation is committed, archived, and covered
by 96 focused regressions plus the repository commit gate. No v3 native module
has been built or loaded. The last own-trajectory Current bridge check is an
immutable API v2 result: seeds `2000..2003` were consumed and the first replay
stopped at unsupported `The Cleric` semantics.

The existing bridge registration schema intentionally permits only that reused
historical Stage 2 cohort. Changing its `reused_seeds` field or treating the new
resolver as inherited authorization would erase the distinction between old and
new evidence. The local external simulator checkout also has a dirty physical
source identity, so a parent Git commit alone is insufficient provenance.

The production repository contains unrelated untracked historical reports. A
valid execution boundary can therefore require a clean tracked tree, exact
registration blob at `HEAD`, and `HEAD == origin/master` without requiring the
whole directory to have no untracked files.

## Goals / Non-Goals

**Goals:**

- Build and bind one API v3 native module without constructing an environment
  before registration.
- Introduce an independent registration and evaluator for one fixed new cohort.
- Prove exact physical identity, seed isolation, legal Current action mapping,
  deterministic replay, terminal completion, and aggregate four-category
  coverage.
- Preserve a durable consumed marker before the first environment exists and a
  canonical pass or fail result afterward.
- Keep the result structural and independently verifiable without replaying
  native seeds.

**Non-Goals:**

- Reusing `2000..2003`, touching reserved final-test seeds `6000..6031`, or
  selecting seeds after observing simulator trajectories.
- Revalidating all 25 events empirically, requiring a rare N'loth encounter, or
  claiming simulator/live mechanics parity.
- Comparing terminal floor or victory against a baseline, tuning Current,
  fitting a model, changing reward, or authorizing formal RL.
- Importing the adapter into Communication Mod or launching live gameplay.

## Decisions

### Use a new evaluator and schema instead of widening historical Stage 2

Add `analysis_scripts/noncombat_total_event_native_compatibility.py` with a new
input schema. It may reuse typed hydration, Current session, native identity,
and canonical hashing helpers from the bridge, but it does not add a third mode
to the v1/v2 registration validator. Historical registrations and reports
remain readable and unchanged.

The new registration binds the archived implementation closeout and r2 bridge
result as predecessors, but neither predecessor grants execution authority. The
new capability's own registration, source commit, module identity, cohort, and
limits are the only authority for the run.

Alternative considered: edit the r2 `reused_seeds` list. Rejected because those
seeds are consumed and the old schema explicitly proves equality with prior
policy-validity evidence.

### Separate implementation, module binding, registration, and execution

The sequence has four irreversible boundaries:

1. Implement the evaluator with fake-environment regressions, run focused tests
   and the commit gate, commit, and push it.
2. Build the adapter out of tree and load only its API/build-info surface. Hash
   the module and physical adapter/simulator sources. Do not instantiate
   `Environment`.
3. Generate the exact registration and seed ledger, commit and push them, and
   verify the tracked tree is clean, the registration bytes equal the `HEAD`
   blob, and local `HEAD` equals `origin/master`.
4. Execute once. Before the first `Environment(seed, 0)` call, atomically write
   an execution journal that marks all registered seeds consumed.

The registration need not contain its own commit hash. Execution proves
prepublication by recording `HEAD`, requiring the registration path to be
tracked at that commit, and requiring the same commit at `origin/master`.

Alternative considered: generate and execute an uncommitted registration in
one command. Rejected because a failure would leave no independently reviewable
pre-seed contract.

### Freeze a small untouched structural cohort

The exact cohort is `7000..7007`. It is fixed in the proposal before native
inspection and is disjoint from fit `0..19`, smoke `1000..1031` and
`2000..2063`, policy-validity `3000..3063`, warm-start train `4000..4031`,
validation `5000..5015`, and reserved final-test `6000..6031`.

A generated seed ledger binds the exact prior registration files and expands
their consumed or reserved seed sets. The evaluator recomputes the ledger from
those bound files before journal creation. It accepts no seed, replay, category,
decision-limit, or timeout override from the CLI.

Each seed runs twice with a fresh episode-local Current session, at most 500
target decisions, and a total execution deadline of 120 seconds. The complete
cohort becomes consumed at first environment construction. If execution stops
partway through, the untouched suffix is still unavailable to a retry under
this identity.

Alternative considered: pre-screen many seeds and register those with broad
event coverage. Rejected because pre-screening is already seed use and would
turn the compatibility cohort into selected evidence.

### Gate structural behavior, not event frequency or policy quality

Every selected action must be one reported candidate and the returned
transition must name that action. Source snapshot/candidate hashes, fallback,
tracker, event semantics source, Current position, and simulator choice index
are recorded at every applicable decision. Both replays must produce identical
canonical trajectory bytes and a valid terminal outcome.

The aggregate must include at least one route, shop, event, and card-reward
decision. Every native event decision must resolve through the total contract;
versioned inline fallback is not expected from v3 snapshots. Encountered event
identities and sparse mappings are diagnostics. N'loth absence is not a gate,
because an eight-seed unselected cohort cannot guarantee a rare event and the
contract regressions remain the total-coverage evidence.

Terminal floor and victory are recorded only to make trajectories complete.
They are not compared, thresholded, or promoted to baseline evidence.

### Publish one operational journal and deterministic canonical artifacts

The journal is written atomically before environment construction and records
registration hash, preregistration commit, cohort, start state, and
`cohort_consumed=true`. It may contain timestamps and is therefore operational,
not a deterministic replay target. On normal pass or fail, it is finalized and
bound by the manifest. If the process dies, a `started` journal is itself a
terminal consumed record requiring read-only closeout, never a retry.

Canonical artifacts contain configuration, trajectory rows or a field-specific
failure, metrics, report, and manifest. A separate verifier reloads the
registration and preserved rows, rejects duplicate keys or identity drift, and
recomputes every deterministic artifact without importing or loading the native
module.

Alternative considered: prove reproducibility by running all seeds a third
time. Rejected because the two in-execution replays are the preregistered native
reproduction, while later verification must not spend the cohort again.

## Risks / Trade-offs

- [The module imports but its first environment crashes] -> Persist the consumed
  journal first, publish the exact blocker if possible, and prohibit retry.
- [A native call hangs past the Python deadline] -> Retain the started journal;
  the external command timeout may terminate the worker, but the cohort remains
  consumed and the result is closed out as failed.
- [The eight seeds miss a rare dynamic event] -> Report observed identities and
  keep total event coverage grounded in contract regressions, not frequency.
- [Untracked historical files make the repository appear dirty] -> Require only
  tracked-clean status plus exact committed registration bytes and pushed HEAD.
- [A positive floor or victory is overinterpreted] -> Publish no comparison or
  policy threshold and keep every downstream authority false.
- [The external simulator checkout drifts] -> Bind parent, dirty flag, compiled
  source digest, file count, and both dependency commits before seed access.

## Migration Plan

1. Add red registration, identity, journal, fake-environment, deterministic
   replay, failure, publication, and verifier regressions.
2. Implement the new evaluator and any narrow reusable bridge observation
   surface; run focused tests, strict OpenSpec validation, and the commit gate.
3. Commit and push implementation before building the v3 module.
4. Configure and build in a new ignored directory; collect build/source identity
   without constructing an environment.
5. Generate the seed ledger and exact registration, verify them, commit and push
   the preregistration boundary.
6. Recheck pushed HEAD and execute once. Preserve pass, fail, timeout, or partial
   journal state without retry.
7. Run the no-native verifier, update project direction, sync specs, archive,
   commit, and push.

Before step 6, rollback may remove the new evaluator, ignored module, and
unexecuted registration. After journal creation, rollback never deletes the
registration or execution evidence; only later code can be reverted.

## Open Questions

None. The seed set, replay count, limits, gates, consumption rule, and authority
are fixed before implementation.
