# Guard-intervention combat RL training continuation

## Decision

The r2 continuation passes the offline gate and may proceed to one fresh matched
candidate-versus-parent evaluation. The training cohort has no promotion
authority.

## Offline evidence

The continuation completed exactly 20 additional games and produced
`ep40_steps9269` with 1,294 optimizer updates. On the successor replay,
SmoothL1 improved from `3.777830` for the promoted parent to `3.069603` for the
successor. Parent/candidate greedy-action agreement is `88.037%`, narrowly above
the fixed `88%` minimum.

The successor differs from the parent by `2.815%` relative L2. Its tensors are
finite, all stored executed actions remain valid under their masks, the frozen
anchor exactly equals the promoted parent, and the final anchor loss is finite
and positive at `0.309627`.

## Training context

The 20 continuation games reached 636 total floors, mean `31.8`, including 13
Act 2 boss reaches and four Act 3 entries. No game won. These outcomes were
collected under expert mixing and high epsilon, so they are diagnostic only.

The retained rotating logs cover the final approximately 40 minutes. They show
no invalid RL action, expert-action failure, RL action failure, or replay
rejection. Guard counts from training are not comparable to the epsilon-zero
production baseline.

## Next step

Run a fresh matched epsilon-zero evaluation for the successor and promoted
parent. Compare paired victories, total floors, Act 3 exposure, and the rate of
positive-energy raw RL EndTurn interventions. Do not promote automatically.
