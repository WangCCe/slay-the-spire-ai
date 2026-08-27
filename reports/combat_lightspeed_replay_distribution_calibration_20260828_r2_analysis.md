# Replay distribution calibration r2 analysis

## Verdict

`replay_distribution_calibration_ready`

The report and manifest are intact. It compares 7,685 complete real replay
transitions from 40 zero-update production-r16 runs with 19,512 transitions from
1,256 initialized fresh LightSTS profiles. Six floor strata from `0..34` meet
the registered common-support threshold; Act 3 does not.

## Main signal

The largest stable mismatch is progression inventory and survivorship, not an
isolated combat action-family shift:

- Potion occupancy at floors `11..17` is `0.152` real versus `1.038`
  simulator (`|SMD|=1.252`). The floor `6..10` and `28..34` effects are also
  large (`0.879` and `0.857`).
- Relic occupancy is higher in the simulator by `0.60..1.11` slots in the
  later common strata, with `|SMD|` up to `0.758`.
- Simulator-minus-real mean reward grows from `+1.22` at floors `0..5` to
  `+10.66` at floors `28..34`.
- In contrast, action-family total variation remains `0.016..0.060`. Maximum
  player-HP and block `|SMD|` are about `0.34`; legal-action count is below
  `0.20`.

## Attribution boundary

The real corpus contains 40 losses and no wins. LightSTS initialized 1,256
isolated profiles, of which 1,102 won and 154 lost; 408 registered profiles were
unreachable because the baseline progression ended earlier. The sources are not
matched by encounter, deck, trajectory, or survival condition. Reward gaps
therefore mix progression, inventory, policy, encounter, survivorship, and
possibly mechanics effects.

Large card, potion, and relic support non-overlap is also inflated by unequal
sample counts and reachable-item coverage. It should rank follow-up questions,
not serve as a frequency-distance or mechanics-equivalence claim.

## Decision

Retain production r16 and do not train or start gameplay from this report. The
next step is a read-only real-trace context attribution over the existing r14/r15
`runtime_evidence.zip` archives and run records. Group combat decisions by floor,
encounter, potion/relic occupancy, deck size, action family, and terminal context
to determine whether the inventory and reward signals persist under narrower
context before changing LightSTS progression generation or starting another fit.
