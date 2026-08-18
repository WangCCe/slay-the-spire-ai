## Why

The first r4 warm-start successor improved held-out reward and victories through a strong battle-index 6 gain, but failed HP and index-specific regression guardrails. A fixed conservative interpolation screen can determine whether a smaller step along that learned parameter direction retains useful gain without spending another training cohort or tuning the trainer.

## What Changes

- Add a source-bound utility that linearly interpolates compatible simulator-only combat checkpoints at explicitly declared alpha values.
- Preserve simulator-only authority and bind parent, candidate, alpha, input hashes, and output parameter hashes in each generated checkpoint and manifest.
- Reject production-compatible, hash-mismatched, structurally incompatible, or non-floating checkpoint pairs before writing outputs.
- Evaluate fixed alpha candidates with the existing frozen LightSTS comparator on one fresh development cohort.
- If and only if a fixed candidate passes aggregate and per-index guardrails, confirm that single alpha on a second fresh cohort.
- Success means a confirmed smaller step that improves reward without HP, victory, or material battle-index regressions. Rollback is deletion of generated simulator-only candidates while retaining r4.

## Capabilities

### New Capabilities

- `combat-lightspeed-checkpoint-interpolation`: Construct immutable simulator-only checkpoints at preregistered linear steps between two compatible frozen candidates.

### Modified Capabilities

None.

## Impact

- new analysis utility and focused tests
- generated simulator-only interpolation checkpoints and frozen comparison reports
- no fitting, game process, CommunicationMod, production checkpoint, or production configuration changes
