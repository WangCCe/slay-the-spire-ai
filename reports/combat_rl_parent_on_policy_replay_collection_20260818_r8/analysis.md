# Promoted-r8 replay collection r8

## Decision

Accept r8 as a complete 20-game production-policy replay and reserve all 3,318
transitions for one frozen-candidate confirmation. Do not fit, select, or tune
against this cohort before the candidate is frozen.

## Collection outcome

All 20 registered seeds completed in order. The cohort reached 424 total
floors, averaged 21.20, entered Act 2 nine times, reached three Act 2 bosses,
and entered Act 3 once. It recorded no victory.

Unlike r7, this checkpoint did not reach the 4,096-transition storage limit.
Its source and stored transition counts are both 3,318, so no prefix was
discarded and the replay is complete.

## Integrity

Online and target networks both equal the promoted r8 weights. Optimizer state
is empty, optimizer step is zero, and total/TD losses are null. Runtime evidence
contains 6,233 decision rows, all sourced from `combat_rl`, with no optimizer
update, expert action, invalid action, RL failure, agent-level fallback,
traceback, critical error, exception, or post-start CommunicationMod error
growth. Production configuration was restored and all experiment processes
were closed.

## Next iteration

Use consumed replay data, including r7, to fit a materially larger bounded
combat successor. Freeze its training configuration and checkpoint before
opening r8 metrics. Then evaluate the frozen candidate exactly once on this
complete replay. The r10 result rules out another smallest-passing interpolation
step of roughly `1e-6` relative L2 as a useful successor strategy.
