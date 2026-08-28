## 1. Regression Contract

- [x] 1.1 Add failing focused tests for immutable bindings, disjoint seeds,
  target-floor filtering, aligned concatenation, and source-component metadata.
- [x] 1.2 Add failing focused tests for exact context cells, density-ratio
  weights, zero-weight unmatched cells, ESS/SMD metrics, and support decisions.
- [x] 1.3 Add fail-closed tests for replay/corpus identity drift, malformed
  tensors, illegal actions, non-finite values, partial outputs, and repeated
  output paths.

## 2. Balanced Corpus Runner

- [x] 2.1 Implement the source-only binding, validation, filtering,
  concatenation, weighting, support-gate, and canonical publication helpers.
- [x] 2.2 Implement the fixed native collection runner for seeds
  `268000..269023`, `270000..270511`, battle indices `10..14`, and the existing
  paired-return recipe without optimizer updates.
- [x] 2.3 Publish compatible combined corpus tensors, separate context weights,
  support report and summary, source snapshots, and artifact hashes with no
  training or gameplay authority.

## 3. Preflight And Execution

- [x] 3.1 Create and commit the immutable execution registration with exact
  source, native, checkpoint, replay, existing-corpus, seed, gate, and output
  bindings.
- [x] 3.2 Run strict OpenSpec validation, focused pytest, and a source-only
  preflight that performs no native loading or output publication.
- [x] 3.3 Execute the registered native collection once and verify floor,
  context-mass, ESS, SMD, legality, seed-isolation, and artifact-identity
  evidence without starting fitting or gameplay.

## 4. Closeout

- [x] 4.1 Record the pass/fail decision and downstream authority boundary in
  the report and tasks without changing seeds, gates, profiles, or bounds.
- [x] 4.2 Run focused regression tests and exactly one timed commit gate for the
  completed source boundary; retain the timing report for the queued gate-speed
  work.
- [ ] 4.3 Commit and push the cohesive change, sync the capability spec, and
  archive the OpenSpec change only after implementation and evidence agree.
