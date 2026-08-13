# Card Counterfactual Uplift Residual Cross-Fit

- Verdict: `card_counterfactual_uplift_residual_ready_for_audit_proposal`
- Outer folds: `4`
- Source states: `46`
- Action flips: `6`
- Corrected actions: `4`

| Metric | Frozen entry | Uplift residual |
| --- | ---: | ---: |
| Mean regret | 0.053776 | 0.045385 |
| Maximum regret | 0.368421 | 0.368421 |
| Weighted pairwise accuracy | 0.460385 | 0.611349 |
| Unique-best accuracy | 0.312500 | 0.375000 |

## Checks

- corrected_actions: `pass`
- fold_maximum_regret_nonincreasing: `pass`
- fold_mean_regret_safety: `pass`
- maximum_regret_nonincreasing: `pass`
- mean_regret_decreased: `pass`
- pairwise_accuracy_increased: `pass`
- unique_best_accuracy_nondecreasing: `pass`

## Boundary

- Source-only exposed development evidence; audit seeds were not accessed.
- No native module, game, CommunicationMod, or production model was loaded.
- A positive verdict authorizes only a separate audit proposal.
