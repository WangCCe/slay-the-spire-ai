# Combat RL Update Stability Diagnosis R1

## Decision

Keep the current combat RL training defaults. Do not promote or continue the
failed schema-2 candidate, but do not attribute its ten-seed gate result to
numerical instability.

After the separate Scrap Ooze lethal-choice guard is fixed, the next training
step should be one fresh 25-game replicate from the frozen schema-2 entry
checkpoint with the existing optimizer, learning rate, dropout, and gradient
clip. This provides new replay and a genuinely independent training result
instead of repeatedly evaluating or tuning the failed candidate.

## Fixed-Replay Evidence

The final checkpoint retains the newest 4,096 of 5,223 transitions. On all
4,096 retained rows:

- Mean Smooth-L1 TD loss fell from `5.1156` at entry weights to `4.5879` at
  final weights.
- Median absolute TD error fell from `1.5597` to `1.0750`.
- Entry and final greedy action indices agreed on only `54.30%` of states.
- The replay reward mean was `-1.7285`; `309 / 4,096` rows were terminal.
- Under train-mode dropout, one forward pass changed about `10.5%` of greedy
  next actions relative to eval mode, and `47.29%` of next states changed at
  least once over 32 passes.

The loss movement is stable while the policy is sensitive. The entry policy's
median valid-action Q margin was only `0.2681`, so modest Q movement can change
many discrete actions without exploding TD error.

## Offline Ablations

Each configuration used three fixed batch schedules, 282 Adam updates, a
chronological 3,072-row training partition, and the newest 1,024 rows as a
held-out panel.

| Change | Held-out loss | Entry action agreement | Relative L2 | Result |
|---|---:|---:|---:|---|
| Current defaults | 5.2554 | 51.37% | 1.4947% | Reference |
| Deterministic bootstrap argmax | 5.2575 | 51.79% | 1.5045% | No improvement |
| Disable dropout | 5.2690 | 52.02% | 1.5642% | Worse held-out loss and drift |
| Gradient clip 5 | 5.3286 | 53.45% | 1.3985% | Worse held-out loss |
| Gradient clip 1 | 5.4273 | 68.46% | 1.0204% | All updates clipped; worse loss |
| Reset Adam, LR 1e-4 | 5.3387 | 55.21% | 1.0990% | Worse held-out loss |
| Preserve Adam, LR 3e-5 | 5.4215 | 67.71% | 0.9900% | Worse held-out loss |
| Reset Adam, LR 3e-5 | 5.4412 | 68.52% | 0.4534% | Worse held-out loss |

For the current defaults, held-out loss improved monotonically at the recorded
checkpoints: `5.67 -> 5.68 -> 5.48 -> 5.44 -> 5.39 -> 5.26` at
`0 / 8 / 32 / 64 / 128 / 282` updates. The 282-update horizon is therefore not
an offline early-stopping failure.

## Gate Uncertainty

The preregistered gate remains a valid fail: one candidate paired win, four
baseline wins, five ties, and `167` versus `181` total floors. It is not strong
causal evidence of training harm. The paired mean floor delta was `-1.4` with
sample standard deviation `8.15`; its approximate 95% interval crosses zero,
and the exact two-sided sign test over the five non-ties is `p=0.375`.

The floor-14 candidate death was independently traced to the shared heuristic
event policy repeatedly selecting Scrap Ooze's first option until HP reached
zero. That bug is outside the combat DQN and should be fixed before the next
fresh training replicate.

## Scope

This diagnosis used CPU-only offline model fitting. It did not start the game,
load CommunicationMod, modify production checkpoints, or inspect protected seed
inventories. The raw reports bind the analysis script and both input checkpoints
by SHA-256.
