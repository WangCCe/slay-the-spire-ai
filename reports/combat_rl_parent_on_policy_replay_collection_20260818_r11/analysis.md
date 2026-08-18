# Promoted-r8 fresh replay collection r11

## Decision

Accept the naturally completed 20-game collection and consume its fixed
4,096-transition replay window for the one registered frozen r15 confirmation.
The confirmation passed and grants authority only for a separately registered
matched live gate.

## Collection result

The run completed 20/20 games without native recovery. All run seeds match the
registered base35 seed pool in order. Floors were
`[16, 22, 16, 33, 30, 16, 33, 16, 29, 33, 22, 27, 16, 16, 33, 16, 16, 33, 33, 33]`:
489 total, mean `24.45`, median `24.5`, 12 Act 2 entries, seven Act 2 boss
reaches, no Act 3 entries, and no victories.

The terminal checkpoint records 4,154 source transitions. Its fixed replay
capacity retained the latest 4,096 and omitted the earliest 58, exactly matching
the preregistered confirmation horizon. Online and target weights remain
bytewise tensor-equal to production r8, optimizer state is empty, and no loss
was emitted. Runtime evidence contains 7,552 combat-RL decision rows and 20
sim-divergence rows with no traceback, critical log, or RL action failure.

## Frozen confirmation

Frozen r15 passed all conditions on the retained 4,096 transitions. Full-return
SmoothL1 improved from `43.2584076` to `43.2172852` and one-step SmoothL1 from
`3.9035542` to `3.8783906`. Parent action agreement was `99.2188%`, off-target
disagreement was `0.8314%`, and positive-energy End Turn count decreased from
2,018 to 2,004. Relative L2 remained the frozen `1.1741702e-5`.

The confirmation's metadata-only `source_commit` value has the correct
`5763ef84d` prefix but an incorrectly expanded suffix. The raw output is
preserved and an adjacent erratum binds the actual registration commit; the
single evaluation was not rerun and its result is unchanged.

## Next step

Register one new 20-pair, zero-epsilon matched live gate comparing frozen r15
with production r8. Do not train, interpolate, change thresholds, or reuse a
prior live cohort before that gate.
