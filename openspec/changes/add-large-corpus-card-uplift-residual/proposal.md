## Why

The expanded corpus provides 497 train and 126 development card states with
similar informative-state density and return scales, removing the main support
constraint behind the failed 61-state uplift experiment. A fixed low-capacity
residual can now test whether counterfactual return supervision improves the
frozen r7 card policy without another native collection or broad architecture
search.

## What Changes

- Bind the expanded canonical train/development datasets and frozen r7 entry
  checkpoint as source-only inputs.
- Select one hierarchical card-uplift residual from the existing fixed
  shrinkage/strength grid using seed-level cross-validation on train only.
- Fit the selected residual once on full train, persist it, and evaluate the
  frozen candidate once on development.
- Treat unseen development card ids with the train-only global uplift prior.
- Publish regret, pairwise, unique-best, action-flip, unseen-card, and fold
  diagnostics; no audit, gameplay, promotion, or production loading occurs.

## Capabilities

### New Capabilities

- `noncombat-large-corpus-card-uplift-residual`: Defines train-only model
  selection, fixed residual fitting, one-shot development evaluation, artifact
  publication, and the downstream audit gate.

### Modified Capabilities

None.

## Impact

- Adds one source-only analysis runner and focused tests.
- Reuses the existing frozen-entry scorer and hierarchical card-uplift model;
  no native simulator or new dependency is required.
- Success authorizes only a separate reserved-audit proposal. Failure retains
  the r7/native policy and ends this residual family on the expanded corpus.
