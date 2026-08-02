## 1. Recovery And Registration Contracts

- [x] 1.1 Add registration v2 validation that binds the immutable v1
  registration/failure record, absent-output assertion, recovery mode, unchanged
  corpus/source/signature/suitability/verdict/limit contracts, and all-false
  authority.
- [x] 1.2 Add regressions rejecting v1 retry, failure-lineage drift, changed
  120-second bound, changed signatures/checks, or recovery authority drift.

## 2. Single Validated Context

- [x] 2.1 Add a typed validated audit context returned by one registered loader
  after physical, runtime, archive, dataset, lineage, and source checks.
- [x] 2.2 Route run and strict recomputation through that context so the train
  archive/full validator run exactly once per command and never inside the timed
  body.
- [x] 2.3 Add call-count, stale-context, raw-mapping, dataset-identity, and
  cross-registration context regressions.

## 3. Exact Representation Optimization

- [x] 3.1 Reuse only payload-validated policy-view hashes for the adapter
  signature while preserving the v1 serializer as a fixture reference.
- [x] 3.2 Compute structured global features once per decision and compose the
  unchanged route/card candidate features and float32 vectors.
- [x] 3.3 Add adversarial reference-versus-optimized tests proving exact semantic
  maps, vector bytes, candidate/decision signatures, alias metrics,
  suitability, verdict, and canonical artifact equality.
- [x] 3.4 Add fail-closed tests for missing/reordered policy views, non-finite
  caches, cross-row cache reuse, and any reference-byte mismatch.

## 4. Synthetic Performance Gate

- [x] 4.1 Add a deterministic generated workload of exactly 300 route and 302
  card-reward multi-candidate rows with no registered corpus path, seed, or
  state dependency.
- [x] 4.2 Run the optimized representation pass under production Windows Python,
  verify exact counts/isolation, and require elapsed time at most 90 seconds.
- [x] 4.3 Run focused and adjacent pytest, Python compilation, strict OpenSpec
  validation, and one repository commit gate without real-corpus execution.

## 5. Fresh Registration And One-Shot Recovery

- [ ] 5.1 Commit and push implementation/OpenSpec, then create, verify, commit,
  and push one v2 registration binding the consumed failure and unchanged
  evidence contract.
- [ ] 5.2 Execute the fresh registered audit exactly once; do not retry, profile,
  tune, or change limits/semantics after the attempt.
- [ ] 5.3 Strictly recompute a published result or preserve a terminal failure,
  perform the final read-only identity/equivalence/authority/inventory audit,
  and update project direction.
- [ ] 5.4 Run bounded final verification, sync/archive completed changes only if
  the original canonical result exists, commit scoped files, and push `master`.
