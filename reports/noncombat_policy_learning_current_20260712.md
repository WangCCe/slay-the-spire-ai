# Current-Imitation Frozen Batch 2 Pilot

Status: bounded supervised training succeeded; independent raw-evidence review is pending.

## Support and configuration

- Source commit: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Dataset: 470 Current-only eligible rows across 14 trajectories; no Bottled targets.
- Split: 8 train / 2 validation / 4 test trajectories; groups are disjoint.
- Training: CPU, seed `0`, learning rate `1e-3`, maximum 50 epochs, patience 5; 43 epochs run.
- Support blocked: `false`; category blocks: none.

## Held-out metrics

| Split | Samples | Candidate legality | Model/reference top-1 | Frequency/reference top-1 | Mean cross-entropy | ECE |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 84 | 1.0 | 0.785714 | 0.654762 | 0.423915 | 0.059279 |
| Test | 157 | 1.0 | 0.770701 | 0.694268 | 0.506876 | 0.078990 |

## Artifacts

- Model SHA-256: `342FD7020D821F7A5F309FDDCCFAAA637E434B747316F21B8DAE571837D1CD83`.
- Metrics SHA-256: `8ED9AD657B86BBE40113BCE529BE8184FCD7AFB0923390512E27D48DF7976220`.
- Artifact manifest SHA-256: `E082B49CBA48F27C63F5362068CD8CA61F4772415A6B5F2D0A6271BED66A1598`.
- Artifact-manifest hash closure: verified.

This result measures agreement with the frozen Current behavior labels. It does not establish outcome improvement, off-policy value, formal non-combat RL readiness, or live-policy promotion readiness; both readiness flags remain false.

## Phase B verification

Raw evidence is `APPROVED_FOR_PHASE_B` with no Critical or Important findings after the accepted report correction. Post-isolation config and checkpoint path/size/UTC-mtime/SHA-256 evidence is unchanged. Focused pytest passed 97 tests in 17.82 seconds; the full suite passed 2,375 tests in 74.87 seconds; strict OpenSpec validation passed for the change and all 32 items; `git diff --check` reported no whitespace errors.

This remains a 14-trajectory, zero-victory supervised imitation result. OPE is unsupported, formal non-combat RL remains blocked, and live promotion remains blocked.
