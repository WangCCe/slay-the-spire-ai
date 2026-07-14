# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b3_b7_samples.jsonl |
| sample_sha256 | `aa61da25c93cdfa24ec57f787fbd41b5e4921c1a1a2bf9cb75f799133159b292` |
| target_manifest_hash | `25955774b5792078317a7e43c54971355ba073b50fc7436d78e53ee9672a6af5` |

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
| input decisions | 1253 |
| complete decisions | 1253 |
| complete trajectories | 125 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 125 |
| zero-weight trajectories | 0 |
| exact ESS | 125 |
| exact ESS fraction | 1 |
| exact max normalized weight | 1/125 |

## Blockers

- `estimator_validation_not_implemented`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
