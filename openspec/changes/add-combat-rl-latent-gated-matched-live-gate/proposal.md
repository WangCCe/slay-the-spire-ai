## Why

The r3 live shadow proved that the latent-gated adapter is callable against
production r16 with exact parent parity, legal actions, zero runtime errors,
and 20.31 ms p95 adapter latency across 300 decisions. It also disagreed with
the parent on 45.67% of decisions, so replay and shadow evidence can no longer
answer whether those corrections improve real gameplay.

## What Changes

- Add an explicit eval-only latent-gated candidate runtime that loads production
  r16 as the frozen parent and applies the registered candidate action only when
  its gate is open, before the existing outer safety guards.
- Require a committed, source-bound candidate-mode registration with immutable
  artifact, parent, trace, decision-budget, and policy-precondition bindings.
- Record parent proposal, candidate selection, final guarded action, legality,
  parity, takeover, latency, and runtime-error evidence without training.
- Preregister and run one fresh ten-pair candidate-versus-r16 Ironclad A0 gate
  with epsilon zero, expert mix disabled, identical seed order, and production
  configuration restored between arms and after completion.
- Qualify only if the candidate wins more floor pairs than r16, at least one
  pair differs, total floors and progression counts are non-worse, victories
  are non-worse, both arms complete, and runtime/identity checks all pass.
- Keep promotion separate. A tie, any failed criterion, or invalid evidence
  retains production r16.

## Capabilities

### New Capabilities

- `combat-rl-latent-gated-matched-live-gate`: Eval-only candidate takeover,
  source-bound matched gameplay execution, evidence reconciliation, and a
  preregistered qualification decision.

### Modified Capabilities

None.

## Impact

This affects RL v2 eval routing, the latent-gated live registration/runtime,
the batch wrapper, focused tests, and new tracked registration/report files.
It does not alter training, the candidate artifact, the production r16
checkpoint, non-combat policy, or existing outer guards. Rollback removes the
candidate registration environment variable and restores the byte-identical
production configuration; r16 remains authoritative throughout the gate.
