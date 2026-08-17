# Stronger-TD full-step matched live gate

## Decision

Retain the promoted r8 parent. The frozen r11 candidate failed the
preregistered matched-seed gate and must not be promoted.

| Metric | Candidate | Parent |
| --- | ---: | ---: |
| Games | 20 | 20 |
| Victories | 0 | 0 |
| Total floors | 442 | 448 |
| Mean floor | 22.10 | 22.40 |
| Median floor | 20.50 | 22.00 |
| Act 2 entered | 11 | 12 |
| Act 2 boss reached | 4 | 4 |
| Act 3 entered | 0 | 0 |

Nineteen floor pairs tied. The parent won the sole non-tied pair by six
floors, so paired wins were `0-1` and the candidate's summed floor delta was
`-6`. The candidate also entered Act 2 one fewer time and failed the registered
paired-win, Act 2 entry, and total-floor conditions.

## Divergent pair

Pair 12 used seed `DCC3CE07FAEE4` (`8228335284597443162`). Both arms entered
the floor-16 Slime Boss combat with the same route, deck, relics, HP, and
potions. The first trace-visible action difference occurred on turn 4 after
both played Sever Soul: the candidate targeted Spike Slime (L) with Strike,
while the parent targeted Acid Slime (L).

By the start of turn 6, the candidate faced two additional Spike Slime (M)
enemies, while the parent still faced the original two large slimes and the
boss. After both played Ghostly Armor+, the candidate spent its remaining two
energy on Heavy Blade against Acid Slime (L) and ended with 13 block. The
parent played Strike against Acid Slime (L), then Defend, and ended with 18
block. The candidate died to Slime Boss on floor 16; the parent cleared the
boss and continued to floor 22.

This is direct evidence that the stronger one-step TD update changed target
selection and multi-turn split control in a harmful way. It does not establish
that the turn-4 target alone caused the final loss, but it is enough to reject
the candidate and to stop treating one-step SmoothL1 improvement as a
sufficient objective.

## Integrity

Both arms completed all twenty registered seeds naturally. Candidate and
parent decision traces contain 6,685 and 6,777 rows, all with source
`combat_rl`; they contain 28 and 26 simulator-divergence rows. The bytes added
to `communication_mod_errors.log` contained no new traceback, critical error,
or exception. No training, expert actions, invalid RL actions, or agent
fallbacks occurred.

Production was restored to the promoted r8 configuration with SHA-256
`f87804b2768b8ff53d0760fbfd267c5282afed21081ea888c336e0263041efcb`.

## Next experiment

Do not promote r11 and do not repeat this gate. The next candidate should not
be another increase in one-step TD weight. Reuse consumed development replay
to investigate an outcome- or sequence-aware objective that can distinguish
target choices whose immediate values look similar but whose later enemy-split
states differ. Require a general metric across supported trajectories rather
than optimizing specifically for this seed. Collect a new production-policy
holdout only after that objective has a credible offline construction.
