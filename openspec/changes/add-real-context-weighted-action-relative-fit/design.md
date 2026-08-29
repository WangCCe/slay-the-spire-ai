## Context

The source-bound context-support gate combines 8,313 training rows with 10,688
fresh evaluation rows and reports
`corpus_support_ready_for_separate_weighted_fit`. The training partition covers
`0.938321` of real context mass with ESS `812.325`; the augmented evaluation
partition covers `0.931034` with ESS `959.391`. Every registered legality,
provenance, seed-isolation, maximum-weight, floor-coverage, and weighted-SMD
condition passes.

The prior expanded item-semantic classifier used a fixed 4,096-update recipe
without real-context weighting. Its untouched fresh result failed decisively:
212 interventions, precision `0.339623`, mean selected advantage `-0.055328`,
regret `2.97746`, and 59 severe harms. This change tests whether distribution
alignment can repair that fixed recipe before considering a new architecture.

The base training corpus is
`af2c1d40f307eacee951333462ad5688e276f6006c8a6b0b5f5189b92845bbe2`.
Fresh evaluation is assembled in memory from base corpus
`c91532a0a5eb9ce8dc5611bdf54104f24b4567a78ad03425615dec574a6de6ce`
and formal supplement
`e63bbc303abef4a71ad545cb55481d0bdeb74429a835edfcb612139aa8b3b1df`.
The reachability POC is excluded. Real context comes only from the bound r14
and r15 replays with hashes
`eed11099d1b8d35baa8ce0ccbf87efb6fb4a864e6fe6246837b0cac91c505014`
and `67c3a49fbb2094d20793214c0a4a294684054eb6f4a24ac59573fab29c39a2dd`.

## Goals / Non-Goals

**Goals:**

- Run one deterministic CPU fit that changes only the sampling and calibration
  measure from simulator frequency to the bound real-context measure.
- Prevent states with many supported actions or ranking pairs from receiving
  extra influence solely because they generate more pairs.
- Preserve a strict fit/calibration/fresh-evaluation boundary and report raw
  safety evidence alongside weighted policy-quality evidence.
- Produce one immutable development artifact and a binary offline decision.

**Non-Goals:**

- Changing the parent, architecture, features, labels, optimizer, update count,
  loss coefficients, class boundaries, threshold quantile, or gate values.
- Loading the native LightSTS module, collecting another corpus, starting the
  game or CommunicationMod, running a sweep, or automatically retrying after
  any result is observed.
- Loading or writing the real production checkpoint, granting runtime policy
  authority, qualification, or promotion.

## Decisions

### Bind the support-passing evidence exactly

The registration binds the support-gate report, base train and evaluation
corpora, formal evaluation supplement, both real replays, simulator-only r16
parent, items export, runner source, and fixed recipe hashes. The runner
reconstructs the 10,688-row fresh partition in memory and verifies the same
support decision before fitting. It never persists a mutable replacement for
the published source corpora.

Alternative: copy the combined evaluation tensors into a new preregistration
artifact. Rejected because an in-memory deterministic append is already
verified, and another serialization would add identity drift without evidence.

### Split training by source-seed parity

Every even source seed in the 8,313-row training corpus belongs to fit; every
odd source seed belongs to calibration. The split is computed before pair
expansion. Each split independently derives exact-cell state weights against
the same complete real target. Fresh evaluation is neither loaded nor hashed
by the training process until model weights and calibration threshold are
frozen.

The preregistered audit expects 4,100 fit rows and 4,213 calibration rows. The
split audits remain descriptive rather than reusing whole-partition maximum
weight or ESS gates, because those gates were defined for the final corpus
partitions, not half-splits. Both halves must still have finite non-negative
weights, nonzero real overlap, all three classes, and ranking support.

Alternative: fit on all training rows and calibrate on half of fresh
evaluation. Rejected because it consumes part of the final evaluation and the
audited half-evaluation concentration is materially worse.

### Weight pairs without multiplying state influence

