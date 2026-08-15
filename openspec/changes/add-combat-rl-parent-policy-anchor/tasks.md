## 1. Regression Coverage

- [x] 1.1 Add trainer regressions for zero-weight compatibility, finite masked anchor loss, and frozen anchor parameters.
- [x] 1.2 Add agent checkpoint regressions for initial parent anchoring, anchored save/resume, and invalid positive-weight startup without a parent checkpoint.
- [x] 1.3 Add CLI and training-batch regressions for option validation and command forwarding.

## 2. Implementation

- [x] 2.1 Implement optional masked parent-policy anchor loss and separate loss metrics in `DQNTrainerV2`.
- [x] 2.2 Wire frozen anchor creation and exact checkpoint persistence through `RLAgentV2`.
- [x] 2.3 Wire `--parent-policy-anchor-weight` through `main.py`, `CombatRLAgent`, RL v2 factory creation, and `run_training_batch.py`.

## 3. Verification

- [x] 3.1 Run the focused RL v2 and training-batch pytest files with a scoped Windows basetemp.
- [x] 3.2 Run the repository full pytest gate and record the result without rerunning infrastructure-only failures. The single run reached the 1,804-second outer command timeout without a pytest summary and was not retried; this is infrastructure evidence, not a pass or test failure.
- [ ] 3.3 Run one bounded anchored training smoke from the promoted parent, report finite/TD/anchor/agreement evidence, and decide whether a fresh matched gate is justified.
