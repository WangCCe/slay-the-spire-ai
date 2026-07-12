# Frozen Batch 2 Non-Combat Policy Pilot Support

Review status: `approved_duplicate_candidate_evidence`.

Independent read-only re-review verdict: `APPROVED_DUPLICATE_CANDIDATE_EVIDENCE`; Critical 0, Important 0, Minor 0.

## Frozen source

- Behavior candidate and dataset source commit: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Evidence base: `1f39503e5ee31fb937c765ce4af49c28c2fc0618`.
- Policy implementation: `7c24b23dd6ca365a2ac7db66a3c5a447cec254c9`.
- Qualification report SHA-256: `B526552829D3B844F141C48A081C461E7CDE9F97F1948B6F24473702CF628148`.
- Window: `1783787478..1783790134`; trace tail: `10000`; exact export allowlist: 25 report rows.
- Samples SHA-256: `134A0CD03E8108C19AA1FB27E9BBF8802D48C86A93D9B606E830058C928FE09E`.
- Export report SHA-256: `F1B1AB0926A183678217B65A0474BFF4871AF9E32E6F513572BF4FDA295A85ED`.

## Raw-review correction

The current correction addresses duplicate same-name shop candidates and
contradictory report status. Ten frozen rows now contain 20 deterministic
slot-suffixed candidates with preserved shop inventory and slot metadata; no
row retains a duplicate action ID. Name-only ambiguous labels remain unmapped.
The earlier export-report semantic correction remains in force. Formal RL
training and live promotion remain blocked, off-policy evaluation remains
unsupported. The approved evidence does not change those permanent boundaries.

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
| Current labels present / mapped action IDs | 1,453 / 1,451 |
| Bottled labels present / mapped | 1,453 / 1,407 |
| Bottled confidence | high 1,152; medium 119; low 182 |
| Matched outcome rows / runs | 488 / 14 |
| Victories among matched rows / runs | 0 / 0 |
| Rows with duplicate candidate action IDs | 0 |
| Slot-disambiguated candidates / affected rows | 20 / 10 |

The export command's 25 `--run-file` values exactly equal the qualification table and introduce no other run. The generated JSONL has unique matched outcomes for only 14 of those 25 runs; 11 allowlisted runs do not produce a unique join. This is a support limitation, not evidence of 25 independent trajectories.

## Support decisions

| Mode | Eligible rows | Trajectories | Split trajectories | Split rows | Overall blocked | Category blocks |
|---|---:|---:|---|---|---|---|
| Current | 470 | 14 | train 8; validation 2; test 4 | train 229; validation 84; test 157 | false | none |
| Bottled | 387 | 14 | train 8; validation 2; test 4 | train 188; validation 70; test 129 | false | none |

All four categories are evaluable in both modes under the unchanged structural gate. Current excludes 965 rows without trajectory provenance and 18 without candidates. Bottled additionally excludes 83 rows below its confidence requirement. The split manifest is identical across modes and its trajectory sets are disjoint.

## Training decisions

Both unblocked modes were trained with CPU, seed `0`, learning rate `1e-3`, maximum `50` epochs, and patience `5`. Current stopped after 41 epochs; Bottled stopped after 28. Validation and test candidate legality are `1.0` for both modes.

The corrected 14-file pilot inventory SHA-256 is `0A222C212052712712621E046CE6AA3A0393E3BEA83B038D9D9017BC72489BFB`. Current model/metrics/artifact-manifest hashes are `2E99CB9BC0F152364A6179C09ECC41265BFA4A90F059FB13373BB7F202938509`, `AF316B9B7723301BF611206019F451537B7EE26BB75759B4EBE27CA04423C6BB`, and `A42F3BFA7F602804329C36051AC95CE4D340995CDFB8F8C0B1517BAF86E4AC23`. Bottled equivalents are `29AF1FA00CC952934A22C298E3E7E2A40F3EB3B80C79C15E3E3CA60D64EE4FFB`, `123F4FF16664815E12F5CA021E5B64BC1D2FCC02D9068E1EDEEBAB3C07C1A638`, and `AA1910AB914112E850872AF297EEC73DEAAB16972048C4DFAFCC529773CDB1DF`. Both manifest hash closures were recomputed successfully and no transaction debris remains.

These are supervised pipeline and representation results only. Unknown behavior propensities and absent contextual alternative-action overlap keep off-policy evaluation unsupported. Outcomes are diagnostics only; no causal uplift, formal RL readiness, or live-promotion claim is made.

## Review and isolation

- Current verdict: `APPROVED_DUPLICATE_CANDIDATE_EVIDENCE`; Critical 0, Important 0, Minor 0.
- The reviewer independently recomputed raw counts, zero duplicate IDs, 470/387 dataset rows, 8/2/4 splits, all metrics within `1e-12`, both artifact hash closures, and 101 focused tests.
- Current post-correction isolation comparison: CommunicationMod config and all five active combat checkpoints are unchanged from `duplicate_candidate_correction_pre_isolation` across path, size, UTC mtime, and SHA-256.
- Superseded history: the earlier `APPROVED_FOR_PHASE_B` verdict was invalidated by the two accepted duplicate-candidate/report-status findings; that correction gate is now superseded by the current approval.
- Final correction-focused pytest: 101 passed in 15.09 seconds.
- Final full pytest: 2,379 passed in 68.00 seconds.
- Strict OpenSpec change validation: valid.
- Strict OpenSpec all validation: 32 passed, 0 failed.
- `git diff --check`: exit 0; no whitespace errors; line-ending warnings only.

The evidence base remains 14 matched trajectory groups with zero victories. Behavior propensities remain unknown, so valid OPE, formal non-combat RL, and live promotion remain unavailable.
