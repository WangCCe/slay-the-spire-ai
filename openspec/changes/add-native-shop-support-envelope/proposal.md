## Why

Source-complete reconciliation against the installed game and tracked live
Courier evidence proved that the bound simulator corrupts Courier restocks and
Sozu/full-capacity potion transactions. A fail-closed boundary is required now
so those known-invalid transitions cannot enter compatibility or future RL
evidence while a separate simulator-mechanics repair remains pending.

## What Changes

- Fail every native shop decision explicitly when the player owns The Courier,
  before snapshots, candidates, baseline labels, or transitions can be used.
- Keep shop potions visible but omit `buy_potion` candidates when Sozu or full
  potion capacity means the simulator cannot obtain the potion.
- Preserve all non-potion candidates and supported A0 shop behavior.
- Add source-contract and bounded reused-seed regressions, then build a new
  provenance-bound API v3 successor without overwriting frozen modules.
- Publish blocker semantics and counts without running a fresh formal cohort.

Success means every known Courier shop state fails with the exact unsupported
reason, invalid potion transactions cannot be selected through the adapter,
supported reused-seed smoke remains deterministic, and focused plus commit-
gate verification passes.

Non-goals are correcting Courier replacement RNG, items, prices, egg effects,
or upstream shop mechanics; changing Current policy, bridge labels, purge
observation, reward, model, training, or live gameplay; and authorizing a third
formal native gate. Rollback removes the support checks, tests, successor
ignored build, and closeout while leaving external sources, frozen modules,
and consumed cohorts unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-adapter`: Require an explicit fail-closed support
  envelope for known-invalid native shop states and transactions.

## Impact

- `simulator_adapters/sts_lightspeed/noncombat_adapter.cpp`
- Native adapter source and integration tests
- A distinct ignored API v3 successor build and provenance closeout
- Read-only use of the bound `sts_lightspeed` checkout and existing development
  seeds `0..19`
- No Communication Mod, live configuration, gameplay policy, bridge, model,
  reward, OPE, formal cohort, training, loading, qualification, or promotion
  changes
