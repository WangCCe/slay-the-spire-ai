## Why

The action-level counterfactual POC found nonzero formal-return spread in 11 of
15 card-reward states and a unique best action in seven, while the existing
trajectory-level continuation moved parameters without changing behavior. The
next useful step is a small real training pilot that tests whether direct action
ranking improves disjoint consumed-seed counterfactual predictions.

## What Changes

- Collect complete action-return labels from consumed train seeds `1000..1015`
  and disjoint consumed holdout seeds `1016..1023`, using at most two card states
  per seed and at most 128/64 action branches respectively.
- Permit only the pre-registered Courier restock simulator blocker to censor a
  seed, with at most two train censors and one holdout censor, no replacement,
  and minimum support of 24 train and 12 holdout source states.
- Restore the tracked r7 card-policy checkpoint as an isolated entry model and
  build a new candidate-card Adam optimizer; do not reuse trajectory optimizer
  moments across the changed objective.
- Fit 32 preregistered full-batch updates with a return-margin-weighted pairwise
  ranking loss over train states only.
- Compare entry and trained models on held-out mean top-action regret, weighted
  pairwise accuracy, unique-best top-1 accuracy, maximum regret, and greedy
  action changes.
- Pass only if train loss decreases, held-out mean regret decreases, held-out
  pairwise accuracy increases, unique-best accuracy and maximum regret do not
  regress, and at least one held-out wrong action changes to a best action.
- Keep the trained checkpoint experiment-local. Do not access fresh/protected
  seeds, launch gameplay, run OPE, qualify/promote a policy, or modify production
  checkpoints or CommunicationMod.

If data support or any held-out gate fails, stop with the original r7/native
rollback. Do not tune the objective, step count, split, seeds, or gate against
the result.

## Capabilities

### New Capabilities

- `noncombat-card-counterfactual-ranking-training-pilot`: Defines fixed
  consumed-seed train/holdout action-return collection, pairwise card-policy
  fitting, disjoint holdout gates, and experiment-only checkpoint isolation.

### Modified Capabilities

None.

## Impact

The change adds an analysis-only dataset/training module, a thin one-shot native
runner, focused tests, and bounded reports/checkpoints. It reuses the action
counterfactual evaluator, tracked r7 entry checkpoint, native adapter, formal
reward contract, and candidate card policy. Live agent behavior and production
artifacts remain unchanged.
