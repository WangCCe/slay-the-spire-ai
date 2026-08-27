# Deployment-Consistent Enum Identity Ablation

## Verdict

Retain production r16. Collision-free encounter identity is a positive representation direction, but this experiment is ineligible for fresh confirmation because two registered technical criteria and one parent policy criterion failed.

## Technical Evidence

Both arms completed with `technical_smoke_ready`, 50,043 source transitions, 66,740 prepared replay rows, and 256 optimizer updates. Behavior telemetry, corpus reward metrics, and parent evaluation rows matched. The generated manifests verified successfully.

The registered source-transition identity hashes did not match because those hashes include the encoded observation and the enum arm adds encounter columns. This makes the registered cross-representation equality criterion unsuitable, but it cannot be relaxed after outcome access. The enum migration also produced a maximum Q delta of `7.63e-6`, above the registered `1e-6` limit despite zero action mismatches and zero-valued inserted columns.

## Enum Versus Control

Across 843 matched terminal profiles, enum-v1 improved reward by `+0.4075`, HP by `+0.2764`, and enum-only versus control-only victories were `5:3`. Reward deltas by battle index were `+0.0148`, `+0.1557`, `+0.7104`, and `+1.1350` for indices 0, 3, 6, and 9. Every registered enum-versus-control policy criterion passed.

## Enum Versus Parent

Enum-v1 improved reward by `+0.2791` and HP by `+0.2147` against r16, with all battle-index reward deltas positive. Enum-only versus parent-only victories were `11:12`, so the immutable victory criterion failed.

## Decision

Do not tune or repeat this cohort, package either simulator-only checkpoint, or start gameplay. The evidence supports encounter identity as a useful late-battle representation, but the next experiment must be structurally new: preserve exact parent computation and carry per-row guard-replacement provenance before combining representation learning with a proxy-aware conservative objective.
