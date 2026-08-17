# Targeted Parent-EndTurn Imitation Training r4

## Decision

Authorize one fresh matched zero-epsilon gate against the promoted parent. Do not
promote from training outcomes, and do not continue training before the matched
gate resolves policy quality.

## Training Result

The corrected weight-`0.325` initialization completed exactly five games and 171
optimizer updates. The final checkpoint is finite, retains the exact frozen parent
anchor, and remains close to the promoted parent (`0.006735` relative L2).

The targeted objective was active at the final update with loss `2.139009` across
63 eligible parent-EndTurn correction states. No action failures, replay
rejections, agent fallbacks, tracebacks, or critical errors occurred.

## Offline Gate

All preregistered offline rules passed on the final replay:

- positive-energy EndTurn share: `0.583444` versus parent `0.624668`;
- parent greedy-action agreement: `0.890137` (minimum `0.88`);
- Smooth L1: `2.929095` versus parent `3.945786`;
- targeted correction agreement: `0.033590` versus parent `0`.

The five training runs averaged floor `20.6` and produced no victories. Those
outcomes are training context only because exploration and online updates make
them unsuitable for promotion.

## Next Step

Run candidate and parent on one fresh matched seed pool with epsilon zero. Require
matched seed completion, no runtime failures, lower positive-energy EndTurn share,
and no regression in victories, Act 2 entry, Act 2 boss reach, or total floors.
