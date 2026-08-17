# Stronger-TD full-step combat update r11

## Decision

Freeze the r11 candidate for exactly one confirmation on the untouched r8
replay. Do not fit, select, or tune against r8.

| Metric | Parent | Candidate |
| --- | ---: | ---: |
| r6 SmoothL1 | 4.143157 | 4.116015 |
| Parent action agreement | 100% | 99.3880% |
| Off-target disagreement | 0% | 0.4765% (8 states) |
| Positive-energy end turns | 1,975 | 1,961 |
| Relative L2 from parent | 0 | 0.000009748 |

The candidate passes every preregistered development condition. Its parameter
movement is about 7.1 times the rejected r10 candidate, remains well below the
`0.0005` upper bound, and changes enough actions to avoid repeating the known
`1e-6` no-effect regime. All three deterministic replicate labels produced the
same training and validation metrics.

The stronger TD ratio reduced r6 SmoothL1 by `0.027143` without clipping or
oscillation: gradient norm fell from `4.22` on the first step to `0.70` on the
eighth. No interpolation sweep was performed; alpha `1.0` was fixed before
training.

The complete 3,318-transition r8 replay has not been loaded. It remains a
one-use confirmation set and has no fitting or threshold-selection authority.
