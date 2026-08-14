## Context

The prior raw pairwise model exceeded a robust untrained baseline but changed
every fresh action and worsened Current. Its train-only confidence margin was
not harm-separable. A Current-relative weighted loss POC on the bound train
partition found an epoch-32 fit-only model with 15 tune overrides, 4 corrections,
0 harms, and mean regret 0.112939 versus Current 0.133772.

## Goals / Non-Goals

**Goals:**
- Optimize candidate score differences only relative to Current's legal action.
- Select a conservative fit-only model and margin with no tune harms.
- Evaluate the frozen selection on one new source-complete cohort.

**Non-Goals:**
- Reuse prior development or fresh evaluation outcomes.
- Refit after threshold selection, tune on fresh outcomes, or retry.
- Change live policy or claim direct promotion readiness.

## Decisions

1. Bind train dataset SHA-256 `e346d26e2e29d297b316d9247ef9cf6619bb3fce274b0b88f34d69a9be5f736a`
   and reconstruct the existing 48/16 hash split.
2. Train epochs `1, 2, 4, 8, 16, 32` with return-difference-weighted logistic
   loss for every non-tied candidate versus Current using fixed batch size 16.
3. Evaluate direct score margins `0, 0.01, 0.02, 0.05, 0.1, 0.2`. Eligible
   selections must override, correct, improve mean regret, preserve maximum
   regret, and produce zero tune harms. Select lowest mean regret, then maximum
   regret, more corrections, higher margin, and lower epoch.
4. Keep the selected fit-only model to preserve margin calibration. Evaluate it
   once on fresh seeds `95460..95491`, at most 16 sources, with 12 complete and
   4 informative minimum support.

## Risks / Trade-offs

- [Fit-only leaves 16 rows unused for weights] -> Those rows are necessary for
  honest objective and margin selection; do not refit after calibration.
- [Tune safety may not generalize] -> Require fresh mean/max regret,
  nonzero override and correction, and harms not exceeding corrections before
  permitting only live shadow.
