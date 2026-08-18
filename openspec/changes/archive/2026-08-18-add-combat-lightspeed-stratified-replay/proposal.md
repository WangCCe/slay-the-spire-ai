## Why

The fixed parent-action constraint was active and improved aggregate reward and victories, but index 9 still regressed while initialized training profiles fell from `256` at index 0 to `154` at index 9. The runner currently samples a single transition pool without an explicit battle-index representation contract, so one bounded stratified replay experiment is the next isolated test.

## What Changes

- Tag collected simulator transitions with their requested battle index and report source transition counts per stratum.
- Add an optional deterministic replay preparation mode that retains every source transition and oversamples smaller battle-index strata to the largest stratum count.
- Interleave balanced strata before insertion, bind the balance seed and duplication counts, and leave default replay unchanged.
- Run one new-seed experiment from r4 using the fixed parent-action weight `1.0`, the same optimizer budget, and battle-index-balanced replay.
- Success means complete finite training plus reward uplift without aggregate HP, victory, early-combat, or material per-index regression. Failure retains r4 and disables stratification by default.
- Rollback is omission of the optional flag; no production or live setting changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Add optional deterministic battle-index replay stratification and explicit source/prepared stratum metrics.

## Impact

- LightSTS replay transition metadata, training runner configuration/reporting, and focused tests
- one bounded CPU-only simulator training experiment
- no replay-buffer core, game process, CommunicationMod, production checkpoint, or default behavior changes
