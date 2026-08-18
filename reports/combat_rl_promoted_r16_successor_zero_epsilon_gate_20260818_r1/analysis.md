# Promoted-r16 successor matched live gate

## Decision

Frozen r17 fails the preregistered 20-pair live qualification. Retain production
r16. Do not promote r17 and do not rerun or tune against this cohort.

## Result

Candidate floors were
`[16, 16, 16, 16, 29, 31, 33, 16, 21, 16, 16, 16, 33, 33, 33, 16, 41, 19, 33, 33]`;
parent floors were
`[16, 33, 16, 16, 29, 31, 33, 16, 21, 16, 16, 16, 33, 33, 33, 16, 33, 19, 33, 33]`.
Each arm won one pair and 18 pairs tied. Total floors were 483 versus 492.
R17 had 11 versus 12 Act 2 entries, seven versus eight Act 2 boss reaches,
and one versus zero Act 3 entries. Neither arm won a run.

The two divergent pairs followed matching route prefixes. On pair 2, r17 died
to Slime Boss at floor 16 while r16 cleared it and reached floor 33. On pair
17, r17 cleared Collector and reached floor 41 while r16 died to Collector at
floor 33. These opposite outcomes leave paired wins tied and do not offset the
registered Act 2 and total-floor regressions.

Both arms completed 20/20 games naturally with all seeds matching in order.
Neither arm used native recovery or emitted a traceback, critical error, RL
action failure, agent fallback, training action, or expert action. Production
configuration was restored after each arm and remains on r16.

## Scope

The gate rejects this candidate even though it produced the cohort's only Act 3
entry. A later experiment may consume r13 for a new bounded fit, but r17 and
this live cohort are closed and cannot be rerun or used to adjust the fixed
gate thresholds.
