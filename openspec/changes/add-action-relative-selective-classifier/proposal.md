## Why

The scalar action-relative residual and its bootstrap ensemble could not reach
the required intervention precision, while a family conformal correction made
the policy abstain on every holdout state. Existing labels contain enough
beneficial actions, but the training objectives do not directly distinguish a
safe beneficial candidate from neutral and severe-harm alternatives.

## What Changes

- Add a development-only pair-level classifier over the frozen r16 latent
  state, actual guard action, candidate action, and legal action mask.
- Classify each supported card or potion alternative as beneficial
  (`advantage >= 0.5`), neutral, or severe harm (`advantage < -0.5`) and add a
  fixed within-state ranking objective.
- Fit only on seeds `262000..262191`; derive one registered negative-class
  exclusion threshold only from calibration seeds `262192..262255`; leave
  evaluation seeds `263000..263127` untouched until the final offline decision.
- Require at least 30 holdout interventions, precision at least 0.65, mean
  selected true advantage above 0.18881003558635712, policy regret below
  3.1811342239379883, zero severe-harm, illegal, or forbidden selections, and
  exact artifact roundtrip.
- Run one new seed-disjoint matched LightSTS gate only if every offline
  condition passes. Do not start gameplay or alter production r16 in this
  change.

Success is a non-empty selective policy that passes all fixed holdout gates and
does not regress candidate-only victories, mean reward, or mean HP in the
conditional fresh simulator gate. Failure closes the recipe without a sweep.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-selective-classifier`: Pair-level beneficial,
  neutral, and severe-harm classification; fixed calibration; source-bound
  artifacts; and offline/fresh-simulator decisions.

### Modified Capabilities

None.

## Impact

The change adds isolated offline model and runner modules, focused tests,
OpenSpec artifacts, and reports. It reuses committed r16 shadow and corpus
bytes, adds no dependency, and does not change live routing, CommunicationMod
configuration, production checkpoints, rewards, or action spaces. Rollback is
non-use of the development artifact.
