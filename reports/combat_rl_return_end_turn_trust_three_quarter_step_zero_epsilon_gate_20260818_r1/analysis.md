# Three-quarter-step End Turn trust matched live gate

## Decision

Frozen r15 passes the preregistered 20-pair live qualification and is eligible
for a separate conservative promotion decision. The gate itself restored
production r8 and did not promote the candidate.

## Result

Candidate floors were
`[16, 16, 33, 50, 19, 33, 16, 28, 8, 33, 33, 16, 33, 20, 33, 16, 16, 16, 27, 16]`;
parent floors were
`[16, 16, 33, 50, 16, 33, 16, 28, 8, 33, 33, 16, 33, 20, 33, 16, 16, 16, 27, 16]`.
R15 won one pair, production r8 won none, and 19 pairs tied. Total floors were
478 versus 475. R15 had 11 versus 10 Act 2 entries; both arms had seven Act 2
boss reaches, one Act 3 entry, and no victories.

The only divergent pair was seed `13063F556CF16`. Both policies followed the
same path through floor 16. Production r8 died to The Guardian at floor 16;
r15 cleared the boss and reached floor 19 before dying to Masked Bandits.

Both arms completed 20/20 games naturally with all seeds matching in order.
Neither arm used native recovery or emitted a traceback, critical error, RL
action failure, agent fallback, training action, or expert action. Production
configuration was restored after each arm and remains on r8.

## Scope

This result satisfies every fixed gate condition, but 19 of 20 pairs tied and
neither arm won a run. It supports a low-risk baseline replacement, not a large
effect or win-rate claim. Promotion must remain a separate committed decision
with the current r8 configuration retained as rollback.
