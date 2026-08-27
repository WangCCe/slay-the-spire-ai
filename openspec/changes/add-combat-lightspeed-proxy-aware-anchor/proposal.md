## Why

Deployment-consistent LightSTS replay currently stores the guard-replaced card action while parent-anchor cross entropy labels the same row with the frozen parent's raw `EndTurn`. Removing the anchor materially regressed reward and victories, so the next structural step is to preserve conservative anchoring while making confirmed guard replacements label-consistent.

## What Changes

- Retain an optional per-transition anchor override through LightSTS replay preparation, the RL v2 replay buffer, sampling, and checkpoint round trips.
- Mark the override only when the registered deployment guard actually replaces the frozen parent's raw action; parent, epsilon-exploration, uniform, and forced-EndTurn rows remain frozen-parent anchored.
- Make parent-policy cross entropy use the stored executed action only for marked rows and the masked frozen-parent greedy action everywhere else.
- Report proxy-aware anchor eligibility and loss evidence, while preserving the existing all-false simulator authority and production-incompatible checkpoint contract.
- Preserve default behavior and legacy checkpoint compatibility when no override metadata is supplied.
- Success means focused regressions prove mixed-row labels, replay/checkpoint preservation, unchanged default anchoring, immutable parent parameters, and coherent runner evidence.
- Non-goals are encounter-identity architecture changes, reward or target changes, model fitting, gameplay, CommunicationMod, qualification, packaging, or promotion.
- Rollback is the opt-in metadata and label selection path; the default false/sentinel value leaves existing callers and checkpoints on the current raw-parent anchor behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-deployment-consistent-behavior`: Retain row-level guard-replacement provenance and bind proxy-aware anchor evidence for simulator-only replay.
- `combat-rl-parent-policy-anchor`: Allow an explicit per-transition executed-action override while preserving frozen-parent greedy labels by default.

## Impact

- `analysis_scripts/combat_lightspeed_training_smoke.py`: transition provenance, replay insertion, loss telemetry, report/checkpoint source binding, and CLI opt-in.
- `spirecomm/ai/rl/v2/replay_buffer.py`: backward-compatible optional transition metadata and serialization.
- `spirecomm/ai/rl/v2/trainer.py`: mixed-row parent anchor targets and telemetry.
- Focused LightSTS and RL v2 transition tests; no native module rebuild and no production configuration change.
