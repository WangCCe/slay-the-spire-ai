# Combat RL zero-epsilon entry control

## Decision

Pause additional combat RL training. The 25-game update did not pass the matched greedy improvement gate.

## Result

The frozen entry checkpoint and post-training checkpoint were evaluated on the same ordered 10 seeds with `epsilon=0`, conservative routing, ascension 0, and the same fixed non-combat policy and safety layer.

| Metric | Entry checkpoint | Post-training checkpoint | Post minus entry |
| --- | ---: | ---: | ---: |
| Victories | 0 | 0 | 0 |
| Total floor | 234 | 224 | -10 |
| Mean floor | 23.4 | 22.4 | -1.0 |
| Median floor | 22.0 | 16.0 | -6.0 |
| Act 1 boss reaches | 10 | 9 | -1 |
| Act 2 entries | 5 | 4 | -1 |

Paired outcomes favored the entry checkpoint on 4 seeds, the post-training checkpoint on 2, and tied on 4. The paired floor differences, post minus entry, were `[-13, 0, -2, 0, 2, 0, 17, 0, -12, -2]`.

The large opposite-signed changes show policy-update instability across seeds. This cohort is sufficient to reject an unqualified continuation, but not to claim a statistically significant regression.

## Next step

Use frozen checkpoints and the existing training artifacts for an offline learner diagnostic. Inspect replay composition, update count, target-network synchronization, reward scale, and Q-value/action drift. Do not start another live training batch until that analysis identifies a bounded corrective hypothesis and a cheaper promotion gate.
