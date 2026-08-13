## 1. Training Core

- [x] 1.1 Add regressions for informative-row batching, frozen ownership, deterministic epoch training, and model round-trip.
- [x] 1.2 Implement deterministic mini-batch pairwise training and finite/frozen guards over existing state-conditioned card heads.

## 2. Train-Only Selection

- [x] 2.1 Implement five seed-level folds, fixed epoch checkpoints, held-out score aggregation, gates, and deterministic selection.
- [x] 2.2 Stop without final fitting or development access when no checkpoint passes every train-only gate.

## 3. Final Fit And Development

- [x] 3.1 Bind and merge existing/rare train inputs, fit and restore one final full model, then load development.
- [x] 3.2 Implement merged and rare-only one-shot development metrics, take-skip safety, canonical reports, and all-false downstream authority.

## 4. Verification And Execution

- [x] 4.1 Run focused and adjacent tests, compilation, diff checks, and strict OpenSpec validation; do not repeat the 47-minute unrelated full suite.
- [ ] 4.2 Commit and push the source-bound runner, execute it once, verify artifacts, and publish the pass/no-go evidence.
- [ ] 4.3 Access no reserved audit seed; propose a separate audit only if the development verdict passes.
