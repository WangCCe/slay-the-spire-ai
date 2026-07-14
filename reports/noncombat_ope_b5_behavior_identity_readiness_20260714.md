# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b5_samples.jsonl |
| sample_sha256 | `fbd4d9ea8251254bc0780db9682b7b7afc813c07c0b9c98d64c93a54e0c3ad98` |
| target_manifest_hash | `712f8506313b5844cf80978899fbc9d7fbd80d6df2f5422888029a15315d7b29` |

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
| input decisions | 245 |
| complete decisions | 245 |
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
- `primary_outcome_degenerate`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
