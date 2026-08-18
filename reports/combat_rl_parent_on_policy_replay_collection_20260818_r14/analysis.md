# Promoted-r16 fresh replay collection r14

## Decision

Accept the naturally completed 20-game collection and consume all 3,765 replay
transitions for the one registered frozen r18 confirmation. The confirmation
passed and grants authority only for a separately registered matched live gate.

## Collection result

The run completed 20/20 games without native recovery. All run seeds match the
registered base35 seed pool in order. Floors were
`[33, 20, 33, 21, 16, 16, 16, 16, 16, 16, 33, 13, 25, 16, 16, 21, 16, 33, 50, 22]`:
448 total, mean `22.4`, median `18`, ten Act 2 entries, five Act 2 boss reaches,
one Act 3 entry, and no victories.

The terminal checkpoint records 3,765 complete, untruncated transitions.
Online and target weights remain tensor-equal to production r16, optimizer
state is empty, and no loss was emitted. Runtime evidence contains 6,928
combat-RL decision rows and 17 sim-divergence rows with no parse error,
traceback, critical log, or RL action failure.

## Frozen confirmation

Frozen r18 passed every registered condition on all 3,765 transitions.
Full-return SmoothL1 improved from `49.9499817` to `49.9241028` and one-step
SmoothL1 from `4.1513276` to `4.1313233`. Parent action agreement was
`99.5219%`, off-target disagreement was `0.3850%`, and positive-energy End
Turn count decreased from 1,988 to 1,977. Relative L2 remained the frozen
`7.6056703e-6`.

## Next step

Register one new 20-pair, zero-epsilon matched live gate comparing frozen r18
with production r16. Do not train, interpolate, change thresholds, or reuse a
prior live cohort before that gate.
