# Non-Combat Formal Reward Contract

- Verdict: `formal_reward_contract_ready`
- Contract: `noncombat-formal-reward-contract-v1`
- Registration SHA-256: `dcda155c98f3bf76dd60df5236a62792ad85510dd94b82f97883d05e5afaad81`
- Training, gameplay, evaluation, loading, and promotion authority: `false`

## Ordered Channels

1. `terminal_victory`: primary objective; one only for an explicit terminal player victory.
2. `floor_progress`: simulator-only potential shaping; bounded to `[0, 1]` over a valid monotone episode.

## Optimization Boundary

A future proposal must use victory-first lexicographic optimization or prove a scalar victory weight strictly greater than `1.0`. The smoke's `victory_bonus=1.0` is not automatically formal-compatible, and this contract selects no production weight.

## Provenance Boundary

Live and OPE evidence keeps victory primary and floor reached diagnostic. Simulator floor shaping is not attributed to live trajectories. Current, Bottled, SimpleAgent, teacher agreement, HP, gold, deck heuristics, behavior probabilities, and OPE estimates are excluded from reward.

## Verification

- `authority_tests`: `true`
- `bounds_tests`: `true`
- `excluded_field_invariance_tests`: `true`
- `formula_tests`: `true`
- `provenance_boundary_tests`: `true`
- `reference_exclusion_tests`: `true`
- `scalarization_tests`: `true`
- `terminal_objective_tests`: `true`

## Interpretation

This artifact closes only the formal reward-definition prerequisite. It does not authorize training and does not resolve baseline-policy or target-supported-outcome evidence.
