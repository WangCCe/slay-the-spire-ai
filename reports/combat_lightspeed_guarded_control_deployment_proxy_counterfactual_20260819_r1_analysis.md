# Guarded Control Deployment Proxy Counterfactual

## Verdict

Retain production r16 and stop live evaluation of this candidate family. The transfer gap is supported.

## Evidence

- The comparison completed with 1,685 matched terminal pairs, no blockers, no unexpected initialization failures, and no unsupported states.
- The shared proxy replaced 11,451 eligible raw EndTurn actions for r16 and 10,849 for the candidate; every eligible action had a supported replacement.
- Unguarded candidate-minus-parent evidence was `+2.127219` mean reward, `+1.780154` mean player HP, and `118:71` candidate-only versus parent-only victories.
- Guard-aware evidence became `-0.009720` mean reward, `-0.077745` mean player HP, and `19:17` candidate-only versus parent-only victories.
- Guard-aware reward deltas by battle index were `-0.110938`, `-0.152487`, `-0.200269`, and `+0.671935` for indices 0, 3, 6, and 9.

The large LightSTS uplift was therefore dominated by raw EndTurn outcomes that production already repairs. Once both policies receive the same bounded recovery, the candidate is effectively neutral and slightly worse on aggregate reward and HP, matching the direction of the failed live floor gate.

The proxy is intentionally not an exact implementation of `CombatRLAgent` fallback behavior. It is sufficient to reject more live spending on this candidate, but it cannot authorize promotion or claim simulator equivalence.

## Next Direction

The source and trace audit found no action-index or packaging mismatch. The next training change should preserve frozen-parent card-to-card ordering, not merely parent-versus-EndTurn margin. A new candidate must first show material guard-aware simulator improvement before packaging or live evaluation.
