# Promoted-r16 fresh replay collection r15

## Decision

Accept the naturally completed 20-game collection and consume all 3,920 replay
transitions for the one registered frozen r19 confirmation. The confirmation
passed and grants authority only for a separately registered matched live gate.

## Collection result

The run completed 20/20 games without native recovery. All run seeds match the
registered base35 seed pool in order. Floors were
`[24, 22, 33, 16, 8, 22, 28, 16, 16, 33, 25, 16, 16, 33, 33, 22, 7, 13, 30, 33]`:
446 total, mean `22.3`, median `22`, 12 Act 2 entries, five Act 2 boss reaches,
no Act 3 entry, and no victories.

The terminal checkpoint records 3,920 complete, untruncated transitions.
Online and target weights remain tensor-equal to production r16, optimizer
state is empty, and no loss was emitted. Runtime evidence contains 7,091
combat-RL decision rows and 13 sim-divergence rows with no parse error,
traceback, critical log, or RL action failure.

## Frozen confirmation

Frozen r19 passed every registered condition on all 3,920 transitions.
Full-return SmoothL1 improved from `42.1685371` to `42.1447563` and one-step
SmoothL1 from `4.0497952` to `4.0337324`. Parent action agreement was
`99.5153%`, off-target disagreement was `0.3619%`, and positive-energy End
Turn count decreased from 2,043 to 2,031. Relative L2 remained the frozen
`6.8058181e-6`.

## Next step

Register one new 20-pair, zero-epsilon matched live gate comparing frozen r19
with production r16. Do not train, interpolate, change thresholds, or reuse a
prior live cohort before that gate. After the r19 loop closes, do not start r20
without first revisiting simulator and offline candidate generation.
