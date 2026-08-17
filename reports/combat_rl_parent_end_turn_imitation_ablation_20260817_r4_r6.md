# Parent-EndTurn Imitation Weight Selection

## Decision

Select targeted imitation weight `0.325` for one fresh five-game smoke from the
original replay-initialized parent checkpoint. Do not continue from the failed
weight-`0.2` output.

## Design

All variants started from the promoted parent, trained for 298 updates on the
same final r2 replay, and used three fixed batch-sampling replicates. The only
varied parameter was the parent-EndTurn-only imitation weight. A candidate had
to satisfy all of the following in every replicate:

- parent greedy-action agreement `>= 0.88`;
- positive-energy EndTurn share below the untrained parent baseline;
- positive targeted correction agreement;
- Smooth L1 no more than `1.10x` the parent baseline.

The coarse (`r4`), refinement (`r5`), and final boundary (`r6`) sweeps are kept
as raw JSON artifacts. The search stopped after the predeclared narrow boundary
scan; no additional replay-specific decimal tuning was performed.

## Result

The parent baseline positive-energy EndTurn share was `0.666667`. Weight `0.325`
was the smallest final-scan value to pass all guards:

- worst parent agreement: `0.885742`;
- worst positive-energy EndTurn share: `0.660256`;
- worst targeted correction agreement: `0.015842`;
- worst Smooth L1: `3.008544` versus parent `3.781563`.

Weights `0.31` and `0.32` retained parent agreement but failed the EndTurn
directional guard in at least one replicate. Higher passing weights were not
selected because they spend more parent-policy deviation for the same purpose.

## Authority

This is an offline training-screen result, not gameplay evidence and not
promotion authority. It authorizes only one bounded five-game training smoke,
followed by the same offline checkpoint gates used for r2.
