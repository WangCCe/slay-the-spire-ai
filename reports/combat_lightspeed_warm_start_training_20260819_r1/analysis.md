# R4 warm-start LightSTS training decision

## Decision

Retain the r4 simulator parent. The run is technically complete, but the full-step successor is not replication-eligible and has no live-transfer authority.

## Training result

- Replay transitions: `17,210`
- Optimizer updates: `256/256`
- Parameter L2 delta: `1.5244839280`
- Reachable held-out profiles: `217/256`
- Unsupported or truncated held-out profiles: `0`
- Candidate-only victories: `5`
- Parent-only victories: `2`
- Mean reward delta: `+0.4702616360`
- Mean player HP delta: `-0.0276497696`

## Battle-index attribution

| Battle index | Reachable profiles | Reward delta | HP delta | Candidate-only wins | Parent-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 64 | -0.3598 | -0.5781 | 0 | 0 |
| 3 | 61 | -0.2552 | -0.4754 | 0 | 0 |
| 6 | 51 | +3.6213 | +1.3137 | 4 | 0 |
| 9 | 41 | -1.0742 | -0.1707 | 1 | 2 |

The aggregate reward and victory count improved because of the large battle-index 6 gain. The candidate nevertheless fails the aggregate HP guardrail, the battle-index 0 HP guardrail, and the preregistered material index-regression threshold at battle index 9.

## Next step

Do not retrain or tune on this cohort. Treat the parent-to-candidate parameter direction as a development candidate and test preregistered smaller interpolation steps on a fresh simulator cohort. This is intended to determine whether the index 6 gain survives while early- and later-battle regressions contract. No interpolation result can authorize production loading or live promotion.

