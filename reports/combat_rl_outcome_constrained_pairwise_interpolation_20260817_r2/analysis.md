# Outcome-Constrained Parent Interpolation

## Decision

No interpolation alpha is stable across all three training schedules. Do not
write a candidate checkpoint, do not collect confirmation replay for this
design, and do not run a live gate.

## Development Result

The fixed raw update was retrained for each schedule and interpolated toward
the parent at `alpha=0.25`, `0.5`, and `0.75` on the consumed r3 development
cohort.

Seed 101 failed unseen SmoothL1 at every alpha. Seed 202 improved SmoothL1 at
every alpha, but did not reduce positive-energy EndTurn by the required one
percentage point; its `0.5` and `0.75` variants also exceeded the 3% off-target
drift ceiling. Seed 303 passed all conditions only at `alpha=0.75`.

| Alpha | Seed 101 pass | Seed 202 pass | Seed 303 pass | Stable |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | no | no | no | no |
| 0.50 | no | no | no | no |
| 0.75 | no | no | yes | no |

No checkpoint was emitted. r3 remains development evidence only and has no
fresh-confirmation or live authority.

## Interpretation

Parent interpolation controls drift, but it cannot reconcile the schedule
dependent conflict between the pairwise guard-action target and the TD target.
The live gates already showed that reducing raw EndTurn does not reliably
improve progression. Continuing to tune imitation weight or interpolation
alpha on r3 would optimize a behavioral surrogate that has now failed twice.

The next experiment should remove pairwise imitation and train only a small TD
term against the Q-value parent anchor. Its gate should require unseen TD
improvement and much tighter parent preservation, without requiring the model
to copy guard actions. Any design selected on r3 still requires a new replay
cohort before live evaluation.
