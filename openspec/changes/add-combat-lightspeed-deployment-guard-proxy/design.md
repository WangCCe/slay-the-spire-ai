## Context

The LightSTS runner currently sends the network's selected legal action straight to the native simulator. Production combat instead wraps the same network in `CombatRLAgent`; notably, a raw end-turn with usable energy can be replaced by `_get_non_end_turn_fallback`. The first 10-pair live gate showed that this distinction changes several outcome-divergent decisions, so bare-policy simulator uplift is not sufficient transfer evidence.

## Goals / Non-Goals

**Goals:**

- Add a deterministic, opt-in evaluation transform for the narrow wasteful-end-turn boundary.
- Apply it symmetrically to frozen control and candidate policies.
- Emit enough telemetry to distinguish raw policy behavior from proxy-executed behavior.
- Preserve historical unguarded evaluation and all training behavior by default.

**Non-Goals:**

- Reimplement the full production `CombatRLAgent`, `OptimizedAgent`, potion logic, lethal search, or CommunicationMod protocol.
- Change replay collection, optimizer targets, model structure, or production checkpoints.
- Treat proxy results as mechanics equivalence, qualification, promotion, or live policy evidence.

## Decisions

### Use an evaluation-only mode

Add a shared `deployment_guard_proxy` evaluation configuration with `none` as the default and one registered mode, `greedy-native-reward-on-wasteful-end-turn-v1`. The training smoke and frozen-candidate comparison expose the same option, while the transform runs only inside paired held-out evaluation. Keeping collection and fitting untouched isolates the question exposed by the live gate: whether the apparent uplift survives a shared deployed-action approximation.

Alternative considered: apply the proxy during training. Rejected because that changes the policy objective before the transfer diagnosis is established.

### Replace only eligible raw end-turn actions

An action is eligible only when the raw policy selected end-turn, the current snapshot reports positive player energy, and at least one legal card-play action exists. The proxy clones the environment for each legal card action, steps it once, excludes unsupported successors, computes the existing immediate native reward, and executes the highest-scoring card action. Ties use the existing RL action index for deterministic ordering.

Alternative considered: port `_get_non_end_turn_fallback` exactly. Rejected for this iteration because the production fallback depends on richer Python game objects and heuristics that the native adapter does not expose. The simpler proxy is explicitly diagnostic and testable with current simulator APIs.

### Preserve raw and executed evidence separately

Each policy evaluation records raw end-turn, eligible, replacement, and no-supported-replacement counts. Aggregate rows sum those fields. The report binds the mode so guarded and unguarded evidence cannot be confused.

### Keep authority unchanged

The report retains false gameplay, transfer, qualification, promotion, mechanics-equivalence, and live-policy-quality authority. A counterfactual result may reject further live spending or motivate a more faithful adapter, but it cannot promote a checkpoint.

## Risks / Trade-offs

- [Immediate reward can choose a different card than production fallback] -> Name and document the proxy as non-equivalent; use it only to test sensitivity to end-turn recovery.
- [Clone stepping may reach unsupported native states] -> Exclude those candidate replacements and retain the raw end-turn when no supported card successor exists.
- [Proxy can improve both policies by different amounts] -> Apply identical rules independently and report intervention counts for each arm.
- [Schema growth affects old report assertions] -> Add fields without changing default action execution; bump the report schema and update focused tests.

## Migration Plan

1. Add configuration validation, proxy helper, and telemetry tests.
2. Confirm default `none` behavior and existing focused tests.
3. Rerun the frozen guarded-control experiment once with the registered proxy and verify the candidate parameter hash is unchanged.
4. Record whether the prior simulator uplift survives; do not resume live qualification from proxy evidence alone.

Rollback is setting the mode to `none` or reverting the isolated runner change. No production state requires migration.

## Open Questions

- If the diagnostic aligns with live outcomes, should a later change expose enough native state to reproduce the exact production fallback rather than the immediate-reward proxy?
