# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 263
- Differences: 78
- Categories: card_reward=42, event=43, route=166, shop=12
- Evidence quality: complete=253, partial=10
- Oracle modes: bottled_style=263

## Comparison Rows

| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|---|
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.38: M@3,0 -> ?@3,1 -> $@2,2 -> ?@1,3 -> M@1,4 -> R@0,5: reward=7.38, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.38: M@3,0 -> ?@3,1 -> $@2,2 -> ?@1,3 -> M@1,4 -> R@0,5: reward=7.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Reckless Charge | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@4,1 -> ?@5,2 -> M@4,3 -> M@4,4 -> R@3,5 -> M@3,6: reward=6.10, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@4,1 -> ?@5,2 -> M@4,3 -> M@4,4 -> R@3,5 -> M@3,6: reward=6.10, survivability=1.00 |
| event | decision_trace | 2 | complete | bottled_style | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 2 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 2 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: ?@5,2 -> M@4,3 -> M@4,4 -> R@3,5 -> M@3,6 -> R@3,7: reward=6.20, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: ?@5,2 -> M@4,3 -> M@4,4 -> R@3,5 -> M@3,6 -> R@3,7: reward=6.20, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Enter | choose 0: Enter | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,3 -> M@4,4 -> R@3,5 -> M@3,6 -> R@3,7 -> T@3,8: reward=6.70, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,3 -> M@4,4 -> R@3,5 -> M@3,6 -> R@3,7 -> T@3,8: reward=6.70, survivability=1.00 |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Pray | choose 0: Pray | high | Bottled common event handling takes Golden Shrine gold, using Omamori for the curse option when available. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> ?@4,5 -> M@3,6 -> M@2,7 -> T@3,8 -> R@4,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> ?@4,5 -> M@3,6 -> M@2,7 -> T@3,8 -> R@4,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,5 -> M@3,6 -> M@2,7 -> T@3,8 -> R@4,9 -> E@3,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,5 -> M@3,6 -> M@2,7 -> T@3,8 -> R@4,9 -> E@3,10: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | bottled_style | Disarm | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,6 -> M@2,7 -> T@1,8 -> M@1,9 -> E@2,10 -> M@2,11: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,6 -> M@2,7 -> T@1,8 -> M@1,9 -> E@2,10 -> M@2,11: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.20: R@3,7 -> T@3,8 -> R@4,9 -> E@3,10 -> ?@3,11 -> $@2,12: reward=11.20, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.20: R@3,7 -> T@3,8 -> R@4,9 -> E@3,10 -> ?@3,11 -> $@2,12: reward=11.20, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: T@3,8 -> R@4,9 -> E@3,10 -> ?@3,11 -> $@2,12 -> ?@2,13: reward=11.10, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: T@3,8 -> R@4,9 -> E@3,10 -> ?@3,11 -> $@2,12 -> ?@2,13: reward=11.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@4,9 -> E@3,10 -> ?@3,11 -> $@2,12 -> ?@2,13 -> R@1,14: reward=9.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@4,9 -> E@3,10 -> ?@3,11 -> $@2,12 -> ?@2,13 -> R@1,14: reward=9.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: E@3,10 -> ?@3,11 -> $@2,12 -> ?@2,13 -> R@1,14: reward=8.50, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: E@3,10 -> ?@3,11 -> $@2,12 -> ?@2,13 -> R@1,14: reward=8.50, survivability=1.00 |
| shop | decision_trace | 11 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 11 | complete | bottled_style | Meal Ticket | Meal Ticket | high | Bottled shop relic list ranks Meal Ticket as buyable. |
| shop | decision_trace | 11 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: M@5,11 -> R@4,12 -> ?@5,13 -> R@4,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: M@5,11 -> R@4,12 -> ?@5,13 -> R@4,14: reward=4.20, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Dropkick | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.20: R@4,12 -> ?@5,13 -> R@4,14: reward=3.20, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.20: R@4,12 -> ?@5,13 -> R@4,14: reward=3.20, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@5,13 -> R@4,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@5,13 -> R@4,14: reward=2.10, survivability=1.00 |
| event | decision_trace | 14 | complete | bottled_style | choose 2: Grow | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Reckless Charge | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| card_reward | decision_trace | 16 | complete | bottled_style | Bludgeon | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.90: M@2,0 -> $@2,1 -> M@2,2 -> ?@3,3 -> M@4,4 -> E@4,5: reward=10.90, survivability=1.00 |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.90: M@2,0 -> $@2,1 -> M@2,2 -> ?@3,3 -> M@4,4 -> E@4,5: reward=10.90, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | bottled_style | Seeing Red | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.86: $@2,1 -> M@2,2 -> ?@3,3 -> ?@2,4 -> R@2,5 -> M@1,6: reward=8.86, survivability=1.00 |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.86: $@2,1 -> M@2,2 -> ?@3,3 -> ?@2,4 -> R@2,5 -> M@1,6: reward=8.86, survivability=1.00 |
| shop | decision_trace | 19 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 19 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 19 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@3,2 -> ?@3,3 -> ?@2,4 -> R@2,5 -> M@1,6 -> M@2,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 19 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@3,2 -> ?@3,3 -> ?@2,4 -> R@2,5 -> M@1,6 -> M@2,7: reward=7.60, survivability=1.00 |
| event | decision_trace | 20 | complete | bottled_style | choose 1: Fight! | choose 0: Pay | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | bottled_style | Trip | Trip | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Trip. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 3 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@1,1 -> ?@2,2 -> M@1,3 -> M@2,4 -> E@2,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 3 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@1,1 -> ?@2,2 -> M@1,3 -> M@2,4 -> E@2,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Sever Soul | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@5,1 -> M@5,2 -> ?@5,3 -> M@5,4 -> E@6,5 -> M@5,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@5,1 -> M@5,2 -> ?@5,3 -> M@5,4 -> E@6,5 -> M@5,6: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> ?@5,3 -> M@5,4 -> E@6,5 -> M@5,6 -> R@6,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> ?@5,3 -> M@5,4 -> E@6,5 -> M@5,6 -> R@6,7: reward=7.60, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 1: Donut | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,3 -> M@5,4 -> E@6,5 -> M@5,6 -> M@4,7 -> T@3,8: reward=8.00, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,3 -> M@5,4 -> E@6,5 -> M@5,6 -> M@4,7 -> T@3,8: reward=8.00, survivability=1.00 |
| event | decision_trace | 4 | complete | bottled_style | choose 1: Purify | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.74: M@5,4 -> E@6,5 -> M@5,6 -> R@6,7 -> T@5,8 -> $@5,9: reward=9.74, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.74: M@5,4 -> E@6,5 -> M@5,6 -> R@6,7 -> T@5,8 -> $@5,9: reward=9.74, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 2: Grow | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.54: R@5,5 -> M@5,6 -> R@6,7 -> T@5,8 -> $@5,9 -> R@4,10: reward=7.54, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.54: R@5,5 -> M@5,6 -> R@6,7 -> T@5,8 -> $@5,9 -> R@4,10: reward=7.54, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.94: M@5,6 -> R@6,7 -> T@5,8 -> $@5,9 -> R@4,10 -> E@4,11: reward=8.94, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.94: M@5,6 -> R@6,7 -> T@5,8 -> $@5,9 -> R@4,10 -> E@4,11: reward=8.94, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.02: R@6,7 -> T@5,8 -> $@5,9 -> R@4,10 -> E@4,11 -> ?@4,12: reward=9.02, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.02: R@6,7 -> T@5,8 -> $@5,9 -> R@4,10 -> E@4,11 -> ?@4,12: reward=9.02, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@3,8 -> M@2,9 -> ?@2,10 -> ?@1,11 -> R@0,12 -> ?@1,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@3,8 -> M@2,9 -> ?@2,10 -> ?@1,11 -> R@0,12 -> ?@1,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@2,9 -> ?@2,10 -> ?@1,11 -> R@0,12 -> ?@1,13 -> R@0,14: reward=6.20, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@2,9 -> ?@2,10 -> ?@1,11 -> R@0,12 -> ?@1,13 -> R@0,14: reward=6.20, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 10 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: ?@2,10 -> ?@1,11 -> R@0,12 -> ?@1,13 -> R@0,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: ?@2,10 -> ?@1,11 -> R@0,12 -> ?@1,13 -> R@0,14: reward=5.20, survivability=1.00 |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Give Gold | choose 0: Give Gold | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 11 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: ?@1,11 -> R@0,12 -> ?@1,13 -> R@0,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: ?@1,11 -> R@0,12 -> ?@1,13 -> R@0,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@2,12 -> ?@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@2,12 -> ?@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@1,13 -> R@0,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@1,13 -> R@0,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Clothesline | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@2,0 -> ?@2,1 -> ?@3,2 -> M@4,3 -> M@3,4 -> E@3,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@2,0 -> ?@2,1 -> ?@3,2 -> M@4,3 -> M@3,4 -> E@3,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.88: $@6,1 -> M@5,2 -> M@4,3 -> M@3,4 -> E@3,5 -> M@2,6: reward=8.88, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.88: $@6,1 -> M@5,2 -> M@4,3 -> M@3,4 -> E@3,5 -> M@2,6: reward=8.88, survivability=1.00 |
| shop | decision_trace | 2 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@5,2 -> M@4,3 -> M@3,4 -> E@3,5 -> M@2,6 -> E@2,7: reward=9.00, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@5,2 -> M@4,3 -> M@3,4 -> E@3,5 -> M@2,6 -> E@2,7: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | True Grit | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@4,3 -> M@3,4 -> E@3,5 -> M@2,6 -> E@2,7 -> T@3,8: reward=9.50, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@4,3 -> M@3,4 -> E@3,5 -> M@2,6 -> E@2,7 -> T@3,8: reward=9.50, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: M@5,4 -> E@4,5 -> M@3,6 -> M@4,7 -> T@3,8 -> $@2,9: reward=9.64, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: M@5,4 -> E@4,5 -> M@3,6 -> M@4,7 -> T@3,8 -> $@2,9: reward=9.64, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Combust | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.74: E@4,5 -> M@3,6 -> M@4,7 -> T@3,8 -> $@2,9 -> M@2,10: reward=9.74, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.74: E@4,5 -> M@3,6 -> M@4,7 -> T@3,8 -> $@2,9 -> M@2,10: reward=9.74, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@5,6 -> R@5,7 -> T@5,8 -> M@5,9 -> R@6,10 -> E@6,11: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@5,6 -> R@5,7 -> T@5,8 -> M@5,9 -> R@6,10 -> E@6,11: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Immolate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@5,7 -> T@5,8 -> R@4,9 -> M@5,10 -> M@5,11 -> M@5,12: reward=6.70, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@5,7 -> T@5,8 -> R@4,9 -> M@5,10 -> M@5,11 -> M@5,12: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: T@5,8 -> R@4,9 -> M@5,10 -> M@5,11 -> M@5,12 -> M@5,13: reward=5.50, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: T@5,8 -> R@4,9 -> M@5,10 -> M@5,11 -> M@5,12 -> M@5,13: reward=5.50, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@5,9 -> R@6,10 -> E@6,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@5,9 -> R@6,10 -> E@6,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=5.50, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: R@6,10 -> E@6,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: R@6,10 -> E@6,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@6,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@6,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=4.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@5,12 -> M@5,13 -> R@5,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@5,12 -> M@5,13 -> R@5,14: reward=3.10, survivability=1.00 |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Buy 1 Potion | choose 0: Buy 1 Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Armaments | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 3 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@5,0 -> ?@5,1 -> ?@6,2 -> $@5,3 -> M@4,4 -> E@5,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 3 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@5,0 -> ?@5,1 -> ?@6,2 -> $@5,3 -> M@4,4 -> E@5,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Whirlwind | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@5,1 -> M@5,2 -> M@4,3 -> M@4,4 -> E@5,5 -> R@5,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@5,1 -> M@5,2 -> M@4,3 -> M@4,4 -> E@5,5 -> R@5,6: reward=7.60, survivability=1.00 |
| event | decision_trace | 2 | complete | bottled_style | choose 1: Purify | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.78: ?@6,2 -> $@5,3 -> M@4,4 -> E@5,5 -> R@5,6 -> ?@5,7: reward=7.78, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.78: ?@6,2 -> $@5,3 -> M@4,4 -> E@5,5 -> R@5,6 -> ?@5,7: reward=7.78, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 1: Donut | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@6,3 -> ?@5,4 -> E@5,5 -> R@5,6 -> ?@5,7 -> T@5,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@6,3 -> ?@5,4 -> E@5,5 -> R@5,6 -> ?@5,7 -> T@5,8: reward=8.10, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | Reckless Charge | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,4 -> R@3,5 -> M@2,6 -> R@1,7 -> T@0,8 -> E@1,9: reward=8.20, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,4 -> R@3,5 -> M@2,6 -> R@1,7 -> T@0,8 -> E@1,9: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.94: E@5,5 -> M@6,6 -> R@6,7 -> T@6,8 -> M@6,9 -> $@5,10: reward=8.94, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.94: E@5,5 -> M@6,6 -> R@6,7 -> T@6,8 -> M@6,9 -> $@5,10: reward=8.94, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,6 -> R@1,7 -> T@0,8 -> E@1,9 -> ?@0,10 -> M@0,11: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,6 -> R@1,7 -> T@0,8 -> E@1,9 -> ?@0,10 -> M@0,11: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@3,7 -> T@3,8 -> ?@2,9 -> M@1,10 -> M@0,11 -> M@0,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@3,7 -> T@3,8 -> ?@2,9 -> M@1,10 -> M@0,11 -> M@0,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@2,9 -> M@1,10 -> M@0,11 -> M@0,12 -> E@0,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@2,9 -> M@1,10 -> M@0,11 -> M@0,12 -> E@0,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@2,9 -> M@1,10 -> M@0,11 -> M@0,12 -> E@0,13 -> R@0,14: reward=7.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@2,9 -> M@1,10 -> M@0,11 -> M@0,12 -> E@0,13 -> R@0,14: reward=7.60, survivability=1.00 |
| event | decision_trace | 10 | complete | bottled_style | choose 0: Buy 1 Potion | choose 0: Buy 1 Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@1,10 -> M@0,11 -> M@0,12 -> E@0,13 -> R@0,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@1,10 -> M@0,11 -> M@0,12 -> E@0,13 -> R@0,14: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@0,11 -> M@0,12 -> E@0,13 -> R@0,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@0,11 -> M@0,12 -> E@0,13 -> R@0,14: reward=5.60, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: M@0,12 -> E@0,13 -> R@0,14: reward=4.60, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: M@0,12 -> E@0,13 -> R@0,14: reward=4.60, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Havoc | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: E@1,13 -> R@1,14: reward=2.50, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: E@1,13 -> R@1,14: reward=2.50, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Metallicize | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 14 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | bottled_style | Blind | Blind | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Blind. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.58: M@4,0 -> M@5,1 -> ?@4,2 -> $@3,3 -> ?@4,4 -> M@3,5: reward=7.58, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.58: M@4,0 -> M@5,1 -> ?@4,2 -> $@3,3 -> ?@4,4 -> M@3,5: reward=7.58, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.74: M@5,1 -> ?@4,2 -> $@3,3 -> ?@4,4 -> M@3,5 -> R@2,6: reward=7.74, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.74: M@5,1 -> ?@4,2 -> $@3,3 -> ?@4,4 -> M@3,5 -> R@2,6: reward=7.74, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Flame Barrier | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.18: ?@4,2 -> $@3,3 -> ?@4,4 -> M@3,5 -> R@2,6 -> E@1,7: reward=9.18, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.18: ?@4,2 -> $@3,3 -> ?@4,4 -> M@3,5 -> R@2,6 -> E@1,7: reward=9.18, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.90: $@3,3 -> ?@4,4 -> M@3,5 -> R@2,6 -> E@1,7 -> T@0,8: reward=9.90, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.90: $@3,3 -> ?@4,4 -> M@3,5 -> R@2,6 -> E@1,7 -> T@0,8: reward=9.90, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@4,4 -> M@3,5 -> R@2,6 -> E@1,7 -> T@0,8 -> R@0,9: reward=7.10, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@4,4 -> M@3,5 -> R@2,6 -> E@1,7 -> T@0,8 -> R@0,9: reward=7.10, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Give Potion | choose 0: Give Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@3,5 -> R@2,6 -> E@1,7 -> T@0,8 -> R@0,9 -> ?@0,10: reward=7.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@3,5 -> R@2,6 -> E@1,7 -> T@0,8 -> R@0,9 -> ?@0,10: reward=7.10, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | bottled_style | Brutality | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: R@2,6 -> E@1,7 -> T@0,8 -> R@0,9 -> ?@0,10 -> M@0,11: reward=7.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: R@2,6 -> E@1,7 -> T@0,8 -> R@0,9 -> ?@0,10 -> M@0,11: reward=7.10, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: E@1,7 -> T@0,8 -> R@0,9 -> ?@0,10 -> M@0,11 -> E@0,12: reward=8.50, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: E@1,7 -> T@0,8 -> R@0,9 -> ?@0,10 -> M@0,11 -> E@0,12: reward=8.50, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: T@3,8 -> R@3,9 -> M@4,10 -> R@3,11 -> ?@4,12 -> M@3,13: reward=6.70, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: T@3,8 -> R@3,9 -> M@4,10 -> R@3,11 -> ?@4,12 -> M@3,13: reward=6.70, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@3,9 -> M@4,10 -> R@3,11 -> ?@4,12 -> M@3,13 -> R@3,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@3,9 -> M@4,10 -> R@3,11 -> ?@4,12 -> M@3,13 -> R@3,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@4,10 -> R@3,11 -> ?@4,12 -> M@3,13 -> R@3,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@4,10 -> R@3,11 -> ?@4,12 -> M@3,13 -> R@3,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Uppercut | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@3,11 -> ?@4,12 -> M@3,13 -> R@3,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@3,11 -> ?@4,12 -> M@3,13 -> R@3,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@4,12 -> M@3,13 -> R@3,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@4,12 -> M@3,13 -> R@3,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Sword Boomerang | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@3,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@3,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Hemokinesis | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision candidate is available yet.
