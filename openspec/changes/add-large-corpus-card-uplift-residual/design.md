## Context

The original hierarchical card-uplift residual was selected on 46 exposed
states and then worsened mean regret on a 15-state audit. The new corpus has
497 train and 126 development states, 72% informative states in both
partitions, and only one development-only card id. The frozen r7 entry scorer,
counterfactual returns, and residual codec already exist and can be reused
without native loading.

## Goals / Non-Goals

**Goals:**

- Select residual shrinkage and strength using train seeds only.
- Fit and persist one low-capacity card-uplift model before development access.
- Evaluate the frozen candidate once on development with fixed gates.
- Preserve exact source, dataset, entry-checkpoint, and model lineage.

**Non-Goals:**

- Add state-conditioned neural layers, tune against development, or collect
  more native data.
- Access reserved audit seeds, modify production checkpoints, or claim policy
  quality.
- Retry with a different grid or gate after reading development results.

## Decisions

### Reuse the hierarchical card-uplift residual

For each take action, the target is its formal return minus the skip return.
The fit stores a global mean and a shrinkage-adjusted mean for each train card
id. A candidate score is the frozen r7 score plus the selected strength times
that uplift; skip receives zero residual. This model has roughly one scalar per
observed card and gives unseen cards the train-only global prior.

This is preferred over another neural ranker because the prior full ranker
overfit, the question is specifically whether additional support rescues the
existing residual family, and the small model is easy to freeze and audit.

### Select configuration with five train-only seed folds

Use the existing fixed grid: shrinkage `{1,3,10}` and strength
`{16,32,64,128}`. For each configuration, fit on four folds and score the held
out fold, aggregating predictions over all train rows. Selection minimizes mean
regret, then maximum regret, then maximizes weighted pairwise and unique-best
accuracy, with weaker strength and greater shrinkage as deterministic ties.
Development rows and summaries are not inputs to selection.

### Freeze before one-shot development evaluation

After selection, fit once on all train rows and persist the canonical model.
Restore that exact model before scoring development. A ready verdict requires:

- train cross-fit mean regret decreases, maximum regret does not increase,
  weighted pairwise accuracy increases, and unique-best accuracy does not
  decrease;
- development mean regret decreases, maximum regret does not increase,
  weighted pairwise accuracy increases, and unique-best accuracy does not
  decrease;
- at least four development actions are corrected and worsened actions do not
  exceed corrected actions.

Passing authorizes only a separate reserved-audit proposal.

## Risks / Trade-offs

- [Card identity misses state interactions] -> Treat this as a narrow residual
  family test; a no-go ends the family rather than adding capacity post hoc.
- [One development-only card] -> Use the frozen global prior and report unseen
  take actions explicitly.
- [Development gate variance] -> Use 126 complete states and multiple regret
  and ranking metrics; do not retry or alter gates after access.
- [Entry policy drift] -> Bind and byte-check the r7 checkpoint and source
  scorer before any fit.
