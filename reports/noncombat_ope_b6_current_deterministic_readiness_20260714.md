# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b6_samples.jsonl |
| sample_sha256 | `3a04a11bd2cf0c6e5a84713afcda043586b9ad4f5efc1418922d62b703990729` |
| target_manifest_hash | `58e70d2513dbf094a5bd3c470ccad305e45131f847e62db84e874fee50cfd54e` |

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
| input decisions | 249 |
| complete decisions | 249 |
| complete trajectories | 25 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 24 |
| zero-weight trajectories | 1 |
| exact ESS | 6286927943394609569062430392107202497947194451206663127574/266187625091570246274737411870392334111653265638416703787 |
| exact ESS fraction | 6286927943394609569062430392107202497947194451206663127574/6654690627289256156868435296759808352791331640960417594675 |
| exact max normalized weight | 5000000000000000000000000000/97110204999741990831929450769 |

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
