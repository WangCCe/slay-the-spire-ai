## Why

Warm-start LightSTS training repeatedly improves aggregate reward and victories but changes greedy behavior enough to regress HP or individual battle strata, and parameter interpolation did not produce a monotonic conservative candidate. The existing masked parent-policy objective can constrain legal-action ordering during training directly, which is the next evidence-backed attempt to reduce this forgetting.

## What Changes

- Allow warm-start LightSTS training to enable the existing frozen parent-policy cross-entropy objective at an explicitly declared non-negative weight.
- Require a bound warm-start parent for every positive weight and freeze that exact loaded state as the anchor.
- Record separate total, TD, and parent-policy losses plus the configured weight and frozen-anchor identity.
- Preserve zero-weight fresh and warm-start behavior.
- Run one fixed `weight=1.0` mixed-battle training experiment on new train/evaluation seeds; do not sweep the weight.
- Success means finite non-zero anchor evidence and held-out reward improvement without aggregate HP, victory, early-combat, or material per-index regression. Failure retains r4 and disables the optional objective by default.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Add optional frozen parent-action preservation for simulator-only warm-start training and separate objective metrics.

## Impact

- LightSTS training runner configuration, report schema, and focused tests
- one bounded CPU-only simulator training/evaluation report
- no game process, CommunicationMod, production checkpoint, or default training behavior changes
