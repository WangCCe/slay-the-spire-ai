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
produces a very small policy step. The r7 result should decide only whether this
frozen candidate can enter a matched live gate; it should not be used to change
the candidate or thresholds.
