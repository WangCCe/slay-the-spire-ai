# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b5_samples.jsonl |
| sample_sha256 | `fbd4d9ea8251254bc0780db9682b7b7afc813c07c0b9c98d64c93a54e0c3ad98` |
| target_manifest_hash | `56476f5e0ad4b075c1e6f2f20b870bb72b1d157674a6e61f3f48ae8fd63bc5f1` |

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
| input decisions | 245 |
| complete decisions | 245 |
| complete trajectories | 25 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 16 |
| zero-weight trajectories | 9 |
| exact ESS | 64927545705456909685270952934922461342289/4102857178608191940699659651933652731179 |
| exact ESS fraction | 64927545705456909685270952934922461342289/102571429465204798517491491298341318279475 |
| exact max normalized weight | 20000000000000000000/254808841497811668233 |

## Blockers

- `complete_trajectory_count_below_minimum`
- `effective_sample_size_below_minimum`
- `estimator_validation_not_implemented`
- `identity_self_check_not_applicable`
- `nonzero_weight_trajectory_count_below_minimum`
- `primary_outcome_degenerate`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
