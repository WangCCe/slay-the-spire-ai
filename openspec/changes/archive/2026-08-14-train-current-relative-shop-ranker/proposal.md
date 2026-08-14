## Why

The raw shop ranker learned above-random pairwise structure but worsened Current
on a fresh cohort, and its score margin did not separate corrections from harms.
A train-only POC showed that optimizing each candidate directly against the
Current action can produce 4 tune corrections, 0 harms, and lower regret.

## What Changes

- Bind the committed 64-source state-conditioned shop train dataset.
- Train a ranker with weighted Current-relative pairwise loss.
- Select epoch and direct score-margin threshold only on the existing internal
  fit/tune split, requiring zero tune harms and nonzero improvement.
- Keep the selected fit-only model calibrated and evaluate it once on fresh
  seeds `95460..95491`.
- Publish model, selection, fresh outcomes, verdict, and canonical identities.

## Capabilities

### New Capabilities
- `noncombat-current-relative-shop-ranking`: Current-relative shop objective, conservative train-only override selection, and one-shot fresh evaluation.

### Modified Capabilities

None.

## Impact

Adds one offline CPU trainer/evaluator and focused tests. It reads one committed
training dataset and loads the registered native simulator for fresh evaluation,
but does not access previous development/fresh datasets, production checkpoints,
protected seed inventories, gameplay, CommunicationMod, or live policy state.
