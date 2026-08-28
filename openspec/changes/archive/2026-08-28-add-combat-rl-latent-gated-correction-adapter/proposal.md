## Why

The existing abstaining residual head failed because its gate could not separate direct from guard-changed decisions, while the subsequent LightSTS-pretrained parent-latent gate and legal-action correction POC passed on both an independent replay and a fresh 10-game production-r16 replay. The fresh confirmation improved overall executed-action agreement from `0.4549` to `0.5942`, retained `0.9405` direct agreement, reached `0.3051` changed agreement, and reduced positive-energy EndTurn selections by `415`, so the mechanism is ready to become a tested, serializable development adapter.

## What Changes

- Add a frozen-parent combat RL adapter that derives intervention features from the parent's inventory-aware latent representation, parent Q values, and legal-action mask.
- Add an abstaining gate and a separate legal-action correction head; a closed gate returns the exact parent action, and an open gate may select only a currently legal action.
- Add a versioned, development-only artifact contract with exact parent identity, configuration, correction parameters, and serialization round-trip checks.
- Add focused regressions for parent immutability, closed-gate parity, legal-action enforcement, deterministic artifact restoration, and malformed artifact rejection.
- Keep production r16 authoritative. Do not integrate the adapter into CommunicationMod, package a production candidate, start a live policy gate, or claim policy quality in this change.

## Capabilities

### New Capabilities
- `combat-rl-latent-gated-correction-adapter`: Frozen-parent latent intervention gating, legal-action correction, and development artifact serialization contracts.

### Modified Capabilities

None.

## Impact

- Affects combat RL v2 network-adapter code, experiment artifact helpers, and focused tests.
- Uses only existing PyTorch and RL v2 model dependencies.
- Consumes the committed fresh confirmation report at `reports/combat_rl_latent_gated_correction_confirmation_20260828_r1/report.json` as evidence, not as runtime input.
- Rollback is deletion or non-use of the development adapter; no production checkpoint, gameplay configuration, or agent routing changes are permitted.
