## Context

The current collector samples legal non-EndTurn actions uniformly and trains one-step TD from those trajectories. This produces broad data, but the live candidate failure and guard-aware counterfactual show that the deployed policy's guarded EndTurn boundary dominates outcomes. Penalty-based attempts to constrain the learned policy did not transfer on fresh seeds.

## Goals / Non-Goals

**Goals:**

- Collect replay from the same frozen raw parent plus explicit guard proxy used in evaluation.
- Retain bounded deterministic exploration for action coverage.
- Store the action actually executed after guard transformation.
- Support complete-trajectory return targets without changing default collection.

**Non-Goals:**

- Claim exact equivalence with production fallback.
- Train online during collection or mutate the frozen parent.
- Add another anchor/margin loss, native adapter API, or production behavior.
- Tune exploration after fresh outcomes.

## Decisions

### Registered behavior modes

Keep `uniform-non-end-turn-v1` as the default. Add `frozen-parent-guarded-epsilon-v1`, which requires a warm-start parent and `greedy-native-reward-on-wasteful-end-turn-v1` proxy. At each decision below the action-per-turn cap, one deterministic RNG draw selects exploration with probability epsilon; exploration uses the existing legal non-EndTurn selector, while the parent branch selects the frozen network action and applies the proxy. The action-per-turn safety bound always forces EndTurn without proxy replacement.

### Store executed actions

Replay action indices, rewards, and successors bind the post-proxy action. This aligns the target with the actual simulator transition. The frozen parent is loaded before collection and receives no optimizer updates until collection finishes.

### First experiment uses complete discounted returns

Use epsilon `0.10`, fresh train seeds `144000..145023`, evaluation seeds `146000..146255`, and complete discounted returns with `0.99` discount. Full returns avoid bootstrapping from the bare parent on guarded transitions. Retain parent cross-entropy weight `1.0` as the sole conservative objective.

## Risks / Trade-offs

- [Proxy differs from production fallback] -> Keep authority simulator-only and require later live evidence only after strong fresh simulator gates.
- [Narrow behavior coverage] -> Reserve 10% exploration and report exact branch/action counts.
- [Parent anchor conflicts with guarded executed cards] -> Treat the fresh outcome gate as decisive and avoid post-outcome tuning.
- [Longer collection due to clones] -> Use one bounded registered arm and no duplicate control training.

## Migration Plan

Add selector regressions and telemetry, run focused tests, then one fresh experiment. Disable by restoring the default behavior mode.

## Open Questions

- If the fresh gate passes, whether to compare 5% and 10% exploration only on separately registered cohorts.
