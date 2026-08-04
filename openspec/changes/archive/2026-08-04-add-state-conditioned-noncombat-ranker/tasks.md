## 1. Regression First

- [x] 1.1 Add failing ranker regressions for state-only ordering reversal,
  candidate-order equivariance, repeated scoring, state-dict round trip, and
  fail-closed tensor validation.
- [x] 1.2 Add failing diagnostic regressions for complete opportunity counts,
  card-reward take saturation, raw score margins, order-independent canonical
  output, and malformed-row rejection.

## 2. Additive Implementation

- [x] 2.1 Add the versioned CPU-only one-hidden-layer
  `StateConditionedCandidateRanker` in a new module without editing any r2-bound
  source file.
- [x] 2.2 Add strict tensor validation and stable architecture metadata while
  preserving one output score per supplied candidate.
- [x] 2.3 Add the standard-library anti-collapse diagnostic summarizer with
  all-false experiment, training, live, and promotion authority.

## 3. Verification And Publication

- [x] 3.1 Run the new focused pytest module with a fresh scoped basetemp and no
  cache provider.
- [x] 3.2 Run the unchanged r2 independent verifier and prove its source-bound
  implementation files have no diff from registered commit
  `8d123fdf32bd94bc29e53a97f217a2b7ca40c4fe`.
- [x] 3.3 Run the registered `commit` test gate and strict full-tree OpenSpec
  validation. The `full` profile is not required because this change touches no
  shared test infrastructure or `full_only` test; live gameplay validation is
  not applicable because no production or gameplay path imports the module.

  Evidence: focused pytest passed 23 tests; `commit` passed 3,828 tests with 11
  skips; strict OpenSpec passed 64 items. The commit gate took 320.40 seconds,
  which is recorded as a performance-bound drift rather than hidden or retried.
- [x] 3.4 Update project direction with the verified capability boundary,
  complete the checklist, review the scoped diff, and commit and push the
  cohesive change without authorizing an experiment.
