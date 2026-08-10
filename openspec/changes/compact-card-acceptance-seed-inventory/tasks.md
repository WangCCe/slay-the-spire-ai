## 1. Planning And RED Evidence

- [x] 1.1 Strict-validate and independently review the proposal, design, delta spec, and tasks; resolve every actionable planning finding before source edits.
- [ ] 1.2 Add failing tests that require the v4 exact field set, reject v3 or unknown inline `rows`, and preserve all existing authority, receipt, cohort, and digest bindings.
- [ ] 1.3 Add failing repeated-provenance tests proving traversal equivalence, exact per-source/total row counts, unique excluded seeds, and compact artifact size independent of occurrence-row payload size.
- [ ] 1.4 Add a failing publication regression proving canonical inventory bytes above 64 MiB fail before staging or output creation.

## 2. Compact Inventory Implementation

- [ ] 2.1 Implement deterministic occurrence iteration and aggregate source scanning without a repository-wide provenance-row list.
- [ ] 2.2 Implement v4 compact inventory construction and validation with exact source registry, row counts, excluded seeds, cohorts, role digests, authority evidence, and whole-inventory digest.
- [ ] 2.3 Update independent `verify-inventory` reconstruction to compare aggregate evidence without materializing or comparing inline occurrence rows.
- [ ] 2.4 Enforce the 64 MiB canonical pre-publication ceiling while preserving atomic publication, direct API behavior, and the existing bounded CLI completion envelope.

## 3. Verification And Closeout

- [ ] 3.1 Run the focused compact-inventory regressions and complete owning seed-inventory pytest file under the registered Windows temp convention.
- [ ] 3.2 Run compile/import-isolation checks and strict global OpenSpec validation without reading the terminal r3 inventory or accessing real seed values.
- [ ] 3.3 Request independent code/spec/authority review and resolve all actionable findings.
- [ ] 3.4 Run the configured commit and full pytest gates once at their reviewed boundaries, record duration, and record fresh gameplay validation as not applicable because production imports and gameplay behavior are unchanged.
- [ ] 3.5 Commit and push the source-only repair, sync and archive this change, strict-validate the global OpenSpec set, and leave parent task 6.2 plus every r4/training/downstream authority incomplete.
