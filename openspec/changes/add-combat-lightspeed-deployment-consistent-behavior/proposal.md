## Why

Fresh guard-aware evidence rejects both card-only and top-action margin fixes: production r16 still leads reward and victories. The remaining mismatch is upstream because LightSTS replay is collected from uniform non-EndTurn actions while production executes a frozen policy plus guards, so TD training optimizes a different action distribution than deployment.

## What Changes

- Add an opt-in LightSTS replay behavior mode driven by the immutable warm-start parent and the registered deployment guard proxy.
- Execute the guarded parent action on most decisions and a deterministic bounded exploration action at a registered rate.
- Record parent, exploration, raw EndTurn, eligibility, and proxy replacement counts in corpus evidence.
- Preserve uniform behavior as the default and leave production gameplay untouched.
- Run one fresh-cohort experiment using complete-trajectory discounted returns; success requires material guard-aware reward, HP, and victory uplift over r16. Rollback is selecting the existing default behavior mode.

## Capabilities

### New Capabilities

- `combat-lightspeed-deployment-consistent-behavior`: Defines guarded frozen-parent replay collection, bounded exploration, evidence, and simulator-only authority.

### Modified Capabilities


## Impact

- Affects only the LightSTS training smoke collection/configuration path and focused tests.
- Reuses the existing native environment clone, frozen parent network, and deployment guard proxy; adds no dependency or production import.
- No packaging, gameplay, or promotion is authorized.
