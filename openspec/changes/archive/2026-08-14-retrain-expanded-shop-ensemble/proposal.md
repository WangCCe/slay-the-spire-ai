## Why

The original 112-source shop corpus was insufficient for either low-capacity or state-conditioned OOF improvement. A verified 384-source independent expansion now raises support to 496 unique states, so the frozen cross-validated ensemble deserves one data-scale retraining attempt without changing its architecture or gate.

## What Changes

- Bind the original four datasets and the expansion dataset by exact hashes, requiring 496 unique compatible sources.
- Reuse the existing five-fold, five-initialization Current-relative ensemble with the same epochs and vote quorums.
- Persist an OOF no-go without accessing fresh seeds when no configuration improves Current under all gates.
- If OOF succeeds, freeze the ensemble and run exactly one 32-source evaluation on reserved seeds `95492..95555`.
- Do not alter architecture, objective, thresholds, seed schedules, gameplay, CommunicationMod, or production checkpoints.

Success requires OOF eligibility first, then fresh gated mean-regret improvement, maximum-regret noninferiority, at least one correction, and no more worsened than corrected decisions. Rollback remains Current; the trained ensemble receives at most permission for a separate live-shadow proposal.

## Capabilities

### New Capabilities

- `noncombat-expanded-shop-ensemble-retraining`: Defines exact 496-source retraining, unchanged OOF selection, frozen model publication, and one reserved fresh gate.

### Modified Capabilities

None.

## Impact

The change adds a thin wrapper around the existing tested cross-validation runner, three focused wrapper regressions, and bounded training/evaluation artifacts. No live policy surface changes.
