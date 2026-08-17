# Outcome-Constrained Pairwise Candidate

## Decision

Do not create a live candidate. The fixed `TD=0.05`, pairwise `0.02`,
Q-anchored configuration failed the all-replicate unseen gate, so the script
correctly emitted only a report and no checkpoint.

## Unseen r3 Result

| Metric | Parent | Seed 101 | Seed 202 | Seed 303 |
| --- | ---: | ---: | ---: | ---: |
| SmoothL1 | 4.1228 | 4.2215 | 4.0154 | 4.0831 |
| Parent agreement | 100% | 94.13% | 96.00% | 95.75% |
| Positive-energy EndTurn | 70.64% | 65.05% | 69.35% | 67.60% |
| Intervention margin coverage | 0.00% | 3.84% | 1.17% | 1.97% |
| Off-target parent disagreement | 0.00% | 3.35% | 5.15% | 3.81% |

All three schedules transferred the pairwise behavior to unseen r3 states,
but all exceeded the fixed 3% off-target drift ceiling. Seed 101 also worsened
unseen SmoothL1 and fell below 95% parent agreement. Seeds 202 and 303 improved
TD fit, showing that the outcome term has useful signal, but the raw update is
not stable enough to authorize a live gate.

## Interpretation

The new outcome constraint caught a failure that the earlier replay-local
imitation gate would have missed. Low parameter L2 alone (`0.00178` to
`0.00190`) does not guarantee limited greedy-policy drift.

r3 is now a consumed development cohort and must not be presented as unseen
evidence for a revised candidate. The next bounded diagnostic should retrain
the same fixed configuration and interpolate each replicate back toward the
parent on r3. If interpolation produces a stable region with lower TD error,
at least 95% parent agreement, and at most 3% off-target drift across all
replicates, validate one fixed alpha on a new r4 parent replay before any live
evaluation.
