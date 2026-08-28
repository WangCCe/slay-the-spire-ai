# Combat RL latent-gated correction fresh confirmation

- Verdict: `fresh_confirmation_passed_ready_for_candidate_mechanism_change`
- Fresh games: `10`
- Fresh replay transitions: `2159`
- Candidate-callable decision spans: `998`
- Direct / changed spans: `454 / 544`
- Optimizer updates during collection: `0`
- Parent identity: exact production r16

## Fresh holdout

| Metric | Result | Gate |
|---|---:|---:|
| Direct gate open | 0.1256 | <= 0.15 |
| Changed gate open | 0.7757 | >= 0.75 |
| Direct candidate agreement | 0.9405 | >= 0.85 |
| Changed raw correction agreement | 0.3989 | >= 0.35 |
| Changed gated candidate agreement | 0.3051 | >= 0.25 |
| Overall agreement uplift | +0.1393 | >= +0.10 |
| Positive-energy EndTurn delta | -415 | <= 0 |

All registered confirmation conditions passed. This authorizes a separate,
focused candidate-mechanism implementation change. It does not authorize
candidate packaging, gameplay evaluation, qualification, or promotion.
