# Single-step SGD trust region r7

## Decision

**Eligible for fresh replay confirmation only.** The selected checkpoint is not
eligible for live evaluation or production use until it passes an untouched r4
parent replay cohort.

## Result

All three deterministic replicate labels produced identical metrics. The
promoted parent r3 one-step SmoothL1 was `4.122797`; all registered trust-region
scales improved it while remaining inside the policy-drift limits:

| alpha | SmoothL1 | parent agreement | off-target disagreement | relative L2 |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 4.116972 | 0.999018 | 0.002061 | 0.0000014983 |
| 0.50 | 4.111227 | 0.998773 | 0.002576 | 0.0000029966 |
| 1.00 | 4.099967 | 0.996810 | 0.006698 | 0.0000059932 |

The preregistered selection rule chose the smallest passing alpha, `0.25`.
The final seed 404 fit reproduced the same result and wrote:

- checkpoint SHA-256: `0e92acec8928e0b467f1440e2cbe0f15b6b940d095e29aae26e82b76ff5a7a46`
- size: `2,272,526` bytes

## Interpretation

The aligned first-order TD signal generalizes from r1+r2 to r3 when followed by
one unpreconditioned SGD step. The earlier Adam failures were optimizer-path
failures, not evidence that the replay cohorts demanded conflicting updates.

The improvement is intentionally small and the r3 cohort is consumed. The next
step is to collect a new deterministic 20-game r4 parent-policy replay cohort,
then compare this frozen candidate with the parent on that untouched replay.
Do not change the candidate, threshold, seed list, or production configuration
in response to r4.
