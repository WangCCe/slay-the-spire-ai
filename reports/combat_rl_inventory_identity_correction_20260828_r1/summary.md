# Combat RL Inventory Identity Correction

- Verdict: `inventory_identity_correction_complete`
- Joined transitions: 7685
- Potion occupied occurrences recovered: 1904
- Relic occupied occurrences recovered: 1478
- Unresolved potion occurrences: 0
- Unresolved relic occurrences: 0
- Historical replay checkpoints were not modified.
- This corrects source-encoder attribution only; residual LightSTS differences remain descriptive.

## Floor Strata

| Stratum | N | Potion original | Potion corrected | Potion simulator | Relic original | Relic corrected | Relic simulator |
|---|---:|---:|---:|---:|---:|---:|---:|
| floor_00_05 | 1197 | 0.148 | 0.309 | 0.347 | 1.126 | 1.135 | 1.059 |
| floor_06_10 | 774 | 0.222 | 0.624 | 0.789 | 1.632 | 1.703 | 1.675 |
| floor_11_17 | 2873 | 0.152 | 0.481 | 1.038 | 2.575 | 2.812 | 3.179 |
| floor_18_22 | 1418 | 0.033 | 0.169 | 0.287 | 3.764 | 3.956 | 4.554 |
| floor_23_27 | 433 | 0.005 | 0.115 | 0.381 | 4.730 | 4.850 | 5.648 |
| floor_28_34 | 859 | 0.033 | 0.283 | 0.529 | 6.267 | 6.738 | 7.375 |
| floor_35_39 | 36 | 0.000 | 0.000 | 0.053 | 8.000 | 8.000 | 12.000 |
| floor_40_44 | 31 | 0.000 | 0.000 | n/a | 10.613 | 10.613 | n/a |
| floor_45_50 | 64 | 0.000 | 0.000 | n/a | 11.000 | 11.000 | n/a |

## Interpretation

The initial calibration's largest inventory mismatch mixed real replay encoder undercount with simulator progression differences. Display-name fallback explains every occupied alias observed in the joined traces; any remaining cross-source delta must be evaluated after this correction and is not by itself evidence of a simulator mechanics bug.
