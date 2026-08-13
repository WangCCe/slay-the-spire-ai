# Large-Corpus State-Conditioned Card Ranking

- Verdict: `state_conditioned_card_ranking_not_ready_after_development`
- Selected epochs: `8`
- Development accessed: `True`
- Audit accessed: `False`

- Development checks: `{'corrected_actions': True, 'maximum_regret_nonincreasing': True, 'mean_regret_decreased': False, 'pairwise_accuracy_increased': False, 'unique_best_accuracy_nondecreasing': False, 'worsened_actions_bounded': False}`
- Rare development checks: `{'best_take_to_skip_errors_nonincreasing': True, 'mean_regret_decreased': False, 'pairwise_accuracy_nondecreasing': False}`
- Rare best-take-to-skip errors: `{'entry': 18, 'trained': 11}`

## Boundary

- Epoch selection used train seeds only.
- The final model was persisted and restored before development access.
- Native code, game, CommunicationMod, and reserved audit seeds were not accessed.
- A positive verdict authorizes only a separate reserved-audit proposal.
