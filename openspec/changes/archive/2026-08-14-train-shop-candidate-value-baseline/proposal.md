## Why

The viable shop counterfactual corpus contains 43 complete sources and 36
informative sources, but it does not retain full state features. A bounded
candidate-only baseline can test whether reusable shop item-value signal exists
now without misrepresenting the result as state-conditioned RL or recollecting
the fixed cohort.

## What Changes

- Convert the committed shop corpus into deterministic source-isolated fit,
  tune, and holdout partitions.
- Train one CPU candidate-value ranker from action kind, price, upgrade, slot,
  and stable identity-hash features.
- Select the epoch on train-internal tune rows and compare the frozen model
  once against Current and deterministic initialization on holdout rows.
- Publish canonical model, metrics, configuration, and manifest artifacts.
- Keep Current as rollback; a passing result authorizes only a separate fresh
  shadow-evaluation proposal.

## Capabilities

### New Capabilities
- `noncombat-shop-candidate-value-baseline`: Source-isolated candidate-only shop ranking training and one-shot holdout evaluation.

### Modified Capabilities

None.

## Impact

Adds one offline analysis runner, focused tests, one new OpenSpec capability,
and a report directory. It does not access native simulation, protected seed
inventories, gameplay, CommunicationMod, or production checkpoints, and it does
not alter policy behavior.
