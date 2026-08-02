## Context

The structured baseline-ranker POC compared independently trained legacy and
structured models over 870 multi-candidate rows from 32 already observed train
seeds. The structured model improved route agreement in all four held-out folds
and card reward in aggregate, but worsened cross entropy in every fold and
collapsed its independent event/shop heads. Its immutable failure audit permits
at most one later train-only residual/hybrid experiment.

The new POC must therefore isolate the narrow hypothesis: structured
candidate-relative information may correct legacy route/card errors when the
legacy scorer remains the base. The existing train-only archive is the only
allowed corpus. Validation/final cohorts, the external native simulator, live
gameplay, rewards, outcomes, and production policy loading remain outside the
boundary.

## Goals / Non-Goals

**Goals:**

- Compare one frozen legacy control with one legacy-plus-residual candidate on
  identical seed-grouped held-out decisions.
- Preserve legacy event/shop outputs exactly while allowing bounded route/card
  corrections from the existing structured feature projection.
- Require separate aggregate and per-fold agreement and cross-entropy evidence
  for route and card reward, not only a pooled accuracy gain.
- Publish canonical per-fold metrics, training histories, delegation proofs,
  residual diagnostics, model identities, and deterministic replay.
- Produce a terminal implementation-fit verdict that either authorizes a
  separate fresh-study proposal or stops this baseline-imitation sequence.

**Non-Goals:**

- No new or reused validation/final seed, native module load, simulator rollout,
  floor/victory measurement, DAgger, reward optimization, formal RL, live game,
  qualification, promotion, or checkpoint discovery.
- No replacement event/shop head, teacher fallback, candidate filtering,
  architecture search, threshold adjustment, or post-result retry.
- No claim that SimpleAgent is optimal or that a passing candidate has policy
  quality outside the already observed train corpus.

## Decisions

### 1. Bind existing evidence rather than derive another corpus

The registration will hash-bind the existing canonical train-only gzip and
manifest, the completed structured POC manifest, its failure audit, the exact
implementation source files, runtime, seeds `4000..4031`, and all POC values.
The runner will load the train input through the existing fail-closed validator
and reject any non-train cohort field or identity mismatch.

Reusing the canonical train input avoids a second extraction path. The previous
structured result is bound only as rationale and lineage; its predictions and
metrics cannot enter fitting, feature construction, thresholds, or selection.

### 2. Share one trained legacy base between control and candidate

For each of four sorted round-robin seed folds, train
`legacy-hash-mlp-multichoice-v1` once on the other 24 seeds with the registered
legacy schedule. Freeze that exact model. The control evaluates its logits
directly, and the candidate uses the same logits as its base. This removes
initialization and optimizer noise from the paired comparison and makes exact
event/shop delegation provable.

After a passing cross-validation gate only, fit one all-train legacy base and
one all-train residual for a selected implementation artifact. There are eight
fold fits in the normal path and at most ten fits in the selected path.

### 3. Add one zero-initialized bounded route/card residual

The sole candidate is
`legacy-plus-structured-route-card-residual-v1`. For route and card-reward
rows, it computes:

`candidate_logit = frozen_legacy_logit + tanh(residual_raw_logit)`

The residual has separate route and card-reward heads, each a fixed
`2048 -> 32 -> 1` ReLU MLP over the existing
`noncombat-structured-policy-features-v1` projection. The final linear layer is
initialized to exact zero, so the candidate starts at the base policy, and the
`tanh` multiplier fixes every correction to `[-1, 1]`. Only residual parameters
receive gradients. They are trained for 20 deterministic Adam epochs at
`0.001`, category-balanced across route/card, on multi-candidate fit rows.

For event and shop, the candidate returns the same base score tensor without
calling a residual head. The evaluator records hexadecimal logits and
probabilities and requires exact equality of candidate ids, logits,
probabilities, selected action, and target probability with the control.

An unconstrained replacement head was rejected because it already produced
majority collapse. A learned mixture gate was rejected because it adds another
selection surface. A hand-selected action fallback was rejected because it can
hide poor probability calibration and does not test a coherent ranker.

### 4. Use paired seed-grouped evaluation with materialized fold evidence

The same deterministic four folds and complete multi-candidate rows are used.
Singleton rows remain schema/coverage diagnostics only. Each canonical model
result contains base and residual training histories and hashes; each canonical
prediction contains fold, candidates, selected action, correctness, cross
entropy, target probability, and full score/probability hex arrays.

`metrics.json` materializes aggregate and per-fold metrics for both policies,
paired deltas for every category, delegation checks, and per-fold residual
maximum/mean/RMS magnitude. Consumers must not need to reconstruct a required
gate from predictions. The manifest closes the exact managed inventory, and a
primary execution plus one replay must be canonically identical.

### 5. Freeze a terminal gate before real fitting

Selection requires all structural, identity, finite-value, bound, inventory,
and replay checks plus:

- event and shop delegation exact on every held-out row;
- overall agreement delta at least `+0.03` and macro agreement delta at least
  `+0.02`;
- aggregate route agreement delta at least `+0.05` and card-reward agreement
  delta at least `+0.01`;
- aggregate route and card-reward cross-entropy deltas at most `-0.01` each;
- in every fold, route and card-reward agreement deltas at least `0.0`, their
  cross-entropy deltas at most `0.0`, macro agreement delta at least `0.0`, and
  overall cross-entropy delta at most `0.0`; and
- every observed residual magnitude within the registered `1.0` bound.

A valid threshold miss yields
`poc_valid_without_route_card_residual` and no selected model. Contract,
resource, identity, or replay failure yields `blocked`. A pass yields
`route_card_residual_selected`, but authorizes only a separately reviewed fresh
simulator-study proposal. No alternate residual width, scale, schedule, loss,
fold split, or retry is allowed after execution.

## Risks / Trade-offs

- **The same observed corpus has already informed the hypothesis** -> Treat the
  result only as terminal implementation fit and require entirely fresh cohorts
  for policy-quality evidence.
- **A one-logit correction may be too weak** -> Prefer a clean negative over
  expanding architecture after observation; the fixed bound protects the base.
- **Route/card folds are small** -> Require non-regression in every fold and
  positive separate aggregate margins rather than accepting a pooled gain.
- **Exact delegation can be broken by duplicate evaluation paths** -> Share the
  same base tensors and publish hexadecimal score/probability equality proofs.
- **Canonical model histories increase artifact size** -> Keep only ten bounded
  fits and compact deterministic JSON; timing stays in a noncanonical journal.

## Migration Plan

1. Implement registration, shared-base residual model, paired evaluation,
   terminal gate, and artifact contracts against synthetic fixtures.
2. Run focused tests, compilation, the repository commit gate, and strict
   OpenSpec validation before binding the implementation commit.
3. Check in and push one registration that binds the existing input and
   motivating evidence, then execute exactly one primary run plus one replay.
4. Perform a read-only identity, leakage, metric, delegation, residual-bound,
   replay, authority, and inventory audit.
5. Publish the verdict, update project direction, sync/archive the change, and
   stop baseline-imitation trials if the gate does not pass.

Rollback deletes only this POC's code, tests, registration, reports, and spec
artifacts. It does not alter prior evidence, live configuration, checkpoints,
production agent code, or the simulator checkout.

## Open Questions

None. The candidate, folds, schedule, limits, thresholds, and no-retry rule are
fixed by this design before fitting on the registered corpus.
