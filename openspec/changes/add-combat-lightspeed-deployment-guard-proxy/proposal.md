## Why

The first matched live gate for the guarded-control LightSTS candidate contradicted its large simulator uplift: the production parent often emitted raw `EndTurnAction`, then recovered through `ENERGY_GUARD` and heuristic fallback, while LightSTS evaluated that raw action directly. We need a bounded diagnostic that evaluates both frozen policies under the same explicit end-turn guard proxy before spending more real-game runs or changing training.

## What Changes

- Add an opt-in LightSTS evaluation-only deployment guard proxy that may replace a wasteful raw end-turn with a deterministic legal card action selected by immediate native reward.
- Apply the same proxy independently to control and candidate evaluations and report raw end-turn, eligibility, and replacement counts.
- Preserve the current unguarded evaluation as the default and leave transition collection, optimization, checkpoints, and production gameplay unchanged.
- Use the proxy only as simulator transfer-diagnostic evidence; it does not claim exact equivalence with `CombatRLAgent` production guards or authorize promotion.
- Success means a frozen-checkpoint counterfactual run completes deterministically and reveals whether the previously reported candidate advantage survives the proxy. Rollback is removal or disabling of the opt-in mode, which restores byte-for-byte evaluation behavior outside report schema additions.

## Capabilities

### New Capabilities

- `combat-lightspeed-deployment-guard-proxy`: Defines an evaluation-only, deterministic proxy for production wasteful-end-turn recovery and its evidence contract.

### Modified Capabilities


## Impact

- Affects the shared evaluation path in `analysis_scripts/combat_lightspeed_training_smoke.py`, the frozen-candidate comparison CLI, their focused tests, and simulator experiment reports.
- Adds no runtime dependency, native adapter change, CommunicationMod behavior, production checkpoint mutation, or live-game authority.
- Prevents further live qualification of this candidate family from relying only on bare-policy LightSTS uplift.
