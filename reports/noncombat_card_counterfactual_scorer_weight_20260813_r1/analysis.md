# Scorer-Weight Counterfactual Pilot Analysis

## Result

The fixed 128-parameter scorer-weight pilot is not ready. It completed 185
counterfactual action branches and 32 full-batch optimizer steps in 554.016
charged seconds. The development gate failed, so audit seeds `1024..1031` were
not accessed.

## Evidence

- Train loss decreased from `3.003983` to `2.730732`.
- Train weighted pairwise accuracy increased only from `0.454546` to
  `0.467350`.
- Train mean/max regret and unique-best accuracy were unchanged.
- Development had zero action flips and zero corrected actions.
- Every development decision metric was unchanged: mean regret `0.020833`, max
  regret `0.192982`, weighted pairwise accuracy `0.490196`, and unique-best
  accuracy `0.25`.
- The experiment model remained under this report directory and all downstream
  authority stayed false.

## Decision

Do not extend the step count, tune the learning rate, or access the audit for
this architecture. The final scorer weights can reduce the pairwise objective
slightly but cannot change the selected actions. Use the persisted full
train/development feature datasets for cheaper cross-fitted architecture
development before proposing another audit or fresh evaluation.
