# Non-Combat Card-Acceptance Objective Architecture Contract

- Policy schema: `noncombat-card-acceptance-policy-v1`
- Objective schema: `noncombat-card-acceptance-objective-v1`
- Report schema: `noncombat-card-acceptance-objective-architecture-contract-report-v1`
- Parameter sharing: `none`
- Acceptance: `z_take - logsumexp(all explicit non-take families)`
- Empirical authorization: `not-authorized-source-only-contract`

## Synthetic Invariants

- `acceptance_independent_of_conditional`: `true`
- `conditional_gradient_isolated`: `true`
- `conditional_independent_of_acceptance`: `true`
- `entropy_identity`: `true`
- `expected_conditional_entropy_cross_head`: `true`
- `extremes_finite`: `true`
- `family_gradient_isolated`: `true`
- `family_permutation_invariant`: `true`
- `gradient_reconstruction_exact`: `true`
- `parameter_identity_disjoint`: `true`
- `parameter_storage_disjoint`: `true`
- `probability_normalized`: `true`

## Boundary

This source-only contract selects no loss, coefficient, optimizer,
cohort, execution, evaluation, policy promotion, or gameplay behavior.
