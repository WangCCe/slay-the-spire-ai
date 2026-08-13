# Family-Preserving Conditional Card Ranking

- Verdict: `family_preserving_conditional_card_ranking_not_ready_after_crossfit`
- Selected epochs: `None`
- Development accessed: `False`
- Audit accessed: `False`
- Metric policy: `two-stage-family-then-conditional-greedy-v1`

## Boundary

- Only the 64-value conditional scorer weight was trainable.
- Entry family choices were required to remain exact.
- Reserved audit seeds, native code, game, and CommunicationMod were not accessed.
