# Multi-step SGD combat update r9

## Decision

Reject r9 without writing a candidate checkpoint. All three deterministic
replicate labels produced identical results, and none of the registered
interpolation alphas improved the consumed r6 development replay.

| Alpha | Relative L2 | r6 SmoothL1 | Parent agreement | Off-target disagreement |
| ---: | ---: | ---: | ---: | ---: |
| Parent | 0 | 4.143157 | 100% | 0% |
| 0.50 | 1.0321e-5 | 4.178433 | 99.2211% | 0.2978% |
| 0.75 | 1.5482e-5 | 4.197334 | 98.7204% | 0.5956% |
| 1.00 | 2.0643e-5 | 4.217055 | 98.4979% | 0.7147% |

The trust-region action constraints remained within their registered bounds,
but SmoothL1 worsened at every alpha, so the result is not eligible for r7
holdout evaluation or live gameplay.

## Diagnosis

The first two full-gradient steps were stable. From step 3 onward, raw gradient
norm increased from `7.73` to approximately `16..21`, was clipped, and TD plus
parent-anchor losses alternated. The fixed `0.0008` learning rate that was safe
for one full-gradient step is too large for this eight-step path.

r7 was not loaded or evaluated. A new fixed experiment may retain eight steps
and all thresholds while reducing learning rate to `0.0002`; it must remain
development-only until a candidate is frozen.
