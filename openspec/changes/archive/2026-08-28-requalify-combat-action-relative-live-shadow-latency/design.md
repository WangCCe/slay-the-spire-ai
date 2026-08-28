## Context

The original r1 live shadow was behavior-neutral and passed every readiness
condition except p95 latency (`41.089705ms` versus `20ms`). Commit `d074bb170`
reused one parent latent per input state and passed 4,295 commit-profile tests,
but its immutable CPU preflight stopped on a `1e-6` prediction comparison. The
runtime change was rolled back in `342872934`.

A diagnostic reconstruction over the exact 32-warmup/256-measurement schedule
found six best-score comparisons outside `1e-6`, none outside `1e-5`, zero
action mismatches, and zero gate mismatches. Maximum best and candidate deltas
were `2.861023e-6` and `6.377697e-6`; the smallest threshold and ranking margins
were much larger at `0.008984` and `0.000790`.

## Goals / Non-Goals

**Goals:**

- Preserve the post-failure numeric diagnosis with no qualification authority.
- Use standard float32 `rtol=1e-5` and `atol=1e-5` prediction equivalence while
  retaining exact action, gate, abstention, legality, safety, and telemetry
  equivalence.
- Reapply the exact already-gated runtime optimization and run a new immutable
  CPU preflight with unchanged model, artifact, corpus, schedule, and speed
  gates.
- If offline gates pass, obtain one fresh five-game behavior-neutral live
  latency result under the unchanged production readiness contract.

**Non-Goals:**

- Retrain, refit, tune threshold, change artifact bytes, or change policy
  authority.
- Relax the 15ms offline p95, 2x p50 speedup, or 20ms live p95 targets.
- Reinterpret or overwrite the failed r1 benchmark and live evidence.
- Run raw full pytest or repeat the commit gate for source bytes already covered
  by the passing `d074bb170` gate.

## Decisions

### Separate numerical equivalence from behavioral equivalence

Predictions use `rtol=1e-5` and `atol=1e-5`, a conventional float32 tolerance
that remains above the complete fixed-schedule diagnostic maximum. Actions,
gate decisions, abstentions, legality, forbidden-action handling, and telemetry
must remain exact. This treats batch-shape arithmetic as numerical noise without
weakening the behavior contract.

Alternative: retain `1e-6`. Rejected because it failed solely on float32
rounding while every observed behavioral margin remained orders of magnitude
larger. Alternative: check actions only. Rejected because score drift still
needs a bounded numerical contract.

### Reuse the prior runtime gate only for byte-equivalent source

The runtime implementation SHALL match the `d074bb170` selection diff exactly.
Focused and adjacent tests cover the new tolerance and runner behavior. The
recorded `4295 passed, 26 skipped, 21 deselected` commit gate may be reused only
if the resulting runtime source diff is byte-equivalent; otherwise one new
commit gate is required. This avoids spending another 163 seconds on identical
production code while remaining fail closed for new code.

### Make formal execution immutable, not development

Implementation and test defects may be repaired before a registration is
committed. After the new CPU registration is committed, that registration is
executed once without changing source, inputs, schedule, tolerance, or speed
limits. A pass authorizes one separately committed r2 live registration; a fail
stops live execution. This preserves evidence integrity without treating normal
pre-registration development as an irreversible experiment.

### Keep live readiness unchanged

The live r2 shadow remains production-r16, epsilon zero, behavior-neutral, and
bounded to five games, 512 decisions, at least 100 eligible decisions, zero
errors, and p95 inference at most 20ms. The candidate still has no action
authority.

## Risks / Trade-offs

- [A `1e-5` score delta changes a near-tied action or threshold decision] ->
  Require exact actions and gates on every benchmark call; stop on any mismatch.
- [Offline CPU improvement does not survive CommunicationMod scheduling] ->
  Keep the unchanged five-game live p95 gate authoritative.
- [The reintroduced runtime differs from the already-gated commit] -> Verify
  byte-equivalent runtime source or run a new commit gate before registration.
- [A new registration is tuned after failure] -> Freeze all inputs and limits
  before execution and preserve any terminal result without same-registration
  retry.

## Migration Plan

Publish the diagnostic report, add tolerance regressions, reapply and verify the
runtime optimization, run focused/adjacent validation, and commit source. Commit
and execute the new CPU registration once. Only on pass, commit one r2 live
registration, temporarily append it to the backed-up production-r16 command,
complete at most five games, restore the exact config, and publish readiness.
Rollback restores repeated-state selection; no checkpoint migration is needed.

## Open Questions

If r2 passes offline but still misses only live p95, a later change must decide
whether to expose the production parent's already-computed latent or redefine
where latency is measured. This change will not relax the live threshold.
