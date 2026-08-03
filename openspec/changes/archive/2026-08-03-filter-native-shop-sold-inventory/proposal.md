## Why

The source-complete shop audit proved that the API v3 adapter serializes sold
fixed-slot inventory with `price == -1`, while the live game and Communication
Mod remove those items from the visible shop lists. Any native trajectory that
buys an item and remains in the shop will therefore fail bridge hydration
before Current can make its next decision.

## What Changes

- Filter exactly `price == -1` card, relic, and potion entries from native shop
  snapshot arrays while retaining each visible item's original fixed `slot`.
- Preserve unaffordable positive-price items in snapshots even when they have
  no legal candidate, matching Communication Mod's state/choice separation.
- Preserve Courier replacement entries and their source slots.
- Fail snapshot generation on shop inventory prices below `-1` instead of
  treating arbitrary negatives as sold.
- Add source and bridge regressions for sparse visible slots, candidate mapping,
  sentinel filtering, positive-price preservation, and historical isolation.
- Build the corrected API v3 module into a new ignored directory and run only
  bounded reused development-smoke seeds. Do not overwrite the frozen module or
  run a fresh formal compatibility cohort in this change.

Success means the corrected module omits sold entries after a native purchase,
keeps legal action ids tied to original slots, and passes focused plus commit-
gate verification. Rollback removes the adapter filter, tests, new ignored
build, and source-only evidence; both consumed cohorts and the frozen module
remain unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-adapter`: Require Communication Mod-compatible visible
  shop inventory semantics for sold, unaffordable, and Courier-replaced slots.

## Impact

- `simulator_adapters/sts_lightspeed/noncombat_adapter.cpp`
- Adapter and bridge tests plus a source-only closeout report
- A new ignored out-of-tree API v3 module build with a distinct byte identity
- Read-only use of the local game jar, Communication Mod checkout, and
  `D:\CLionProjects\sts_lightspeed`
- No live gameplay configuration, Current shop scoring, reward, model,
  training, formal cohort, loading, qualification, or promotion changes
