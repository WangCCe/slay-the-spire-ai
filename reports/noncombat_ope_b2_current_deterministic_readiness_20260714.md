# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b2_samples.jsonl |
| sample_sha256 | `b7436b5a7ef12f345e54172f56ecb05b7aefe59f4ed9007805cc20aa4e90820f` |
| target_manifest_hash | `91f97cb7edf1872fed009bf12043dfb3e4b5cd3a10982f0e5de15da1d1432e48` |

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
| nonzero-weight trajectories | 8 |
| zero-weight trajectories | 17 |
| exact ESS | 1936291079828224375201/270073503359154748801 |
| exact ESS fraction | 1936291079828224375201/6751837583978868720025 |
| exact max normalized weight | 10000000000/44003307601 |

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
