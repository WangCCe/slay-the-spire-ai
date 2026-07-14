# Non-combat OPE readiness

Status: BLOCKED

## Source

| Field | Value |
| --- | --- |
| sample_file | known_propensity_exploration_eval_20260714_b3_b6_samples.jsonl |
| sample_sha256 | `9e50338e28a5402b91be000943ce561a4948f968708ac8d46b7a9b54d3b16df1` |
| target_manifest_hash | `9eabfc9e4193851067a712602b56e3931595ec09ab268f78dbb7b4fc6fc4023a` |

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
| input decisions | 996 |
| complete decisions | 996 |
| complete trajectories | 100 |
| blocked trajectories | 0 |
| nonzero-weight trajectories | 62 |
| zero-weight trajectories | 38 |
| exact ESS | 2216731162588355773273204392521470155432702473868974655923809032910510833991344109868415447554642407850568913324447762599910031076472323889/45931652770543192602273015161100053739179511482075721380171930524016630441924637918077671363374114956920400925939030107301128912089773439 |
| exact ESS fraction | 2216731162588355773273204392521470155432702473868974655923809032910510833991344109868415447554642407850568913324447762599910031076472323889/4593165277054319260227301516110005373917951148207572138017193052401663044192463791807767136337411495692040092593903010730112891208977343900 |
| exact max normalized weight | 81633930507242669951883230137372732258884216840502960607500000000000/1488869088465589634518770627048624622398144729998273246769613698024583 |

## Blockers

- `effective_sample_size_below_minimum`
- `ess_fraction_below_minimum`
- `estimator_validation_not_implemented`
- `identity_self_check_not_applicable`

## Limitations

- No OPE estimator, policy value, uplift, or confidence interval is computed.
- Overlap screens reject weak support but do not validate an estimator.
- Terminal outcomes remain separate diagnostics, not a formal RL reward.
