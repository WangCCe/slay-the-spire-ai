# Bottled-Auxiliary Frozen Batch 2 Pilot

Review status: `approved_duplicate_candidate_evidence`.

Independent read-only re-review verdict: `APPROVED_DUPLICATE_CANDIDATE_EVIDENCE`; Critical 0, Important 0, Minor 0.

## Support and configuration

- Source commit: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Dataset: 387 Bottled-only eligible high-confidence mapped rows across 14 trajectories; no Current targets.
- Split: 8 train / 2 validation / 4 test trajectories; groups are disjoint.
- Training: CPU, seed `0`, learning rate `1e-3`, maximum 50 epochs, patience 5; 28 epochs run.
- Support blocked: `false`; category blocks: none.

## Held-out metrics

| Split | Samples | Candidate legality | Model/reference top-1 | Frequency/reference top-1 | Mean cross-entropy | ECE |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 70 | 1.0 | 0.728571 | 0.685714 | 0.532315 | 0.062797 |
| Test | 129 | 1.0 | 0.744186 | 0.744186 | 0.483571 | 0.064340 |

## Artifacts

- Model SHA-256: `29AF1FA00CC952934A22C298E3E7E2A40F3EB3B80C79C15E3E3CA60D64EE4FFB`.
- Metrics SHA-256: `123F4FF16664815E12F5CA021E5B64BC1D2FCC02D9068E1EDEEBAB3C07C1A638`.
- Artifact manifest SHA-256: `AA1910AB914112E850872AF297EEC73DEAAB16972048C4DFAFCC529773CDB1DF`.
- Artifact-manifest hash closure: verified.

The model's test agreement equals the category-frequency reference. Bottled is an auxiliary reference label source, not reward or ground truth. This result does not establish outcome improvement, off-policy value, formal non-combat RL readiness, or live-policy promotion readiness; both readiness flags remain false.

## Review and isolation

The reviewer independently reproduced the 387-row dataset, 8/2/4 trajectory split, metrics within `1e-12`, candidate legality, and artifact hash closure. The current post-correction config and five-checkpoint inventory is unchanged from the correction pre-isolation snapshot across path, size, UTC mtime, and SHA-256. The earlier `APPROVED_FOR_PHASE_B` verdict and subsequent two accepted findings are retained as superseded history; the current verdict is `APPROVED_DUPLICATE_CANDIDATE_EVIDENCE`.

Final correction verification passed 101 focused tests in 15.09 seconds and 2,379 full-suite tests in 68.00 seconds. Strict validation passed for this change and all 32 OpenSpec items; `git diff --check` found no whitespace errors.

This remains a 14-trajectory, zero-victory auxiliary-label result. OPE is unsupported, formal non-combat RL remains blocked, and live promotion remains blocked.
