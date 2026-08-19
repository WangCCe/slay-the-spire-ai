## Why

The guarded-control candidate passed bare-policy LightSTS gates but lost its first matched live floor gate; a symmetric deployment-guard counterfactual erased its simulator uplift, and trace review found repeated parent `Bash`/`Perfected Strike`/`Swift Strike` choices drifting to ordinary `Strike`. Existing objectives protect the parent only against EndTurn or through soft argmax imitation, so they do not preserve a positive card-to-card Q margin.

## What Changes

- Add an optional frozen-parent card-action ranking guard to RL v2 training, disabled by default.
- For replay rows with at least two legal card actions, preserve a clipped positive margin between the parent's best legal card action and its best legal card alternative.
- Bind guard weight, cap, eligibility, loss, and ranking violations in simulator reports and checkpoints.
- Run one bounded same-cohort objective ablation, then require material guard-aware LightSTS improvement before any fresh confirmation, packaging, or live gate.
- Success means finite positive eligibility, reduced card-action ranking violations, unchanged default behavior, and a candidate that beats both production r16 shadow and the prior guarded control under preregistered guard-aware metrics. Rollback is setting the new weight to `0.0` or reverting the isolated objective; no production checkpoint is changed.

## Capabilities

### New Capabilities

- `combat-lightspeed-parent-card-ranking-guard`: Defines the optional frozen-parent legal-card ranking margin objective and its evidence boundary.

### Modified Capabilities


## Impact

- Affects `spirecomm/ai/rl/v2/trainer.py`, the LightSTS training smoke CLI/report/checkpoint binding, and focused tests.
- Adds no dependency, action-space change, native adapter change, CommunicationMod behavior, or automatic production authority.
- The first experiment reuses an already observed development cohort only as an objective ablation and cannot qualify a candidate.
