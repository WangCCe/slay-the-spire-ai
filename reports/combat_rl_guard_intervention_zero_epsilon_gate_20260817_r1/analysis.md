# Guard-intervention combat RL matched gate

## Decision

Retain the promoted parent. The candidate improved floor outcomes but failed the
pre-registered guard-intervention condition, so it is not promoted.

## Paired outcomes

All 20 seed pairs matched. The candidate won seven floor pairs, the parent won
five, and eight tied. Candidate total floors were `418` versus `378`; it also
reached Act 2 eight times versus seven and reached an Act 2 boss four times
versus one. Neither arm entered Act 3 or won a run.

## Guard objective

The candidate returned EndTurn on 939 of 1,340 raw RL decisions, compared with
813 of 1,364 for the parent. Of those EndTurn decisions, `92.01%` retained
positive energy for the candidate versus `88.07%` for the parent. The required
non-increase therefore failed.

Both arm logs are complete from startup through natural 20-game exit. Neither
arm recorded an invalid action, RL failure, traceback, or post-start
CommunicationMod error growth.

## Interpretation

The successor learned a policy that was somewhat better on floors but more
dependent on the outer energy guard. Replay TD fit and 88% parent agreement were
not sufficient to align the learned greedy action with the guard-replaced
action. Continuing the same training recipe would not target the failed metric.

## Next step

Use the archived candidate replay and matched logs for an action-level audit of
parent-to-candidate transitions into EndTurn. Determine whether the failure is
caused by replay action binding, Q-target credit, or missing direct imitation
pressure. Only then change the training objective and run a smaller smoke
training batch before another full gate.
