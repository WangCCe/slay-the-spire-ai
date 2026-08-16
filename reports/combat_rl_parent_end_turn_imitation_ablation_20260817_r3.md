# Parent-EndTurn imitation fixed-replay ablation

## Decision

Select `weight=0.20` for one bounded training successor. The objective is
restricted to positive-energy replay states where the frozen parent selects
EndTurn but the emitted action was not EndTurn.

## Evidence

Three fixed-replay replicates used identical batches for weights `0.00`,
`0.10`, `0.20`, `0.30`, and `0.40`, with 32 updates per replicate. Weight
`0.20` was the only nonzero value to satisfy all predeclared script rules:

- minimum parent greedy-action agreement: `88.77%`;
- maximum positive-energy EndTurn share: `61.60%`, below the baseline minimum
  of `69.07%`;
- minimum correction-action agreement: `0.46%`, above the zero baseline;
- worst SmoothL1: `3.3061`, within the 10% TD-fit guard.

The 64-update scan left less parent-agreement margin, so the bounded live
training design should reduce optimizer exposure rather than compensate with a
larger objective weight.

## Scope

This is fixed-replay optimization evidence only. It authorizes implementation
and one bounded training batch, not gameplay promotion. The rejected global
positive-energy imitation objective remains available for historical
checkpoint compatibility but is mutually exclusive with this objective.
