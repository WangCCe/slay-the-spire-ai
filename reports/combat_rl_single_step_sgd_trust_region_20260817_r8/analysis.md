# Second single-step SGD trust region r8

## Decision

The selected alpha-0.25 checkpoint is eligible for one fresh replay
confirmation only. It is not eligible for live evaluation or production use.

The r5 replay was untouched before this fixed experiment, but the registered
rule evaluated three interpolation scales on r5 and selected the smallest
passing scale. r5 is therefore consumed selection data, not an independent
confirmation cohort.

## Result

All three deterministic replicate labels produced identical results. The
promoted parent r5 one-step SmoothL1 was `4.218847`. Every registered scale
improved it while remaining inside the policy-drift limits:

| alpha | SmoothL1 | parent agreement | off-target disagreement | relative L2 |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 4.214702 | 0.998898 | 0.002063 | 0.0000011689 |
| 0.50 | 4.210607 | 0.997797 | 0.004126 | 0.0000023377 |
| 1.00 | 4.202564 | 0.995869 | 0.007736 | 0.0000046753 |

The fixed rule selected alpha `0.25`. The final candidate checkpoint has
SHA-256
`edf7d33124a3fbbc3abee6bae6c7b9654ea9a9191dcf151e5c0b000c71a4f454`.

## Interpretation

A second unpreconditioned TD step again transfers across cohorts without broad
policy drift. The effect remains intentionally small: only four r5 off-target
states changed action relative to the current parent. This is evidence that the
incremental SGD path remains stable, not yet evidence that the second update
improves live progression.

Collect one new zero-update parent-policy replay cohort, freeze this candidate,
and compare it once on that cohort. Do not change alpha, learning rate, seed,
or thresholds in response to the new replay.
