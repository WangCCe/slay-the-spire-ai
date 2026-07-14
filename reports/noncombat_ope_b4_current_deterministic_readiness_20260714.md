# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b4_samples.jsonl |
| sample_sha256 | `2ec6a286299a0bda0f5cd4c09638c975aefe81df17e1452356293c44b148ef5a` |
| target_manifest_hash | `e3ddd4f61b1611b6423c45e67fff0e17991a83551d3c43d32a28d23de2d60ea4` |

## Readiness gates

| Gate | Status |
| --- | --- |
| causal_uplift_ready | BLOCKED |
| estimator_validation_ready | BLOCKED |
| formal_noncombat_rl_training_ready | BLOCKED |
| identity_self_check_passed | BLOCKED |
| input_valid | PASS |
| live_policy_promotion_ready | BLOCKED |
| ope_ready | BLOCKED |
| outcome_contract_ready | PASS |
| overlap_ready | BLOCKED |
| target_policy_ready | PASS |

## Accounting

| Metric | Value |
| --- | ---: |
| input decisions | 272 |
| complete decisions | 272 |
| complete trajectories | 25 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 12 |
| zero-weight trajectories | 13 |
| exact ESS | 475438225229307388820061101443106281/41084042044447867678476160509089481 |
| exact ESS fraction | 475438225229307388820061101443106281/1027101051111196691961904012727237025 |
| exact max normalized weight | 81920000000000000/689520286307304659 |

## Blockers

- `complete_trajectory_count_below_minimum`
- `effective_sample_size_below_minimum`
- `ess_fraction_below_minimum`
- `estimator_validation_not_implemented`
- `identity_self_check_not_applicable`
- `max_normalized_weight_above_maximum`
- `nonzero_weight_trajectory_count_below_minimum`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
