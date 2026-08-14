# Card uplift live intervention canary R2

## Result

The three-game fresh canary completed after bounding candidate inference to two
PyTorch threads. All operational gates passed:

- 40 decision rows, including 37 complete ordinary card rewards.
- 26 candidate substitutions and 11 agreements.
- 3 generated-combat-card fallbacks, all outside the supported boundary.
- 0 runtime errors and 0 invalid actions.
- Mean / median / P95 / maximum latency: 66.44 / 62.17 / 111.81 / 147.52 ms.
- The pre-canary CommunicationMod configuration was restored byte-for-byte.

The prior R1 maximum was 203.48 ms. R2 remained below the unchanged 200 ms
gate without changing the model or threshold.

## Runs

| Run | Floor | Victory | Killed by | Substitutions |
| --- | ---: | :---: | --- | ---: |
| `1786700135.run` | 16 | false | The Guardian | 6 |
| `1786700307.run` | 38 | false | 4 Shapes | 13 |
| `1786700508.run` | 33 | false | Collector | 7 |

## Decision

The live adapter is operationally ready for a larger bounded candidate
evaluation. These three losses are not a policy-quality verdict, but the second
and third runs reached Acts 3 and 2 while exercising the candidate 20 times.
No promotion or production checkpoint mutation is authorized by this report.
