## 1. Contract And Regression Coverage

- [ ] 1.1 Add focused regressions for exact input binding, even/odd seed
  isolation, partition-local context weights, and rejection before optimizer
  updates when any provenance or split condition differs.
- [ ] 1.2 Add focused regressions for state-mass-preserving classification and
  ranking weights, deterministic replacement plans, zero-weight exclusion, and
  fixed recipe enforcement.
- [ ] 1.3 Add focused regressions for the weighted higher calibration quantile,
  fresh-evaluation isolation, raw safety metrics, weighted value metrics, and
  fail-closed offline decisions.

## 2. Weighted Fit Implementation

- [ ] 2.1 Implement the compact source-bound runner that validates and combines
  the registered corpora, loads the real target, creates the seed-parity split,
  and derives auditable partition-local state weights.
- [ ] 2.2 Implement deterministic weighted classification and ranking sample
  plans while preserving the item-semantic model, frozen parent, optimizer,
  update budget, and loss recipe.
- [ ] 2.3 Implement weighted negative calibration, raw plus weighted fresh
  evaluation, atomic artifact publication, and development-only authority.

## 3. Verification And Registration

- [ ] 3.1 Run Python compilation, the focused weighted-fit tests, reused
  action-relative tests, and strict OpenSpec validation without running the
  full gate during iteration.
- [ ] 3.2 Publish and commit one source-only registration/preflight that binds
  the source commit, exact evidence hashes, fixed command, CPU interpreter,
  output path, recipe, gates, and single-attempt boundary.

## 4. Single Fit And Decision

- [ ] 4.1 Execute the registered CPU fit once, without native loading, game,
  CommunicationMod, parameter sweep, or post-result retry.
- [ ] 4.2 Validate artifact roundtrip, raw and weighted report metrics, source
  snapshots, manifest hashes, and the fail-closed authority decision.

## 5. Closeout

- [ ] 5.1 Run exactly one timed full commit gate for the completed source
  boundary and record its timing report; do not rerun it solely for review.
- [ ] 5.2 Commit the immutable result, sync the new capability to main specs,
  archive the completed change, validate OpenSpec strictly, and push master.
