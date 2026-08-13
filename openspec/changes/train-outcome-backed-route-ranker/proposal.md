## Why

The existing route learner imitates SimpleAgent, but the teacher-sufficiency audit proves that SimpleAgent omits current survivability and run resources and is not a policy-quality gate. The native simulator can clone a route decision and continue every legal branch to a terminal outcome, so route learning can now use direct outcome-backed action comparisons instead of teacher agreement.

## What Changes

- Add a bounded route-only collector that forces every legal map-node action at selected source states, re-decides from branched states with the frozen Current policy, and records formal terminal return for each branch.
- Train a small CPU state-conditioned route ranker on train-only counterfactual rows and evaluate it once on a disjoint development cohort.
- Compare the learned ranker with the current-policy route action and a deterministic untrained control using regret, pairwise ordering, and action-change diagnostics.
- Publish compact datasets, model identity, metrics, and a clear ready/no-go verdict from one command.
- Keep card reward, shop, event, live gameplay, production checkpoints, reserved card seeds, promotion, and formal RL out of scope.

Success requires lower development mean regret without worse maximum regret, improved weighted pairwise accuracy, and at least one corrected route decision without more worsened decisions. A failed gate stops this route model family; it does not authorize threshold tuning on the same development cohort.

## Capabilities

### New Capabilities

- `noncombat-route-counterfactual-ranking-training`: Collect outcome-backed route branches and train/evaluate one bounded route ranker.

### Modified Capabilities

None.

## Impact

- Adds a route-specific analysis runner and focused tests under `analysis_scripts/` and `tests/`.
- Reuses the exact API v3 native simulator adapter, formal reward contract, state-conditioned policy input, and Current-policy bridge without changing production gameplay behavior.
- Writes only a new report directory. Rollback is removal of the new runner, tests, OpenSpec change, and generated report; no production model or CommunicationMod configuration is modified.
