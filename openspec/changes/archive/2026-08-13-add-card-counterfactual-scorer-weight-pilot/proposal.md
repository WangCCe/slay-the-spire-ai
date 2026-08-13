## Why

The full card-policy ranking pilot fit 30 train states but regressed every
material disjoint holdout metric, with model movement dominated by the two large
hidden matrices. A 128-parameter scorer-weight-only pilot is the next bounded
test of whether the counterfactual signal generalizes without hidden-feature
overfitting.

## What Changes

- Reconstruct and persist full reusable counterfactual feature/return datasets
  for train seeds `1000..1015` and exposed development seeds `1016..1023`,
  requiring their compact identities to match the completed full-model run.
- Restore the tracked r7 entry model, freeze all parameters except
  `family_head.scorer.weight` and `conditional_ranker.scorer.weight`, and perform
  exactly 32 full-batch pairwise ranking steps with a fresh Adam optimizer.
- Require the same development regret, pairwise, unique-best, maximum-regret,
  corrected-flip, and fit gates used by the full-model pilot.
- Only if all development gates pass, collect a new independent consumed audit
  from seeds `1024..1031`, persist it, and evaluate once without further fitting.
- Require the audit mean regret and weighted pairwise accuracy to improve,
  unique-best accuracy and maximum regret not to regress, and at least one
  wrong-to-best correction before declaring the method ready for a later fresh
  evaluation proposal.
- Keep every model experiment-local. Do not access audit early, use fresh or
  protected seeds, tune against development/audit, launch gameplay, or change
  production checkpoints or CommunicationMod.

Failure at development stops before audit access. Failure at audit stops without
changing the model or rerunning. Rollback remains the tracked r7 checkpoint and
native SimpleAgent.

## Capabilities

### New Capabilities

- `noncombat-card-counterfactual-scorer-weight-pilot`: Defines reusable
  counterfactual feature datasets, scorer-weight-only fitting, a staged exposed
  development gate, and a conditionally accessed independent consumed audit.

### Modified Capabilities

None.

## Impact

The change extends analysis-only training and runner modules, adds focused
tests, and writes bounded datasets, a local candidate model, and reports. It
does not alter live policy loading, gameplay, reward semantics, native adapter
behavior, or production artifacts.
