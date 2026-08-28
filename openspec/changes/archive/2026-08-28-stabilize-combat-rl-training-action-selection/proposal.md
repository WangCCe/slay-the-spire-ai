## Why

The fresh executed-action provenance cohort proved that zero-update `--train` collection leaves the dueling online network in train mode during behavior action selection. Dropout then changes 44 of 239 directly emitted actions relative to frozen production-r16 eval-mode greedy decisions, so a replay collected only to persist transitions is not deployment-consistent even at epsilon zero.

## What Changes

- Evaluate the RL v2 online network in eval mode while selecting a greedy behavior action, then restore its exact prior mode.
- Preserve epsilon exploration, optimizer-update train mode, target-network behavior, action masks, and checkpoint state.
- Add regressions for deterministic greedy selection, prior-mode restoration, and exception-safe restoration.
- Validate with a bounded fresh zero-update production-r16 replay whose direct unmarked actions all match frozen r16 eval-mode greedy decisions.
- Do not train a candidate, change guard behavior, tune rewards, or promote a checkpoint in this change.

Success requires focused tests, the qualified commit gate, and fresh evidence showing 100% frozen-parent agreement on direct unmarked rows while nonzero legal executed-action overrides remain reconciled. The rollback boundary is the temporary mode switch around greedy action selection; reverting it restores the previous collection behavior without changing checkpoint formats.

## Capabilities

### New Capabilities

- `combat-rl-training-action-selection-parity`: require RL v2 training and replay-collection action selection to use inference semantics while preserving optimizer training mode.

### Modified Capabilities

None.

## Impact

- `spirecomm/ai/rl/v2/trainer.py`: greedy behavior action selection mode boundary.
- RL v2 trainer tests: deterministic selection and mode restoration regressions.
- Fresh replay evidence under `reports/`; no CommunicationMod protocol, guard, replay schema, or checkpoint-weight change.
