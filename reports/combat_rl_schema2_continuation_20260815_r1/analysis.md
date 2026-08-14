# Combat RL Schema-2 Continuation R1

## Result

The bounded 25-game continuation crossed the persisted 4,096-transition replay
threshold and performed 282 Adam updates. The final checkpoint is finite and has
1.45% whole-model relative L2 drift from its entry weights. This validates the
repaired resume path under live training; it does not establish policy quality.

## Training

- Accepted transitions: 3,658 (`13413 -> 17071`)
- Replay at exit: newest 4,096 of 5,223 in-memory transitions
- Adam step: `2679 -> 2961` (+282)
- Epsilon: `0.887444 -> 0.837854`
- Episode: `15 -> 40`, aligned with `ep40_steps17071`
- Relative L2 drift: embeddings 0.25%, hidden 7.44%, value 6.33%, advantage
  10.36%, unused output layer 0%

## Integrity

Replay rejection, episode-close failure, checkpoint-save failure, and NaN
matches were all zero. One warm-up action validation failed on floor 18 because
Clash validation passed the `Game` object where remaining hand cards were
required. The fallback agent recovered; the failure occurred before optimizer
updates. The call site was fixed after the batch and the focused combat RL guard
module passes `171 passed in 5.05s`.

## Gameplay

The 25 training games averaged 19.92 floors with median 16. Eleven entered Act 2,
five reached an Act 2 boss, none entered Act 3, and none won. Because exploration
and expert mixing were active and weights changed during the cohort, these
outcomes cannot be compared directly with the frozen policy.

## Next Step

Commit the Clash fix and this candidate, then preregister a fresh matched seed
pool. Evaluate the candidate and frozen entry checkpoint at epsilon zero under
the fixed code. Promotion requires a paired-win advantage plus no regression in
victories, Act 2 entry/boss reach, total floors, or runtime integrity.
