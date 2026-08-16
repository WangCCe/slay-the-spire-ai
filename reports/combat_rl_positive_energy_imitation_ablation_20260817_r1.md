# Positive-energy executed-action imitation ablation

## Decision

Select `positive_energy_action_imitation_weight=0.25` for the next bounded
combat RL continuation. Do not use `0.5`, and do not promote any model from
this fixed-replay analysis.

## Design

- Parent: promoted alpha-0.20 checkpoint.
- Replay: 4,096 transitions from guard-intervention training r2.
- Partition: 3,072 training transitions and 1,024 holdout transitions.
- Updates: 64 per variant, batch size 128, learning rate `1e-4`.
- Replicates: seeds 101, 202, and 303.
- Variants: imitation weights `0`, `0.25`, and `0.5` with TD loss plus the
  existing weight-1 parent anchor.
- Eligible label: the replay's executed action when energy ratio is positive
  and that action is not `EndTurn`.

## Result

| Weight | Parent agreement, mean/min | Executed agreement, mean | Eligible agreement, mean | Positive-energy EndTurn, mean/max | Smooth L1, mean/max | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `0` | 87.24% / 86.52% | 24.84% | 8.41% | 66.10% / 69.59% | 3.1065 / 3.1247 | Baseline |
| `0.25` | 90.82% / 89.55% | 27.05% | 11.29% | 56.18% / 59.76% | 3.0819 / 3.0911 | Pass |
| `0.5` | 81.67% / 80.86% | 29.82% | 15.20% | 44.95% / 46.40% | 3.0956 / 3.1245 | Reject |

Weight `0.25` passes in all three replicates: its worst positive-energy
`EndTurn` share remains below the best zero-weight replicate, its worst
executed-action agreement remains above the best zero-weight replicate, its
minimum parent agreement exceeds 88%, and its TD loss does not regress.

Weight `0.5` improves imitation more aggressively but violates the parent
agreement floor in every replicate. That tradeoff is not justified by this
evidence.

## Next experiment

Continue from the r2 training checkpoint with parent anchor weight `1.0` and
positive-energy action imitation weight `0.25`. The checkpoint already contains
4,096 replay transitions and 1,294 optimizer steps, so this continuation can
learn immediately. Require a fresh matched zero-epsilon evaluation before any
promotion; keep the currently promoted alpha-0.20 checkpoint in production.

The machine-readable result is
`reports/combat_rl_positive_energy_imitation_ablation_20260817_r1.json`. It is
bound to source commit `ab5390e96`, script SHA-256
`afd636d81335d9a7ddf83cb28b496fba787e0df07055f9dc466b14b28c15dbda`, and the
input checkpoint hashes recorded there.
