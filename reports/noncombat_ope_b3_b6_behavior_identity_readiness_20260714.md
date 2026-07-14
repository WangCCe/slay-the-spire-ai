# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b3_b6_samples.jsonl |
| sample_sha256 | `9e50338e28a5402b91be000943ce561a4948f968708ac8d46b7a9b54d3b16df1` |
| target_manifest_hash | `0309dd48d30013d718bea445f17ea2f4c24d0f2c1607cf55c183a87b2de21f0d` |

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
| overlap_ready | PASS |
| target_policy_ready | PASS |

## Accounting

| Metric | Value |
| --- | ---: |
| input decisions | 996 |
| complete decisions | 996 |
| complete trajectories | 100 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 100 |
| zero-weight trajectories | 0 |
| exact ESS | 100 |
| exact ESS fraction | 1 |
| exact max normalized weight | 1/100 |

## Blockers

- `estimator_validation_not_implemented`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
