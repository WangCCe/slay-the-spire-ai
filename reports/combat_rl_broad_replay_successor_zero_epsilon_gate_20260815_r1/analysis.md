# Combat RL broad replay successor zero-epsilon gate R1

## Decision

**Reject the broad-replay successor, retain the promoted parent, and stop unanchored continuation training from this parent.**

## Matched result

The candidate lost the paired floor comparison `1-8-11`. Its mean paired floor delta was `-3.4`; the two-sided exact sign-test p-value was `0.0390625`.

The candidate produced 463 total floors versus 531 for the parent, entered Act 2 eight times versus 13, reached the Act 2 boss six times versus seven, and entered Act 3 once versus three times. Neither arm recorded a victory.

All 20 `seed_played` identities matched in the registered order. Both arms completed without runtime integrity warnings beyond their expected CommunicationMod launch messages.

## Interpretation

This is the second independent fresh matched rejection of a continuation from the promoted parent. The Guardian-only successor lost `3-7-10`; this broad successor lost `1-8-11` with a statistically detectable sign-test result. Both candidates improved replay TD metrics but regressed live outcomes.

The evidence now points to policy forgetting in unanchored TD continuation, rather than insufficient seed breadth. Further training should preserve the parent policy explicitly while optimizing TD loss. Repeating the same continuation recipe, changing seed mixes, or averaging checkpoints is not justified by the current evidence.

The production configuration was restored to the parent checkpoint and all game/Python processes were closed.
