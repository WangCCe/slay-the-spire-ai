# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b4_samples.jsonl |
| sample_sha256 | `2ec6a286299a0bda0f5cd4c09638c975aefe81df17e1452356293c44b148ef5a` |
| target_manifest_hash | `4639ebd178c45a3c5dddfc9e0df5bfc9c8b798fa5178b0a18d5af9fced302cc4` |

## Readiness gates

| Gate | Status |
| --- | --- |
| causal_uplift_ready | BLOCKED |
| estimator_validation_ready | BLOCKED |
| formal_noncombat_rl_training_ready | BLOCKED |
| identity_self_check_passed | PASS |
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
| nonzero-weight trajectories | 25 |
| zero-weight trajectories | 0 |
| exact ESS | 25 |
| exact ESS fraction | 1 |
| exact max normalized weight | 1/25 |

## Blockers

- `complete_trajectory_count_below_minimum`
- `effective_sample_size_below_minimum`
- `estimator_validation_not_implemented`
- `nonzero_weight_trajectory_count_below_minimum`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
