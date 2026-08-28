## Why

The five-member bootstrap ensemble reduced holdout interventions from 162 to
38 and improved mean selected advantage and policy regret, but precision was
only 0.447 and one supposedly positive lower-confidence score hid a true
`-5.999` Gambler's Brew decision. Bootstrap disagreement therefore is not a
calibrated safety margin, and changing its multiplier after this result would
be post-hoc tuning.

## What Changes

- Deterministically split the existing training partition by seed into fit
  seeds `262000..262191` and calibration seeds `262192..262255`; keep the
  existing evaluation seeds `263000..263127` untouched until the final offline
  decision.
- Refit the fixed five-member bootstrap ensemble only on fit rows.
- Compute a fixed 90% one-sided finite-sample conformal correction from
  calibration residuals separately for card and potion alternatives. Clamp
  corrections at zero so calibration cannot make a score less conservative.
- Rank and gate alternatives by the calibrated lower margin with the unchanged
  0.5 return-unit intervention threshold.
- Require at least 30 holdout interventions, precision at least 0.65, mean
  selected true advantage above 0.12269661575555801, policy regret below
  3.2472479343414307, zero selected advantages below `-0.5`, and zero illegal
  or forbidden selections.
- Permit one new seed-disjoint matched LightSTS gate only if every offline
  condition passes; otherwise close without retry or sweep.
- If a registered fit attempt terminates before holdout evaluation because of
  a deterministic runner-contract defect, preserve that failure evidence and
  permit one replacement source snapshot and registration. The replacement
  SHALL keep the recipe, inputs, seed partitions, alpha, threshold, and gates
  unchanged and SHALL NOT rerun the failed registration.
- Do not start CommunicationMod gameplay, alter r16, load the candidate in
  production, or promote a checkpoint in this change.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-conformal-margin-gate`: Seed-disjoint internal
  calibration, action-family conformal lower margins, source-bound artifacts,
  and fixed offline/fresh-simulator decisions.

### Modified Capabilities

None.

## Impact

The change adds an isolated conformal wrapper and bounded CPU fit/evaluation
runner around the existing development-only ensemble. It reuses the committed
r16 parent and existing corpus bytes, adds no dependency, and does not touch
production configuration. Failure leaves the parent and prior artifacts
unchanged and closes only this recipe.
