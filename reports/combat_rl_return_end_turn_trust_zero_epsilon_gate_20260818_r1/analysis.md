# Full-return End Turn trust matched live gate

## Decision

Retain promoted r8. Frozen r13 is a valid offline-improving and behavior-safe
candidate, but it produced no observable live outcome difference in this gate.
It is not promoted and this seed pool must not be rerun or tuned against.

## Result

Both arms completed all 20 shared seeds with clean runtime evidence. The floor
vectors were identical:

`[22, 16, 10, 33, 28, 30, 16, 33, 16, 16, 16, 16, 33, 30, 16, 16, 14, 33, 21, 24]`

Each arm reached 439 total floors, entered Act 2 ten times, reached an Act 2
boss four times, and recorded zero Act 3 entries and zero victories. Candidate
paired wins were zero, parent paired wins were zero, and all 20 pairs tied.

Candidate and parent runtime archives contain 6,438 and 6,440 decision rows,
respectively, all from `combat_rl`; each has 21 sim-divergence rows and zero
traceback, critical, or nonzero RL failure markers. Neither arm required a
native recovery.

## Qualification

All non-regression conditions pass, but the candidate does not have more paired
floor wins than the parent and no floor pair is non-tied. The preregistered
all-tie rule therefore returns
`retain_promoted_r8_r13_has_no_observable_live_benefit`.

## Next step

Do not repeat this gate or weaken the End Turn trust term. The `alpha=0.5`
candidate was behaviorally safe but too small to affect outcomes. Use consumed
r7 for fitting and r6/r8/r9/r10 for development to test a larger effective
full-return step under the same direct margin-preservation constraint. Freeze a
new candidate only if all four replay cohorts retain loss improvement and the
existing action guards.
