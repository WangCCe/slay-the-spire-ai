# Multi-step low-rate SGD combat update r10

## Decision

Freeze the alpha-0.5 r10 candidate for exactly one evaluation on the fixed r7
replay tail. Do not fit, select, or tune against r7.

All three deterministic replicate labels were byte-equivalent and all three
registered alphas passed the consumed r6 development gate. The plan selected
the smallest passing alpha.

| Metric | Parent | Candidate |
| --- | ---: | ---: |
| r6 SmoothL1 | 4.143157 | 4.139495 |
| Parent action agreement | 100% | 99.9166% |
| Off-target disagreement | 0% | 0.1191% (2 states) |
| Positive-energy end turns | 1,975 | 1,974 |

The selected checkpoint moved `1.3652e-6` in relative L2 from the promoted r8
parent. Eight lower-rate full-gradient steps remained stable, with mean parent
anchor loss `0.000108`, unlike the clipped oscillation in r9.

The selected movement is only about 17% larger than the previous r8 update,
despite eight optimizer steps. This establishes that lower learning rate fixes
stability but the current parent-anchor plus smallest-passing-alpha design still
produces a very small policy step.

## Frozen r7 holdout

The one-use r7 replay-tail confirmation passed without fitting or checkpoint
writing. The replay contains the newest 4,096 of 4,194 source transitions, so
this is a truncated-tail holdout rather than complete-cohort evidence.

| Metric | Parent | Candidate |
| --- | ---: | ---: |
| r7 SmoothL1 | 3.885212 | 3.882030 |
| Parent action agreement | 100% | 99.9268% |
| Off-target disagreement | 0% | 0.0962% (2 states) |
| Positive-energy end turns | 2,063 | 2,062 |

The preregistered report conditions passed, and the additional directional
guard also passed because positive-energy end turns did not increase. The
frozen r10 candidate is eligible for a separate bounded matched-seed live gate.
The r7 holdout is now consumed and must not be reused for candidate selection,
threshold changes, or further tuning.
