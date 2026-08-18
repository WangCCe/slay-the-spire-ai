## Why

The first LightSTS later-battle runs compared each trained candidate with a different random initialization, so their large gains do not establish whether continued training improves the current strongest frozen simulator candidate. The latest frozen comparison leaves the r4 and r6 candidates effectively tied, making a bound warm-start experiment the shortest path to an interpretable training result.

## What Changes

- Allow the bounded LightSTS training runner to load an explicitly supplied simulator-only smoke checkpoint as its initial online and target policy.
- Bind the input checkpoint path, file hash, checkpoint kind, and parameter hash in the report and successor checkpoint.
- Evaluate the unchanged loaded policy as control and the post-training policy as candidate on the same held-out profiles.
- Reject production-compatible or structurally incompatible checkpoints before collecting transitions.
- Run one fixed-budget mixed-battle experiment from the r4 candidate; success means complete finite training plus a directly interpretable held-out candidate-versus-r4 result. This does not authorize live transfer or promotion.
- Roll back by omitting the optional input checkpoint, which preserves the existing seeded fresh-initialization behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Add an optional, source-bound simulator-only warm-start mode with frozen-parent control evaluation.

## Impact

- `analysis_scripts/combat_lightspeed_training_smoke.py`
- focused training-smoke regressions and report/checkpoint schemas
- one bounded CPU-only LightSTS experiment and its immutable report artifacts
- no CommunicationMod, game process, production checkpoint, or production configuration changes
