# Rare-Card Card Uplift Residual

- Verdict: `rare_card_uplift_residual_not_ready`
- Selected configuration: `{'shrinkage': 1, 'strength': 128}`
- Target model cards: `16`
- Unseen development take actions: `0`

| Partition | Metric | Frozen entry | Residual |
| --- | --- | ---: | ---: |
| Merged development | mean_top_action_regret | 0.106925 | 0.080702 |
| Rare development | mean_top_action_regret | 0.121162 | 0.088268 |
| Rare development | weighted_pairwise_accuracy | 0.636089 | 0.655342 |

## Boundary

- Residual selection used merged train rows only.
- The fitted residual was persisted before development row access.
- Reserved audit seeds, native code, game, and CommunicationMod were not accessed.
- A positive verdict authorizes only a separate fresh simulator/live-shadow proposal.
