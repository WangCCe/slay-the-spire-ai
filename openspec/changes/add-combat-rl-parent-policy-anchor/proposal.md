## Why

Two independent fresh matched gates rejected RL v2 continuations from the promoted combat parent even though both successors improved replay TD metrics. The Guardian continuation lost `3-7-10`, and the broad continuation lost `1-8-11` with a two-sided sign-test p-value of `0.0390625`, showing that unanchored TD updates are forgetting live-useful parent behavior.

## What Changes

- Add an optional frozen-parent policy anchor for RL v2 training continuations.
- When enabled, load the starting checkpoint's online policy into a non-trainable anchor network and add a masked policy-distillation loss to the existing TD loss.
- Expose the anchor weight through the main CLI and training batch wrapper, reject invalid or unsupported combinations, and record the active setting in checkpoint metadata and logs.
- Keep the default weight at zero so existing training and evaluation behavior is unchanged.
- Validate with focused unit tests, the existing full test gate, and a bounded training smoke before any fresh matched promotion gate.

Success requires a finite anchored checkpoint that improves replay TD fit while preserving materially more parent greedy actions than the rejected unanchored broad successor. Live policy quality still requires a separate fresh matched zero-epsilon gate.

Non-goals are automatic weight tuning, changing reward shaping or replay sampling, supporting RL v1, altering evaluation behavior, or promoting a checkpoint from offline evidence alone.

Rollback is immediate: omit the option or set its weight to `0.0`; no production checkpoint or CommunicationMod configuration is changed by this capability.

## Capabilities

### New Capabilities
- `combat-rl-parent-policy-anchor`: Optional frozen-parent policy preservation during RL v2 continuation training.

### Modified Capabilities

None.

## Impact

Affected surfaces are `main.py`, `scripts/run_training_batch.py`, RL v2 agent/trainer construction and checkpoint metadata, and focused RL v2/training-runner tests. The change adds no dependency and remains compatible with the Windows CommunicationMod production path.
