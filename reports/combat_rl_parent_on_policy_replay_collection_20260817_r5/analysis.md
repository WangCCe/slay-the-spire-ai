# Promoted-policy replay collection r5

## Decision

Accept the r5 cohort as a complete untouched replay set for the next combat RL
candidate. All 20 registered seeds completed naturally and produced `3631`
transitions.

Unlike r4, the terminal replay is below the `4096` checkpoint storage limit.
The terminal checkpoint therefore contains every source transition and does not
require reconstruction.

## Zero-update integrity

The terminal online and target networks remain exactly equal to the promoted
single-step SGD parent. The optimizer state is empty, optimizer step is zero,
and both recorded loss fields are null. The runtime logs contain no training
loss, expert action, invalid action, RL failure, replay failure, fallback,
traceback, critical error, or post-start CommunicationMod error growth.

## Coverage

The 20 runs reached `462` total floors with a mean of `23.1` and median of
`22.5`. Eleven runs entered Act 2 and four reached an Act 2 boss. No run entered
Act 3 or achieved victory. This cohort contains useful mid-run coverage without
being truncated at the replay boundary.

## Next step

Freeze the next bounded SGD candidate using only replay data already consumed
by prior decisions. Then run one offline comparison against r5. Do not fit,
select an interpolation, or change thresholds after reading r5 candidate
metrics.
