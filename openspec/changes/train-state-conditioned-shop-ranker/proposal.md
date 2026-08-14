## Why

The first shop baseline improved holdout mean regret but failed its pairwise
stability gate because the committed corpus omitted full state features. A
fresh state-conditioned experiment is the smallest honest test of whether deck,
gold, relic, potion, and floor context resolves that limitation.

## What Changes

- Extend the shop collector with opt-in state/candidate feature capture while
  preserving its existing default artifact contract.
- Collect disjoint fresh train and development shop sources from fixed A0 seeds.
- Select one state-conditioned ranker using only train-internal fit/tune rows,
  then evaluate the frozen model once on development.
- Publish canonical datasets, model, metrics, configuration, and manifest.
- Keep Current as rollback; success authorizes only a separate fresh shadow
  proposal and failure is terminal for this cohort and configuration.

## Capabilities

### New Capabilities
- `noncombat-state-conditioned-shop-ranking`: Fresh source-isolated shop counterfactual collection, state-conditioned training, and one-shot development evaluation.

### Modified Capabilities

None.

## Impact

Touches the offline shop collector, adds one training runner and focused tests,
and writes one report directory. It loads the registered native simulator on
CPU but does not launch gameplay or CommunicationMod, access production
checkpoints or protected seed inventories, or change live policy behavior.
