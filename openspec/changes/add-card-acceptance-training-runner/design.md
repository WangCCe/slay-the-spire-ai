## Context

The r6 inventory registration and bounded training request are independently
reviewed and pushed. The registered experiment control exposes validation,
authority, lease, journal, resource, checkpoint, continuation, terminal, and
rollback APIs. The runtime exposes the complete paired training loop. No source
module composes those APIs into one production command, so parent task 6.4 must
remain blocked even though request publication is valid.

The experiment control/runtime bytes remain identical to source commit
`525c302df2d54cf06c756a9dc55fbae4ed9cb8b0`. Registration support was added
later to the seed-inventory producer and independent verifier. The runner must
bind that additive support without redefining the registered experiment source
or rewriting the pushed r6 registration/request.

## Goals / Non-Goals

**Goals:**

- Provide one exact Windows CPU runner with a canonical launch manifest and a
  closed `preflight`, `run-training`, and `terminalize-dead-owner` command set.
- Validate every immutable registration/request/authorization/approval/source/
  path/resource binding before runtime or native import.
- Compose the existing execution context, lease, write-ahead accounting,
  registered training schedule, complete checkpoints, and terminal lifecycle.
- Preserve the existing setup reopen and sole complete-checkpoint continuation
  semantics without adding retry or tuning paths.
- Close a partial prefix after a proven process death without restoring runtime
  state, accessing seeds, or replaying any environment.
- Make every pre-runtime failure testable without native, model, environment,
  checkpoint, or seed access.

**Non-Goals:**

- Publishing training authorization, resolving the current conversation
  watermark, or launching task 6.5.
- Changing the model, objective, optimizer, cohorts, resources, simulator,
  native dependency, runtime algorithm, or r6 request.
- Adding canary/holdout execution, gameplay integration, CommunicationMod, OPE,
  qualification, promotion, or production model loading.
- Generalizing a reusable job framework beyond this exact training stage.

## Decisions

### Add a standalone runner without modifying registered experiment modules

Create `noncombat_card_acceptance_empirical_successor_training_runner.py`. It
imports only the standard library and the source-only control plane at module
load. The independent registration verifier and Torch/native runtime are loaded
through explicit private loaders only after the runner has validated the launch
manifest, request, authorization, approval, launch observation, source bytes,
output state, and resource identity.

This preserves the registered experiment control/runtime identity. Modifying
the existing experiment CLI was rejected because it would invalidate the
source commit and source-inventory digest carried by the r6 registration and
request. A generic orchestration framework was rejected because it adds no
evidence for the immediate training boundary.

### Freeze a launch manifest before authorization

The canonical launch manifest binds the r6 registration/request/review paths
and digests, exact runner path/hash/pushed commit, registered experiment source
commit/inventory, current additive seed-inventory producer path/hash,
independent registration-verifier path/hash, Windows
interpreter, the exact source-inventory path/hash already bound by the r6
registration request, output root, resource map, denied operations, and exact closed CLI
set. It binds the exact argument shape and authority requirements of all three
commands; an unregistered command or argument is source drift. It also binds
one canonical rollback-authority document/hash, exact candidate-disabled local
control target, control checkpoint/config identities, and read-only production
CommunicationMod/checkpoint inventory.
It grants no execution authority. The manifest and a text-only independent
review must be pushed before parent task 6.4 may publish authorization.

Keeping this separate from the already pushed stage request avoids rewriting a
valid request. The later runner requires both the existing stage authorization
and the exact manifest, so neither can substitute for the other.

### Bind each reviewed command transitively after authority exists

The source-only preflight manifest grants no authority. Its canonical runner
composite contains the launch-manifest SHA, exact command identity,
rollback-authority SHA, request SHA, registration SHA, output root, resource
map, and a proof that every command operation is a subset of the request's
execution authority. Rollback is restricted to restoring the candidate-disabled
target JSON inside the bound output root plus byte-level identity observation;
it cannot broaden model, native, environment, seed, gameplay, production-model,
qualification, promotion, or downstream authority.

