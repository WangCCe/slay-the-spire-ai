# Targeted Interpolation Endpoint Diagnosis

## Decision

Stop the old-replay parent-EndTurn imitation and interpolation recipe. The live
behavior reversal is not caused by alpha `0.9`; it is cross-cohort instability
in the replay-target relationship.

## Same-Cohort Result

The direct endpoint was run on the already observed 20-seed interpolation-gate
cohort for diagnosis only:

| Metric | Endpoint | Alpha 0.9 | Parent |
| --- | ---: | ---: | ---: |
| Total floors | 455 | 477 | 471 |
| Mean floor | 22.75 | 23.85 | 23.55 |
| Act 2 entered | 10 | 10 | 10 |
| Act 2 boss reached | 6 | 6 | 6 |
| Act 3 entered | 0 | 2 | 2 |
| Historical live EndTurn share | 0.903010 | 0.900853 | 0.869927 |
| Aligned live EndTurn share | 0.576102 | 0.572106 | 0.525456 |

All three arms had zero victories. The endpoint completed all games without
action failures, fallbacks, tracebacks, or post-start error growth.

## Finding

Interpolation did not introduce the live-metric reversal. Alpha `0.9` slightly
improved both EndTurn definitions relative to the endpoint and recovered 22
floors, including two Act 3 entries. Both trained variants nevertheless ended
positive-energy decisions more often than the same-cohort parent.

On the prior fresh cohort, the direct endpoint improved the aligned metric over
its parent (`0.565714 < 0.587077`). On this cohort it regressed
(`0.576102 > 0.525456`). The old replay's offline directional result therefore
does not generalize reliably to fresh parent-policy trajectories.

This third arm reused seeds after observing parent and alpha outcomes. Its floor
results are diagnostic context only and cannot promote or demote a checkpoint.

## Next Step

Do not tune another imitation weight or interpolation alpha. First collect an
immutable zero-epsilon replay under the promoted parent without optimizer
updates. Any next targeted objective must train and evaluate against that
on-policy state distribution, with the live and offline metric denominators
kept identical.
