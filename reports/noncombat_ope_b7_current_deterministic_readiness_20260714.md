# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b7_samples.jsonl |
| sample_sha256 | `efd2deaa1a182b5c609561b11f9f799a471c95ce17d5585c7cebb84c235bbcbf` |
| target_manifest_hash | `d7d0826bcc142a7d6f691a27f6d0bb28a8909c7daf7abcc89c1c637f558de4e6` |

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
| input decisions | 257 |
| complete decisions | 257 |
| complete trajectories | 25 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 25 |
| zero-weight trajectories | 0 |
| exact ESS | 616657264959926723206803011203257094641711200108877768950756285976001/24666499620812672592447565939043598474641421040354425509440231978001 |
| exact ESS fraction | 616657264959926723206803011203257094641711200108877768950756285976001/616662490520316814811189148476089961866035526008860637736005799450025 |
| exact max normalized weight | 1000000000000000000000000000000000/24832584741825139359284269929011999 |

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