For standing delegation, a deterministic runner-composite resolver validates
the existing delegated stage approval, immutable broad grant and exclusions,
and a fresh runner launch observation that names the composite digest. It may
bind only a proven request-subordinate composite. For exact external-human mode,
the approval message and fresh runner launch observation must carry the exact
composite digest verbatim. Both modes produce an all-false run envelope binding
the stage authorization, approval mode/record, launch observation, and composite.
The envelope is independently reviewed and pushed before `run-training`.

`terminalize-dead-owner` never reuses the run envelope as current authority.
After the prior owner is proven dead, a new composite and fresh authority
resolution bind the run-envelope SHA, old owner, lease bytes, output root,
journal/resource/checkpoint prefix, fixed failure classification, manifest and
rollback SHA. The independently reviewed pushed terminalization envelope is
required before stale-lease reclamation. Its SHA is written to a closure marker
before rollback and terminal publication. A sibling terminalization guard,
created by the original run before the managed output root and excluded from
its artifact inventory, serializes closure commands. While holding that guard,
the terminalizer revalidates process death, exact lease bytes, the envelope-
bound failure prefix, and terminal absence immediately before stale-lease
reclamation; a conflict releases the guard without changing the execution lease
or managed output.

If a terminalizer dies after lease reclamation or closure-marker publication,
the same terminalization envelope may perform an idempotent closure-only resume.
It must prove the new terminalizer owner dead, preserve the original bound
failure prefix exactly, accept only the identical closure marker and already
published registered rollback/terminal suffix, and continue the fixed closure
sequence. It cannot create a new failure classification, access runtime/seeds,
or make training runnable. Ambiguous staging remains fail-closed evidence and is
never deleted or repaired automatically.

The runner revalidates every transitive edge. This bridges the older request/
stage-authorization schema to the new source-bound runner without modifying
registered control bytes or treating an envelope as authority by itself. Any
missing, unpushed, stale, revoked, mismatched, broadened, or wrong-command edge
fails before lifecycle acquisition or rollback-context creation.

### Use one process-owned lifecycle

The runner process validates all source-only inputs, builds one immutable
execution context, and acquires the existing `ExecutionLease` under its own PID.
All journal, resource, checkpoint, stage, terminal, and rollback operations use
that exact context and lease. Runtime import and environment construction occur
only inside this owned lifecycle.

The runner partitions the registration's exact sorted 512-seed training cohort
into eight fixed slices and calls `collect_and_complete_paired_training_chunk`
once per remaining 64-pair chunk. It journals candidate then control before each
environment, charges resources monotonically, and publishes that chunk's
canonical checkpoint before starting the next slice. The runner derives the
control plane's eight component hashes from canonical checkpoint subdocuments;
the independent runner verifier repeats that derivation from raw bytes. This
preserves the registered runtime bytes while making complete boundaries durable.

Before the first chunk the runner publishes a canonical zero-progress initial
checkpoint bound to the registered matched bootstrap. For every chunk it
publishes a chain record containing the predecessor checkpoint file SHA,
initial component hashes/counters, final checkpoint file SHA, final component
hashes/counters, and chunk seeds. The in-memory initial checkpoint bytes must
equal the predecessor's final bytes; on continuation, the restored runtime must
re-encode to the same predecessor bytes. Any discontinuity fails before the
next environment access or control-plane checkpoint publication.

The pushed r6 registration file remains byte-for-byte immutable and retains its
original self-digest. After the runner independently validates that registration
against the manifest-bound source inventory and independently validates the
manifest-bound rollback authority, its registration validator returns a
process-local execution view that adds only `rollback_authority_sha256`. The
original `registration_sha256` remains the request/lease identity. A write-once
runner-launch marker binds the manifest SHA, run-envelope SHA, command identity,
and rollback SHA
inside the managed artifact prefix so the independent runner verifier can
reconstruct this composition. No file registration is rewritten or rehashed.

Before runtime import, an authorized `run-training` launch reobserves the
manifest-bound control and production-isolation identities. Family saturation
or any registered failure path executes the existing registered rollback before
terminal publication. Successful no-collapse training publishes its training
terminal without enabling the candidate and leaves later canary/holdout
authorization separate.

