# Targeted Parent-EndTurn Imitation Matched Gate

## Decision

Retain the promoted parent. The targeted candidate produced the project's first
recorded real Ironclad victory, but it did not pass the full matched promotion
rule.

## Milestone

Candidate run `1786927917.run` reached floor 51 with `victory=true`. On the same
seed the parent reached floor 50 and died to Donu and Deca. This is valid fresh
epsilon-zero gameplay evidence and completes the long-term first-victory
milestone independently of the promotion decision.

## Matched Result

Across 20 fresh matched seeds:

| Metric | Candidate | Parent | Gate |
| --- | ---: | ---: | --- |
| Victories | 1 | 0 | pass |
| Total floors | 476 | 488 | fail |
| Mean floor | 23.8 | 24.4 | context |
| Act 2 entered | 11 | 12 | fail |
| Act 2 boss reached | 7 | 6 | pass |
| Act 3 entered | 1 | 1 | context |
| Positive-energy EndTurn share | 0.884806 | 0.894096 | pass |

Candidate won 3 floor pairs, parent won 5, and 12 tied. Candidate's total-floor
delta was `-12`. Both arms completed all seeds in identical order with no action
failures, fallbacks, tracebacks, or post-start error growth.

## Interpretation

The targeted objective transferred in the intended local direction and enabled a
real win, but it did not improve consistency across the cohort. The eight non-tied
pairs are concentrated enough for a read-only divergence audit: candidate gains
were `+1`, `+17`, and `+12`, while losses were `-8`, `-5`, `-15`, `-11`, and `-3`.

Do not resume training or tune the objective from aggregate results alone. First
compare the decision traces for those eight pairs and identify whether the five
losses share an actionable combat pattern distinct from the three gains.
