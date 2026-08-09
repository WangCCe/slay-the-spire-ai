## 1. Planning Boundary

- [x] 1.1 Validate and independently review proposal, design, specification, fixed intervention set, verdict predicates, authority boundary, and rollback scope.
- [x] 1.2 Commit and push the complete planning boundary before implementation or sealed-evidence access for this change.

## 2. Regression Contracts

- [x] 2.1 Add RED trust-root, lease, containment, byte-binding, vector reconstruction, clipping, malformed-input, and helper-source identity tests.
- [x] 2.2 Add RED recorded, family-policy-ablation, conflict-projection, non-conflict identity, zero-conditional-norm, and fixed-verdict tests.
- [x] 2.3 Add RED independent-acceptance, conditional-perturbation, max-pooled coupling, tie, extreme-value, and analytical-versus-finite-difference synthetic tests.
- [x] 2.4 Add RED import-isolation, deterministic canonical JSON/Markdown, no-raw-vector, 1 MiB JSON/64 KiB Markdown bound, and exact all-false authority tests.

## 3. Source-Only Implementation

- [x] 3.1 Implement strict published-audit trust-root validation and independent reopening of only the bound r2 source evidence under the inactive lease.
- [x] 3.2 Implement standard-library vector decoding, exact recorded reconstruction, frozen clipping, and the three fixed gradient compositions.
- [x] 3.3 Implement synthetic independent-coordinate contracts, fixed feasibility predicates, compact canonical reports, and fail-closed publication.
- [x] 3.4 Pass focused tests, py_compile, import-isolation checks, strict OpenSpec validation, and diff checks without loading Torch, model/native/runtime/game modules, seeds, or CommunicationMod.

## 4. Source Boundary

- [x] 4.1 Run the requalified repository `commit` gate once and record test or infrastructure evidence without blind retry. The one invocation reported 3,601 passes, 16 skips, and one test-isolation failure in 294.13 seconds; the failed node and focused boundary were repaired and verified without retrying the gate.
- [x] 4.2 Obtain independent source review with no unresolved correctness or authority findings.
- [x] 4.3 Commit and push source and tests before either publication process opens sealed evidence. The first publication pre-start failed before evidence analysis because the initial implementation attempted a non-reentrant second lease lock; the corrected single-owner verifier guard is bound to pushed source commit `0f3f042d0`.

## 5. Deterministic Publication And Closeout

- [x] 5.1 Run two fresh isolated source-only publications with separate staging roots and verify byte-identical canonical JSON and Markdown. Both publications bound source `30e9a5580`, producing JSON SHA-256 `c30160cab6bd39a3f93ee65235f432642f8988d5e6dae17b2473d73c9a757156` (73,889 bytes) and Markdown SHA-256 `16628decc23c013de0cf174ed8b6dbcc8e4c243ebd00e54e7d9325d3f93f0aa3` (1,755 bytes).
- [x] 5.2 Verify exact input/source identities, all eight chunk summaries, intervention invariants, fixed verdict, report bounds, no raw vectors, and all-false authority in the canonical pair. The verdict is `bounded_conditional_conflict_guard_feasible`, with projection applied only to conflicting chunks 1 and 4; the result selects no intervention or downstream authority.
- [x] 5.3 Run the unchanged repository `full` gate once, strict OpenSpec validation, diff checks, and final independent review; record that fresh gameplay validation is not applicable because live behavior did not change. The one `full` invocation passed 5,439 tests with 18 skips in 2,357.70 seconds of pytest, 2,361.43 seconds including orchestration; strict validation and diff checks passed, and final independent review found no P1 or P2.
- [ ] 5.4 Update project direction, sync and archive the completed change, then commit and push the canonical reports and closeout metadata.
