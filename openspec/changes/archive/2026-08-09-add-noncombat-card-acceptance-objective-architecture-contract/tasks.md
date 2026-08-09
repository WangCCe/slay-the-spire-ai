## 1. Planning Boundary

- [x] 1.1 Independently review the proposal, design, new capability spec, explicit family/conditional API, gradient-ownership claims, future successor gate, rollback, and all-false authority with no unresolved P1 or P2. Final independent review found no P1/P2 after the exact import, family, numerical, successor, API, metadata-value, and nested-report contracts were fixed.
- [x] 1.2 Run strict OpenSpec and diff validation, then commit and push the complete planning boundary before implementation. Strict validation, diff checks, and the complete reviewed planning boundary were pushed in commit `a3e2edc70`.

## 2. Regression Contracts

- [x] 2.1 Add RED architecture tests for exact dependency metadata, disjoint head parameters/storage/namespaces, float64-accumulated and range-checked family means, complete `take/skip/bowl` identity, permutations, one-family fallback, float32 feature extremes, malformed inputs, prohibited transitive imports, and unchanged legacy imports.
- [x] 2.2 Add RED explicit-logit objective tests for aligned family/conditional/joint probabilities, exact `z_take-logsumexp(z_skip,z_bowl)` acceptance, selected terms, per-family/expected/joint entropy, complete three-family ties and permutations, missing `take`, float32 logit extremes with finite float64 acceptance, and finite autograd.
- [x] 2.3 Add RED gradient-ownership tests proving family-policy isolation, conditional-policy and per-family-entropy isolation, exact named-component reconstruction, and explicit cross-head dependence of expected conditional entropy.
- [x] 2.4 Add RED exact signatures, ordered dataclass fields and tensor shapes/dtypes, metadata mappings, schema versions, nested report fields and dated paths, 131,072-byte JSON/32,768-byte Markdown bounds, checkpoint namespace, exact prohibited-module import isolation, no-loss/coefficient/update API, preservation, fixed future-entry fields, and exact all-false authority tests. The two-file focused suite failed RED only because both new modules were absent (`2` collection errors in `6.78s`).

## 3. Source-Only Implementation

- [x] 3.1 Implement `noncombat_card_acceptance_policy.py` over preprojected tensors with validated card-reward inputs, float64-accumulated canonical exact-family aggregation, two non-aliased public ranker instances, acceptance metadata, stable checkpoint namespaces, and no policy-input/simulator/runtime imports.
- [x] 3.2 Implement `noncombat_card_acceptance_objective.py` with explicit family and conditional logits, selected policy terms, entropy decomposition, greedy tie sets, and no loss, coefficient, advantage, optimizer, sampling, or update API.
- [x] 3.3 Implement deterministic synthetic ownership evidence and canonical JSON/Markdown rendering with exact schemas, field sets, byte bounds, future successor binding/metric/rollback fields, limitations, and fixed all-false authority. The new focused suite passed `40` tests in `19.22s`.

## 4. Verification And Source Boundary

- [x] 4.1 Pass the new focused suite, direct ranker/distribution/objective and legacy-import preservation dependencies, py_compile, fresh-process exact prohibited-module isolation, strict OpenSpec validation, and diff checks. The combined source/preservation suite passed `107` tests in `42.01s`; py_compile, strict OpenSpec, and diff checks passed.
- [x] 4.2 Obtain independent implementation review with no unresolved correctness, gradient-ownership, preservation, checkpoint, or authority findings. Three fixture/signature/permutation P2 findings were fixed; the final re-review found no P1/P2 and the focused suite passed `42` tests in `17.68s`.
- [x] 4.3 Run the configured repository `commit` gate once and record any test, duration, or infrastructure result without blind retry. The single invocation passed `3651` tests with `16` skips in `296.62s` pytest time and `300.29s` total gate time.
- [x] 4.4 Commit and push the complete source, tests, report renderer, and source-only review boundary before canonical publication. The reviewed source-only boundary was pushed in commit `23051ad5a`.

## 5. Publication And Closeout

- [x] 5.1 Render two fresh-process canonical JSON/Markdown pairs at the fixed dated paths, verify byte identity, exact schema/field sets, synthetic invariants, 131,072-byte JSON/32,768-byte Markdown bounds, checkpoint namespaces, prohibited imports, future-entry fields, and all-false authority, then stage one canonical pair. JSON SHA-256 is `244bbfd045f901d2f1302d1976d1618d9725c56d8d86db22dd207c2724d792e1` at `5113` bytes; Markdown SHA-256 is `8cd16e1943e6e46c41e3f2c95714ee3ab13c4ab4e2efb74667d0bce6a269234e` at `1088` bytes.
- [x] 5.2 Run the unchanged repository `full` gate once, strict OpenSpec validation, final diff checks, and final independent review; record that fresh gameplay validation is not applicable because no production or empirical import changes. The single unchanged `full` gate passed `5481` tests with `18` skips in `2339.93s` pytest time and `2343.85s` total; all strict OpenSpec validation passed `80/80`, diff checks were clean, and final review found no P1/P2. Fresh gameplay is not applicable because production and empirical imports remain unchanged.
- [x] 5.3 Update project direction with the contract result and separate empirical-successor gate, sync and archive the completed change, then commit and push canonical reports and closeout metadata. Direction item 60, the main capability spec, canonical reports, and the dated archive were pushed in commit `d4f5bdccd`.
