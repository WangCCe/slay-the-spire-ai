## Why

The frozen card-uplift candidate passed a 64-pair fresh simulator gate and the
repaired three-game live canary completed 26 legal substitutions with zero
errors and maximum latency of 147.52 ms. Three games are sufficient for an
operational canary but too small to estimate live victory and floor outcomes,
so the next useful evidence is a larger bounded candidate-owned cohort.

## What Changes

- Add an explicit live-evaluation configuration for 1 to 25 fresh Ironclad
  games using the already frozen entry checkpoint and uplift residual.
- Reuse the canary eligibility, unique action mapping, Current fallback,
  two-thread inference bound, canonical decision rows, and production
  isolation behavior.
- Publish run-level victory, floor, death, intervention, error, and latency
  evidence; success requires at least one real victory and operational safety.
- Keep training, exploration, promotion, production checkpoint mutation, and
  CommunicationMod configuration ownership out of scope.
- Restore the pre-evaluation CommunicationMod configuration exactly; Current
  remains the rollback before and after the bounded cohort.

## Capabilities

### New Capabilities

- `noncombat-card-uplift-live-evaluation`: Source-bound, bounded live candidate
  evaluation and its outcome, safety, latency, and rollback evidence.

### Modified Capabilities

None.

## Impact

The change touches `spirecomm/ai/card_uplift_shadow.py`, `main.py`,
`scripts/run_training_batch.py`, focused tests, and a new report/configuration
family. It loads only the existing frozen card-uplift artifacts and does not
change the default gameplay command or production checkpoints.
