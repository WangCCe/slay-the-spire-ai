## Why

The frozen-score audit shows that joint-probability argmax would change 24.2%
of trained-canary card rewards and 57.3% of trained-canary shops, while event
and route have zero family entropy. A future hierarchical experiment therefore
needs an explicit source-only contract that keeps stochastic objective terms,
entropy components, and deterministic score-greedy selection separate.

## What Changes

- Add a source-only helper that validates one selected action and exposes its
  family, conditional, and joint log probabilities from the checked-in
  max-pooled distribution.
- Expose family, expected conditional, and joint entropy as separate finite
  differentiable tensors. Do not combine them into a loss or choose any
  coefficient.
- Define deterministic evaluation metadata from raw scores: all tied maximum
  action IDs, a unique greedy action only outside ties, and a two-stage max-
  score result that must match the raw-score result outside ties. Do not use
  joint candidate probability as a greedy rule.
- Cover multi-family card reward/shop behavior, one-family event/route fallback,
  selected-action identity, ties, permutation behavior, float32 limits,
  finite gradients, metadata, and import isolation with synthetic source-only
  regressions and a deterministic design report.
- Do not edit or import the consumed simulator-learning experiment, any runner,
  ranker, policy input, checkpoint, registration, or gameplay path. Do not load
  a model or native simulator, access a seed or holdout, select entropy
  coefficients, train, authorize an experiment, or claim intervention
  effectiveness. Success is exact synthetic identity and gradient evidence,
  all-false authority, focused/full verification, and independent review.
  Rollback is deletion of this additive module, tests, report, docs, and
  OpenSpec change.

## Capabilities

### New Capabilities

- `noncombat-hierarchical-policy-objective-contract`: Defines selected-action
  hierarchical log-probability terms, separately observable entropy terms,
  score-greedy and tie semantics, deterministic evidence, and no-authority
  boundaries.

### Modified Capabilities

None.

## Impact

The change adds one source-only analysis module, focused tests, one deterministic
design report, project-direction documentation, and OpenSpec artifacts. It
depends on but does not modify `noncombat_action_family_distribution`. No
production or empirical execution path changes.
