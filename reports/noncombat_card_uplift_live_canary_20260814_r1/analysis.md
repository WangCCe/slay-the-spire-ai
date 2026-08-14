# Card uplift live intervention canary

## Result

The bounded live canary completed exactly three fresh Ironclad games and made
22 real card-reward substitutions without a runtime error or invalid action.
It failed the preregistered operational gate because one decision took
203.4806 ms, above the fixed 200 ms maximum.

- Decision rows: 32
- Complete eligible rows: 31
- Candidate agreements: 9
- Candidate substitutions: 22
- Ineligible Current fallbacks: 1
- Runtime errors: 0
- Invalid actions or CommunicationMod command errors: 0
- Mean latency: 65.8777 ms
- Median latency: 57.0018 ms
- P95 latency: 162.5598 ms
- Maximum latency: 203.4806 ms

## Runs

| Run | Floor | Victory | Killed by | Substitutions |
| --- | ---: | :---: | --- | ---: |
| `1786666842.run` | 16 | false | The Guardian | 9 |
| `1786666940.run` | 16 | false | Slime Boss | 5 |
| `1786667095.run` | 27 | false | Slavers | 8 |

The floors and losses are descriptive only. Three games do not support a
causal or policy-quality comparison.

## Decision

Operational verdict: **no-go**. Do not promote, qualify, replay the cohort,
raise the latency threshold, or treat the 22 substitutions as a quality claim.
The saved pre-canary CommunicationMod configuration was restored byte-for-byte;
Current remains the default policy and no production checkpoint was modified.

The canary nevertheless answers the main feasibility question: the frozen
uplift model can map and execute live card-reward actions with strict fallback.
Any future deployment work must be separately registered and address startup
latency outside this consumed canary.
