# Second single-step SGD matched live gate

## Decision

The frozen second single-step SGD candidate passes every preregistered
condition and is qualified for a separate promotion decision. This gate did
not modify the production configuration.

| Metric | Candidate | Parent |
| --- | ---: | ---: |
| Games | 20 | 20 |
| Victories | 0 | 0 |
| Total floors | 467 | 466 |
| Mean floor | 23.35 | 23.30 |
| Median floor | 21 | 21 |
| Act 2 entered | 11 | 11 |
| Act 2 boss reached | 7 | 7 |
| Act 3 entered | 0 | 0 |

The paired result was `1` candidate floor win, `0` parent wins, and `19`
ties. All twenty seed pairs matched, and the summed candidate-minus-parent
floor delta was `+1`.

## Divergent pair

The only non-tied pair was seed-pool index 17 (`B1CB56EEADD34`). Both arms
used `seed_played=408467810743907677` and followed the same non-combat path
through floor 29. The candidate took `3` damage from Snecko while the parent
took `11`, entered the floor-30 Snake Plant fight with `15` HP rather than
`10`, survived it, and died to Centurion and Healer on floor 31. The parent
died to Snake Plant on floor 30. This is a combat-policy trajectory difference,
not a seed or route mismatch.

## Integrity

Both arms completed all twenty games naturally. Candidate and parent decision
traces contain `6,957` and `6,906` rows respectively, all with source
`combat_rl`. Neither arm produced an invalid or failed RL action, agent-level
fallback, training or expert action, traceback, critical error, or post-start
CommunicationMod error growth.

Production configuration was restored to SHA-256
`a480cf80b550dae3dbe94b35f898a1dc8e95cab3174565421884fabb98d62c2b`,
and the experiment processes were closed.

## Interpretation

The observed live difference is deliberately small: nineteen of twenty pairs
were equivalent at the floor-outcome level. The result supports bounded
non-inferiority and one favorable combat divergence, not a large live uplift.
A promotion decision should use the full evidence chain: lower SmoothL1 loss
on both fresh r5 and r6 parent-policy replays, `99.972%` parent action
agreement on r6, very small parameter movement, and this complete matched live
gate.
