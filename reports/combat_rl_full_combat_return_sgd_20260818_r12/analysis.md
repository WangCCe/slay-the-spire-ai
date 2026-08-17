# Full-combat-return SGD candidate r12

## Decision

Freeze interpolation `alpha=0.5` for one fresh production-policy replay
confirmation. This is an offline candidate only and has no live-evaluation or
promotion authority.

The construction keeps r11's optimizer, eight full-dataset SGD steps,
learning rate, TD weight, and parent anchor. The only substantive change is the
target: rewards are discounted through the rest of each recorded combat rather
than bootstrapping after one action.

## Cross-cohort result

| Development replay | Parent full-return loss | Candidate | Parent one-step loss | Candidate | Agreement | Off-target |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.5518 | 46.5204 | 4.1432 | 4.1217 | 99.5828% | 0.6552% |
| r8 | 50.6912 | 50.6614 | 4.3358 | 4.3164 | 99.7890% | 0.3494% |

Positive-energy End Turn count stayed at 1,975 on r6 and changed from 1,643
to 1,644 on r8. Relative parameter movement is `7.4170e-6`: larger than the
r10 step that produced twenty live ties, but smaller than both the raw
full-return update and the rejected r11 step.

## Selection

The exploratory interpolation sweep was development-only. `alpha=1.0`
improved both losses but exceeded the fixed 1% off-target limit on both
cohorts and added six positive-energy End Turns on r8. Smaller steps through
0.5 passed the loss and action guards. The largest passing value, 0.5, was
therefore refit as the frozen candidate.

The r11 Slime Boss pair remains a diagnostic, not a training row. This
candidate was selected from general replay metrics and was not fitted to that
single seed.

## Next step

Collect a new 20-game, zero-epsilon, zero-update replay under the promoted r8
parent. Evaluate this frozen checkpoint once on that replay using both full-
combat-return and one-step metrics, with the same action guards. Do not change
the model or thresholds after reading the fresh cohort.
