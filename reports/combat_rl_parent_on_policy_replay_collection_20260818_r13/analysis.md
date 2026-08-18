# Promoted-r16 fresh replay collection r13

## Decision

Accept the naturally completed 20-game collection and consume the stored 4,096
replay transitions for the one registered frozen r17 confirmation. The
confirmation passed and grants authority only for a separately registered
matched live gate.

## Collection result

The run completed 20/20 games without native recovery. All run seeds match the
registered base35 seed pool in order. Floors were
`[29, 33, 16, 13, 25, 22, 12, 33, 16, 33, 21, 33, 30, 22, 33, 33, 16, 19, 33, 33]`:
505 total, mean `25.25`, median `27`, 15 Act 2 entries, eight Act 2 boss reaches,
no Act 3 entries, and no victories.

The terminal checkpoint records 4,137 source transitions. Its fixed 4,096-row
serialization limit omitted 41 rows and marks the stored replay as truncated;
the complete 20 run records and runtime evidence remain archived. Online and
target weights remain tensor-equal to production r16, optimizer state is empty,
and no loss was emitted. Runtime evidence contains 7,651 combat-RL decision
rows and 12 sim-divergence rows with no parse error, traceback, critical log,
or RL action failure.

## Frozen confirmation

Frozen r17 passed every registered condition on the stored 4,096 transitions.
Full-return SmoothL1 improved from `40.4774399` to `40.4488678` and one-step
SmoothL1 from `4.0149384` to `3.9985926`. Parent action agreement was
`99.3164%`, off-target disagreement was `0.7163%`, and positive-energy End
Turn count decreased from 2,047 to 2,034. Relative L2 remained the frozen
`7.5350467e-6`.

The raw confirmation supplied the correct registration commit prefix with an
incorrect manually expanded suffix. The adjacent provenance erratum binds the
actual registration commit. The evaluation was not rerun and its model,
replay, thresholds, and result are unchanged.

## Next step

Register one new 20-pair, zero-epsilon matched live gate comparing frozen r17
with production r16. Do not train, interpolate, change thresholds, or reuse a
prior live cohort before that gate.
