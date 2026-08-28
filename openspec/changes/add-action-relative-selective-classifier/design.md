## Context

The scalar action-relative residual over-intervened and lost its matched live
gate. A five-member bootstrap ensemble reduced interventions but reached only
0.447 precision. A family conformal correction then produced zero
interventions because its regression scores were too biased and noisy.

The earlier `GuardAdvantageResidual` is not a substitute: it predicts whether
any positive alternative exists at state level, then chooses an action with a
separate head. It opened on 507 of 839 holdout states and its fresh LightSTS
gate regressed 8 candidate-only victories versus 28 control-only victories.

The committed corpus has enough selective opportunity. Fit seeds contain 496
of 1,226 states with at least one supported action advantage `>=0.5`, but the
pair labels mix beneficial, neutral, and severe-harm actions. Production r16
and the actual guard action remain the immutable baseline.

## Goals / Non-Goals

**Goals:**

- Learn one score per legal card or potion alternative directly from its
  paired return class relative to the actual guard action.
- Give severe harm an explicit class rather than treating all regression
  errors or negative alternatives alike.
- Use seed-disjoint fit, calibration, and holdout partitions without selecting
  a threshold or recipe from the holdout.
- Spend the execution budget on one substantive CPU fit before any fresh
  simulator or gameplay validation.

**Non-Goals:**

- Tuning class boundaries, batch balance, loss weights, architecture, update
  count, calibration quantile, threshold, or gates after seeing the result.
- Reusing the state-level guard residual, scalar residual, ensemble, or
  conformal artifact as the candidate.
- Intervening with EndTurn or noncombat actions.
- Starting CommunicationMod gameplay, changing r16, or promoting a checkpoint
  in this change.

## Decisions

### Pair-level three-class labels

Each supported candidate branch receives exactly one label from paired return
advantage relative to the guard action:

- severe harm: advantage `< -0.5`;
- neutral: advantage `>= -0.5` and `< 0.5`;
- beneficial: advantage `>= 0.5`.

Only combat card actions `0..59` and potion actions `60..89` are supported.
EndTurn 90 is forbidden, and action-space indices `91..132` are noncombat.
Rows with no supported alternative are synchronously excluded from tensors and
metadata and reported.

Binary positive-vs-rest labels were rejected because they erase the severe
tail that caused the ensemble's worst false positives. Scalar regression was
rejected because two fitted variants already failed precision.

### Frozen-parent pair classifier

The classifier consumes frozen r16 latent state, guard one-hot, candidate
one-hot, and legal action mask. A two-layer head with hidden width 128 emits
three logits. The production parent is deep-copied, frozen, and hashed before
and after fitting.

Fit seeds are `262000..262191`. Each of 4,096 deterministic CPU updates samples
128 pairs from each class. The loss is three-class cross entropy plus `0.5`
times a within-state ranking loss that orders beneficial candidates above
neutral or severe candidates from the same source state. Adam learning rate is
`0.001`; no scheduler or early stopping is allowed.

Natural-frequency batches were rejected because neutral pairs dominate and
would make the rare class gradients incidental. Class weights were rejected in
favor of explicit deterministic sampling whose exact pair indices can be
hashed and reproduced.

### Fixed calibration threshold

Candidate evidence is
`beneficial_logit - logsumexp(neutral_logit, severe_logit)`. Calibration seeds
are `262192..262255`. The immutable selection threshold is the finite-sample
higher 95th percentile of evidence scores from all non-beneficial calibration
pairs, using rank `ceil((n + 1) * 0.95)`. No calibration row enters optimizer
or bootstrap access.

At inference, legal supported candidates are ranked by evidence and the guard
is retained unless the maximum evidence meets the calibrated threshold. This
directly controls negative-class score tails without subtracting return-unit
corrections from already biased regression output.

### Untouched holdout and conditional fresh simulator

Evaluation seeds `263000..263127` are loaded only after fitting and threshold
calibration complete. The candidate passes only with at least 30
interventions, precision at least 0.65, mean selected true advantage above
0.18881003558635712, mean regret below 3.1811342239379883, zero selected true
advantage below `-0.5`, and zero illegal or forbidden selections.

Only a complete offline pass may authorize one separately registered matched
LightSTS gate on fresh seeds. That gate requires candidate-only victories at
least control-only victories, non-negative paired reward and HP deltas, zero
nonterminal exclusions, positive interventions, and zero forbidden
interventions. This change does not authorize a real-game gate.

## Risks / Trade-offs

- [Class-balanced fitting distorts probability priors] -> Rank raw evidence and
  derive the gate only from held-out negative calibration scores; do not treat
  softmax output as a calibrated probability.
- [A global negative threshold may treat cards and potions differently] ->
  Publish family metrics but keep one threshold to avoid a post-hoc family
  degree of freedom.
- [Five percent pair false-positive control may not imply selected-action
  precision] -> Preserve the untouched holdout precision and severe-harm gates.
- [Existing paired returns inherit simulator error] -> Keep the artifact
  development-only and require fresh simulator plus later real-game evidence.
- [One fixed recipe can fail] -> Close without threshold, weight, update, seed,
  or architecture sweep.

## Migration Plan

1. Add label, classifier, selection, calibration, and artifact tests.
2. Add one source-bound runner and registration for the fixed CPU recipe.
3. Execute one fit/calibration/holdout decision and publish all evidence.
4. Run one fresh LightSTS gate only after a complete offline pass.
5. Run focused tests and exactly one final timed commit gate, sync, archive,
   commit, and push.

Rollback is non-use of the development artifact. No production state changes.

## Open Questions

None for this recipe. Any change to labels, sampling, ranking weight,
architecture, calibration quantile, or gates requires a new preregistration.
