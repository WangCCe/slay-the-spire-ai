# Non-Combat Action-Family Distribution Design

## Evidence Boundary

This report uses fixed synthetic score vectors only. It does not load a
simulator or native module, access a seed or holdout, train or select a
model, set a coefficient, or establish intervention effectiveness.

## Selected Factorization

- Family identity: `kind`.
- Family aggregation: `max-candidate-score-v1`.
- Score input dtype: `float32`; distribution dtype: `float64`.
- Joint probability: `p(family) * p(candidate | family)`.
- Entropy: `H(joint) = H(family) + E[H(candidate | family)]`.

## Synthetic Invariants

- Equal-score family probabilities with three `take` candidates and one
  `skip`: `skip=0.500000`,
  `take=0.500000`.
- Equal-score candidate probabilities:
  `take=0.166667` each and `skip=0.500000`.
- Duplicate-score family mass invariant: `true`.
- Single-family fallback matches ordinary softmax: `true`.
- Entropy decomposition holds within `1e-6`: `true`.
- Opposite finite float32 limits retain finite outputs: `true`.
- Focused tests also cover normalization, identity-preserving permutations,
  fail-closed inputs, finite selected-log-probability gradients, and fair
  tied-maximum gradients.

## Alternatives

- `logmeanexp`: dense gradients, but a duplicated above- or below-average
  candidate changes family mass.
- Separate family head: cardinality independent, but requires new features,
  parameters, checkpoints, and supervision not justified by source-only evidence.
- Flat candidate softmax: retains the measured candidate-count pressure.

## Risks And Open Questions

- Max pooling concentrates family-level gradients on top-scoring candidates.
- Greedy selection is undefined here. Two-stage score argmax and joint-
  probability argmax can differ and require an explicit later decision.
- Source-only invariants do not prove that training will avoid the observed
  card-reward collapse.
- A later review must decide whether `kind` is adequate for every shop state.
- A later registered design must choose family and conditional entropy
  coefficients before any empirical execution.

## Authority

- experiment_execution: false
- formal_rl: false
- gameplay: false
- model_loading: false
- native_loading: false
- policy_promotion: false
- qualification: false
- seed_access: false
- training: false
