# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b3_samples.jsonl |
| sample_sha256 | `b7f8f88e2b418e54cee8c1d8a646e613122b0be531b9d068ea5a16966ddf87f2` |
| target_manifest_hash | `c923e9d7226e1093e41e503fc9489f9d163c58a56b17a979a7122d4af29bc5a2` |

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
| input decisions | 230 |
| complete decisions | 230 |
| complete trajectories | 25 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 10 |
| zero-weight trajectories | 15 |
| exact ESS | 332092729849339447443361/38104289120531136322981 |
| exact ESS fraction | 332092729849339447443361/952607228013278408074525 |
| exact max normalized weight | 100000000000/576274873519 |

## Blockers

- `complete_trajectory_count_below_minimum`
- `effective_sample_size_below_minimum`
- `ess_fraction_below_minimum`
- `estimator_validation_not_implemented`
- `identity_self_check_not_applicable`
- `max_normalized_weight_above_maximum`
- `nonzero_weight_trajectory_count_below_minimum`
- `primary_outcome_degenerate`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
