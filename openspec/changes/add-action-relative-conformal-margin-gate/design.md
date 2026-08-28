## Context

The first action-relative residual over-intervened and lost its matched live
gate. A five-member bootstrap ensemble then reduced holdout interventions to 38
and improved aggregate selected value, but only 17 interventions cleared the
true 0.5 margin. Its worst error assigned LCB `0.670538` to a Gambler's Brew
branch whose true advantage was `-5.999053`. The ensemble sample standard
deviation therefore did not provide a calibrated lower bound.

The committed training corpus spans seeds `262000..262255`; the untouched
evaluation corpus spans `263000..263127`. Production r16 remains authoritative.
The next recipe must fit and calibrate without consulting the evaluation
partition and must not tune against either failed holdout result.

## Goals / Non-Goals

**Goals:**

- Convert raw ensemble disagreement into a finite-sample, one-sided lower
  margin using a seed-disjoint internal calibration partition.
- Preserve actual bounded model fitting while preventing calibration rows from
  entering optimizer updates.
- Treat card and potion alternatives separately because they have different
  action semantics and observed error tails.
- Reject the candidate before LightSTS when precision, coverage, value, regret,
  tail safety, legality, or provenance is insufficient.

**Non-Goals:**

- Sweeping alpha, action families, threshold, member count, seeds, architecture,
  update budget, or gate conditions.
- Regenerating the corpus or modifying LightSTS mechanics.
- Loading the candidate in CommunicationMod, starting gameplay, or promoting a
  production checkpoint.

## Decisions

### Fixed seed-level fit/calibration split

Rows from seeds `262000..262191` form the fit partition; rows from
`262192..262255` form calibration. Tensor rows and metadata are subset together,
and no calibration row enters bootstrap generation or optimizer sampling. The
existing evaluation corpus is loaded only after fitting and calibration have
completed.

Row-level random splitting was rejected because states from one simulator seed
share trajectory context. Collecting a new corpus was rejected to isolate the
calibration change from data and mechanics changes.

### One-sided conformal correction over raw ensemble LCB

The refitted ensemble retains raw score `mean - sample_std`. For each
calibration pair, nonconformity is `raw_score - true_advantage`. For each action
family, the correction is the higher finite-sample quantile at rank
`ceil((n + 1) * 0.9)`, clamped to at least zero. The policy score is raw score
minus the registered family correction.

Clamping prevents calibration from making the prior score less conservative.
A 90% target is fixed before execution. Bootstrap multiplier and threshold
sweeps were rejected because they repeat the failed recipe's post-hoc degree of
freedom.

### Card and potion calibration families

Actions `0..59` use the card correction and actions `60..89` use the potion
correction. EndTurn 90 remains forbidden. Each family must contain at least 100
calibration pairs; otherwise fitting closes without evaluation. Finer action or
encounter strata were rejected because their support is sparse and would add
many hidden tuning choices.

### Fixed untouched-holdout gate

The candidate passes only with at least 30 interventions, precision at least
0.65 for true advantage `>=0.5`, mean selected true advantage above
0.12269661575555801, mean policy regret below 3.2472479343414307, zero selected
advantages below `-0.5`, and zero illegal or forbidden selections. The value
and regret limits remain the committed single-residual baselines; the failed
ensemble is evidence for calibration design, not a new adjustable gate.

### Conditional fresh simulator gate

Only an offline pass may create one separately registered matched LightSTS run
on fresh seeds. The existing paired victory, reward, HP, terminality,
intervention, and forbidden-action conditions remain unchanged. This change
does not authorize a real-game gate.

## Risks / Trade-offs

- [Global family correction may be overly conservative] -> Preserve the fixed
  minimum intervention count and close rather than lower coverage after seeing
  the result.
- [Marginal conformal coverage does not guarantee selected-action coverage] ->
  Retain untouched holdout precision and severe-harm conditions.
- [Internal split reduces fit data by 25%] -> Keep the previous bounded update
  budget and report fit/calibration support; any larger corpus is a future
  preregistered change.
- [Simulator returns are imperfect labels] -> Keep the result development-only
  and require fresh simulator and later real-game evidence before promotion.

## Migration Plan

1. Add the conformal wrapper, split/calibration helpers, artifact contract, and
   focused RED/GREEN tests.
2. Commit source, then commit one registration binding the existing corpus,
   parent, baseline report, audit report, recipe, and output path.
3. Execute one bounded CPU fit/calibration/holdout decision.
4. Run one fresh LightSTS gate only on offline pass; otherwise publish closure.
5. Run focused validation and one commit gate, sync the spec, and archive.

Rollback is non-use of the development artifact. No production state changes.

## Open Questions

None for this recipe. Any different alpha, split, family definition, gate, or
corpus requires a new preregistration.
