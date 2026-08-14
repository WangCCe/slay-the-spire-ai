# Matched-Seed Current Control R1

## Result

The frozen card-uplift candidate reached 184 total floors (mean 18.4) and Current reached 168 (mean 16.8) on the same ordered list of 10 game seeds. Neither arm won. Five seeds had the same terminal floor and death reason. The candidate's descriptive floor delta was +16 total and +1.6 mean.

This result does not establish candidate benefit. Both `--eval` batches used the default `epsilon=0.05`, so combat actions retained independent exploration. On seed `-1724633684991443347`, the candidate made zero card-reward substitutions and selected exactly the same three cards through floor 7, yet it died to Gremlin Nob on floor 8 while Current reached the Guardian on floor 16. Same-seed runs are therefore not deterministic pairs under this configuration.

## Decision

Do not promote the card-uplift candidate, but do not calibrate or reject it based on the live skip rate either. Its descriptive result was not worse than Current, while both arms remained at zero victories. Keep the candidate frozen and move the next substantial training budget to the shared combat policy.

Any future same-seed live card-policy comparison must explicitly set `--epsilon 0`. Even then, the report must verify deterministic agreement on a no-substitution control before treating pair deltas as policy evidence.

## Pair Summary

| Seed | Candidate | Current | Delta | Candidate substitutions |
| --- | ---: | ---: | ---: | ---: |
| -94388446499042873 | 7 | 7 | 0 | 3 |
| 6262004061678501130 | 16 | 16 | 0 | 2 |
| -1496310916568639749 | 16 | 16 | 0 | 9 |
| 2426813284755187112 | 12 | 14 | -2 | 6 |
| -1622507530551266734 | 16 | 16 | 0 | 5 |
| -1724633684991443347 | 8 | 16 | -8 | 0 |
| 3069523256066178880 | 27 | 31 | -4 | 6 |
| -846151994304447793 | 16 | 16 | 0 | 8 |
| 400722356582234121 | 33 | 20 | +13 | 11 |
| 3565798865398725384 | 33 | 16 | +17 | 12 |
