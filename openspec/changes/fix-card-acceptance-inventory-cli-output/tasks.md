## 1. Freeze Planning

- [x] 1.1 Strict-validate and independently review the proposal, design, delta spec, and tasks; resolve every actionable finding before code edits.
- [x] 1.2 Commit and push the planning-only change from a tracked-clean source boundary without staging r3 output or unrelated historical artifacts.

## 2. Add Red Regressions

- [ ] 2.1 Replace the existing full-artifact CLI expectation with RED build and verify tests for the exact twelve-field bounded completion schema, canonical self-digest preimage, operation/status pair, output/receipt/inventory byte identities, and the 2,048-byte maximum.
- [ ] 2.2 Add RED cases proving a large ignored operation payload does not grow stdout; staging, output closure, receipt canonicality/digest, file replacement during streaming hash, symlink, identity drift, and oversized-envelope failures write no stdout.
- [ ] 2.3 Preserve explicit regressions for byte-identical `check-dispatch` output and unchanged direct `build_inventory`/`verify_inventory` full-mapping returns.

## 3. Implement Bounded Completion

- [ ] 3.1 Add the frozen completion constants and strict receipt/output/completion validators using only standard-library operations, one fixed-buffer streaming inventory-byte hash, and no inventory parsing or reconstruction.
- [ ] 3.2 Route only build/verify CLI success through the bounded completion builder; keep dispatch bytes, operation behavior, durable output, receipt ordering, and exceptions unchanged.

## 4. Verify And Publish

- [ ] 4.1 Run the focused CLI/receipt/output nodes, then the complete owning seed-inventory pytest file under the registered Windows temp parent; run compile/import isolation and strict OpenSpec validation.
- [ ] 4.2 Run the repository commit test gate instead of the raw unpartitioned full suite, record timing/result, run diff checks, and obtain independent code review with no unresolved finding. Fresh gameplay validation is not applicable because no gameplay path changes.
- [ ] 4.3 Commit and push the cohesive source/test/change result; grant no r4 inventory invocation, registration, training, evaluation, qualification, promotion, or gameplay authority.

## 5. Closeout

- [ ] 5.1 Sync the delta spec, archive the completed change, strict-validate the global OpenSpec set, and push closeout. Leave any r4 proposal as a distinct later decision.
