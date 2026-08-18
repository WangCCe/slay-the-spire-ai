## Why

The post-settlement r4 LightSTS replication produced a strong held-out result, but every episode still began at the first combat with a starter-era state. Further optimizer runs on that narrow surface would measure repeated early-combat fitting rather than whether the policy can handle the elite, boss, deck, relic, and attrition states that matter to full runs.

## What Changes

- Allow the offline combat environment to reset to a zero-based battle index by letting the native deterministic baseline resolve all earlier out-of-combat states and combats.
- Bind the requested and reached battle index plus run-state coverage fields into snapshots, calibration reports, and training provenance.
- Fail explicitly when the native baseline loses, the run ends, or a bounded advancement step cannot reach the requested battle; never substitute a different combat.
- Add a bounded coverage calibration over registered `(seed, battle_index)` profiles before using later battles for training.
- Run one stratified simulator-only training replication only if calibration demonstrates materially broader encounter and progression coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-bridge`: Extend deterministic reset and calibration from the first combat to registered later-battle profiles while preserving production isolation.

## Impact

The change affects the native combat adapter constructor, the Python bridge and calibration/training configuration, focused tests, and source-only reports. It does not start Slay the Spire or CommunicationMod, alter production checkpoints, manually synthesize combat state, or claim LightSTS/game equivalence. Success requires deterministic profile replay, no silent fallback, coverage beyond starter-era first combats, and source-bound artifacts. Rollback is selecting the prior immutable adapter module and first-combat-only reports.
