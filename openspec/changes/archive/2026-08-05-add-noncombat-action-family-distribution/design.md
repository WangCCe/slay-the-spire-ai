## Context

The consumed state-conditioned experiment applies one softmax to every legal
candidate and regularizes that candidate distribution's entropy. In the common
card-reward shape, three `take` candidates therefore receive 75% of the mass at
equal scores while one `skip` candidate receives 25%. The terminal audit also
showed a mean candidate-minus-kind entropy gap of `0.8815`, so the existing
entropy scalar is not an adequate statement about family exploration.

Candidates already carry a validated, nonempty `kind`. This gives card rewards
the `take`, `skip`, and optional `bowl` families; shops use purchase/removal/
leave kinds. Current event and route candidates each have one kind, so a family
factorization must reduce exactly to the ordinary within-family softmax there.

## Goals / Non-Goals

**Goals:**

- Define an additive, differentiable distribution over complete candidate sets
  with explicit family and within-family probabilities.
- Remove direct equal-score family mass dependence on candidate count.
- Make family, conditional, and joint entropy independently observable.
- Prove deterministic normalization, identity alignment, permutation behavior,
  duplicate-score family-mass invariance, single-family fallback, and finite
  gradients with synthetic source-only tests.

**Non-Goals:**

- Do not modify the consumed experiment or any production policy path.
- Do not choose entropy coefficients, rewards, thresholds, seeds, or cohorts.
- Do not claim that the distribution prevents collapse, improves floor, or is
  ready for training, gameplay, qualification, loading, or promotion.
- Do not redefine simulator candidate kinds or merge distinct legal actions.

## Decisions

### Use validated candidate `kind` as the family identity

The helper accepts one finite CPU float32 score per candidate plus aligned
candidate action IDs and kinds. It rejects empty or duplicate action IDs,
empty kinds, shape mismatches, non-finite scores, non-CPU tensors, and non-
float32 tensors. Family order is sorted by kind for deterministic metadata;
candidate outputs remain aligned to input order.

This reuses an existing adapter contract and adds no simulator or policy-input
dependency. It also makes one-family event and route decisions a useful
identity boundary rather than inventing unsupported subfamilies.

### Factorize with max-pooled family logits

For candidate score `z_i` and family `g(i)`, define:

```
m_g = max(z_i for i where g(i) = g)
p(g) = softmax(m)_g
p(i | g) = softmax(z within g)_i
p(i) = p(g(i)) * p(i | g(i))
```

The implementation uses tensor `amax`, retaining autograd and distributing tie
gradients across equal maxima. A later policy-gradient integration can use
`log p(selected family) + log p(selected candidate | family)` without changing
the ranker or adding model parameters.

Validated ranker scores enter as CPU float32. The distribution promotes family
logits before subtraction and exposes its logits, log probabilities,
probabilities, and entropies as CPU float64. This keeps opposite finite float32
limits, the hierarchical log-probability sum, and their autograd derivatives
finite without clipping. Because the capability is not integrated with a
runner, a later execution design must bind and test any runtime dtype choice.

Max pooling is selected because family mass is unchanged by adding a distinct
same-family action with a score equal to any existing action, and equal family
best scores yield equal family mass regardless of family cardinality. It also
matches the domain interpretation that the best available card or shop item can
make its action family attractive.

Alternatives considered:

- `logmeanexp` gives dense smooth gradients and equal-score count neutrality,
  but duplicating an above- or below-average candidate changes the family logit
  and therefore fails the stronger duplicate-score family-mass invariant.
- A learned family head removes candidate-count dependence but adds parameters,
  checkpoint identity, family features, and supervision choices that the
  source-only audit cannot justify.
- Flat candidate softmax preserves the current implementation but directly
  retains the measured structural count pressure.

### Decompose entropy instead of replacing it with one opaque scalar

The helper exposes:

```
H_family = H(F)
H_conditional = sum_g p(g) H(C | F=g)
H_joint = H_family + H_conditional = H(C)
```

Tests prove the equality numerically and prove that single-family decisions
have zero family entropy while preserving ordinary candidate entropy. No loss
function or coefficient is selected here. A later algorithm proposal must
state separately how family and conditional entropy enter its objective.

### Keep the capability additive and authority-free

The module imports Torch but no native adapter, simulator runner, replay,
registration, or gameplay surface. Stable metadata records the distribution
schema, aggregation, entropy decomposition, and an exact all-false authority
map. A deterministic Markdown report records the selected design, reproduced
synthetic invariants, rejected alternatives, and unresolved empirical claims.

## Risks / Trade-offs

- [Max pooling concentrates family-level gradients on best-scoring candidates]
  -> Use `amax` for fair tie gradients, retain conditional gradients for every
  candidate in the selected family, and require a later empirical gate before
  claiming value.
- [Greedy semantics are not implied by the joint candidate probabilities] -> A
  later caller could choose the highest-scoring family and then its highest-
  scoring candidate, which matches the original score argmax, while argmax over
  joint candidate probabilities can differ. This capability defines neither
  rule and does not claim that source-only tests fix the observed collapse.
- [`kind` may be too coarse or too fine for a later task] -> Publish exact
  family membership and require a separate schema review before integration.
- [Equal family mass can overrepresent a rare shop action kind] -> Do not tune
  or integrate from synthetic invariants alone; measure category-specific
  behavior in a separately registered experiment if one is later approved.
- [A duplicate-score test is not permission to duplicate or deduplicate legal
  actions] -> Keep unique action IDs mandatory and scope the invariant only to
  family mass under an added distinct legal action with an existing score.
- [Float64 distribution outputs differ from the current runner's float32
  intermediates] -> Keep this capability unintegrated, retain exact additive
  log-probability and extreme-gradient regressions, and require a later runtime
  design to bind dtype, performance, checkpoint, and optimizer behavior.

## Migration Plan

1. Add the isolated helper, focused tests, and deterministic report.
2. Verify existing policy and experiment modules remain byte-for-byte
   untouched and the helper grants no execution authority.
3. Sync and archive only after focused tests, the repository test gate, and
   strict OpenSpec validation pass.
4. Roll back by deleting the additive files; there is no data, checkpoint,
   registration, or runtime migration.

## Open Questions

- Should a later training objective regularize only family entropy or use
  separately registered family and conditional coefficients?
- Is the existing `kind` taxonomy adequate for every shop state, especially
  interactions among purchase and leave actions?
- Does max-pooled family training avoid empirical card-reward collapse without
  damaging floor or category coverage? Only fresh preregistered evidence can
  answer this.
- Should later deterministic evaluation use two-stage score argmax or joint-
  probability argmax? The execution design must choose and test one explicitly.
