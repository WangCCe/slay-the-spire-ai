# Promoted-r8 replay collection r9

## Decision

Accept r9 as a complete fresh 20-game production-policy replay and reserve all
3,679 transitions for one frozen r12 confirmation. Do not fit, interpolate,
select, or change thresholds against this cohort.

## Collection outcome

All 20 registered seeds completed in order. The cohort reached 474 total
floors, averaged 23.70, entered Act 2 eleven times, reached six Act 2 bosses,
and entered Act 3 once. Its deepest run reached floor 50 and died to Awakened
One. It recorded no victory.

The checkpoint did not reach the 4,096-transition storage limit. Source and
stored transition counts are both 3,679, so the replay is complete and suitable
for full-combat-return evaluation without a missing prefix.

## Integrity

Online and target networks both equal the promoted r8 weights. Optimizer state
is empty, total and TD losses are null, and no training update occurred.
Runtime evidence contains 7,016 decision rows, all sourced from `combat_rl`,
with no expert action, invalid action, RL failure, agent fallback, traceback,
critical error, exception, or post-start CommunicationMod error growth.

The archive excludes stale `ai_debug.log.5` content from the preceding live
gate and contains exactly the five log segments spanning r9, both trace files,
and the CommunicationMod error log. Production configuration was restored and
all experiment processes were closed.

## Next step

Evaluate the frozen r12 checkpoint once on this replay using horizon 4,096,
gamma 0.99, full-return and one-step loss improvement, at least 99% parent
action agreement, at most 1% off-target disagreement, and no more than one
additional positive-energy End Turn. A failing condition ends r12 without a
live gate.
