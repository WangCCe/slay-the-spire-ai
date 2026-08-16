# Promoted alpha-0.20 production validation r3

The promoted command completed five games on the post-Reaper-fix source. Floors were `38, 16, 16, 16, 16`, for a mean of `20.4`. One game defeated both the Act 1 and Act 2 bosses and entered Act 3; the other four died to Act 1 bosses. No victory was achieved.

The bounded trace path remained effective: the final decision trace was `5,935,345` bytes and the simulator trace was `91,286` bytes. The previous Reaper plus Magic Flower mismatch did not recur.

All six simulator rows formed three paired Headbutt selection-boundary transitions. During the temporary discard-selection screen, the game deferred one reactive or replayed attack effect; immediately after `CardSelectAction`, that effect appeared and produced the inverse mismatch. The three observed variants were Byrd Flight stun intent, Curl Up block, and the second Double Tap hit. The accompanying source change extends the existing Headbutt delayed-effect mechanism only for those conditionally proven fields.

Focused verification passed all 13 Headbutt divergence tests. The promoted checkpoint remains the production baseline; the next bounded batch should validate that the paired Headbutt rows disappear while retaining any unrelated simulator evidence.
