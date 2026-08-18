# Stratified LightSTS replay replication decision

## Decision

The method did not replicate under the preregistered per-index guardrail. Retain r4, reject both stratified candidates for live use, and do not run another same-scale replication.

## Replay evidence

| Battle index | Source transitions | Prepared transitions | Duplicates |
|---:|---:|---:|---:|
| 0 | 3,952 | 5,187 | 1,235 |
| 3 | 4,489 | 5,187 | 698 |
| 6 | 5,187 | 5,187 | 0 |
| 9 | 3,222 | 5,187 | 1,965 |

All `16,850` source transitions were retained and all strata were equalized to `5,187`. Index 9 required `37.9%` duplicated rows, so equal representation did not provide equal unique-state diversity.

## Held-out result

- Reachable matched profiles: `203/256`
- Mean reward delta: `+1.1037805689`
- Mean player HP delta: `+0.7192118227`
- Candidate-only victories: `7`
- R4-only victories: `3`

| Battle index | Reward delta | HP delta | Candidate-only wins | R4-only wins |
|---:|---:|---:|---:|---:|
| 0 | +0.4492 | +0.7188 | 0 | 0 |
| 3 | +3.2304 | +2.2258 | 3 | 0 |
| 6 | +1.7858 | +1.0208 | 3 | 1 |
| 9 | -3.1273 | -3.0000 | 1 | 2 |

The aggregate and early-combat criteria passed, but index 9 materially failed. Across the two independent runs, the procedure-level weighted index 9 reward delta is approximately `-1.562` over `65` reachable profiles and weighted HP delta is approximately `-0.508`; the late-stage failure cannot be dismissed as a single-cohort edge.

## Implication

Do not tune the oversampling ratio or anchor weight and do not transfer either candidate. A distinct next experiment may test greater unique later-battle trajectory diversity with substantially larger fresh training and evaluation cohorts while keeping the established recipe fixed. That is a new scale/diversity question, not another replication of this change.

