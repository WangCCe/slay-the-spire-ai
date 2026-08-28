## Context

The frozen-parent action-relative residual used one scalar scorer and a fixed
0.5 return-unit intervention threshold. On its untouched 839-state evaluation
corpus it intervened 162 times with 0.383 precision, mean selected true
advantage 0.122697, and mean policy regret 3.247248. It passed a fresh LightSTS
gate but lost the subsequent matched live gate, including confident Defend
choices that were worse than the guard action. A read-only threshold curve
showed better precision at higher thresholds, but choosing one after observing
the failed cohort would be post-hoc tuning.

The existing train and evaluation corpora are seed-disjoint and source-bound.
The evaluation corpus must remain untouched by fitting, model selection, and
threshold selection. The production r16 parent remains authoritative.

## Goals / Non-Goals

**Goals:**

- Fit a materially different action-relative candidate that exposes epistemic
  disagreement across deterministic bootstrap members.
- Use a fixed lower-confidence score for both action ranking and abstention.
- Reject weak candidates on untouched holdout evidence before native simulator
  evaluation.
- Preserve exact source, parent, corpus, bootstrap, and member provenance.
- Perform actual bounded CPU training while keeping the development artifact
  isolated from production.

**Non-Goals:**

- Tuning the confidence multiplier, threshold, member count, architecture, or
  training budget after observing holdout or fresh-gate results.
- Adding the ensemble to CommunicationMod or production agent loading.
- Starting gameplay, promoting a checkpoint, or changing r16.
- Regenerating the corpus or changing LightSTS mechanics in this change.

## Decisions

### Five deterministic pair-level bootstrap members

Each member uses the same frozen parent and scorer architecture but a distinct
registered initialization seed and a deterministic with-replacement bootstrap
of the expanded action-relative training pairs. Pair-level bootstrap directly
matches the supervised objective and produces auditable index hashes.

Using only different initializations on the same full dataset was rejected
because it tends to understate epistemic uncertainty. A new three-way corpus
was also rejected for this iteration because the existing evaluation partition
already provides an untouched holdout and new data collection would mix model
design with simulator/corpus changes.

### Shared parent with independent scorer heads

The ensemble stores one frozen parent network and five independent scorer
heads. This avoids five copies of the parent and keeps prediction behavior
close to the existing action-relative implementation. The artifact stores only
member scorer states plus the parent identity.

### Fixed lower-confidence score

For every legal supported alternative, the ensemble computes member prediction
mean and unbiased sample standard deviation. The policy score is
`mean - 1.0 * standard_deviation`; it selects the maximum score and intervenes
only when that score is at least 0.5. Member count, confidence multiplier, and
threshold are fixed before holdout access and are not swept.

### Untouched holdout decision

The existing evaluation corpus is loaded only after fitting all member heads.
It passes only when all provenance and safety checks pass, intervention count
is at least 30, intervention precision is at least 0.65, mean selected true
advantage exceeds 0.12269661575555801, and mean policy regret is below
3.2472479343414307. These last two values are the committed prior single-model
holdout baselines. Failure closes the recipe.

### Conditional fresh LightSTS gate

If and only if the offline decision passes, one separately registered matched
LightSTS gate uses a new seed interval and the existing deployment-consistent
guard proxy. Its conditions remain candidate-only victories at least control,
non-negative paired reward and HP deltas, no excluded nonterminal profiles, at
least one intervention, and no forbidden intervention. Failure closes the
recipe without retraining or changing the gate.

## Risks / Trade-offs

- [Bootstrap disagreement may still be poorly calibrated] -> Require both
  holdout precision and coverage, then an independent fresh simulator gate.
- [Pair-level sampling can overrepresent states with many alternatives] ->
  Preserve the existing pair-level supervised objective and report per-state
  selection metrics; revisit only in a future preregistered recipe.
- [Five heads increase latency] -> Measure holdout and simulator inference
  latency; do not add live loading in this change.
- [The holdout has already been inspected for the prior model] -> Freeze all
  ensemble hyperparameters and pass conditions in committed artifacts before
  running the fit; prohibit sweeps and retries.
- [Offline success may not transfer to the game] -> Keep r16 authoritative and
  require a later separately registered real-game gate before any promotion.

## Migration Plan

1. Add the isolated ensemble model, artifact contract, fit/evaluation runners,
   and focused tests.
2. Commit a source-bound fit registration before one bounded CPU execution.
3. If offline conditions pass, commit a fresh LightSTS registration and execute
   it once; otherwise publish closure evidence.
4. Sync and archive this change after evidence and tests are complete.

Rollback is deletion or non-use of the development artifact. No production
state or configuration is migrated.

## Open Questions

None for this registered recipe. Any alternative confidence multiplier,
bootstrap unit, corpus, or architecture requires a new change and new evidence.
