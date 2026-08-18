# Promoted-r15 fresh replay collection r12

## Decision

Accept the naturally completed 20-game collection and consume all 3,688 replay
transitions for the one registered frozen r16 confirmation. The confirmation
passed and grants authority only for a separately registered matched live gate.

## Collection result

The run completed 20/20 games without native recovery. All run seeds match the
registered base35 seed pool in order after the game's signed 64-bit conversion.
Floors were
`[30, 22, 27, 29, 19, 40, 16, 16, 33, 27, 21, 16, 22, 22, 21, 11, 16, 33, 11, 25]`:
457 total, mean `22.85`, median `22`, 14 Act 2 entries, three Act 2 boss
reaches, one Act 3 entry, and no victories.

The terminal checkpoint records 3,688 transitions, below the fixed 4,096
maximum confirmation horizon, so the replay is complete and untruncated.
Online and target weights remain tensor-equal to production r15, optimizer
state is empty, and no loss was emitted. Runtime evidence contains 6,862
combat-RL decision rows and 12 sim-divergence rows with no parse error,
traceback, critical log, or RL action failure.

## Frozen confirmation

Frozen r16 passed every registered condition on all 3,688 transitions.
Full-return SmoothL1 improved from `44.3240280` to `44.2992554` and one-step
SmoothL1 from `4.1721177` to `4.1547594`. Parent action agreement was
`99.4035%`, off-target disagreement was `0.5747%`, and positive-energy End
Turn count decreased from 1,815 to 1,804. Relative L2 remained the frozen
`6.9546563e-6`.

## Next step

Register one new 20-pair, zero-epsilon matched live gate comparing frozen r16
with production r15. Do not train, interpolate, change thresholds, or reuse a
prior live cohort before that gate.
