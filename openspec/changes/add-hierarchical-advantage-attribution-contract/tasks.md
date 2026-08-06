## 1. Freeze And Review The Contract

- [ ] 1.1 Strictly validate and independently review the proposal, design,
  delta spec, trajectory-disjoint provenance, component taxonomy, clipping
  semantics, synthetic fixtures, and all-false authority; resolve findings,
  then commit and push planning before implementation.
- [ ] 1.2 Add RED tests for fold/trajectory leakage, split trajectories,
  canonical fit identities, pre-decision feature provenance, exact residual-
  over-scale arithmetic, constant-shift invariance, fixed-zero/unit-scale
  compatibility, and invalid scale or hidden normalization.
- [ ] 1.3 Add RED tests for exact component/parameter identity, full-gradient
  and separately supplied full-loss reconstruction, zero-filled unused
  parameters, cancellation, global clip factor, aggregate-first clipping,
  dtype/shape/nonfinite drift, and rejection of optimizer state or parameter
  deltas.
- [ ] 1.4 Add RED synthetic fixtures for aligned and opposing row-local versus
  shared-parameter directions, within/across-family max-pool ties,
  deterministic bytes, metadata, API-surface limits, and import isolation.

## 2. Implement The Source-Only Capability

- [ ] 2.1 Implement immutable trajectory/fold and fit-set records, canonical
  identity validation, pre-decision feature allowlisting, and exact advantage
  arithmetic without fitting a baseline or reading a path.
- [ ] 2.2 Implement the five fixed scalar component boundary, ordered named
  CPU float32 parameter validation, explicit zero gradients, independent full
  differentiation, reconstruction tolerances, norms, dots, and cosines.
- [ ] 2.3 Implement one complete-gradient norm and uniform clip factor at the
  fixed `1.0` ceiling; preserve additive reconstruction after clipping and
  expose no optimizer transform or parameter-delta API.
- [ ] 2.4 Implement deterministic tiny shared-ranker evidence, tie fixtures,
  canonical metadata/report rendering, and the exact future-registration
  evidence checklist with every downstream authority false.

## 3. Verify And Publish

- [ ] 3.1 Turn every RED boundary green, run the full focused suite plus
  relevant hierarchical distribution/objective regressions with a fresh
  system-temp basetemp, `py_compile`, `git diff --check`, and strict change/
  global OpenSpec validation.
- [ ] 3.2 Obtain an independent implementation and interpretation review;
  resolve every actionable finding and rerun only affected focused/relevant
  tests before publication.
- [ ] 3.3 Publish the deterministic source-only design report and update
  project direction with the bounded next gate; do not launch gameplay because
  no production or empirical behavior path changes.
- [ ] 3.4 Run the repository `commit` test gate once, sync the accepted
  capability to main specs, archive the completed change, commit/push only the
  scoped source, tests, report, direction, and OpenSpec files, and preserve all
  consumed evidence and unrelated local artifacts.
