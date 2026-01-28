# Change: Restore full training state from checkpoints

## Why
Training currently reloads only network weights, so epsilon/optimizer/step counters reset after restarts.
Restoring the full trainer state keeps exploration and optimization consistent across long runs.

## What Changes
- Load trainer checkpoints when training mode is enabled.
- Restore epsilon, optimizer state, and step counters from the checkpoint.
- Fall back to weight-only loading if a full checkpoint is unavailable.

## Impact
- Affected specs: training-checkpoint-restore (new)
- Affected code: `spirecomm/ai/rl/agent.py`
