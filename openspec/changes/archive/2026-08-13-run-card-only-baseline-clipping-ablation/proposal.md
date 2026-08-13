## Why

The 16-step card-only continuation moved parameters coherently but produced no
final fixed-probe action flips and a non-monotonic function response. Existing
r7 evidence shows that 133 of 566 card baseline predictions hit the lower clip,
but r1 did not persist enough per-step evidence to determine whether clipping is
materially changing the optimizer direction.

## What Changes

- Add a one-step, two-branch mechanism ablation from exact r1 checkpoint `004`.
- Collect one 64-seed candidate-only consumed-development cohort and reuse its
  stored states, candidates, selections, rewards, and returns for both branches.
- Keep branch A on the current clipped held-out baseline and change branch B only
  to the corresponding unclipped held-out predictions.
- Persist advantage, objective, gradient, parameter, and fixed-probe
  function-space telemetry for both branches.
- Require branch A to reproduce the existing checkpoint `005` candidate model
  exactly before interpreting branch B.
- Stop after one optimizer step. Do not access fresh/protected cohorts, run
  gameplay, load production checkpoints, promote a policy, or claim policy
  quality.

Success means the experiment isolates baseline clipping and reports whether it
materially changes the one-step update and policy function. Failure of support,
ownership, reproduction, source binding, or isolation rolls back to checkpoint
`004` and produces no continuation proposal.

## Capabilities

### New Capabilities

- `noncombat-card-only-baseline-clipping-ablation`: Defines the shared-trajectory
  one-step ablation, exact reproduction gate, telemetry, and authority boundary.

### Modified Capabilities

None.

## Impact

The change adds an experiment-scoped runtime/runner, focused tests, one local
checkpoint pair, and compact reports. It reuses the existing card-only policy,
candidate rollout, cross-fitted baseline, optimizer, fixed probe, and consumed
development schedule. CommunicationMod, game processes, native SimpleAgent
rollback behavior, protected cohorts, and production checkpoint discovery are
unchanged.
