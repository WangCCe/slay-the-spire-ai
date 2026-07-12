# Current-Imitation Frozen Batch 2 Pilot

Review status: `approved_duplicate_candidate_evidence`.

Independent read-only re-review verdict: `APPROVED_DUPLICATE_CANDIDATE_EVIDENCE`; Critical 0, Important 0, Minor 0.

## Support and configuration

- Source commit: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Dataset: 470 Current-only eligible rows across 14 trajectories; no Bottled targets.
- Split: 8 train / 2 validation / 4 test trajectories; groups are disjoint.
- Training: CPU, seed `0`, learning rate `1e-3`, maximum 50 epochs, patience 5; 41 epochs run.
- Support blocked: `false`; category blocks: none.

## Held-out metrics

| Split | Samples | Candidate legality | Model/reference top-1 | Frequency/reference top-1 | Mean cross-entropy | ECE |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 84 | 1.0 | 0.785714 | 0.654762 | 0.421083 | 0.079940 |
| Test | 157 | 1.0 | 0.777070 | 0.694268 | 0.498015 | 0.083893 |

## Artifacts

- Model SHA-256: `2E99CB9BC0F152364A6179C09ECC41265BFA4A90F059FB13373BB7F202938509`.
- Metrics SHA-256: `AF316B9B7723301BF611206019F451537B7EE26BB75759B4EBE27CA04423C6BB`.
- Artifact manifest SHA-256: `A42F3BFA7F602804329C36051AC95CE4D340995CDFB8F8C0B1517BAF86E4AC23`.
- Artifact-manifest hash closure: verified.

This result measures agreement with the frozen Current behavior labels. It does not establish outcome improvement, off-policy value, formal non-combat RL readiness, or live-policy promotion readiness; both readiness flags remain false.

## Review and isolation

The reviewer independently reproduced the 470-row dataset, 8/2/4 trajectory split, metrics within `1e-12`, candidate legality, and artifact hash closure. The current post-correction config and five-checkpoint inventory is unchanged from the correction pre-isolation snapshot across path, size, UTC mtime, and SHA-256. The earlier `APPROVED_FOR_PHASE_B` verdict and subsequent two accepted findings are retained as superseded history; the current verdict is `APPROVED_DUPLICATE_CANDIDATE_EVIDENCE`.

Final correction verification passed 101 focused tests in 15.09 seconds and 2,379 full-suite tests in 68.00 seconds. Strict validation passed for this change and all 32 OpenSpec items; `git diff --check` found no whitespace errors.

This remains a 14-trajectory, zero-victory supervised imitation result. OPE is unsupported, formal non-combat RL remains blocked, and live promotion remains blocked.
