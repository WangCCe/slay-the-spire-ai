## Why

The source-bound latent-gated candidate passed two independent replay gates, but it disagrees with production r16 on roughly 45% and 55% of evaluated decisions. A behavior-neutral live shadow is needed now to verify runtime callability, legal action selection, parent parity, and fresh-state disagreement before the candidate receives any gameplay authority.

## What Changes

- Add an opt-in RL v2 live-shadow runtime that loads the exact development adapter against the exact production parent after checkpoint initialization.
- Record one compact JSONL event per eligible greedy combat decision, including parent, correction, candidate, gate, legality, and game-context telemetry.
- Guarantee that shadow evaluation cannot replace the action selected by production r16 and is unavailable during training, epsilon exploration, or expert-mix selection.
- Fail closed on registration, source/worktree, artifact, checkpoint, metadata, parent-state, or output-path binding differences; isolate later shadow inference/write failures from production action selection while marking the shadow evidence incomplete.
- Add a bounded read-only summarizer for trace completeness and preregistered live-shadow readiness checks.

## Capabilities

### New Capabilities
- `combat-rl-latent-gated-live-shadow`: Defines exact runtime binding, behavior-neutral shadow evaluation, structured trace publication, and bounded readiness reporting for the latent-gated combat candidate.

### Modified Capabilities

None.

## Impact

- Affects RL v2 inference initialization and greedy combat action selection only when an explicit shadow registration is configured.
- Adds a small runtime module, a trace summarizer, one committed evaluation registration, and focused regression coverage.
- Success means exact parent-action parity, only legal candidate and executed actions, internally consistent traces, zero shadow exceptions, bounded adapter-inference latency, and acceptable end-to-end delay in fresh production-r16 logs.
- Non-goals are online training, candidate action takeover, checkpoint mutation, policy promotion, or gameplay-quality claims from shadow disagreement alone.
- Rollback is removing the shadow registration environment variable; production r16 checkpoint loading and emitted actions remain unchanged.
