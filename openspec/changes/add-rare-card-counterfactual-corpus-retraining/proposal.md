## Why

The live card-uplift shadow cohort produced 20 take-to-skip disagreements and
recommended skipping `Immolate`, while the current training corpus contains no
`Immolate` rows and very little Ironclad rare-card support. The existing
first-two-card-rewards-per-seed collector is therefore not sufficient evidence
for a live intervention canary.

## What Changes

- Add a bounded simulator collector that advances every root trajectory but
  branches only at ordinary card rewards containing one of the 16 Ironclad rare
  cards, with at most two collected states per seed.
- Reserve disjoint train seeds `92000..92255`, development seeds
  `92256..92319`, and untouched audit seeds `92320..92383`.
- Combine the targeted rows with the existing large corpus, retain the frozen
  card-policy entry model, retrain its card-uplift residual, and report rare-card coverage plus
  skip/take diagnostics on development data.
- Require a separate fresh simulator/shadow evaluation before any action
  authority; this change does not run gameplay, promote a policy, or modify a
  production checkpoint.

Success means the collected train/development datasets contain all 16 target
rare-card IDs with no cross-partition source-state overlap, the retrained model
passes finite/canonical artifact checks, and development diagnostics no longer
show unsupported rare-card actions. Failure, timeout, binding drift, or
insufficient coverage leaves the current live shadow model and production
policy unchanged.

## Capabilities

### New Capabilities

- `noncombat-rare-card-counterfactual-corpus-retraining`: Bounded rare-card
  counterfactual collection, corpus merge, retraining, and development-only
  readiness reporting.

### Modified Capabilities

None.

## Impact

This adds one focused analysis collector/runner, a retraining entry point, and
focused tests under `analysis_scripts/` and `tests/`. It reuses the registered
`sts_lightspeed` adapter, existing counterfactual return contract, and current
card-uplift training code. Production gameplay, CommunicationMod, and existing
checkpoint files remain isolated.
