# Discounted-Return LightSTS Result

## Decision

Retain `r4`. Do not run a frozen confirmation and do not transfer either arm to
live gameplay.

Both arms passed every registered technical criterion and used the same 67,380
source transitions. Their full source identity hash and parent evaluation rows
matched exactly. Each arm excluded the same two decision-bound profiles (200
prefix transitions), reported no unsupported states, and completed all 256
optimizer updates.

The discounted-return candidate did not improve policy quality. Against `r4`,
its aggregate deltas were only `+0.045` reward and `+0.025` player HP with tied
candidate-only victories `11:11`. It failed the early HP guard (`-0.504`) and
had a material battle-index-6 reward regression (`-1.113`, victories `3:6`).

Against the matched one-step arm, discounted return was worse at every battle
index. Aggregate deltas were `-0.470` reward and `-0.656` HP, with return-only
victories `7:10`. At battle index 9 the deltas remained negative (`-0.476`
reward, `-0.738` HP, victories `3:4`).

The one-step arm had positive aggregate and battle-index-9 results against
`r4`, but it was registered only as the matched control and regressed at battle
index 6 (`-0.134` reward, victories `7:8`). It receives no confirmation or
promotion authority.

The complete-trajectory and discounted-target implementation remains a
simulator-only opt-in capability. This experiment rejects full Monte Carlo
return as the next candidate recipe; it grants no gameplay, transfer,
qualification, promotion, mechanics-equivalence, or live policy-quality
authority.
