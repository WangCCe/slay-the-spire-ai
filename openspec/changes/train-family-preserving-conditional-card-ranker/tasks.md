## 1. Policy-Aligned Core

- [x] 1.1 Add regressions for take-only loss, exact 64-value ownership, frozen family outputs, and two-stage metric selection.
- [x] 1.2 Implement deterministic conditional-scorer epochs and complete frozen-state/finite guards.

## 2. Selection And Development

- [x] 2.1 Implement five seed folds, fixed epoch checkpoints, train-only two-stage gates, and deterministic selection.
- [x] 2.2 Implement persist-before-read final fitting plus overall and rare one-shot development gates.

## 3. Verification And Evidence

- [x] 3.1 Run focused and adjacent tests, compilation, diff checks, and strict OpenSpec validation; do not run the unrelated 47-minute full suite or gameplay for this source-only experiment.
- [x] 3.2 Commit and push the source-bound runner, execute it once, verify canonical artifacts, and publish pass/no-go evidence.
- [x] 3.3 Keep `92320..92383` untouched and create no audit proposal unless every development gate passes.
