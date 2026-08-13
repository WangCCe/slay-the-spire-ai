## Why

The nested seed-grouped development POC passed every fixed gate with four
corrected actions and no worsened actions, but all evidence came from exposed
seeds `1000..1023`. One untouched consumed audit is required before spending
fresh seeds on evaluation.

## What Changes

- Fix the residual configuration to `shrinkage=3` and `strength=128`, the unique
  mode of the four outer-fold selections.
- Fit one uplift model from all bound exposed rows before audit access.
- Collect at most 64 action branches from audit seeds `1024..1031`, allowing at
  most one registered Courier censor and requiring at least 12 complete states.
- Compare frozen r7 entry and residual predictions on the identical audit rows
  using fixed regret, pairwise, unique-best, and correction gates.
- Persist the audit dataset, experiment-only uplift model, predictions, metrics,
  and terminal verdict; never tune or refit after audit access.

## Capabilities

### New Capabilities

- `noncombat-card-counterfactual-uplift-residual-audit`: Defines fixed exposed
  fitting, one-shot consumed audit collection, read-only paired evaluation,
  experiment isolation, and the fresh-evaluation proposal gate.

### Modified Capabilities

None.

## Impact

- Adds one staged audit runner and focused tests.
- Loads the already-bound native simulator only to collect audit branches; it
  does not start the game or CommunicationMod and does not load production
  checkpoints.
- Success authorizes only a fresh-evaluation proposal. Failure discards the
  experiment model and retains r7/native policy as rollback.
