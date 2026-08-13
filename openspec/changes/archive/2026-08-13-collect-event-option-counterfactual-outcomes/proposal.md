## Why

Reachable event semantics are structurally closed, but existing trajectories record outcomes only for the selected event option. Before spending time on an event policy model, the project needs direct evidence that forcing alternative legal options produces stable, learnable terminal-return differences.

## What Changes

- Add a bounded event-only collector over fresh simulator seeds.
- At each multi-option event source, force every legal option from an immutable clone and continue with the frozen Current policy to terminal.
- Record event identity, option semantics, formal returns, censor reasons, and deterministic branch replays.
- Report signal viability from complete source count, informative return spreads, unique-best actions, event coverage, and replay identity.
- Keep model fitting, development/audit cohorts, gameplay, CommunicationMod, production checkpoints, policy loading, and promotion out of scope.

The POC passes only if it produces at least 64 complete event sources, at least 32 informative sources, at least 8 distinct events, and exact replay for the first 16 source branches. Failure is actionable evidence about event support or signal; implementation defects may be fixed and rerun because no model selection or held-out gate is involved.

## Capabilities

### New Capabilities

- `noncombat-event-option-counterfactual-outcomes`: Collect and validate action-level terminal outcomes for simulator event options.

### Modified Capabilities

None.

## Impact

- Adds one analysis runner, focused tests, and a compact report directory.
- Reuses the API v3 native adapter, reachable event semantics resolver, Current-policy bridge, formal reward, and current-continuation logic.
- Rollback removes only the new runner, tests, change, and report. Production gameplay behavior remains unchanged.
