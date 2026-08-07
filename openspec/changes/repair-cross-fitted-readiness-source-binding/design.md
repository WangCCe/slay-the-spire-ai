## Context

The first pushed readiness implementation was exercised exactly once and
closed before inventory reconstruction as `no_go_source_binding`. Its
`_consumed_cohort` validator and the corresponding standard-library verifier
required a synthetic five-field schedule, while the immutable consumed
registration contains eight fields. The omitted fields are
`canonical_search_start`, `inventory_sha256`, and `selection_schema_version`.

The completed readiness change has since been synced and archived. Both source
binding implementations still name its retired active-change spec path, so that
path is absent at current `master` even after the schedule validator is fixed.
The failed source identity and receipts are terminal and cannot be reused.

## Goals / Non-Goals

**Goals:**

- Validate the exact production consumed-schedule schema and fixed provenance
  identity in both independently implemented source-binding paths.
- Bind the readiness contract to its canonical main spec after archival.
- Prove the correction with positive production-shaped and negative drift
  regressions before changing implementation code.
- Produce a new reviewable source commit that grants no execution authority.

**Non-Goals:**

- Retrying, repairing, deleting, or reinterpreting the consumed readiness
  attempt.
- Changing candidate selection, disjointness, budgets, rehearsal, publication,
  decision precedence, authority, or retry semantics.
- Creating a successor registration or accessing native, runtime, model,
  empirical-seed, training, evaluation, game, or CommunicationMod surfaces.

## Decisions

1. **Require one exact eight-field schedule.** The auditor and verifier will
   independently require `canonical_search_start`, `chunk_count`, `chunks`,
   `episodes_per_chunk`, `inventory_sha256`, `seeds`, `seeds_sha256`, and
   `selection_schema_version`. Permissive subset validation was rejected
   because it created the terminal false negative; accepting arbitrary extra
   fields would weaken drift detection.

2. **Pin the three provenance values to the consumed identity.** Both modules
   will independently require canonical search start `0`, inventory SHA-256
   `435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174`,
   and selection schema
   `noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1`. The full
   registration blob is already path, size, and SHA-256 bound, so fixed values
   make the intended source contract explicit without adding another full
   63 MiB canonicalization pass.

3. **Keep the published candidate schema unchanged.** Provenance is validated
   while reading the bound registration; the normalized `consumed_cohort`
   remains registration binding, registration id, count, seeds, and seed
   digest. Expanding that artifact was rejected because it would create an
   unrelated publication and verifier migration.

4. **Use the canonical main spec as the contract input.** Both modules will
   bind
   `openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`.
   The archived delta remains historical evidence, while an active-change path
   is lifecycle-dependent and therefore unsuitable as a durable source input.
   The modified requirements must be synced into that main spec before the
   source commit so the bound bytes describe the implemented contract.

5. **Use regression-first source-only verification.** The shared test builder
   will first adopt the production-shaped schedule so the current five-field
   implementation fails. Focused tests will also reject each missing or drifted
   provenance value and assert that every declared bound path exists at the
   tested tree. No test will import Torch/native modules or execute the audit.

## Risks / Trade-offs

- **The fixed consumed registration is intentionally not extensible.** A future
  registration schema change will fail closed and require a separate reviewed
  source change, which is appropriate for an immutable consumed identity.
- **Duplicated constants can diverge between auditor and verifier.** Focused
  agreement tests exercise both implementations against the same positive and
  negative schedules while preserving implementation independence.
- **A canonical spec edit changes source identity.** Source binding already
  hashes the spec bytes, so any such edit correctly requires a new pushed
  readiness source identity.

## Migration Plan

1. Add the production-shaped RED regressions and confirm the existing source
   rejects the valid schedule or names the absent contract path.
2. Apply the minimal auditor and verifier changes.
3. Run focused source-only tests, strict OpenSpec validation, and independent
   code review.
4. Commit and push only the source correction. Do not create or invoke another
   readiness attempt in this change.

Rollback is limited to reverting the new source correction before any later
attempt is proposed. Existing terminal receipts and evidence are immutable.

## Open Questions

None. A later change must separately decide whether a new pushed source identity
is eligible for a new one-shot readiness attempt.

## Verification Outcome

- The focused source-only suite passed 81 tests with one explicit opt-in
  actual-scale skip in 6.16 seconds.
- The main capability spec and this change both passed strict OpenSpec
  validation.
- Independent review closed all findings after regression-backed fixes and
  reported no remaining actionable correctness issue.
- The repository `commit` gate was invoked exactly once. It completed with
  4,514 passed, 18 skipped, and one failed test in 815.11 seconds of pytest
  (819.01 seconds including orchestration).
- The sole failure was
  `tests/test_noncombat_cross_fitted_hierarchical_learning_runtime.py::test_rollout_sampling_is_replayable_and_rejects_source_mutation`.
  Its unchanged runtime constructs an exact-ceiling floating-point deadline and
  then rejects the rounded subtraction result. Neither that runtime nor its
  test is changed or staged by this source-binding repair. The gate was not
  rerun and the unrelated failure was not repaired in this change.
