# Non-Combat Hierarchical Policy Objective Contract

## Evidence Boundary

This report uses fixed synthetic CPU score tensors only. It does not
construct a loss, select a coefficient, sample or train a policy, load a
model or native simulator, access a seed or holdout, or launch gameplay.

## Objective Terms

- Selected joint log probability is exactly family + conditional.
- Family, expected conditional, and joint entropy remain separate.
- The API accepts no coefficient, reward, return, advantage, or loss.

## Deterministic Selection

- Greedy metadata is the complete raw-score maximum set.
- Two-stage max-family then max-within-family produces the same set.
- Ties are sorted by action ID and are not broken by candidate order.
- No joint-probability argmax selection API is defined.

## Synthetic Invariants

- Selected factorization exact: `true`.
- Each exposed term gradient finite: `true`.
- One-family fallback exact: `true`.
- Tied score maxima: `a-action, z-action`.
- Opposite float32 limits finite: `true`.

## Deferred Decisions

- Family and conditional entropy coefficients require a separate
  preregistered experiment proposal.
- Sampling, loss reduction, reward, optimizer, and promotion remain
  undefined here.
- Synthetic gradient identities do not establish intervention value.

## Authority

- coefficient_selection: false
- experiment_execution: false
- formal_rl: false
- gameplay: false
- loss_construction: false
- model_loading: false
- native_loading: false
- policy_promotion: false
- qualification: false
- sampling: false
- seed_access: false
- training: false
