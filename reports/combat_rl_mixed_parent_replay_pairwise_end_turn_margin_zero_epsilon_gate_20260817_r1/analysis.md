# Mixed-Replay Pairwise Margin Matched Gate

## Decision

Retain the promoted parent. The mixed-replay candidate reduced the targeted
positive-energy raw-RL EndTurn behavior, but it regressed both paired outcomes
and aggregate progression. Four preregistered conditions failed, so the strict
all-conditions rule rejects promotion.

## Matched Result

Across 20 fresh matched seeds:

| Metric | Mixed candidate | Parent | Gate |
| --- | ---: | ---: | --- |
| Victories | 0 | 0 | pass |
| Total floors | 427 | 483 | fail |
| Mean floor | 21.35 | 24.15 | context |
| Median floor | 17.5 | 25 | context |
| Paired floor wins | 2 | 7 | fail |
| Act 2 entered | 10 | 12 | fail |
| Act 2 boss reached | 2 | 5 | fail |
| Act 3 entered | 0 | 0 | pass |
| EndTurn share among positive-energy raw RL decisions | 0.511409 | 0.561518 | pass |

Eleven seed pairs tied. The candidate won two pairs by `+13` and `+8` floors,
while the parent won seven pairs and finished `56` aggregate floors ahead.
The candidate also lost two Act 2 entries and three Act 2 boss reaches. This is
a broad progression regression, not a single outlier hiding an otherwise
positive matched result.

## Behavioral Result

The candidate reduced positive-energy raw-RL EndTurn decisions from
`858 / 1528` (`56.15%`) to `762 / 1490` (`51.14%`). The older EndTurn-only
denominator also moved in the intended direction (`87.69%` versus `88.64%`).
The intervention therefore transferred to fresh live trajectories, but that
behavioral change did not improve policy quality.

Both arms completed all 20 registered seeds in the same order. Neither arm
produced an invalid or failed RL action, agent fallback, traceback, critical
error, or post-start CommunicationMod error growth. Production configuration
was restored to SHA-256
`7e923bba944c411512f5f8322a8494bc30f7edda47be0e3f404c5b25edde22b2`,
and all experiment/game processes were closed.

Rotated debug logs contained historical rows, so raw-action metrics were
computed only inside each arm's clean decision-trace time window. Run outcomes
and seed matching came from the 20 arm-local `.run` files.

## Interpretation

Combining a second independent replay cohort improved the offline imitation
metrics but did not make the intervention live-safe. Parent agreement, smooth
L1 anchoring, and a lower positive-energy EndTurn share are insufficient
surrogates for progression on their own.

Do not tune another pairwise-imitation weight on either consumed holdout or
live cohort. The next training experiment should add an outcome-constrained
signal, such as conservative TD learning on the mixed replay, while retaining
the parent anchor and treating pairwise EndTurn imitation as a secondary term.
It must use a fresh offline partition and may reach live evaluation only after
showing that the outcome signal improves without erasing parent agreement.
