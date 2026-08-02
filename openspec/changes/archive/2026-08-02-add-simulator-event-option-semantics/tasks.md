## 1. Contract Regressions

- [x] 1.1 Add adapter tests for exact `Liars Game` labels, ascension-dependent text, source non-mutation, and registered simulator identity.
- [x] 1.2 Add fail-closed adapter tests for unsupported events or phases, missing or duplicate candidate indices, and simulator provenance drift.
- [x] 1.3 Add bridge tests for resolver enrichment, preservation of valid inline semantics, blocker propagation, and unchanged source hashes.
- [x] 1.4 Add successor-registration tests that accept only the declared mutable identity fields and reject every frozen cohort or execution-setting change before row evaluation.

## 2. Narrow Implementation

- [x] 2.1 Implement the versioned pure event-semantics contract and resolver in the offline Python simulator adapter layer.
- [x] 2.2 Integrate resolver enrichment into the Current bridge without changing `OptimizedAgent`, native simulator behavior, or inline-semantic precedence.
- [x] 2.3 Add v2 successor-registration validation, predecessor/output-manifest binding, immutable-field comparison, and report disclosure.
- [x] 2.4 Implement the registered reused-seed Stage 2 executor with exact native identity checks, fixed decision/replay bounds, deterministic trajectory comparison, and guarded artifact transition.

## 3. Frozen Evidence Re-evaluation

- [x] 3.1 Commit the reviewed implementation boundary, then create a hash-bound successor input preserving the predecessor's four rows, settings, authority flags, and Stage 2 seeds.
- [x] 3.2 Strictly run the successor's four-row Stage 1 gate and publish canonical artifacts without modifying predecessor inputs or reports.
- [x] 3.3 Run the single already-consumed-seed Stage 2 compatibility check only if Stage 1 passes; otherwise record the blocker and stop.

## 4. Verification And Closeout

- [x] 4.1 Run focused adapter and bridge pytest with an isolated writable basetemp.
- [x] 4.2 Run global OpenSpec validation and the repository commit test gate; do not substitute the obsolete raw full-suite command.
- [x] 4.3 Update project direction and a closeout report with semantic coverage, predecessor comparison, verdict, authority limits, and rollback boundary.
- [x] 4.4 Sync the accepted delta specs, archive the completed change, commit cohesive artifacts, and push `master`.
