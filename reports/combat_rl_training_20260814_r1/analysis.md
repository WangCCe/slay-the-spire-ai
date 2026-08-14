# Combat RL Training R1

## Result

The existing v2 combat checkpoint resumed for 25 real games with conservative routing and a 30% OptimizedAgent expert mix. Training added 3,638 live combat transitions, moving from 11,848 to 15,486 total steps. The replay buffer reached readiness during the second game and the final rolling average loss was 1.6999.

All 25 games reached an Act 1 boss. Thirteen entered Act 2, one reached floor 50 and died to Donu and Deca, and none won. Mean floor was 23.2 and median floor was 20. No RL error, disabling, or combat fallback marker appeared in the six logs produced by this batch.

These are training-time outcomes under epsilon near 0.85 and a 30% expert action mixture. They show useful trajectory coverage, not the quality of the final greedy policy. The final checkpoint is therefore preserved but not promoted.

## Persistent Gap

The 25 run records contain zero potion uses. This repeats the May training diagnostic despite deeper runs and thousands of new transitions. Before another long training continuation, the action mask, encoding, selection frequency, and reward treatment for potion actions should be checked if the zero-exploration evaluation also shows no potion use.

## Next Step

Run 10 fresh conservative evaluation games from the preserved final checkpoint with `--epsilon 0`. Keep card uplift disabled so the result measures the shared combat policy. Continue training only if the greedy checkpoint is operational and does not regress; otherwise diagnose the checkpoint/replay and potion-action path before spending another batch.
