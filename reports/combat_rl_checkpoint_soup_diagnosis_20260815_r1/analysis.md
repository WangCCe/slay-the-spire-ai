# Combat RL checkpoint soup diagnosis

## Decision

**PASS for a fresh matched live gate; not approved for promotion.** The equal-weight mean of the R1, R2, and R3 online and target weights was the best eligible soup on all three retained replay panels. It should be materialized as a weights-only checkpoint and compared with the exact frozen entry checkpoint on fresh seeds.

## Result

| Candidate | Mean normalized Smooth-L1 | Worst panel | Minimum median-margin ratio | Relative L2 from entry |
| --- | ---: | ---: | ---: | ---: |
| R1 | 0.9176 | 0.9308 | 1.1057 | 0.01455 |
| R2 | 0.9159 | 0.9265 | 1.0740 | 0.01280 |
| R3 | 0.9191 | 0.9298 | 0.9835 | 0.01302 |
| Entry to mean, 25% | 0.9713 | 0.9720 | 0.9495 | 0.00276 |
| Entry to mean, 50% | 0.9461 | 0.9474 | 0.9777 | 0.00553 |
| Entry to mean, 75% | 0.9252 | 0.9270 | 0.9951 | 0.00829 |
| **R1/R2/R3 mean** | **0.9101** | **0.9113** | **0.9917** | **0.01105** |

The selected mean reduced Smooth-L1 loss from `5.1156` to `4.6618` on R1 replay, `5.0104` to `4.5506` on R2 replay, and `5.0677` to `4.6148` on R3 replay. Its greedy action agreement with entry was `58.40%`, `59.16%`, and `57.40%` across the three panels.

All four soup candidates passed the preregistered diagnostic constraints: every panel beat entry loss, every panel retained at least 75% of entry's median action margin, and parameter drift remained below the largest individual-replicate drift. The equal-weight mean ranked first by mean normalized loss.

## Limits

These replay panels are distinct but not strict held-out data: each replicate contributed one replay it had trained on, and the soup was selected using all three. The result diagnoses a shared learned direction and reduced replicate-specific noise; it does not estimate live policy quality or authorize promotion.

## Provenance

- Analysis source commit: `6d067b9b63ff271c117a0cb8f4f7506e9a0f1ab2`
- Frozen entry SHA-256: `79afdd2290323646010f7715fb9a96922d2b9dc05baee271ca0a1042eac4f3d6`
- R1 SHA-256: `72bc4ac046ce933935e1ad46a11bccb25963933999eeafee97588c03e1aaebad`
- R2 SHA-256: `2968ba273e9cba92070dbf1b51159aa739c5f6e8c254c6b5999fe28af4a7d262`
- R3 SHA-256: `f1a606a0eb7c85d8d74bea79b11baf49ab552f58bcb4dd7f2459e1b43b2cf62a`

## Next step

Build a schema-2 `checkpoint_kind="weights"` checkpoint containing only the selected averaged online weights and immutable metadata. Give it one fresh, exact-entry, zero-epsilon matched gate; do not reuse R1-R3 gate seeds and do not continue training from the averaged checkpoint before that gate.
