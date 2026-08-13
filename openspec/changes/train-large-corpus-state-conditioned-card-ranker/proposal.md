## Why

The rare-card counterfactual corpus removed support gaps, but the global
card-ID residual still turned a correct `Impervious` decision into a
`Bludgeon` choice with `2.491228` regret. The next experiment must use the
existing state-conditioned card heads so card value can vary with observable
run state rather than applying one uplift per card ID.

## What Changes

- Merge the existing and rare-card compatible train rows into 773 source
  states, of which 542 contain unequal action returns across 347 seeds.
- Restore the frozen r7 entry checkpoint and train only its existing candidate
  card family head and conditional state-conditioned ranker with the existing
  margin-weighted pairwise loss.
- Use five seed-disjoint train-only folds, deterministic 64-row mini-batches,
  and fixed epoch checkpoints `{1, 2, 4, 8}` to select one training duration
  before reading development rows.
- Fit one final model on all informative train rows, persist/restore it, then
  evaluate the merged 190-state development partition exactly once with
  overall and rare-only regret/ranking/take-skip gates.
- Leave reserved audit seeds `92320..92383` untouched unless a separate later
  change is approved after this development gate.

Success means train-only crossfit and the one-shot development gate both reduce
mean regret and improve pairwise accuracy without increasing maximum regret,
decreasing unique-best accuracy, or increasing rare best-take-to-skip errors.
Failure leaves the r7 entry, residual shadow model, production checkpoints,
gameplay, and reserved audit schedule unchanged.

## Capabilities

### New Capabilities

- `noncombat-large-corpus-state-conditioned-card-ranking`: Train-only
  crossfit, final state-conditioned card-head fitting, and one-shot development
  evaluation on the merged counterfactual corpus.

### Modified Capabilities

None.

## Impact

This adds one source-only training runner and focused tests under
`analysis_scripts/` and `tests/`. It reuses the existing checkpoint, projected
state/candidate tensors, card optimizer, pairwise objective, corpus artifacts,
and model serialization. It does not load native code, run CommunicationMod,
or modify production policy state.
