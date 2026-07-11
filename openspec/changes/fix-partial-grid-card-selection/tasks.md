## 1. Evidence And Scope

- [x] 1.1 Capture the fresh partial Astrolabe GRID state and repeated cardinality exceptions.
- [x] 1.2 Confirm the producer used the total count after two cards were already selected.
- [x] 1.3 Validate the complete change artifacts in strict mode.

## 2. Regression Tests

- [ ] 2.1 Add the exact three-total, two-selected, one-remaining GRID regression.
- [ ] 2.2 Add reconstructed-card UUID and duplicate-without-UUID multiset controls.
- [ ] 2.3 Add an inconsistent-candidate control that requests refreshed state.
- [ ] 2.4 Keep initial neutral, upgrade, purge, transform, remove, and HAND_SELECT behavior covered.

## 3. Minimal Implementation

- [ ] 3.1 Add a stable GRID card identity key with UUID and canonical fallback identity.
- [ ] 3.2 Remove selected card occurrences from GRID candidates by multiplicity.
- [ ] 3.3 Select exactly the remaining required count before applying `CardSelectAction`.
- [ ] 3.4 Preserve existing GRID ranking branches and strict action validation.

## 4. Verification

- [ ] 4.1 Run focused screen and CardSelectAction tests with the Windows production Python.
- [ ] 4.2 Run full pytest with cache disabled and a writable repository-local base temp.
- [ ] 4.3 Review the diff for unrelated screen, policy, coordinator, or action-layer changes.
- [ ] 4.4 Commit one cohesive partial-GRID behavior fix.
- [ ] 4.5 Pass independent spec and code-quality review.

## 5. Fresh Qualification Retry

- [ ] 5.1 Run a new conservative 25-game Batch 1 retry without training.
- [ ] 5.2 Confirm zero GRID cardinality exceptions, invalid commands, and new uncaught gameplay exceptions.
- [ ] 5.3 Inspect fresh decision and sim-divergence evidence for A-class failures.
- [ ] 5.4 Commit a separate Batch 1 retry report while preserving the failed-attempt report.
