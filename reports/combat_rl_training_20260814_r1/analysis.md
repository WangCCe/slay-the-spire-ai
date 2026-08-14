# Combat RL Training R1

## Result

The existing v2 combat checkpoint resumed for 25 real games with conservative routing and a 30% OptimizedAgent expert mix. Training added 3,638 live combat transitions, moving from 11,848 to 15,486 total steps. The replay buffer reached readiness during the second game and the final rolling average loss was 1.6999.

All 25 games reached an Act 1 boss. Thirteen entered Act 2, one reached floor 50 and died to Donu and Deca, and none won. Mean floor was 23.2 and median floor was 20. No RL error, disabling, or combat fallback marker appeared in the six logs produced by this batch.

These are training-time outcomes under epsilon near 0.85 and a 30% expert action mixture. They show useful trajectory coverage, not the quality of the final greedy policy. The final checkpoint is therefore preserved but not promoted.

## Potion Record Correction

The 25 run records contain zero entries in `potions_floor_usage`, but the bounded decision-trace window contains 2,179 combat decisions with a usable potion and 108 actual `PotionAction` rows. The run-record field is therefore not reliable evidence of potion behavior for this CommunicationMod path. Potion action reachability is not the next blocker.

## Next Step

The final checkpoint completed 10 fresh conservative evaluation games with `--epsilon 0`, reaching a mean floor of 22.4 and no victories. Use those exact seeds for an `epsilon=0` evaluation of the frozen entry checkpoint. Continue training only if the post-training checkpoint improves the matched greedy comparison.
