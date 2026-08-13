## Why

The 16-step card-only continuation moved parameters by L2 `1.4969` without a
single fixed-probe greedy action flip or development floor improvement. Replay
diagnostics show the current cross-fitted baseline increases card-advantage
variance and that lower-error baselines expose unstable fold gradients, so more
trajectory-level REINFORCE updates are not justified without a lower-variance
credit signal.

## What Changes

- Add a source-preserving simulator evaluator that clones one card-reward state,
  applies every legal card action, and uses native SimpleAgent for all remaining
  decisions to obtain common-random terminal returns.
- Run a bounded POC on consumed development seeds `1000..1007`, evaluating at
  most the first two card states per seed and at most 64 action branches.
- Require at least eight complete source states and at least four states with a
  nonzero return spread and one unique best action before declaring action-level
  credit viable.
- Repeat one fixed branch from the same source clone and require exact transition,
  terminal, reward, and action-sequence reproduction.
- Publish compact source/action/return evidence with all downstream authority
  false. Do not fit a model, update a policy, access fresh or protected seeds,
  launch gameplay, or change production checkpoints or CommunicationMod.

Success means the fixed viability and determinism gates pass. Failure keeps the
existing native SimpleAgent rollback and stops without expanding the seed set,
changing continuation policy, tuning thresholds, or starting training.

## Capabilities

### New Capabilities

- `noncombat-card-action-counterfactual-credit-poc`: Defines bounded card-state
  cloning, legal-action native continuations, deterministic action-return
  evidence, viability gates, and the no-training authority boundary.

### Modified Capabilities

None.

## Impact

The change adds one experiment-scoped evaluator/runner, focused tests, and a
small report under `reports/`. It reuses the bound native adapter, formal reward
contract, consumed development seeds, and production-isolation checks. It does
not alter live agent behavior, policy loading, reward semantics, Bottled labels,
training checkpoints, or protected cohort inventories.
