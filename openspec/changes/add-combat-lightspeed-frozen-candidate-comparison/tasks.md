## 1. Regression Contract

- [ ] 1.1 Add tests for simulator-only checkpoint validation, exact hash binding, and identical state-dict structure.
- [ ] 1.2 Add tests for reachable-only absolute metrics, per-index summaries, pairwise deltas, and reachability mismatch rejection.

## 2. Comparator Implementation

- [ ] 2.1 Implement a source-only CLI that loads registered frozen candidates on CPU and reuses the existing LightSTS evaluator without fitting.
- [ ] 2.2 Publish source identity, candidate identity, per-policy metrics, all pairwise comparisons, per-index breakdowns, blockers, authority, and artifact hashes.

## 3. Frozen Evaluation

- [ ] 3.1 Run focused comparator and production-import-isolation tests plus strict OpenSpec validation.
- [ ] 3.2 Register one fresh `0,3,6,9` comparison cohort bound to r4, r5, r6, the immutable r3 module, and fixed limits.
- [ ] 3.3 Execute the registered comparison once and review ranking, guardrails, coverage, unsupported states, and truncations.

## 4. Closeout

- [ ] 4.1 Commit and push the implementation and report, sync the new capability spec, and archive the completed change.
