# Full-combat-return SGD candidate r12

## Decision

Reject the frozen `alpha=0.5` candidate after its single fresh production-
policy replay confirmation. It improved both registered loss metrics, but
failed both behavioral guards. It has no live-evaluation or promotion
authority; production remains on r8.

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

## Fresh r9 confirmation

The untouched 20-game r9 production replay contains 3,679 transitions. The
candidate improved full-combat-return SmoothL1 from `48.7806473` to
`48.7507782` and one-step SmoothL1 from `4.2415285` to `4.2200193`. Parent
action agreement was `99.3748%`, above the registered `99%` minimum.

The candidate nevertheless exceeded the off-target disagreement ceiling:
`22` states, or `1.0848%`, versus a `1%` maximum. More importantly,
positive-energy End Turn decisions increased from `1,699` to `1,707`, versus
an allowed increase of at most one. The terminal decision is therefore
`not_eligible_for_live_gate`.

A read-only action diff located only 23 changed greedy decisions. Nine changed
from a parent card or potion action to End Turn while energy remained positive,
and one changed away from a positive-energy parent End Turn, exactly explaining
the net increase of eight. Eleven of the 23 changes moved to End Turn overall.
This is a narrow decision-boundary failure rather than broad policy drift.

## Next step

Do not retry r9, shrink `alpha`, or tune a threshold after reading this cohort.
Use r7 for fitting and the now-consumed r6, r8, and r9 replays for development.
The next candidate should retain the full-combat-return objective but add a
direct trust constraint that preserves the parent's positive-energy non-End
action margin over End Turn. Require cross-cohort loss improvement and the
same action guards before collecting another fresh production replay.
