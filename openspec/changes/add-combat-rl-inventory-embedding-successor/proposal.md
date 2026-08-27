## Why

The corrected r2 production-r16 replay now contains 3,633 training-eligible
transitions with exact potion and relic identities, but the promoted network was
trained while many of those identities encoded as zero. Repeating the prior
whole-network half-step recipe would mostly create another near-neighbor model
instead of testing whether the newly observable inventory signal is useful.

## What Changes

- Add an offline trainer that updates only nonzero potion and relic embedding
  rows while keeping every other production-r16 tensor and both zero rows exact.
- Use deterministic combat-group development splits and stored one-step
  successors so the sanitized replay is not reinterpreted as a contiguous
  full-return trajectory after its exact boundary exclusion.
- Publish a frozen development candidate plus training, parameter-isolation,
  action-drift, and inventory-stratified metrics.
- Require a material but bounded policy difference before spending a separate
  fresh real-game holdout; the r2 corpus itself grants no promotion authority.

Success means finite training, lower development one-step loss, exact
non-inventory parameter preservation, and a measurable inventory-conditioned
action change that remains within the fixed overall drift and End Turn guards.
The live evidence motivating the change is the fresh r2 collection's exact
inventory join, zero optimizer updates, and one excluded cross-floor transition.

Non-goals are changing the production encoder again, mutating r16 or the r2 raw
checkpoint, tuning against a fresh holdout, online training, or promoting a
candidate from development evidence alone. Rollback is deletion of the new
offline script, tests, change artifacts, and isolated report directory.

## Capabilities

### New Capabilities

- `combat-rl-inventory-embedding-successor`: Deterministic, isolated training
  and assessment of potion/relic embedding-only successors from corrected real
  replay.

### Modified Capabilities

None.

## Impact

The change adds one analysis script, focused tests, an isolated training report,
and OpenSpec artifacts. It does not change CommunicationMod configuration,
production checkpoint discovery, gameplay behavior, or runtime dependencies.