For classification, each supported candidate pair receives its source state's
normalized context weight divided by that state's supported-pair count. Pair
weights are then normalized independently inside severe, neutral, and
beneficial classes. A seeded replacement plan draws exactly 128 pairs from each
class per update. Cross entropy remains unchanged.

For ranking, each within-state beneficial-versus-nonbeneficial pair receives
the source state's context weight divided by that state's ranking-pair count.
Those weights are normalized globally and a separate seeded replacement plan
draws exactly 128 ranking pairs per update. Ranking softplus and its `0.5`
coefficient remain unchanged.

Zero-context-weight states remain in provenance and support counts but cannot
be sampled. Sampling-plan hashes, normalized-weight hashes, class mass, ranking
mass, and realized draw counts are published.

Alternative: multiply the existing losses by source-row weights after uniform
pair sampling. Rejected because states with many alternatives would remain
overrepresented and finite batches would spend work on zero-weight rows.

### Use a weighted higher calibration quantile

Each calibration candidate pair receives state weight divided by its supported
pair count. Non-beneficial pair weights are renormalized, evidence is sorted
ascending with deterministic tie handling, and the threshold is the first
evidence whose cumulative weight reaches the higher finite-sample target
`min(1, ceil((n + 1) * 0.95) / n)`, where `n` is the raw non-beneficial pair
count. With equal weights this exactly recovers the existing calibrated rank.

Alternative: preserve the unweighted threshold after weighted fitting.
Rejected because calibration would target simulator pair frequency while fit
and final evaluation target real context.

### Separate raw safety from weighted value gates

Fresh evaluation derives one context weight per source state against the same
real target. It first reuses the existing raw evaluator, then computes:

- weighted intervention precision as beneficial intervention mass divided by
  total intervention mass;
- weighted mean selected advantage as the weighted sum of selected true
  advantage, with abstention contributing zero; and
- weighted mean policy regret as the weighted sum of best-supported-with-guard
  value minus selected value.

The unchanged `0.65`, `0.18881003558635712`, and `3.1811342239379883`
thresholds apply to those weighted metrics. The minimum 30 interventions and
zero severe, illegal, or forbidden selections apply to raw counts. Both raw and
weighted metrics are published so weighting cannot hide absolute harms.

### One-result fail-closed execution

Source-only registration and focused tests precede execution. Exactly one CPU
fit may start. Pre-start validation can stop without consuming the run; after
the started receipt exists, any failure or completed offline failure closes the
recipe. There is no automatic seed, path, threshold, or parameter substitution.
A pass grants only authority to propose and register a fresh matched LightSTS
gate.

## Risks / Trade-offs

- [Risk] Importance-weighted replacement sampling increases gradient variance.
  -> Keep the same large deterministic update budget and publish realized
  sampling concentration; do not tune around the observed result.
- [Risk] Exact context cells omit deck and encounter identity. -> Treat this as
  one bounded distribution-alignment test, not proof of simulator equivalence
  or policy quality.
- [Risk] Weighted averages can hide rare severe actions. -> Preserve raw zero-
  harm, legality, and forbidden-action gates.
- [Risk] A strict one-shot result can reject a promising noisy fit. -> Seeds and
  sampling plans are deterministic; any later uncertainty study requires a new
  proposal rather than an informal retry.

## Migration Plan

1. Commit and validate this OpenSpec change.
2. Add focused regressions for split isolation, pair/ranking weights, weighted
   sampling, weighted quantile, weighted metrics, and fail-closed registration.
3. Implement the compact runner and source-only preflight, then run focused
   tests.
4. Commit the exact registration and execute the single CPU fit.
5. Publish the raw and weighted decision, run exactly one timed full commit
   gate for the cohesive source boundary, sync/archive the change, and push.

Rollback is non-use of the development artifact. Production r16, live runtime,
CommunicationMod configuration, and all source corpora remain unchanged.

## Open Questions

None. Any change to the fixed recipe, split, evidence target, calibration rule,
or gate values requires a new OpenSpec change.
