## Context

The LightSTS runner now loads r4 as an exact warm-start parent and compares its successor directly. A full TD update improves selected strata but changes greedy actions enough to regress others; linear interpolation is non-monotonic. `DQNTrainerV2` already implements masked cross-entropy against a frozen parent greedy action, including finite loss metrics and immutable anchor state.

## Goals / Non-Goals

**Goals:**

- Expose the existing trainer objective in simulator-only warm-start runs.
- Freeze the exact loaded r4 state as both held-out control and parent-action anchor.
- Report enough separate objective evidence to distinguish TD fitting from policy preservation.
- Preserve the existing zero-weight path exactly.

**Non-Goals:**

- Add or change trainer loss mathematics.
- Sweep anchor weights or introduce automatic tuning.
- Reuse development or interpolation cohorts.
- Grant production or live authority.

## Decisions

1. Add `parent_policy_anchor_weight` to `SmokeConfig` and CLI, defaulting to zero. Positive values require a warm-start checkpoint and fail before transition collection otherwise.
2. Construct `DQNTrainerV2` with the declared weight. After exact parent loading, call `set_parent_policy_anchor` with the same frozen state used for control evaluation.
3. Record total, TD, and anchor loss series summaries. A positive-weight technical run requires finite positive anchor loss evidence and exact frozen-anchor identity.
4. Use the already studied weight `1.0` for one experiment. This is a fixed use of an existing objective, not another scalar sweep.
5. Keep the same mixed battle indices and 256-update budget on new seeds so the held-out comparison answers whether direct action preservation improves the prior failure mode.

## Risks / Trade-offs

- [The anchor may suppress useful policy changes] -> Require positive held-out reward and victory evidence, not just parent agreement.
- [Cross-entropy magnitude depends on action-set size] -> Treat weight as fixed experiment configuration and report raw TD and anchor components separately.
- [The objective may still regress a battle stratum] -> Apply the same aggregate, early-combat, and material per-index guardrails before any replication.
- [Positive weight could accidentally run from random initialization] -> Reject it unless a validated simulator-only parent was loaded.

