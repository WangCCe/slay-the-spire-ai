## Why

The first provenance-aware full-network successor improved replay fit and override-label agreement but changed 60.98% of validation decisions, including 25.97% of direct parent decisions, so it correctly failed its aggregate drift gate. A new corpus and a provenance-stratified gate are needed to learn outer-guard behavior without treating desirable override changes and unsafe direct-policy changes as the same signal.

## What Changes

- Register and collect a new ten-game, zero-update production-r16 replay only after the new recipe and gates are frozen.
- Fit exactly one successor on the new corpus with the same objective and learning rate but a reduced fixed budget of 64 optimizer updates.
- Replace aggregate maximum-drift eligibility with separate requirements: direct validation drift at most 10%, override executed-label agreement uplift at least 10 percentage points, overall material drift at least 5%, improved validation TD fit, and no positive-energy End Turn increase above two.
- Preserve the candidate and report on failure, but prohibit same-corpus reruns, recipe changes, fresh holdout, gameplay, qualification, or promotion unless every fixed condition passes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-provenance-aware-successor`: Require recipe-before-corpus collection and provenance-stratified development eligibility for later successor attempts.

## Impact

- Adds one fresh replay registration and evidence directory, then updates the offline successor orchestration and focused tests.
- Uses production r16 only for zero-update collection; it does not modify or train the production checkpoint.
- May start Slay the Spire for the registered collection, restoring CommunicationMod configuration and stopping game processes afterward.
- Success permits only a separately registered fresh holdout against the frozen candidate hash. Failure keeps r16 authoritative and ends this recipe without same-corpus tuning.
