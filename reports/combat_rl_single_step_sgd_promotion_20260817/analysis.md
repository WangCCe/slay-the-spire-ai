# Single-step SGD combat promotion

## Decision

Promote the frozen single-step SGD candidate as the production combat baseline
for bounded five-game evaluation launches.

This is a separate decision from the matched live gate. The gate restored the
previous production configuration before qualification; promotion is based on
the complete evidence chain and does not reinterpret the ten-pair result as a
large live effect.

## Basis

- The candidate improved one-step SmoothL1 on development replay r3 from
  `4.122797` to `4.116972`.
- It independently improved untouched replay r4 from `3.609213` to `3.604594`
  while retaining `99.9126%` parent action agreement.
- The fresh matched live gate passed every registered condition: one candidate
  floor win, zero parent floor wins, nine ties, and `210` versus `204` total
  floors.
- Both live arms completed without invalid actions, RL failures, fallbacks,
  tracebacks, critical errors, or post-start CommunicationMod error growth.

## Scope

The production command remains evaluation-only with epsilon zero, conservative
routing, and a five-game launch bound. It loads only the finite weights artifact
and does not load optimizer or replay state. The previous production config is
retained as a fixed rollback artifact.

Only one of ten live pairs diverged at the floor-outcome level, and neither arm
won a run. The evidence supports a conservative baseline replacement, not a
claim of material win-rate improvement or completion of the first-victory goal.

## Next iteration

Collect a new on-policy replay cohort under this promoted policy. The consumed
r4 replay can then join the training side of the next conservative SGD update,
while the new cohort remains untouched until the next candidate is frozen.
