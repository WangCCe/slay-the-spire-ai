## Context

The consumed state-conditioned experiment samples from one flat candidate
softmax, records one selected candidate log probability, regularizes one total
candidate entropy, and uses raw-score argmax for evaluation. The checked-in
action-family distribution can replace the stochastic factorization, but the
counterfactual audit proves that joint candidate probability cannot silently
replace raw-score argmax and that family entropy alone is zero for event and
route. A narrow adapter is needed before any successor experiment can define a
loss or choose coefficients.

## Goals / Non-Goals

**Goals:**

- Expose the selected action's family, conditional, and joint log-probability
  tensors from the checked-in max-pooled distribution.
- Keep family, expected conditional, and joint entropy separately observable
  and differentiable.
- Define permutation-stable raw-score tie metadata and prove two-stage max-score
  equivalence without introducing a joint-probability greedy rule.
- Preserve exact one-family fallback, finite float32-limit behavior, stable
  metadata, import isolation, and all-false authority.

**Non-Goals:**

- Constructing policy-gradient loss, accepting or selecting entropy
  coefficients, sampling an action, training, loading a model, or authorizing an
  experiment.
- Editing or importing the consumed simulator-learning experiment, a runner,
  policy input, ranker, checkpoint, simulator, CommunicationMod, or gameplay.
- Claiming that the factorization prevents collapse or improves policy quality.

## Decisions

### Return objective terms, not a combined objective

`build_hierarchical_policy_terms` will accept one CPU float32 score tensor,
aligned candidates, and one selected `action_id`. It will call the checked-in
`build_action_family_distribution` and return a frozen dataclass containing
selected family, conditional, and joint log probabilities plus all three
entropy terms. It will not accept coefficients, returns, advantages, rewards,
or a reduction mode.

This prevents a utility API from preregistering experimental choices. A helper
that returned one entropy-regularized loss was rejected because it would hide
the family-versus-conditional decision exposed by the audit.

### Preserve the exact hierarchical identity

The selected family term is indexed by the selected candidate's `kind`; the
conditional and joint terms retain candidate input order. The adapter will
require exact equality between the selected joint term and the sum of selected
family plus conditional terms, and joint entropy must equal family plus
expected conditional entropy within numerical tolerance. Tensors remain CPU
float64 while their source score graph remains CPU float32.

### Define deterministic semantics from scores only

The adapter will expose sorted action IDs tied at the maximum raw score and a
unique greedy action only when that set has one member. It will independently
reconstruct the two-stage max-family-logit then max-within-family set and
require it to equal the raw-score set. It will not expose joint-probability
argmax as a selection API.

Sorting tie IDs gives permutation-stable metadata while candidate-level tensor
alignment remains in input order. Arbitrarily choosing the first tied candidate
was rejected because input permutation would change the reported policy.

### Keep one-family categories explicit

For event and route rows, selected family log probability and family entropy
must be exactly zero, while selected joint log probability equals the selected
conditional term and conditional entropy remains observable. The adapter does
not invent subfamilies for those categories.

### Keep integration absent and evidence synthetic

No existing experiment or runtime module imports the adapter. A deterministic
report will use fixed synthetic score vectors to show multi-family identity,
one-family fallback, tie semantics, and float32-limit finiteness. Stable
metadata binds the dependency schema and exact no-authority map.

## Risks / Trade-offs

- [Max pooling concentrates or splits gradients at family maxima] -> Preserve
  the existing distribution's behavior and test unique and tied maxima without
  claiming optimizer quality.
- [Callers may combine entropy terms incorrectly] -> Do not provide a loss or
  coefficient API; require a later experiment proposal to preregister the
  combination.
- [Score-greedy evaluation differs from stochastic joint probability] -> Name
  and expose only score-derived greedy metadata and document the audited
  distinction.
- [Thin adapters can drift from their dependency] -> Require exact distribution
  metadata and direct tensor identity checks rather than reimplementing the
  factorization.
