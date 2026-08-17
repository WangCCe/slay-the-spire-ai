# Targeted Candidate Interpolation Matched Gate

## Decision

Retain the promoted parent. Alpha `0.9` produced a small floor advantage, but it
failed the core live EndTurn-direction requirement and therefore did not pass
the preregistered all-conditions promotion rule.

## Matched Result

Across 20 fresh matched seeds:

| Metric | Alpha 0.9 | Parent | Gate |
| --- | ---: | ---: | --- |
| Victories | 0 | 0 | pass |
| Total floors | 477 | 471 | pass |
| Mean floor | 23.85 | 23.55 | context |
| Act 2 entered | 10 | 10 | pass |
| Act 2 boss reached | 6 | 6 | pass |
| Act 3 entered | 2 | 2 | context |
| Positive-energy EndTurn share | 0.900853 | 0.869927 | fail |

The candidate won six floor pairs, the parent won five, and nine tied. The
candidate's total-floor delta was `+6`. Both arms completed all seeds in the
same order with no action failures, fallbacks, tracebacks, or post-start error
growth. Candidate runs reached floors 47 and 46, but neither arm won.

## Interpretation

The interpolation recovered some aggregate floor performance, but the offline
EndTurn reduction did not transfer to fresh live trajectories. The candidate
ended positive-energy turns more often than the parent, not less. The small
floor gain cannot override failure of the intervention's defining behavioral
condition.

Rotated debug logs retained older lines, so live action metrics were computed
only from log rows inside each arm's clean decision-trace time window. Run
outcomes and seed matching come from the 20 arm-local `.run` files. The two
evidence sources agree on arm boundaries and completion.

Do not tune another interpolation alpha from this cohort. Preserve the original
targeted candidate's first victory as a milestone, keep the promoted parent in
production, and stop the direct parent-EndTurn imitation/interpolation recipe.

## Next Direction

The useful signal is now broader than EndTurn frequency: small model changes can
produce comparable mean floors but large seed-level trajectory changes. The next
combat RL work should improve policy consistency with a better training target
or replay design, and should use fresh gameplay outcomes rather than another
post-hoc alpha adjustment.
