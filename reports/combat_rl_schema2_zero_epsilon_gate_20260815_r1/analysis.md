# Combat RL Schema-2 Zero-Epsilon Gate R1

## Decision

`FAIL`. Do not continue training or promote the schema-2 candidate.

The candidate won one paired floor comparison, lost four, and tied five. It
reached 167 total floors versus the frozen baseline's 181, and entered Act 2 once
versus twice. Although it reached one Act 2 boss while the baseline reached none,
the preregistered rule requires every condition to pass.

## Paired Result

- Candidate floors: `[16, 16, 16, 33, 16, 14, 16, 8, 16, 16]`
- Baseline floors: `[16, 16, 31, 16, 22, 16, 16, 16, 16, 16]`
- Paired deltas: `[0, 0, -15, 17, -6, -2, 0, -8, 0, 0]`
- Candidate wins / baseline wins / ties: `1 / 4 / 5`
- Victories: `0 / 0`
- Runtime integrity warnings: `0 / 0`

All ten `seed_played` values match pairwise. Both arms ran at epsilon zero with
training and expert mixing disabled.

## Event Death

The candidate's floor-14 run with `killed_by=null` was a valid terminal outcome,
not a protocol failure. At Scrap Ooze the noncombat policy repeatedly selected
`Deeper` until HP reached zero. This contributed a -2 paired delta and exposes a
separate event-policy bug, but it does not explain the larger -15 and -8 losses.

## Next Step

Keep the frozen entry policy as baseline. Do not spend another live cohort on
this candidate. First perform an offline update-stability diagnosis on the final
replay/checkpoint pair, focusing on Q-value and TD-error movement across the 282
updates. Use that evidence to choose one small training change before another
bounded update batch. Treat the Scrap Ooze lethal-choice guard as a separate
narrow gameplay policy fix.
