## Why

The full card ranker overfit while the 128-parameter scorer-only pilot could not
change any action. The newly persisted counterfactual datasets make it possible
to develop a lower-capacity residual policy cheaply, using simulator returns
rather than Bottled labels and without reconstructing native branches.

## What Changes

- Add a deterministic nested seed-grouped cross-fit over the 46 exposed card
  source states from seeds `1000..1023`.
- Fit a smoothed per-card uplift residual over frozen r7 entry logits, with a
  fixed 12-configuration shrinkage/strength grid and deterministic inner-fold
  selection.
- Publish canonical outer-fold predictions, selected configurations, aggregate
  regret/ranking metrics, and an audit go/no-go verdict.
- Require lower mean regret, nonincreasing maximum regret, higher weighted
  pairwise accuracy, nondecreasing unique-best accuracy, corrected actions, and
  fold-level safety before allowing a later audit proposal.
- Keep native loading, audit seeds `1024..1031`, gameplay, production model
  loading, promotion, and policy-quality authority out of scope.

## Capabilities

### New Capabilities

- `noncombat-card-counterfactual-uplift-residual-crossfit`: Defines immutable
  dataset inputs, nested seed-grouped selection, frozen-base uplift residual
  fitting, canonical reporting, and the audit proposal gate.

### Modified Capabilities

None.

## Impact

- Adds one source-only analysis/training module, focused tests, and a canonical
  report under `reports/`.
- Uses only committed scorer-pilot datasets and the tracked r7 entry checkpoint;
  it does not use native simulator, CommunicationMod, protected audit evidence,
  or production checkpoints.
- Success means stable outer cross-fitted improvement sufficient only to propose
  a separate audit. Failure keeps r7/native policy as the rollback and ends this
  residual method on the exposed corpus.
