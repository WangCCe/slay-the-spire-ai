# Bottled-Auxiliary Frozen Batch 2 Pilot

Status: bounded supervised training succeeded; independent raw-evidence review is pending.

## Support and configuration

- Source commit: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Dataset: 387 Bottled-only eligible high-confidence mapped rows across 14 trajectories; no Current targets.
- Split: 8 train / 2 validation / 4 test trajectories; groups are disjoint.
- Training: CPU, seed `0`, learning rate `1e-3`, maximum 50 epochs, patience 5; 28 epochs run.
- Support blocked: `false`; category blocks: none.

## Held-out metrics

| Split | Samples | Candidate legality | Model/reference top-1 | Frequency/reference top-1 | Mean cross-entropy | ECE |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 70 | 1.0 | 0.714286 | 0.685714 | 0.542585 | 0.102666 |
| Test | 129 | 1.0 | 0.736434 | 0.744186 | 0.500675 | 0.109579 |

## Artifacts

- Model SHA-256: `5D5A97A9B064CF54242007A952D39BAA62DFA77511302D05823491C6A748C36B`.
- Metrics SHA-256: `181B4091E01460CE40B11EBD3A5DE1A6CF511BA67662118FD9882DCF06010CC5`.
- Artifact manifest SHA-256: `B998097F5A9E301050406816034DDE5905FA1CCB80A2649E485BD4435EE6EC8E`.
- Artifact-manifest hash closure: verified.

The model's test agreement is slightly below the category-frequency reference. Bottled is an auxiliary reference label source, not reward or ground truth. This result does not establish outcome improvement, off-policy value, formal non-combat RL readiness, or live-policy promotion readiness; both readiness flags remain false.

## Phase B verification

Raw evidence is `APPROVED_FOR_PHASE_B` with no Critical or Important findings after the accepted report correction. Post-isolation config and checkpoint path/size/UTC-mtime/SHA-256 evidence is unchanged. Focused pytest passed 97 tests in 17.82 seconds; the full suite passed 2,375 tests in 74.87 seconds; strict OpenSpec validation passed for the change and all 32 items; `git diff --check` reported no whitespace errors.

This remains a 14-trajectory, zero-victory auxiliary-label result. OPE is unsupported, formal non-combat RL remains blocked, and live promotion remains blocked.
