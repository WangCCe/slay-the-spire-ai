## 1. Contracts And Regression Fixtures

- [x] 1.1 Add failing fixtures for exact source, native, parent, predecessor,
  target, contamination, cohort, output, and authority registration binding.
- [x] 1.2 Add failing fixtures for fixed battle-index-10 partition collection,
  lineage seed isolation, deterministic merge, and row-reference preservation.
- [x] 1.3 Add failing fixtures for context-only fresh projection round trips,
  support-before-optimizer behavior, deferred fresh deserialization, and one
  conditional paired fit.

## 2. Late-Floor Corpus Pipeline

- [x] 2.1 Implement source-only registration and preflight for fit seeds
  `288000..290047`, calibration seeds `290048..290559`, and fresh seeds
  `291000..292023` at battle index 10.
- [x] 2.2 Reuse the existing first-successor collector for the three fixed
  partitions and publish complete collection, exclusion, and provenance
  summaries without adaptive stopping or seed replacement.
- [x] 2.3 Deterministically append new fit and calibration rows to their bound
  predecessor partitions, keep new fresh rows separate, and validate tensor,
  pair-reference, identity, and seed isolation invariants.

## 3. Support And Conditional Fit

- [x] 3.1 Publish a canonical fresh context projection whose identity is bound
  to the sealed fresh corpus without exposing policy labels or metrics.
- [x] 3.2 Evaluate every unchanged context-support and integrity gate against
  the development target using merged train and context-only fresh inputs;
  report missing cells and run-cluster sensitivity descriptively.
- [x] 3.3 Implement an exact fit registration that stops before optimizer
  construction on support failure and otherwise delegates once to the
  unchanged 4,096-update paired control/successor recipe.
- [x] 3.4 Enforce fresh corpus deserialization only after both arms and
  calibration thresholds are frozen; verify parent immutability, equal arm
  samples, artifact round trips, and development-only authority.

## 4. Focused Verification And Source Boundary

- [x] 4.1 Run focused collector, merge, projection, support, fit-wrapper, and
  predecessor regressions with a fresh system-temp pytest child.
- [ ] 4.2 Run strict OpenSpec validation and source-only registration, seed,
  input, output-collision, native-hash, and authority preflights.
- [x] 4.3 Run one timed commit gate for the cohesive source boundary, record its
  tier timings, and do not repeat an unchanged full gate later in the change.
- [ ] 4.4 Commit and push source plus the exact collection registration before
  native loading or environment construction.

## 5. Fixed Development Evidence

- [ ] 5.1 Execute the registered collection once, seal all three fixed
  partitions, and verify manifest, context-projection, merge, support, seed,
  parent, native, and development-authority identities.
- [ ] 5.2 If development support passes, bind and commit the sealed corpus in
  the fit registration and execute the paired fit once; otherwise close without
  fitting, more seeds, threshold changes, or tuning.
- [ ] 5.3 Publish the terminal hard/descriptive decision and contamination
  boundary, commit and push all artifacts without a second full gate, then sync
  and archive the completed OpenSpec change.
