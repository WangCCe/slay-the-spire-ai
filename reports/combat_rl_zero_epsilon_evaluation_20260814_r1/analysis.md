# Combat RL Zero-Epsilon Evaluation R1

## Result

The frozen post-training checkpoint completed 10 fresh conservative games with `epsilon=0`, no card uplift, no RL errors, and no fallback. It reached a mean floor of 22.4, a median of 16, and a maximum of 33. Nine games reached an Act 1 boss, four entered Act 2, and none won.

The checkpoint has usable greedy behavior but has not earned promotion or an automatic training continuation. Training-time depth was partly driven by epsilon near 0.85 and a 30% expert mixture, so the 25-game training outcomes cannot substitute for this result.

## Potion Evidence

The `.run` files again report zero entries in `potions_floor_usage`, but the same evaluation window contains 807 combat decisions with a usable potion and 42 selected `PotionAction` rows. Consecutive rows show potion slots disappearing and Blood Potion increasing HP. The run-record field is not reliable for this path; potion action masking and selection are working.

## Next Step

Convert these 10 `seed_played` values back to the game's seed strings and evaluate the frozen pre-training checkpoint on the same seeds with `epsilon=0`. That matched greedy comparison will isolate whether the 3,638 new transitions improved the policy enough to justify more training.
