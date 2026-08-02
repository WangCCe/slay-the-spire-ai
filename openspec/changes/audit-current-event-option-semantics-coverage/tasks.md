## 1. Contract Regressions

- [x] 1.1 Add Python-AST fixture tests for exact Current event alias discovery, branch ordering, risky-set membership, label dependency, and stable AST hashes.
- [x] 1.2 Add fail-closed tests for missing target functions, unrepresentable branch conditions, stale or duplicate aliases, and canonical event or upstream-enum collisions.
- [x] 1.3 Add bounded C++ source fixture tests for event identity tables, shared and conditional case spans, legal masks, display indices and labels, phase signals, execution bindings, and parser ambiguity.
- [x] 1.4 Add registration, source-identity, canonical-artifact, extra-file, authority, and byte-for-byte recomputation tests that prove no native or gameplay execution path is entered.

## 2. Read-Only Audit Implementation

- [x] 2.1 Implement strict registration loading and verification for the implementation commit/hash, Current source, simulator parent/full-source identity, selected upstream file hashes, canonical event registry, outputs, and all-false authority.
- [x] 2.2 Implement AST-based Current event branch inventory with exact alias accounting and no fuzzy mapping.
- [x] 2.3 Implement the bounded upstream source index for enum/save identity, legal-action, display-label, and execution cases with explicit conditional and phase signals.
- [x] 2.4 Implement source-complete/source-partial classification, reconciliation metrics, canonical JSON and Markdown artifacts, atomic publication, recompute mode, and a CLI that never imports the native adapter module.

## 3. Registered Evidence

- [ ] 3.1 Commit the reviewed audit implementation boundary, then create a registration binding exact Current and upstream source identities plus the complete canonical alias-to-enum registry.
- [ ] 3.2 Run the static audit once without simulator or gameplay execution and publish the registered artifact set.
- [ ] 3.3 Recompute from the same registration and require byte-identical artifacts, reconciled event and status counts, and zero unaccounted Current aliases.
- [ ] 3.4 Write a closeout report and update project direction with source-coverage findings, exact blockers, authority limits, and the separately reviewed next-contract boundary.

## 4. Verification And Closeout

- [ ] 4.1 Run focused audit pytest with an isolated writable basetemp and strict validation of this OpenSpec change.
- [ ] 4.2 Run global OpenSpec validation and the repository commit test gate; do not launch gameplay or substitute the obsolete raw full-suite command.
- [ ] 4.3 Sync the new capability spec, archive the completed change, commit cohesive artifacts, and push `master`.
