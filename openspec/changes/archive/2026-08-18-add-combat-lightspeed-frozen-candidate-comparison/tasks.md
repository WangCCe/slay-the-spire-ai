## 1. Regression Contract

- [x] 1.1 Add tests for simulator-only checkpoint validation, exact hash binding, and identical state-dict structure.
- [x] 1.2 Add tests for reachable-only absolute metrics, per-index summaries, pairwise deltas, and reachability mismatch rejection.

## 2. Comparator Implementation

- [x] 2.1 Implement a source-only CLI that loads registered frozen candidates on CPU and reuses the existing LightSTS evaluator without fitting.
- [x] 2.2 Publish source identity, candidate identity, per-policy metrics, all pairwise comparisons, per-index breakdowns, blockers, authority, and artifact hashes.

## 3. Frozen Evaluation

- [x] 3.1 Run focused comparator and production-import-isolation tests plus strict OpenSpec validation.
- [x] 3.2 Register one fresh `0,3,6,9` comparison cohort bound to r4, r5, r6, the immutable r3 module, and fixed limits.
- [x] 3.3 Execute the registered comparison once and review ranking, guardrails, coverage, unsupported states, and truncations.

## 4. Closeout

- [x] 4.1 Commit and push the implementation and report, sync the new capability spec, and archive the completed change.
