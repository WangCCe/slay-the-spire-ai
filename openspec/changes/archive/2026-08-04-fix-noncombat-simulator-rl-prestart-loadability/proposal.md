## Why

The only authorized bounded non-combat simulator RL execution stopped before
constructing an environment because PyTorch loaded Conda's old MinGW runtime
before the registered CLion-built adapter. The current runner nevertheless
wrote a started journal and consumed the logical execution, conflating a
repeatable startup compatibility check with empirical experiment execution.

## What Changes

- Load and validate the registered native adapter before any operation that
  imports or initializes PyTorch.
- For a fresh execution, initialize the pristine CPU training runtime before
  creating the output directory or started journal. A failure in this phase
  leaves output absent and does not start an experiment attempt.
- For a resume, perform native loading before Torch-state restoration and keep
  pre-rollout load or restore failures non-mutating so the same logical attempt
  retains its last complete journal and checkpoint.
- Preserve the existing one-shot, no-retry, checkpoint, cohort, wall-time,
  canary, holdout, and terminal-publication rules after the started journal is
  written.
- Add regressions for native-before-Torch ordering, absent-output startup
  failure, repeatable pre-start validation, unchanged resume evidence, and
  terminal publication after an actual rollout failure.
- Preserve the archived `noncombat-simulator-rl-20260804-r1` result and all
  historical artifacts byte-for-byte. This change does not authorize a
  successor registration, seed use, training, live use, qualification,
  loading, or promotion.

Success means the focused runner tests prove the corrected boundary, the
archived r1 artifact verifier still passes, and strict OpenSpec plus repository
test gates pass. There is no fresh gameplay requirement because this runner is
offline-only and cannot be discovered by Communication Mod.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-rl-experiment`: Move native/Torch compatibility and
  pristine runtime initialization before the experiment-start boundary while
  retaining fail-closed one-shot semantics after empirical execution starts.

## Impact

- Expected code changes are limited to the experiment module's policy-model
  import boundary, `scripts/run_noncombat_simulator_rl_experiment.py`, and
  focused source-only tests.
- The Windows runtime remains `D:/anaconda/envs/stsai/python.exe`; no package,
  native module, external simulator source, Communication Mod configuration,
  gameplay policy, model, reward, cohort, threshold, or production checkpoint
  changes.
- The read-only root-cause report is
  `reports/noncombat_simulator_rl_native_loadability_audit_20260804.md`.
- Rollback restores the prior runner ordering and removes only this change's
  tests and planning artifacts. It never rewrites the archived r1 evidence.
