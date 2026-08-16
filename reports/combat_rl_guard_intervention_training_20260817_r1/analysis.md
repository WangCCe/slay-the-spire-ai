# Guard-intervention combat RL warm-up

## Decision

Continue training from the archived `ep20_steps3971` checkpoint. Do not evaluate
or promote r1 as a candidate because no optimizer update occurred.

## Evidence

The bounded batch completed exactly 20 games and collected 3,971 valid replay
transitions. Loading a weights-only interpolation intentionally raised
`learning_starts` to 4,096, leaving this batch 125 transitions short of the
first update. The optimizer state is empty, losses are unset, and the online
policy remains tensor-for-tensor identical to the promoted parent.

All checkpoint tensors are finite, all executed replay actions are valid under
their masks, and the frozen anchor exactly equals the promoted parent. This is
therefore a usable replay warm-up checkpoint rather than a failed successor.

## Outcome context

The training cohort reached 503 total floors over 20 games, with 13 Act 2
entries, seven Act 2 boss reaches, one Act 3 entry, and no victory. These
outcomes have training-context authority only.

## Next step

Run one 20-game continuation with the same expert mix, route, and parent anchor.
Learning should begin after approximately 125 accepted transitions. Only a
finite, changed checkpoint with positive optimizer progress may enter the
existing replay-fit and 88% parent-agreement offline gate.