If the training owner dies after creating a lifecycle prefix but before
terminal publication, a separately invoked `terminalize-dead-owner` command may
close that prefix. While holding the sibling terminalization guard, it first
validates the exact manifest, stage authorization, approval and launch
observations, proves the recorded owner is dead, and verifies the exact lease
bytes, envelope-bound journal/resource/checkpoint prefix, and terminal absence.
Only then may it reclaim the stale-owner lease. It may then publish only the process-failure terminal and
registered rollback evidence prescribed by the control plane. Rollback restores
only the experiment-local candidate-disabled target JSON and reobserves the
bound control checkpoint/config and production identities as byte-level
bindings; it never restores a training/runtime checkpoint or loads checkpoint
bytes as a model.
The terminalizer never restores runtime state, decodes or opens the seed
inventory, imports runtime/native/model code, constructs an environment,
consumes continuation authority, or replays a seed.

### Split source-only preflight from execution

`preflight` strict-parses and canonical-compares the manifest and public control
artifacts, verifies pushed/tracked source identities, requires the output root
to be absent, prints one bounded all-false completion, and exits before opening
any output child or rollback-authority target, registration seed decoding,
runtime/native/model import, environment construction, lease acquisition,
checkpoint/config access, or output creation. It validates only the canonical
rollback-authority document/digest and the source-inventory binding copied from
the canonical r6 registration request; it does not open the inventory. An existing output root is a source-only
preflight NO-GO; preflight does not inspect or classify it.

`run-training` repeats the immutable source checks, validates full authority and
the pushed command-specific run envelope, and only then inspects bounded
lifecycle state. It accepts an absent output,
same-identity zero-debit setup reopen, or the existing one-time continuation
from a fully verified complete checkpoint. A partial chunk cannot continue or
replay. `terminalize-dead-owner` is closure rather than recovery: it may seal a
proven-dead owner's existing prefix as a process failure, but cannot make that
identity runnable again.

### Keep authorization outside this change

This change ends after reviewed pushed source and launch manifest. Current-task
watermark inspection is unavailable while the task response is active, so no
approval-time observation is inferred. A later user turn or authoritative task
inspection must provide the fresh watermark required by the existing standing
delegation validator.

## Risks / Trade-offs

- [Risk] A launcher outside the registered source could alter execution. -> Bind
  the exact runner bytes, commit, interpreter, command, and verifier bytes in a
  pushed manifest and reject every drift before runtime import.
- [Risk] Validation itself reveals seeds or loads runtime code. -> Keep preflight
  content/path checks separate and test importer/open ordering with fail-fast
  sentinels.
- [Risk] The callback-driven runtime and control accounting can diverge. -> Make
  the runner the sole adapter and test exact candidate/control debit order,
  checkpoint coordinates, resource totals, and terminal closure.
- [Risk] The inventory registration predates rollback-authority binding. -> Keep
  its bytes and digest immutable, bind the exact rollback authority in the
  pushed launch manifest, add only its hash to a process-local validated context
  view, and publish a launch marker that the independent verifier reconstructs.
- [Risk] A crash leaves a partial output. -> Preserve the lease, journal,
  checkpoint, and partial bytes; reject same-identity replay except the existing
  complete-boundary continuation, and permit only the authorized dead-owner
  terminalizer to publish a non-replay process-failure closure.
- [Risk] Runner work expands into canary/holdout. -> Limit stage to `training`
  and reject other stage requests and authorization maps.

## Migration Plan

1. Commit and push this reviewed planning boundary without authorization.
2. Add RED source-only manifest/CLI/import-order/lifecycle and dead-owner
   terminalization regressions.
3. Implement the minimal runner and standalone manifest verifier.
4. Run focused tests, compile/import probes, registered gates, strict OpenSpec,
   and tool-prohibited source review; commit and push source.
5. Render, independently review, commit, and push one r6 launch manifest and
   source-only preflight. Bind all three commands; do not create authorization,
   terminalize output, or run training.
6. Return to parent task 6.4 only after authoritative current-message watermark
   observation is available. After stage authority exists, render, review, and
   push the exact run envelope before training. A terminalization envelope may
   be rendered only after a proven dead owner requires closure.

Before any `run-training` process invocation, rollback removes only uncommitted
runner planning or preflight artifacts. After invocation, preserve all complete
or partial lifecycle evidence and do not delete, replace, retune, or retry the
identity outside its existing complete-boundary continuation.

## Open Questions

None.
