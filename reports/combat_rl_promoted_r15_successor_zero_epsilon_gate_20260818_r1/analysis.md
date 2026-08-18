# Promoted-r15 successor matched live gate

## Decision

Frozen r16 passes the preregistered 20-pair live qualification and is eligible
for a separate conservative promotion decision. The gate itself restored
production r15 and did not promote the candidate.

## Result

Candidate floors were
`[33, 33, 33, 16, 21, 31, 33, 10, 16, 30, 16, 33, 33, 16, 22, 23, 29, 16, 33, 16]`;
parent floors were
`[33, 33, 33, 16, 21, 31, 33, 10, 16, 30, 16, 33, 33, 16, 22, 23, 29, 16, 16, 16]`.
R16 won one pair, production r15 won none, and 19 pairs tied. Total floors were
493 versus 476. R16 had 13 versus 12 Act 2 entries and seven versus six Act 2
boss reaches. Neither arm entered Act 3 or won a run.

The only divergent pair was seed `88D210A767F81`. Both policies followed the
same path and made the same recorded non-combat choices through floor 16.
Production r15 died to Slime Boss after 12 turns; r16 cleared the boss after 15
turns with 22 HP and reached floor 33 before dying to Champ.

Both arms completed 20/20 games naturally with all seeds matching in order.
Neither arm used native recovery or emitted a traceback, critical error, RL
action failure, agent fallback, training action, or expert action. Production
configuration was restored after each arm and remains on r15.

## Scope

This result satisfies every fixed gate condition, but 19 of 20 pairs tied and
neither arm won a run. It supports a low-risk baseline replacement, not a large
effect or win-rate claim. Promotion must remain a separate committed decision
with the current r15 configuration retained as rollback.
