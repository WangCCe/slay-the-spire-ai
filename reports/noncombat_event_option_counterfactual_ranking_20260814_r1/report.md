# Outcome-Backed Event Option Ranking

- Verdict: `event_counterfactual_ranker_ready_for_shadow_evaluation_proposal`
- Charged seconds: `2395.516`
- Train source states: `245`
- Development source states: `59`
- Selected epoch: `1`
- Selected confidence threshold: `0.50`

## Development

| Policy | Mean regret | P95 regret | Max regret | Unique-best accuracy | Pairwise accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current | 0.024383 | 0.263158 | 0.298246 | 0.588235 | n/a |
| Untrained | 0.029141 | 0.298246 | 0.298246 | 0.529412 | 0.398907 |
| Raw | 0.014868 | 0.157895 | 0.298246 | 0.647059 | 0.726776 |
| Gated | 0.014868 | 0.157895 | 0.298246 | 0.647059 | n/a |

Action changes versus Current: 37; corrected: 6; worsened: 5.

Frozen Current-policy continuation is downstream context, not an unbiased live-policy value estimate. No gameplay, CommunicationMod, production checkpoint, qualification, or promotion authority is granted.
