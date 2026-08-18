# Complete-Trajectory Enum Identity Result

## Decision

Retain `r4`. Do not run a frozen confirmation, repeat enum training, or transfer
the candidate to live gameplay.

The clean replication passed every registered technical criterion. All 3,404
initialized profiles completed, so no trajectory prefixes were excluded; the
runner produced 66,793 source transitions, 81,872 balanced replay rows, 256
optimizer updates, no unsupported states, and no held-out truncations. Parent
migration preserved actions exactly with maximum Q delta `3.58e-7`.

Policy evidence was broadly positive. Across 841 reachable held-out profiles,
the candidate improved mean reward by `+0.558`, player HP by `+0.296`, and
candidate-only victories by `14:6`. Battle index 6 improved by `+0.933` reward
and `+0.555` HP (`7:3` victories); battle index 9 improved by `+1.317` reward
and `+0.532` HP (`5:2` victories).

The preregistered battle-index-0 zero-regression guard failed by small negative
deltas: `-0.0076` reward and `-0.0078` HP. These values cannot be rounded to
zero or reinterpreted after outcome access. The candidate therefore receives
no frozen-confirmation or live authority despite the positive aggregate and
late-combat evidence.

This simulator-only result grants no gameplay, transfer, qualification,
promotion, mechanics-equivalence, or live policy-quality authority.
