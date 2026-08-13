# Outcome-Backed Route Counterfactual Ranking

- Verdict: `route_counterfactual_ranker_not_ready_after_development`
- Charged seconds: `3722.547`
- Train source states: `369`
- Development source states: `90`
- Selected epoch: `4`

## Development

| Policy | Mean regret | Max regret | Unique-best accuracy | Pairwise accuracy |
| --- | ---: | ---: | ---: | ---: |
| Current | 0.042495 | 0.298246 | 0.543478 | n/a |
| Untrained | 0.054191 | 0.508772 | 0.456522 | 0.512676 |
| Trained | 0.042690 | 0.508772 | 0.565217 | 0.631925 |

Action changes versus Current: 42; corrected: 10; worsened: 10.

Native SimpleAgent continuation is fixed downstream context, not an unbiased live-policy value estimate. No gameplay, CommunicationMod, production checkpoint, qualification, or promotion authority is granted.
