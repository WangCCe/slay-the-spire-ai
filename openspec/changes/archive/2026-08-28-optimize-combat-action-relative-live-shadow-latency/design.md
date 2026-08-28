## Context

The r1 behavior-neutral production-r16 shadow produced 314 committed decisions,
164 eligible guard replacements, 31 candidate intervention intents, and zero
runtime errors. Every fixed readiness condition passed except p95 latency,
which was 41.089705ms against a 20ms ceiling. Of the 164 eligible calls, 97
exceeded 20ms, so this is a stable cost rather than one cold-start outlier.

`ActionRelativeAdvantageResidual.select_actions` currently expands one input
state into one row per allowed candidate and then calls `score_candidates`.
That public scorer recomputes embeddings and all frozen parent hidden layers for
every expanded row even though the state is identical. Only guard one-hot,
candidate one-hot, and legal mask differ between pairs.

## Goals / Non-Goals

**Goals:**

- Compute the frozen parent latent exactly once per original batch row.
- Preserve candidate predictions within `1e-6`, and preserve selected actions,
  gate decisions, abstentions, legality, and forbidden-action behavior exactly.
- Demonstrate at least 2x p50 speedup and at most 15ms p95 on a fixed Windows
  CPU benchmark using the unchanged production parent and retained artifact.
- If the offline gate passes, run one new five-game behavior-neutral shadow
  under the unchanged live readiness thresholds.

**Non-Goals:**

- Refit the scorer, change its artifact bytes, threshold, target, or corpus.
- Reuse production-network forward caches across agent APIs or change production
  parent action selection.
- Change guard behavior, action authority, rewards, routing, or noncombat policy.
- Relax the 20ms live gate, extend the five-game cohort, or retry a failed r2.

## Decisions

### Keep public single-pair scoring unchanged

`score_candidates` remains the validating public path used by fitting and
evaluation. Selection will validate the original state batch once, compute its
parent latent once, expand latent rows by candidate-pair indices, construct pair
features, and invoke the same scorer head. This minimizes blast radius and lets
tests use the existing path as an independent repeated-state reference.

Alternative considered: cache latent tensors in `RLAgentV2` during production
action selection. Rejected because that crosses network and agent APIs, risks
stale-state attribution, and is unnecessary to remove the dominant repeated
candidate cost.

### Require output parity before measuring speed

Tests and the microbenchmark compare optimized predictions against the current
expanded-state reference with `rtol=1e-6` and `atol=1e-6`; action, gate,
abstention, and telemetry counts must match exactly. Any mismatch closes the
change before live execution.

Alternative considered: accept action parity alone. Rejected because small
prediction drift near the 0.5 threshold can change future cohorts even when a
small fixture happens to select the same actions.

### Use a conservative offline preflight and an unchanged live gate

The fixed CPU microbenchmark uses the retained production-r16 parent and
unchanged action-relative artifact, 32 warmup calls, and 256 measured calls over
deterministically selected held-out corpus states. It must show p50 speedup at
least 2x, optimized p95 no more than 15ms, exact action/gate parity, and no
errors. Passing authorizes one separately committed r2 registration with the
same 512 decision, 100 eligible, and 20ms p95 live conditions.

Alternative considered: use the r1 live trace as a benchmark replay. Rejected
because it contains state hashes and action support, not the encoded tensors
required for reproducible scorer inference.

## Risks / Trade-offs

- [Batch-size-dependent floating point kernels introduce tiny score drift] ->
  Gate predictions at `1e-6` and require exact action/gate parity.
- [Synthetic or corpus CPU latency does not predict CommunicationMod load] ->
  Keep the existing live threshold authoritative and treat the microbenchmark
  only as a preflight.
- [Optimization improves p50 but scheduling tails remain above 20ms] -> Stop
  after r2 and redesign the latency contract or execution placement separately;
  do not rerun or relax thresholds.
- [Shared residual selection regresses offline evaluation] -> Run focused model,
  fit/evaluation, live-shadow, and adjacent latent-runtime tests plus one commit
  gate at the source boundary.

## Migration Plan

Implement parity tests first, refactor only selection pair scoring, run focused
and commit gates, and commit the source. Run the immutable offline microbenchmark
and publish its decision. Only on pass, commit a new r2 live registration,
temporarily append it to the production-r16 five-game command, restore the exact
prior config, publish readiness evidence, sync specs, and archive the change.
Rollback restores the previous `select_actions` pair expansion; no artifact,
checkpoint, or persistent config migration is required.

## Open Questions

If r2 still fails only on latency, should a later change reuse the production
parent's already-computed latent through an explicit network API, or revise the
20ms requirement to measure full-decision rather than scorer-only overhead?
This change does not decide that question.
