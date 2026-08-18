# Promoted-r8 fresh replay collection r10

## Decision

Accept the recovered 20-game replay as a complete fresh confirmation cohort
for frozen candidate r13. The cohort was then consumed by exactly one offline
confirmation. It grants no automatic promotion authority.

## Recovery

The first launch failed before completing one game or publishing a checkpoint.
Windows Application Event 1000 records `python.exe` failing in `nvcuda64.dll`
at `08:51:05`, exception `0xc0000409`, report ID
`191bb513-4669-48bd-a7c1-257d396e85ac`. The candidate was never loaded.

A minimal CUDA tensor health check then passed. One exact recovery used the
same committed config, r8 initializer, and 20-seed order from a fresh game.
It completed all 20 games naturally. The failed-attempt log is retained beside
the successful runtime logs in `runtime_evidence.zip`; the failed attempt
contributed no `.run` row or replay transition to the recovered checkpoint.

## Collection result

The terminal checkpoint contains all `3,081` source transitions with no
truncation and 252 terminal boundaries. Online and target weights exactly equal
the promoted r8 parent, optimizer state is empty, and no loss was emitted.
All 20 run seeds match the registered base35 seed pool in order.

Floors were
`[16, 24, 18, 33, 16, 30, 16, 22, 14, 16, 16, 33, 16, 16, 29, 16, 33, 16, 7, 16]`:
403 total, mean `20.15`, median `16`, maximum `33`, eight Act 2 entries, three
Act 2 boss entries, no Act 3 entries, and no victories. Runtime evidence holds
5,902 decision rows, all from `combat_rl`, and four sim-divergence rows.

## Confirmation

Frozen r13 passed its one allowed confirmation on all 3,081 transitions.
Full-combat-return SmoothL1 improved from `54.7217827` to `54.7010956` and
one-step SmoothL1 from `4.4317813` to `4.4114928`. Parent action agreement was
`99.6430%`, off-target disagreement was `0.5305%`, and positive-energy End Turn
count decreased from 1,624 to 1,621. All registered conditions passed.

The raw confirmation JSON is preserved at SHA-256
`f63c27dd79e59f18b0a1e2460b423afda484493dbc247f35cb4b9f19ed70bf1b`.
Its `source_commit` argument correctly starts with registered commit prefix
`38b80ac9f` but contains an incorrect manually expanded suffix. The adjacent
erratum binds the actual full commit without changing or rerunning evaluation.

## Next step

Register one bounded 20-pair live gate comparing frozen r13 with production r8
on a new shared seed pool. Do not train, interpolate, or change thresholds
before that gate.
