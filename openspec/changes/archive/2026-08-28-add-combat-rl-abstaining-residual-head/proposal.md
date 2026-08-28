## Why

The fixed callability-filtered full-network fit improved validation SMDP TD and
changed-proposal agreement, but moved `21.67%` of direct validation decisions,
exceeding the preregistered `10%` ceiling. A frozen-parent architecture is now
needed so useful correction learning does not repeatedly destabilize accepted
r16 proposals.

## What Changes

- Add an experiment-only combat RL adapter that freezes production r16 and
  trains only a zero-initialized, low-capacity correction head.
- Make the correction head explicitly abstain: inference returns the exact
  frozen-parent proposal unless a learned gate crosses its fixed threshold.
- Bind residual tensors, gate configuration, frozen-parent identity, optimizer
  state, and deterministic evaluation telemetry in a restorable artifact.
- Require exact zero-entry parent equivalence and focused mechanism tests before
  any fresh replay collection or model fitting is registered.
- Keep the failed R1 development corpus closed to alternate fitting. A later
  training run must use a separately registered fresh cohort and must retain the
  existing direct-disagreement, changed-uplift, TD, End Turn, and integrity
  gates.

Success means the zero-entry adapter is bit-exact with r16 on legal actions,
only residual parameters receive gradients, and a deterministic synthetic
smoke demonstrates both abstention and a bounded correction without mutating
the frozen parent. This change alone grants no policy-quality or promotion
claim.

## Capabilities

### New Capabilities

- `combat-rl-abstaining-residual-head`: Defines frozen-parent correction-head
  construction, abstaining inference, serialization, mechanism validation, and
  downstream training authority.

### Modified Capabilities

- `combat-rl-provenance-aware-successor`: Replaces the failed full-network
  continuation boundary with a separately registered frozen-parent residual
  successor path while preserving the existing evidence gates.

## Impact

The change affects experiment-only combat RL network tooling, focused tests,
OpenSpec requirements, and future registration/report schemas. It does not
change `CombatRLAgent`, CommunicationMod configuration, production checkpoint
discovery, r16 bytes, combat guards, rewards, or online training defaults.
Rollback removes the adapter and its non-production artifacts; production r16
remains authoritative throughout.
