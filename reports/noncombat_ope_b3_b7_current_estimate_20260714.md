# Non-combat OPE estimate

Status: ESTIMATE READY

## Readiness gates

| Gate | Status |
| --- | --- |
| causal_uplift_ready | BLOCKED |
| dataset_estimation_ready | PASS |
| estimator_validation_ready | PASS |
| formal_noncombat_rl_training_ready | BLOCKED |
| live_policy_promotion_ready | BLOCKED |
| ope_estimate_ready | PASS |
| policy_comparison_ready | BLOCKED |

## Accounting

- trajectories: 125
- decisions: 1253
- observed victories: 1
- bootstrap replicates: 10000

## Victory estimates

- behavior: 0.008
- OIS target: 0.0
- SNIS target: 0.0
- OIS uplift: -0.008
- SNIS uplift: -0.008

## Blockers

- none

## Limitations

- The source pool contains only 1 observed victory.
- An OPE estimate is not a causal effect estimate.
- No estimate in this artifact authorizes training or live promotion.
