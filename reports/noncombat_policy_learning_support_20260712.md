# Frozen Batch 2 Non-Combat Policy Pilot Support

Status: `DONE_WITH_CONCERNS` for Phase A only. Independent raw-evidence review, post-isolation comparison, final tests, strict validation, and commit are pending.

## Frozen source

- Behavior candidate and dataset source commit: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Evidence base: `1f39503e5ee31fb937c765ce4af49c28c2fc0618`.
- Policy implementation: `7c24b23dd6ca365a2ac7db66a3c5a447cec254c9`.
- Qualification report SHA-256: `B526552829D3B844F141C48A081C461E7CDE9F97F1948B6F24473702CF628148`.
- Window: `1783787478..1783790134`; trace tail: `10000`; exact export allowlist: 25 report rows.
- Samples SHA-256: `47ADC1F040675410E4AC40FBE53D4B3719E63884D0B53DB53DF19A7E542AF477`.
- Export report SHA-256: `F1B1AB0926A183678217B65A0474BFF4871AF9E32E6F513572BF4FDA295A85ED`.

## Raw-review correction

Independent raw review blocked the initial report semantics because an internal
field-presence result was rendered as promotion authorization and matched
support was stated only at decision-row grain. The corrected export report now
labels the result as an export evidence-presence gate, states that it does not
authorize formal non-combat RL training or live-policy promotion, and renders
488 matched decision rows, 14 unique non-null trajectories, and 0 trajectory
victories. Formal RL training and live promotion remain blocked, off-policy
evaluation remains unsupported, and review status remains pending re-review.

## Direct JSONL audit

| Measure | Result |
|---|---:|
| Lines / v2 schema rows | 1,453 / 1,453 |
| Categories | card_reward 236; event 253; route 882; shop 82 |
| Evidence quality | complete 1,409; partial 44 |
| Behavior policy / commit coverage | 1,453 / 1,453 |
| Rows with eligible trajectory provenance | 488 |
| Unique trajectory groups | 14 |
| Join statuses | matched 488; ambiguous 805; floor_inconsistent 17; missing 143 |
| Probability status | unknown 1,453; non-null probabilities 0 |
| Current labels present / mapped | 1,453 / 1,407 |
| Bottled labels present / mapped | 1,453 / 1,407 |
| Bottled confidence | high 1,152; medium 119; low 182 |
| Matched outcome rows / runs | 488 / 14 |
| Victories among matched rows / runs | 0 / 0 |

The export command's 25 `--run-file` values exactly equal the qualification table and introduce no other run. The generated JSONL has unique matched outcomes for only 14 of those 25 runs; 11 allowlisted runs do not produce a unique join. This is a support limitation, not evidence of 25 independent trajectories.

## Support decisions

| Mode | Eligible rows | Trajectories | Split trajectories | Split rows | Overall blocked | Category blocks |
|---|---:|---:|---|---|---|---|
| Current | 470 | 14 | train 8; validation 2; test 4 | train 229; validation 84; test 157 | false | none |
| Bottled | 387 | 14 | train 8; validation 2; test 4 | train 188; validation 70; test 129 | false | none |

All four categories are evaluable in both modes under the unchanged structural gate. Current excludes 965 rows without trajectory provenance and 18 without candidates. Bottled additionally excludes 83 rows below its confidence requirement. The split manifest is identical across modes and its trajectory sets are disjoint.

## Training decisions

Both unblocked modes were trained with CPU, seed `0`, learning rate `1e-3`, maximum `50` epochs, and patience `5`. Current stopped after 43 epochs; Bottled stopped after 28. Validation and test candidate legality are `1.0` for both modes.

These are supervised pipeline and representation results only. Unknown behavior propensities and absent contextual alternative-action overlap keep off-policy evaluation unsupported. Outcomes are diagnostics only; no causal uplift, formal RL readiness, or live-promotion claim is made.

## Phase B verification

- Independent raw-evidence verdict: `APPROVED_FOR_PHASE_B`; Critical findings 0; Important findings 0 after the accepted report-semantic correction.
- Post-isolation comparison: CommunicationMod config and all five active combat checkpoints are unchanged across path, size, UTC mtime, and SHA-256.
- Focused pytest: 97 passed in 17.82 seconds.
- Full pytest: 2,375 passed in 74.87 seconds.
- Strict OpenSpec change validation: valid.
- Strict OpenSpec all validation: 32 passed, 0 failed.
- `git diff --check`: exit 0; no whitespace errors; line-ending warnings only.

The evidence base remains 14 matched trajectory groups with zero victories. Behavior propensities remain unknown, so valid OPE, formal non-combat RL, and live promotion remain unavailable.
