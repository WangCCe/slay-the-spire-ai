# Positive-energy action imitation training

## Decision

The r3 continuation passes its offline gate and may proceed to one fresh matched
zero-epsilon candidate-versus-parent evaluation. This training cohort has no
promotion authority.

## Objective evidence

The run completed exactly 20 additional games and produced `ep60_steps12830`
with 890 new optimizer updates. The checkpoint stores imitation weight `0.25`,
its final imitation loss is finite and positive at `2.295963`, 93 of the final
128 sampled transitions were eligible, and the frozen anchor still exactly
equals the promoted parent.

On the output replay, positive-energy greedy `EndTurn` share falls from `75.53%`
for the r2 continuation to `62.92%` for r3. Executed-action agreement rises from
`24.15%` to `27.73%`, parent agreement is `90.14%`, and SmoothL1 improves from
`3.8312` to `3.1328`. The output is also nearly aligned with the promoted
parent's `63.02%` positive-energy `EndTurn` share on these states.

## Runtime evidence

All 20 run files and the final checkpoint were archived. The complete rotating
log chain spans startup through `Max games reached (20); exiting.` It contains
2,095 expert actions and 36 logged imitation updates, with no invalid RL action,
RL/expert action failure, replay rejection, traceback, or critical error.

The training games reached 470 total floors, mean `23.5`, with six Act 2 boss
reaches and no Act 3 entry or victory. These outcomes were collected under high
epsilon and expert mixing, so they are diagnostic only and do not override the
offline decision rule.

## Next step

Preregister fresh seeds and run one matched epsilon-zero gate for r3 and the
promoted alpha-0.20 parent. Retain the parent unless the candidate satisfies
both outcome floors and the explicit positive-energy raw-RL `EndTurn` guard.
Do not promote automatically.
