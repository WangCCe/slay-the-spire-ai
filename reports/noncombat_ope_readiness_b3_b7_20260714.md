# Non-combat OPE readiness: B3-B7 overlap milestone

## Verdict

The pooled B3-B7 evidence passes both the known-propensity data qualification
gate and the pre-specified overlap screen for deterministic Current. The final
pool contains 1,253 confirmed decisions from 125 complete run trajectories,
including both terminal victory classes. Deterministic Current retains 87
nonzero-weight trajectories with an ESS of about 66.30, an ESS fraction of
about 0.5304, and a maximum normalized weight of about 0.04454.

This is an overlap milestone, not an OPE result. Estimator validation has not
been implemented, so policy value, uplift, confidence intervals, formal
non-combat RL training, and live policy promotion remain explicitly blocked.
All five batches ran in evaluation mode; no training was started.

## Frozen source

| Field | Value |
| --- | --- |
| canonical pool | `known_propensity_exploration_eval_20260714_b3_b7_samples.jsonl` |
| canonical pool SHA-256 | `aa61da25c93cdfa24ec57f787fbd41b5e4921c1a1a2bf9cb75f799133159b292` |
| pool manifest SHA-256 | `f50554c6b1fb89d4ae3138fef5b105fb0dfce58db80a147a0599457fe57dce67` |
| qualification SHA-256 | `85259842724554d7635e5bd32e8410a05e103c50cb9e1679bccc664fa389287e` |
| independent verification SHA-256 | `73d09e2bf86beba92bc278a400bae7a27a8ff25ac92333173f78d934ecb9cde0` |
| fixed source commit | `2006df2be20151afd759e9fc4deef320bc1f599d` |
| winning run | `1784019948.run` from B4, floor 51, playtime 245 |

## Batch progression

| Batch | Card/shop alternative rate | Decisions | Card support B/A | Shop support B/A | Current nonzero | Current ESS | ESS fraction | Max weight | Wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B3 | 10% / 10% | 230 | 176 / 22 | 30 / 2 | 10 / 25 | 8.7154 | 0.3486 | 0.1735 | 0 |
| B4 | 5% / 5% | 272 | 211 / 15 | 46 / 0 | 12 / 25 | 11.5723 | 0.4629 | 0.1188 | 1 |
| B5 | 3% / 5% | 245 | 197 / 7 | 38 / 3 | 16 / 25 | 15.8250 | 0.6330 | 0.0785 | 0 |
| B6 | 3% / 3% | 249 | 212 / 1 | 36 / 0 | 24 / 25 | 23.6184 | 0.9447 | 0.0515 | 0 |
| B7 | 0.1% / 0.1% | 257 | 211 / 0 | 46 / 0 | 25 / 25 | 24.9998 | 1.0000 | 0.0403 | 0 |

`B/A` means baseline/alternative selected-arm decisions. B7 was a conditional
low-exploration batch. It was collected only after the 100-trajectory B3-B6
pool failed the Current ESS and ESS-fraction screens despite passing source,
qualification, and outcome-variation checks.

## Pool progression

| Metric | B3-B6 preliminary | B3-B7 final |
| --- | ---: | ---: |
| complete trajectories | 100 | 125 |
| confirmed decisions | 996 | 1,253 |
| Current nonzero trajectories | 62 | 87 |
| Current zero-weight trajectories | 38 | 38 |
| Current ESS | 48.2615 | 66.3016 |
| Current ESS fraction | 0.4826 | 0.5304 |
| Current maximum normalized weight | 0.0548 | 0.0445 |
| victories | 1 | 1 |
| overlap blockers | ESS and ESS fraction | none |

The final qualification pool has card-reward support of 1,007 baseline and 45
alternative decisions, plus shop support of 196 baseline and 5 alternative
decisions. The single victory is sufficient for outcome-class variation but is
not sufficient to estimate a reliable policy effect by itself.

## Independent replay

The independent verifier reparsed the canonical JSONL without importing the
main OPE readiness implementation. It checked source hashes, exact rational
probabilities and trajectory products, support normalization, ESS,
concentration, outcome variation, overlap blockers, and closed downstream
gates.

| Pool and target | Checks | Result |
| --- | ---: | --- |
| B3-B6 behavior identity | 94,506 | pass |
| B3-B6 deterministic Current | 93,506 | pass |
| B3-B7 behavior identity | 118,857 | pass |
| B3-B7 deterministic Current | 117,600 | pass |
| total | 424,469 | pass |

The behavior-identity target reconstructs 125 nonzero trajectories with ESS
125 and maximum normalized weight 0.008. It is an arithmetic self-check, not a
candidate-policy effectiveness claim.

## Isolation and verification

Each batch froze a launch baseline, pre-isolation fingerprint, exact post-run
allowlist, post-isolation fingerprint, source manifest, canonical sample, and
qualification artifact. All batch provenance and isolation checks passed, and
the fixed source commit remained unchanged during collection.

| Check | Result |
| --- | --- |
| focused evidence, readiness, and verifier tests | 94 passed in 5.46s |
| full Windows pytest suite | 2,572 passed in 76.96s |
| OpenSpec strict validation | 34 passed, 0 failed |
| JSON, JSONL, and run-record parse audit | 73 JSON files, 6,008 JSONL rows, and 125 runs parsed |
| independent artifact replay | 424,469 checks passed |
| staged byte identity | 233 paths checked, 0 index mismatches |
| final source and readiness assertions | passed |
| Git whitespace check | passed with frozen CRLF treated as line endings |
| live gameplay/training process check | 0 matching processes |

## Remaining blockers

- No estimator or uncertainty method has been specified or implemented.
- No trajectory-level estimator calibration or synthetic ground-truth test
  suite exists.
- One observed victory gives outcome variation, not a stable value estimate.
- No candidate-policy acceptance criteria or repeated-split stability gate has
  been approved.
- Formal reward, training, causal uplift, and live-promotion gates remain
  closed by construction.

## Next gate

Do not start formal non-combat RL training from this overlap result. The next
bounded stage should be a separate OpenSpec estimator-validation change. It
must pre-specify the estimator, uncertainty method, trajectory-level
split/replay protocol, identity and synthetic calibration tests, and
policy-comparison acceptance criteria. Only after those checks pass should a
small offline policy-learning pilot be considered; live promotion remains a
separate gate.
