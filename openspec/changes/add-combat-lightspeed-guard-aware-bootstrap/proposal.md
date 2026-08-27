## Why

Fresh production-r16 LightSTS successors repeatedly reduce optimization losses yet fail held-out HP or reward gates because guarded replay collection stores the action executed by the deployment proxy while both one-step TD and frozen-parent n-step targets bootstrap through an unguarded Q-policy action. In the latest fresh cohort, 21,241 of 51,560 accepted transitions (41.2%) were guard replacements, so this target-policy mismatch is large enough to address before another fit.

## What Changes

- Add an opt-in frozen-parent guard-aware bootstrap policy for complete LightSTS trajectories while preserving raw legal `max Q` bootstrap as the default.
- Compute the deterministic frozen-parent deployment-guard action independently of epsilon exploration and retain enough trajectory provenance to align each nonterminal target with its next-state guarded action.
- Gather immutable parent Q at the registered guarded next action, validate action range and legality before replay insertion or fitting, and bind action-source, replacement, and Q-gap telemetry in simulator-only reports and checkpoints.
- Keep the implementation and first validation simulator-only. Success means focused tests prove deterministic alignment, frozen-parent identity, legal action gathering, backward compatibility, and evidence binding; a later fit requires a separate immutable registration.
- Non-goals: changing the production checkpoint, changing the live deployment guard, tuning reward weights or optimizer settings, starting Slay the Spire or CommunicationMod, fitting a candidate, or claiming policy quality.
- Rollback boundary: the existing raw-greedy bootstrap remains the default and removing the opt-in mode restores prior behavior without checkpoint migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-deployment-consistent-behavior`: Require deterministic frozen-parent guarded target-action provenance independent of the behavior exploration branch when guard-aware bootstrapping is selected.
- `combat-lightspeed-training-smoke`: Add opt-in guard-aware frozen-parent bootstrap values, validation, and simulator-only evidence binding for bounded n-step targets.

## Impact

- Affected code: `analysis_scripts/combat_lightspeed_training_smoke.py` and its focused tests.
- Affected contracts: LightSTS smoke CLI/config, in-memory trajectory metadata, report/checkpoint source bindings, and generated manifest schema versions.
- Unaffected systems: production RL checkpoints, CommunicationMod, live gameplay, the default one-step TD path, and the default raw-greedy frozen-parent n-step path.
