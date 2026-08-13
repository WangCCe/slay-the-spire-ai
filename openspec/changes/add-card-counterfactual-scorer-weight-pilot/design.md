## Context

The full-model pairwise pilot reduced train loss and regret but worsened all
material development metrics. Its two hidden matrices moved by L2 `2.1382` and
`2.0509`, versus `0.1510` and `0.1703` for the scorer weights. Four of five
development action flips were tie-state changes, and the only informative flip
increased regret. Seeds `1016..1023` are therefore exposed development support;
they cannot serve as confirmatory evidence again.

## Goals / Non-Goals

**Goals:**

- Test a 128-parameter scorer-weight-only version of the same direct ranking
  objective.
- Persist full feature/return datasets for cheap future source-only analysis.
- Enforce development-before-audit access and evaluate once on `1024..1031` only
  when every development gate passes.

**Non-Goals:**

- Tune step count, learning rate, loss, or parameter scope against this result.
- Use the failed full-model checkpoint as entry or claim victory improvement.
- Access fresh/protected seeds, run gameplay/OPE, or promote a model.

## Decisions

### Freeze hidden representations and both scorer biases

Only `family_head.scorer.weight` and
`conditional_ranker.scorer.weight` remain trainable. Shared scorer biases cancel
inside the relevant softmax groups, while hidden weights caused the observed
high-capacity movement. A fresh Adam owns exactly 128 scalar parameters.

### Persist canonical feature datasets

Each complete source row stores seed/index/source identity, candidates, returns,
and canonical CPU float32 state/candidate tensors. Restoring the dataset must
round-trip byte exactly. Reconstructed train/development compact identities must
match r2 before fitting, preventing silent data drift.

### Stage development and audit

The 32-step model is evaluated first on exposed development support. Failure
publishes a terminal no-go without constructing any audit environment. Passing
development permits one bounded collection/evaluation of consumed audit seeds
`1024..1031`; the optimizer is not used again after development evaluation.

## Risks / Trade-offs

- [Scorer-only capacity may be too small] -> Treat failure as evidence against
  this architecture and stop rather than unfreezing parameters.
- [Development was used to select the method] -> Make it only an access gate and
  reserve a separate audit partition for evidence.
- [Dataset artifacts are larger] -> Cap canonical dataset size and store them
  once to avoid repeated native reconstruction.
- [Audit support can be sparse or censored] -> Require at least 12 complete
  sources, allow one registered Courier censor, and do not replace seeds.
