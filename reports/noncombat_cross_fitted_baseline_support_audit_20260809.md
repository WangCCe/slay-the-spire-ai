# Cross-Fitted Baseline Support Audit

## Decision

The bounded descriptive verdict is `take_pressure_persists_on_supported_unclipped_rows`.
It authorizes no training, evaluation, OPE, model loading, gameplay,
qualification, promotion, policy-quality, causal, or formal-RL claim.

## Verified Evidence

- Trajectories: 512
- Decisions: 11729
- Chunks/checkpoints: 8
- Victories: 0
- Terminal and manifest were independently verified under the inactive lease.

## Baseline Support

| Support | Rows | Prediction mean | Residual RMSE | Advantage mean |
| --- | ---: | ---: | ---: | ---: |
| Clipped low | 2261 | 0.000000000 | 0.146612645 | 0.116917681 |
| Unclipped | 9468 | 0.163436758 | 0.131036770 | -0.017969848 |

## Card-Reward Attribution

- Global clipping contrast: `supported`
- Clipped direct take pressure: 0.000226246205709
- Unclipped direct take pressure: 0.00951280453333
- Final-window unclipped pressures: 0.00112214321501, 0.00067155040877, 0.00148177369539, 0.00014821169027

The final window contains 1774 multi-family card-reward decisions: {'bowl': 1, 'take': 1773}. The exact registered saturation predicate remains `false`; the single exception does not establish robust greedy diversity.

## Next Gate

Use this result only for a separately reviewed source-level mechanism
proposal. Do not start another empirical run from this audit alone.
