# Promoted-r8 replay collection r7

## Decision

Accept r7 as a complete 20-game production-policy trajectory collection and a
fixed, truncated-tail replay holdout for one later frozen candidate evaluation.
The collection also records the first victory achieved by the promoted r8
combat baseline.

## Production-policy victory

Seed-pool index 7 (`5FD6CB7EF4C64`) produced an AI-marked Ironclad A0 win on
floor 51. The run was a normal non-daily, non-endless, non-trial game. It
defeated Awakened One after a 32-turn final fight and is preserved as
`1786991900.run` with `victory=true`.

This is the second known AI-marked Ironclad victory in the game archive. The
historical first occurred on 2026-08-17 under an end-turn-imitation candidate
that was not promoted because its overall matched gate regressed total floors.
The r7 win is therefore the first victory attributable to the current promoted
r8 baseline. Online and target weights remained byte-equivalent to r8 for the
entire collection, so it was not produced by in-run learning.

## Collection outcome

All 20 registered seeds completed in order. The cohort reached `497` total
floors, averaged `24.85`, entered Act 2 eleven times, reached seven Act 2
bosses, entered Act 3 twice, and won once.

The terminal checkpoint observed `4,194` source transitions. Checkpoint schema
2 stores at most `4,096`, so it preserved the newest `97.663%` and omitted the
oldest 98 transitions. This is not a complete replay and must not be described
as one. Because no successor exists yet and r7 has not been used for fitting or
selection, the fixed 4,096-transition tail remains a valid one-use holdout.

## Integrity

Online and target networks both equal the promoted r8 weights. Optimizer state
is empty, optimizer step is zero, and total/TD losses are null. Runtime evidence
contains `7,693` decision rows, all sourced from `combat_rl`, with no training
update, expert action, invalid action, RL failure, replay failure, agent-level
fallback, traceback, critical error, or post-start CommunicationMod error
growth. Production configuration was restored and all experiment processes
were closed.

## Next iteration

Use only consumed r5 and r6 replay for a bounded multi-update successor. Freeze
all model and interpolation choices before reading r7 candidate metrics, then
evaluate once on the fixed 4,096-transition r7 tail. Do not reconstruct the
missing prefix, substitute another cohort, or tune against r7.
