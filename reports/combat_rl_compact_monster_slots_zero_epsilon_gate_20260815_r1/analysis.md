# Combat RL compact monster-slot zero-epsilon gate R1

## Decision

**Promote the compact monster-slot candidate as the current combat RL v2 checkpoint. Keep the frozen entry checkpoint as the rollback target.**

## Matched result

| Metric | Candidate | Baseline |
| --- | ---: | ---: |
| Victories | 0 | 0 |
| Total floors | 410 | 349 |
| Mean floor | 20.50 | 17.45 |
| Median floor | 16 | 16 |
| Act 2 entries | 8 | 3 |
| Act 2 boss reaches | 3 | 1 |
| Act 3 entries | 0 | 0 |

Across 20 exact seed pairs, the candidate won seven, the baseline won two, and 11 tied. Mean paired floor delta was `+3.05`; the two-sided exact sign-test p-value was `0.1797`.

The candidate passed every preregistered promotion condition. The result is directional rather than conclusive at conventional significance, and neither arm reached Act 3 or won, so this is an incremental checkpoint promotion rather than completion of the gameplay objective.

## Integrity

All 20 seed pairs matched by `seed_played` and order. Both arms ran at epsilon zero with training and expert mix disabled. Candidate and baseline CommunicationMod error growth was limited to expected launch output. The original configuration was restored after the gate and all processes were closed.

## Promotion

The installed CommunicationMod configuration now explicitly binds the promoted checkpoint. This is necessary because eval-mode model creation does not auto-load the latest checkpoint when `--model` is absent. The previous config hash and frozen entry checkpoint remain recorded as rollback targets.
