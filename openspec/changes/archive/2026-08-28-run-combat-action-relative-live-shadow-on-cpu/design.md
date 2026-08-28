## Context

Action-relative live inference currently inherits `RLAgentV2.device`. On the
production Windows environment that is CUDA. The residual selection path is a
single-row workload with several validation branches that convert CUDA tensors
to Python booleans, causing repeated synchronization. The retained r1 trace had
p50/p95 latency of `22.631ms`/`41.090ms`; a 32-warmup, 256-measurement POC on
the same checkpoint, artifact, and rows measured CPU `2.232ms`/`3.432ms` and
CUDA `12.957ms`/`16.313ms`, with no action, gate, or telemetry mismatches.

## Goals / Non-Goals

**Goals:**

- Bind CPU placement explicitly in a new live registration schema.
- Create an immutable CPU mirror for shadow-only inference without moving or
  changing the production CUDA network.
- Preserve parent state identity, artifact identity, predicted behavior, and
  the existing behavior-neutral live contract.
- Run one fresh five-game cohort under the unchanged 20ms live p95 gate.

**Non-Goals:**

- Change production-r16 device placement or action selection.
- Optimize scorer architecture, retrain, tune threshold, or change artifact.
- Relax latency, support, budget, legality, or candidate-authority conditions.
- Grant the CPU residual any action authority.

## Decisions

### Add schema-v2 explicit CPU placement

Schema v2 adds exactly `inference_device: "cpu"`. Schema v1 remains readable
and retains inherited-parent-device semantics for historical reports and tests.
New source-bound registrations must use v2 for CPU placement. An unsupported
device or schema/key combination fails before artifact loading.

Alternative: silently force every action-relative shadow to CPU. Rejected
because device placement is part of experiment identity and historical schema
v1 evidence must remain interpretable.

### Clone the loaded production parent

Initialization validates the active production checkpoint and parent state,
deep-copies the loaded parent, moves only the copy to CPU, loads the residual
artifact against that copy, and verifies the production parent hash again. The
shadow stores CPU as its tensor device; the production agent keeps CUDA.

Alternative: load the checkpoint a second time into a new agent. Rejected
because it repeats mapper/agent initialization and expands the validation
surface. Alternative: move the production parent to CPU and back. Rejected
because it can mutate live gameplay state and optimizer/device references.

### Keep trace schema stable and report registered placement

Event identity already binds registration SHA, source commit, parent, and
artifact. The readiness report will include the registration schema and
inference device; per-event schema need not change. This avoids broad trace
compatibility work while keeping placement auditable.

### Use the next commit gate as timing evidence

Focused initialization, live-shadow, summary, agent, and batch-env tests run
first. The source boundary then runs one `commit` gate with `--timing-report`,
serving both correctness validation and the queued slow-gate attribution. No
second gate is run for profiling.

## Risks / Trade-offs

- [CPU mirror accidentally mutates the production parent] -> Deep-copy before
  `.to("cpu")`; assert original device/data identity in tests and state hash
  before and after initialization.
- [CPU predictions differ materially from CUDA] -> Require `1e-5` numerical
  parity and exact action/gate/telemetry in the fixed POC and tests.
- [Game load raises CPU p95 above 20ms] -> Keep the live readiness gate
  authoritative and stop after one five-game cohort if it fails.
- [Schema-v1 reports stop loading] -> Preserve v1 exact keys and inherited
  device semantics in the loader and summarizer.

## Migration Plan

Publish the POC report, implement schema-v2 parsing and CPU clone initialization,
run focused plus one timed commit gate, and commit source. Commit one r2 live
registration, back up and temporarily append it to the production-r16 command,
run at most five games, restore the exact config, and publish readiness. Rollback
removes the v2 registration and CPU clone path; no checkpoint migration occurs.

## Open Questions

If CPU live p95 still fails while offline POC passes, a later change may add
span telemetry around tensor construction and residual selection. This change
will not alter the 20ms threshold or add candidate authority.
