## Why

Both shop ranker experiments failed only because one deterministic untrained
model outscored the trained model on pairwise accuracy. A read-only 64-seed
audit found that fixed initialization at the 98.4th percentile while the trained
model beat 62 of 64 initializations, so a fresh preregistered distribution gate
is needed before deciding whether the trained model merits live shadowing.

## What Changes

- Load the exact committed epoch-4 state-conditioned shop model without fitting.
- Collect one fixed fresh shop development cohort from seeds `95428..95459`.
- Compare the model with Current and 32 fixed untrained initializations; require
  trained pairwise accuracy to exceed the untrained 75th percentile.
- Retain Current regret, correction, and non-inferiority checks.
- Publish a terminal fresh-evaluation verdict and canonical artifacts.

## Capabilities

### New Capabilities
- `noncombat-shop-robust-initialization-evaluation`: Fresh model evaluation against Current and a preregistered untrained initialization distribution.

### Modified Capabilities

None.

## Impact

Adds one offline evaluator and focused tests. It loads the bound model and native
simulator but performs no training, gameplay, CommunicationMod, production
checkpoint, protected seed, qualification, promotion, or live policy operation.
