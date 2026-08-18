# Promoted-r16 successor r18 matched live gate

## Decision

Frozen r18 fails the preregistered 20-pair live qualification. Retain production
r16. Do not promote r18 and do not rerun or tune against this cohort.

## Result

Candidate floors were
`[33, 50, 28, 16, 16, 16, 16, 33, 33, 25, 25, 31, 16, 16, 33, 16, 23, 27, 33, 30]`;
parent floors were
`[33, 50, 28, 16, 16, 16, 16, 33, 33, 25, 25, 31, 16, 16, 33, 16, 23, 33, 33, 30]`.
R18 won no pair, r16 won one, and 19 pairs tied. Total floors were 516 versus
522. Both arms entered Act 2 13 times and Act 3 once, but r18 reached the Act 2
boss six times versus seven. Neither arm won a run.

The sole divergent pair shared its first 23 route entries. R18 initially took
less Hexaghost damage, 34 over six turns versus 61 over nine, but later took 51
damage over nine turns against Cultist and Chosen versus r16's 24 over six.
The routes then diverged; r18 died at floor 27 to Shelled Parasite and Fungi,
while r16 reached Collector at floor 33.

Both arms completed 20/20 games naturally with all seeds matching in order.
Neither arm used native recovery or emitted a traceback, critical error, RL
action failure, agent fallback, training action, or expert action. Production
configuration was restored after completion and remains on r16.

## Scope

The gate rejects r18 on paired wins, Act 2 boss reaches, and total floors. R14
is consumed and may be used for a new bounded fit, but r18 and this live cohort
are closed and cannot be rerun or used to adjust the fixed thresholds.
