## 1. Planning And RED Evidence

- [x] 1.1 Strict-validate and independently review the proposal, design, delta spec, and tasks; resolve every actionable planning finding before source edits.
- [x] 1.2 Add failing tests that require the v4 exact field set, reject v3 or unknown inline `rows`, and preserve all existing authority, receipt, cohort, and digest bindings.
- [x] 1.3 Add failing repeated-provenance tests proving traversal equivalence, exact per-source/total row counts, unique excluded seeds, and compact artifact size independent of occurrence-row payload size.
- [x] 1.4 Add a failing publication regression proving canonical inventory bytes above 64 MiB fail before staging or output creation.

## 2. Compact Inventory Implementation

- [x] 2.1 Implement deterministic occurrence iteration and aggregate source scanning without a repository-wide provenance-row list.
- [x] 2.2 Implement v4 compact inventory construction and validation with exact source registry, row counts, excluded seeds, cohorts, role digests, authority evidence, and whole-inventory digest.
- [x] 2.3 Update independent `verify-inventory` reconstruction to compare aggregate evidence without materializing or comparing inline occurrence rows.
- [x] 2.4 Enforce the 64 MiB canonical pre-publication ceiling while preserving atomic publication, direct API behavior, and the existing bounded CLI completion envelope.
- [x] 2.5 Update the independent successor verifier and fixtures for the exact v4 aggregate schema, count consistency, inline-row rejection, cohort selection, authority bindings, and digests.

## 3. Verification And Closeout

- [x] 3.1 Run the focused compact-inventory regressions and complete owning seed-inventory pytest file under the registered Windows temp convention.
- [x] 3.2 Run compile/import-isolation checks and strict global OpenSpec validation without reading the terminal r3 inventory or accessing real seed values.
- [x] 3.3 Request independent code/spec/authority review and resolve all actionable findings.
- [x] 3.4 Run the configured commit and full pytest gates once at their reviewed boundaries, record duration, and record fresh gameplay validation as not applicable because production imports and gameplay behavior are unchanged.
  - Commit gate: 3942 passed, 16 skipped; pytest 528.81s, gate 532.19s.
  - Initial full gate exposed the pre-existing nested-deadline floating-point boundary defect: 5771 passed, 18 skipped, 1 failed; pytest 2457.21s, gate 2461.01s.
  - After the separately reviewed deadline fix, final full gate: 5773 passed, 18 skipped; pytest 2476.43s, gate 2480.15s.
  - Fresh gameplay validation: not applicable; compact inventory and deadline-boundary repairs do not alter production imports or gameplay behavior.
- [x] 3.5 Commit and push the source-only repair, sync and archive this change, strict-validate the global OpenSpec set, and leave parent task 6.2 plus every r4/training/downstream authority incomplete.
