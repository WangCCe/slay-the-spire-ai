## Why

The action-relative residual passed one fresh matched LightSTS gate by a small
margin, but simulator evidence cannot establish that its post-guard state and
action assumptions hold in the real CommunicationMod pipeline. The scorer must
first demonstrate behavior-neutral callability on actual production-r16 states
before any candidate takeover is considered.

## What Changes

- Add an explicit, source-bound live shadow registration for the frozen
  action-relative artifact and production r16 parent.
- Defer candidate scoring until the existing execution callback reveals the
  final guard-processed action, while retaining the exact state encoding and
  legal-action mask from the parent proposal.
- Evaluate only real `parent EndTurn -> executed non-EndTurn` guard-replacement
  opportunities, exclude action 90 before maximization, and never replace the
  executed production action.
- Publish bounded schema-versioned JSONL telemetry for support, candidate and
  guard identities, predicted advantage, intervention intent, legality,
  EndTurn safety, execution parity, latency, provenance, and runtime errors.
- Add a read-only summary that requires at least 100 eligible events within a
  maximum 512 committed decisions, zero behavior changes, zero errors, zero
  illegal or forbidden candidates, and p95 inference latency no more than 20ms.
- Run at most one registered five-game production-r16 shadow batch and use its
  trace only to decide whether a separately registered matched live gate is
  justified.

Success means the fixed batch reaches every readiness condition without the
candidate receiving action authority. Non-goals are fitting, tuning, changing
r16 or outer guards, changing CommunicationMod protocol behavior, letting the
candidate execute, claiming gameplay improvement, or promoting a checkpoint.
Rollback removes the shadow environment option, runtime, summarizer, tests, and
reports and restores the previous production-r16 command unchanged.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-live-shadow`: Source-bound, deferred post-guard
  live observation and readiness reporting for the action-relative residual.

### Modified Capabilities

None.

## Impact

The change affects the RL v2 agent's behavior-neutral shadow hook,
`scripts/run_training_batch.py` environment wiring, a new runtime and summary
script, focused tests, OpenSpec artifacts, one tracked registration, and bounded
live reports. It may start Slay the Spire through the existing Windows
CommunicationMod command, but production r16 remains the sole action policy and
no training or checkpoint writing occurs.
