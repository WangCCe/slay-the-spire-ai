# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b3_samples.jsonl |
| sample_sha256 | `b7f8f88e2b418e54cee8c1d8a646e613122b0be531b9d068ea5a16966ddf87f2` |
| target_manifest_hash | `75a12fbee295c83099fb4c4206f338d2ee988c0deae2ed05eee865b0d083628a` |

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
| input decisions | 230 |
| complete decisions | 230 |
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
