# Combat RL Guardian successor zero-epsilon gate R1

## Decision

**Reject the Guardian-curriculum successor and retain the currently promoted parent. Do not repeat the Guardian-only continuation recipe.**

## Matched result

The candidate lost the paired floor comparison `3-7-10`. Its mean paired floor delta was `-3.0`; the two-sided sign-test p-value was `0.34375`.

The candidate produced 500 total floors versus 560 for the parent, reached the Act 2 boss six times versus nine, and entered Act 3 once versus three times. Both arms entered Act 2 on 14 seeds and neither recorded a victory.

All 20 `seed_played` identities matched in the registered order. Both arms completed without runtime integrity warnings beyond their expected CommunicationMod launch messages.

## Interpretation

The successor improved offline TD fit and passed Guardian on four consumed curriculum seeds, but those signals did not generalize to fresh matched play. The largest paired regressions were `-34`, `-17`, `-9`, and `-9` floors. Guardian-only continuation therefore caused material policy regression outside its training cohort.

The production configuration was restored to the parent checkpoint and all game/Python processes were closed. A future combat RL continuation should use a broad seed distribution and preserve parent behavior, rather than concentrating the update on one boss-failure cohort.
