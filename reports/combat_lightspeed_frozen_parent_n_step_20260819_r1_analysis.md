# Frozen-Parent N-Step LightSTS Result

## Decision

Retain the simulator-only r4 parent. Neither n=3 nor n=5 satisfies every
preregistered eligibility condition, so this experiment authorizes no fresh
confirmation, live transfer, qualification, or promotion.

## Technical Result

All three arms completed with `technical_smoke_ready`. They used the same 66,610
source transitions, 80,448 prepared replay rows, 3,392 complete profiles, two
excluded decision-bound profiles, no unsupported states, identical parent
control rows, and 256 optimizer updates. The n-step bootstrap parent hash exactly
matched r4.

| Arm | Reward vs r4 | HP vs r4 | Arm-only wins | r4-only wins |
|---|---:|---:|---:|---:|
| one-step | +0.456 | +0.660 | 11 | 8 |
| n=3 | +0.613 | +0.917 | 12 | 11 |
| n=5 | +0.272 | +0.537 | 11 | 14 |

## Direct Matched Result

| Candidate vs one-step | Reward | HP | Candidate-only wins | One-step-only wins | Battle 0 reward | Battles 6+9 reward |
|---|---:|---:|---:|---:|---:|---:|
| n=3 | +0.157 | +0.257 | 6 | 8 | -0.082 | -0.042 |
| n=5 | -0.185 | -0.124 | 3 | 9 | -0.031 | -0.629 |

n=3 improves aggregate reward and HP but regresses the strict early-combat
guardrail, loses the matched victory comparison, and gives back the benefit at
battle index 9 (`-0.960` reward). n=5 is worse than one-step in aggregate and
later battles. Another horizon must not be tuned on this cohort.

## Verification

- OpenSpec strict validation passed.
- Focused tests: `34 passed, 5 skipped`; native focused tests: `39 passed`.
- Full pytest ran once in 44m52s: `6349 passed, 28 skipped, 230 failed`.
  Failures were outside the changed LightSTS runner/test module and concentrated
  in stale noncombat evidence bindings, Windows qualification fixtures, and an
  existing Reaper fixture. The full suite was not rerun.

## Next Direction

Do not mechanically produce n=7 or another near-neighbor target candidate. The
next combat-training proposal should create a more substantive source of signal,
such as state/reward representation work motivated by the repeated late-battle
weakness, and screen it in LightSTS before returning to the game.
