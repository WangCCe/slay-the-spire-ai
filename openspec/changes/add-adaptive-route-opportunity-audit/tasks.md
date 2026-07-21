## 1. Evidence Contract And Parsing

- [x] 1.1 Add failing synthetic tests for exact adaptive payload grammar, game-boundary assignment, occurrence provenance, callback-independent deduplication, malformed evidence, and deterministic source identities.
- [x] 1.2 Implement typed source, candidate, occurrence, and adaptive-record parsing so the section 1 tests pass without importing gameplay policy code.

## 2. Trace Correlation And Coordinate Reconstruction

- [x] 2.1 Add failing synthetic tests for bounded nearest-time joins, duplicate semantic agreement, map/action validation, unique and ambiguous graph-route reconstruction, and selected-action contradictions.
- [x] 2.2 Implement decision-trace ingestion, occurrence-level joins, semantic fingerprints, graph validation, coordinate path matching, immediate-coordinate classification, and first-divergence evidence.

## 3. Treatment Attribution And Artifact Output

- [x] 3.1 Add failing synthetic tests for run corroboration, same-immediate selection, later revocation, route departure, divergence uptake, realized optional elite, ambiguity exclusion, deterministic JSON, and invalid-integrity CLI exit behavior.
- [x] 3.2 Implement ordered run ingestion, opportunity funnel aggregation, per-opportunity treatment evidence, deterministic schema `adaptive-route-opportunity-audit-v1`, and the read-only CLI.
- [x] 3.3 Add failing regressions for canonical post-boss `null` transition slots, preserve valid slots in run evidence, and fail closed on malformed or action-targeted null slots.
- [x] 3.4 Add failing regressions and deterministic per-record provenance for every callback-independent candidate-generation fallback.

## 4. Frozen Qualification POC

- [x] 4.1 Preserve the initial fail-closed invocation, reviewed transition-slot fix, and final frozen-evidence invocation lineage without launching the game.
- [x] 4.2 Preserve `reports/adaptive_route_opportunity_audit_20260722.json` and verify the registered source identities, expected `346 -> 173`, 58/54 opportunity, one-selection, four separately auditable fallback records, and zero-treatment checks.
- [x] 4.3 Add `reports/adaptive_route_opportunity_audit_20260722.md` as a derivative report with the exact command, execution lineage, JSON-backed evidence, explicitly labeled operator-observed controls, limitations, and no-tuning stop decision.

## 5. Verification And Review

- [ ] 5.1 Run focused audit tests with cache disabled and a writable repository basetemp.
- [ ] 5.2 Run the repository `commit` test gate and preserve its resolved command, test count, duration, and exit code in the report.
- [ ] 5.3 Run strict OpenSpec validation, `git diff --check`, and verify that no gameplay-policy, training, checkpoint, protocol, or live-configuration source changed.
- [ ] 5.4 Complete an independent local code review with no unresolved Critical or Important finding.
- [ ] 5.5 Commit the cohesive read-only audit change on `master` without staging unrelated pre-existing untracked artifacts.
