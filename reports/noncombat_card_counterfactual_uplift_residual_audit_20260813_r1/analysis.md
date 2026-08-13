# Fixed Card Uplift Residual Audit Analysis

## Result

The fixed `shrinkage=3`, `strength=128` uplift residual is not ready for fresh
evaluation. The one-shot consumed audit completed 62 action branches and 15
source states in 179.218 charged seconds. Seed `1024` was censored only for the
registered Courier restock blocker; no replacement seed was used.

## Evidence

- Weighted pairwise accuracy improved from `0.694823` to `0.732970`.
- Maximum regret and unique-best accuracy were unchanged.
- Mean regret worsened from `0.011696` to `0.017544`.
- The residual made one action flip, corrected zero actions, and worsened one.
- At seed `1029`, decision `11`, it changed a zero-regret `skip` to Wild Strike,
  while `skip` and Power Through were best; regret increased to `0.087719`.
- The fixed model was persisted before audit environment construction and was
  not refit after audit access.
- Production isolation passed and all downstream authority remained false.

## Decision

Do not run fresh evaluation, retry this audit, tune the residual strength, or
select a confidence threshold on seeds `1024..1031`. The cross-fitted
development gain did not transfer to top-action regret. Retain the r7/native
policy as rollback. Any successor must be treated as a new method with new
development evidence and a separately reserved evaluation cohort.
