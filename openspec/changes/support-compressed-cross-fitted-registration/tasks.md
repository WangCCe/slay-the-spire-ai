## 1. Regression Contract

- [ ] 1.1 Add producer RED tests for compact v2 construction, structural validation, immutable publication-commit bindings, canonical 8x64 schedule reconstruction, exact source-tree cross-binding, and v1 historical compatibility.
- [ ] 1.2 Add producer preflight and CLI RED tests that accept exact pushed `go` evidence and reject publication ancestry, path, byte, authority, source, decision, eligibility, gzip, inventory, collision, and schedule drift before dependency imports, including old r2 evidence paired with changed control-plane source.
- [ ] 1.3 Add independent-verifier RED tests for compact registration evidence replay from an immutable publication commit, missing or drifted evidence, persisted-preflight disagreement, registered-commit v1 source replay, and unchanged real r1 evidence bytes.

## 2. Compact Registration Implementation

- [ ] 2.1 Implement bounded deterministic-gzip readiness-candidate decoding and complete inventory, candidate, consumed-cohort, disjointness, and schedule validation in the producer's source-only graph.
- [ ] 2.2 Implement the backward-compatible registration-v2 schema and v2-only source registration builder while preserving canonical compact identity and all-false authority.
- [ ] 2.3 Extend inspection, request rendering, and source-only preflight to verify publication ancestry, exact publication-commit readiness paths and bytes, and readiness-to-registration source bindings before the existing current-source, runtime, native, isolation, and authorization gates.
- [ ] 2.4 Extend the standard-library independent terminal verifier with its own compact-registration, registered-source-commit, and readiness-publication validation without copying external evidence into the output bundle.

## 3. Verification And Publication

- [ ] 3.1 Run focused producer, seed-inventory, preservation, readiness, and independent-verifier pytest with a fresh system-temp basetemp.
- [ ] 3.2 Run strict OpenSpec validation and the repository commit test gate; treat pytest infrastructure failures separately and do not launch gameplay for this source-only change.
- [ ] 3.3 Obtain an independent code review, resolve actionable findings, and record the exact evidence and r2 source-obsolescence boundary in project direction.
- [ ] 3.4 Sync the successor delta spec, archive the completed change, commit one cohesive source change, and push `master` with no registration, request, authorization, or empirical artifact.

## 4. Readiness Handoff

- [ ] 4.1 Create a separate preregistered one-shot readiness change bound to the new pushed source; do not reuse r2 eligibility or start the audit under this change.
