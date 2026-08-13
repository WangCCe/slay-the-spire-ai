## 1. Input And Fold Boundaries

- [x] 1.1 Bind and restore the two canonical full datasets plus frozen r7 entry checkpoint
- [x] 1.2 Implement deterministic four-outer/three-inner seed folds with overlap regressions

## 2. Residual Fitting And Evaluation

- [x] 2.1 Implement smoothed per-card uplift fitting, unseen-card prior, and frozen-base score composition
- [x] 2.2 Implement fixed-grid inner selection and outer-held-out prediction materialization
- [x] 2.3 Implement aggregate/per-fold metrics, corrections, fixed terminal gates, and canonical artifacts

## 3. Verification And Execution

- [x] 3.1 Add focused tests for leakage rejection, deterministic selection, model immutability, and verdict classification
- [x] 3.2 Run focused pytest, Python compilation, and strict OpenSpec validation
- [ ] 3.3 Execute the source-only cross-fit once and inspect the fixed audit go/no-go verdict

## 4. Closure

- [ ] 4.1 Sync the capability, archive the change, and commit/push scoped evidence
