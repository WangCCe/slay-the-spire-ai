## Why

Three independent stratified LightSTS candidates improved aggregate and early
combat metrics but regressed at battle index 9, including a 256-seed held-out
run with 152 reachable late-battle profiles. The RL v2 observation describes
monster health, intent, damage, and generic powers but omits encounter identity,
so the learner cannot distinguish enemy-specific future dynamics that become
more important in later battles.

## What Changes

- Add an opt-in simulator-only encounter identity feature to the combat
  LightSTS training runner using a deterministic, source-bound encoding.
- Expand a simulator-only warm-start network with zero-initialized encounter
  columns while preserving the parent policy's pre-training Q values.
- Report the encoding, migration identity check, and held-out evidence needed
  to decide whether the added information improves battle index 9.
- Keep the default observation, production RL architecture, game runtime, and
  CommunicationMod path unchanged.

Success requires exact pre-training parent equivalence and a fresh held-out
simulator result that passes aggregate, early-combat, and late-combat
guardrails. The change grants no live-transfer authority. If equivalence or
late-combat guardrails fail, retain r4 and disable the opt-in feature.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Allow an opt-in encounter-identity
  observation extension with exact simulator-parent migration and explicit
  evidence reporting.

## Impact

The change is confined to
`analysis_scripts/combat_lightspeed_training_smoke.py`, its focused tests,
simulator-only checkpoints, and registered reports. It adds no dependency and
does not change `StateEncoderV2`, production checkpoint loading, gameplay, or
the LightSTS native module.
