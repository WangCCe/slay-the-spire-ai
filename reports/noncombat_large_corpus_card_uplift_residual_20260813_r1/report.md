# Large-Corpus Card Uplift Residual

- Verdict: `large_corpus_card_uplift_residual_ready_for_reserved_audit_proposal`
- Selected configuration: `{'shrinkage': 1, 'strength': 128}`
- Model parameters: `79`
- Unseen development take actions: `1`

| Partition | Metric | Frozen entry | Residual |
| --- | --- | ---: | ---: |
| Train cross-fit | mean_top_action_regret | 0.080942 | 0.067669 |
| Train cross-fit | maximum_top_action_regret | 2.175439 | 2.017544 |
| Train cross-fit | weighted_pairwise_accuracy | 0.509760 | 0.606441 |
| Train cross-fit | unique_best_accuracy | 0.315000 | 0.400000 |
| Development | mean_top_action_regret | 0.099694 | 0.081036 |
| Development | maximum_top_action_regret | 2.315789 | 2.315789 |
| Development | weighted_pairwise_accuracy | 0.483325 | 0.583857 |
| Development | unique_best_accuracy | 0.294118 | 0.450980 |

## Boundary

- Configuration selection used train seeds only.
- The fixed model was persisted before development parsing.
- Reserved audit seeds, native code, game, and CommunicationMod were not accessed.
- A positive verdict authorizes only a separate reserved-audit proposal.
