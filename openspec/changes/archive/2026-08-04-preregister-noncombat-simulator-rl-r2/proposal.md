## Why

The first bounded simulator RL execution consumed its logical execution identity
while failing before native environment construction, registered-seed access, or
training. The Windows loadability defect is now fixed, so a successor needs a
new source-bound preregistration that makes reuse of the untouched cohort an
explicit, independently verifiable decision rather than silently copying the
terminal r1 controls.

## What Changes

- Publish a canonical cohort-reuse inventory that binds the immutable r1
  terminal evidence, proves zero environment, seed, episode, and optimizer
  effects, and distinguishes the one intentional r1 registration overlap from
  any disallowed prior empirical use.
- Publish an all-false r2 preregistration bound to pushed source commit
  `8d123fdf32bd94bc29e53a97f217a2b7ca40c4fe`, the unchanged native adapter,
  the fixed `50000..51663` train/canary/holdout partition, and the new reuse
  inventory.
- Recompute the preregistration independently, require byte-identical output,
  and verify the pushed artifacts without importing native code or Torch.
- Keep execution authorization, native loading, environment construction,
  registered-seed access, training, gameplay, CommunicationMod, qualification,
  live loading, and promotion outside this change.
- Success is a pushed canonical preregistration whose authority remains entirely
  false, whose proposed r2 output is absent, and whose cohort is supported by
  immutable zero-use predecessor evidence. If any binding or reuse claim fails,
  stop and discard only the uncommitted successor artifacts; never alter r1.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-rl-experiment`: Require a terminal predecessor and
  cohort-reuse proof before preregistering a successor over the same untouched
  cohort, while preserving a separate exact execution-authorization gate.

## Impact

The change affects only OpenSpec planning and new canonical files under
`reports/`. It does not change Python source, the native module, simulator
source, production checkpoints, CommunicationMod configuration, or live game
behavior. The preregistration can support a later exact r2 authorization, but
grants no authority by itself.
