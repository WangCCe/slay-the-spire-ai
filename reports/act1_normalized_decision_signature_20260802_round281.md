# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 367
- Differences: 78
- Categories: card_reward=52, event=82, route=212, shop=21
- Evidence quality: complete=355, partial=12
- Oracle modes: bottled_style=367

## Comparison Rows

| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|---|
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | bottled_style | Bandage Up | Dramatic Entrance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dramatic Entrance. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.28: M@1,0 -> M@0,1 -> M@0,2 -> M@0,3 -> $@1,4 -> R@2,5: reward=8.28, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.28: M@1,0 -> M@0,1 -> M@0,2 -> M@0,3 -> $@1,4 -> R@2,5: reward=8.28, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.18: M@1,1 -> M@0,2 -> M@0,3 -> $@1,4 -> R@2,5 -> M@1,6: reward=8.18, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.18: M@1,1 -> M@0,2 -> M@0,3 -> $@1,4 -> R@2,5 -> M@1,6: reward=8.18, survivability=1.00 |
| event | decision_trace | 2 | complete | bottled_style | choose 1: Donut | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@1,2 -> M@0,3 -> $@1,4 -> R@2,5 -> M@1,6 -> E@2,7: reward=9.38, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@1,2 -> M@0,3 -> $@1,4 -> R@2,5 -> M@1,6 -> E@2,7: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.96: M@0,3 -> $@1,4 -> R@2,5 -> M@1,6 -> E@2,7 -> T@2,8: reward=9.96, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.96: M@0,3 -> $@1,4 -> R@2,5 -> M@1,6 -> E@2,7 -> T@2,8: reward=9.96, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.94: $@1,4 -> R@2,5 -> M@1,6 -> E@2,7 -> T@2,8 -> M@1,9: reward=9.94, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.94: $@1,4 -> R@2,5 -> M@1,6 -> E@2,7 -> T@2,8 -> M@1,9: reward=9.94, survivability=1.00 |
| shop | decision_trace | 5 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 5 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: R@2,5 -> M@1,6 -> E@2,7 -> T@2,8 -> M@1,9 -> $@1,10: reward=9.64, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: R@2,5 -> M@1,6 -> E@2,7 -> T@2,8 -> M@1,9 -> $@1,10: reward=9.64, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.54: M@1,6 -> E@2,7 -> T@2,8 -> M@1,9 -> $@1,10 -> ?@0,11: reward=9.54, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.54: M@1,6 -> E@2,7 -> T@2,8 -> M@1,9 -> $@1,10 -> ?@0,11: reward=9.54, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.72: ?@1,7 -> T@0,8 -> ?@0,9 -> $@1,10 -> ?@0,11 -> E@1,12: reward=8.72, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.72: ?@1,7 -> T@0,8 -> ?@0,9 -> $@1,10 -> ?@0,11 -> E@1,12: reward=8.72, survivability=1.00 |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Play | choose 0: Play | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: card0 | choose 0: card0 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: card1 | choose 0: card1 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Intimidate | choose 0: Intimidate | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Discovery | choose 0: Discovery | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Intimidate | choose 0: Intimidate | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Discovery | choose 0: Discovery | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Intimidate | choose 0: Intimidate | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Discovery | choose 0: Discovery | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Intimidate | choose 0: Intimidate | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Discovery | choose 0: Discovery | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.72: T@0,8 -> ?@0,9 -> $@1,10 -> ?@0,11 -> E@1,12 -> M@1,13: reward=8.72, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.72: T@0,8 -> ?@0,9 -> $@1,10 -> ?@0,11 -> E@1,12 -> M@1,13: reward=8.72, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@0,9 -> M@0,10 -> ?@0,11 -> E@1,12 -> M@1,13 -> R@0,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@0,9 -> M@0,10 -> ?@0,11 -> E@1,12 -> M@1,13 -> R@0,14: reward=6.50, survivability=1.00 |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Enemies in your next three combats have 1 HP | choose 0: Enemies in your next three combats have 1 HP | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.38: M@1,0 -> $@1,1 -> M@0,2 -> M@0,3 -> ?@0,4 -> R@0,5: reward=7.38, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.38: M@1,0 -> $@1,1 -> M@0,2 -> M@0,3 -> ?@0,4 -> R@0,5: reward=7.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.40: $@1,1 -> M@0,2 -> M@0,3 -> ?@0,4 -> R@0,5 -> M@0,6: reward=7.40, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.40: $@1,1 -> M@0,2 -> M@0,3 -> ?@0,4 -> R@0,5 -> M@0,6: reward=7.40, survivability=1.00 |
| shop | decision_trace | 2 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,2 -> M@0,3 -> ?@0,4 -> R@0,5 -> M@0,6 -> ?@1,7: reward=6.10, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,2 -> M@0,3 -> ?@0,4 -> R@0,5 -> M@0,6 -> ?@1,7: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@0,3 -> ?@0,4 -> R@0,5 -> M@0,6 -> ?@1,7 -> T@2,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@0,3 -> ?@0,4 -> R@0,5 -> M@0,6 -> ?@1,7 -> T@2,8: reward=6.60, survivability=1.00 |
| event | decision_trace | 4 | complete | bottled_style | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@1,4 -> R@1,5 -> M@0,6 -> ?@1,7 -> T@2,8 -> R@3,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@1,4 -> R@1,5 -> M@0,6 -> ?@1,7 -> T@2,8 -> R@3,9: reward=6.70, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Gather Gold | choose 0: Gather Gold | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@1,5 -> M@0,6 -> ?@1,7 -> T@2,8 -> M@1,9 -> E@0,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@1,5 -> M@0,6 -> ?@1,7 -> T@2,8 -> M@1,9 -> E@0,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@0,6 -> ?@1,7 -> T@2,8 -> M@1,9 -> E@0,10 -> R@0,11: reward=7.00, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@0,6 -> ?@1,7 -> T@2,8 -> M@1,9 -> E@0,10 -> R@0,11: reward=7.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@1,7 -> T@2,8 -> M@1,9 -> E@0,10 -> R@0,11 -> M@0,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@1,7 -> T@2,8 -> M@1,9 -> E@0,10 -> R@0,11 -> M@0,12: reward=8.10, survivability=1.00 |
| shop | decision_trace | 8 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 8 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: T@2,8 -> R@3,9 -> M@4,10 -> M@5,11 -> R@5,12 -> E@5,13: reward=8.20, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: T@2,8 -> R@3,9 -> M@4,10 -> M@5,11 -> R@5,12 -> E@5,13: reward=8.20, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.80: R@3,9 -> M@4,10 -> M@5,11 -> R@5,12 -> E@5,13 -> R@4,14: reward=7.80, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.80: R@3,9 -> M@4,10 -> M@5,11 -> R@5,12 -> E@5,13 -> R@4,14: reward=7.80, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,10 -> M@5,11 -> R@5,12 -> E@5,13 -> R@4,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,10 -> M@5,11 -> R@5,12 -> E@5,13 -> R@4,14: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@2,11 -> M@3,12 -> M@2,13 -> R@3,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@2,11 -> M@3,12 -> M@2,13 -> R@3,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@3,12 -> M@2,13 -> R@3,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@3,12 -> M@2,13 -> R@3,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@2,13 -> R@3,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@2,13 -> R@3,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Offering | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@3,0 -> ?@4,1 -> M@5,2 -> $@6,3 -> M@5,4 -> R@5,5: reward=9.60, survivability=1.00 |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@3,0 -> ?@4,1 -> M@5,2 -> $@6,3 -> M@5,4 -> R@5,5: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | bottled_style | Offering | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 18 | complete | bottled_style | Whirlwind+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: ?@4,1 -> M@5,2 -> ?@5,3 -> M@5,4 -> R@5,5 -> E@5,6: reward=8.60, survivability=1.00 |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: ?@4,1 -> M@5,2 -> ?@5,3 -> M@5,4 -> R@5,5 -> E@5,6: reward=8.60, survivability=1.00 |
| event | decision_trace | 19 | complete | bottled_style | choose 1: Sleep | choose 0: Read | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 19 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,2 -> M@4,3 -> M@3,4 -> M@4,5 -> E@5,6 -> ?@4,7: reward=8.00, survivability=1.00 |
| route | decision_trace | 19 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,2 -> M@4,3 -> M@3,4 -> M@4,5 -> E@5,6 -> ?@4,7: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 20 | complete | bottled_style | Corruption | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 20 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 20 | complete | bottled_style | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 11.60: $@6,3 -> M@5,4 -> R@5,5 -> E@5,6 -> ?@4,7 -> T@4,8: reward=11.60, survivability=1.00 |
| route | decision_trace | 20 | complete | bottled_style | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 11.60: $@6,3 -> M@5,4 -> R@5,5 -> E@5,6 -> ?@4,7 -> T@4,8: reward=11.60, survivability=1.00 |
| shop | decision_trace | 21 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 21 | complete | bottled_style | Offering | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 21 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 21 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@6,4 -> R@5,5 -> E@5,6 -> R@6,7 -> T@5,8 -> E@5,9: reward=9.10, survivability=1.00 |
| route | decision_trace | 21 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@6,4 -> R@5,5 -> E@5,6 -> R@6,7 -> T@5,8 -> E@5,9: reward=9.10, survivability=1.00 |
| event | decision_trace | 22 | complete | bottled_style | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 22 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 22 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: R@5,5 -> E@5,6 -> ?@4,7 -> T@4,8 -> E@5,9 -> R@5,10: reward=9.10, survivability=0.70 |
| route | decision_trace | 22 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: R@5,5 -> E@5,6 -> ?@4,7 -> T@4,8 -> E@5,9 -> R@5,10: reward=9.10, survivability=0.70 |
| route | decision_trace | 23 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@6,6 -> R@6,7 -> T@5,8 -> E@5,9 -> ?@4,10 -> ?@3,11: reward=9.10, survivability=1.00 |
| route | decision_trace | 23 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@6,6 -> R@6,7 -> T@5,8 -> E@5,9 -> ?@4,10 -> ?@3,11: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 24 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@6,7 -> T@5,8 -> E@5,9 -> ?@4,10 -> ?@3,11 -> ?@4,12: reward=9.60, survivability=1.00 |
| route | decision_trace | 24 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@6,7 -> T@5,8 -> E@5,9 -> ?@4,10 -> ?@3,11 -> ?@4,12: reward=9.60, survivability=1.00 |
| route | decision_trace | 25 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: T@5,8 -> E@5,9 -> ?@4,10 -> ?@3,11 -> ?@4,12 -> M@4,13: reward=9.50, survivability=1.00 |
| route | decision_trace | 25 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: T@5,8 -> E@5,9 -> ?@4,10 -> ?@3,11 -> ?@4,12 -> M@4,13: reward=9.50, survivability=1.00 |
| route | decision_trace | 26 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@6,9 -> M@6,10 -> ?@6,11 -> R@6,12 -> M@5,13 -> R@4,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 26 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@6,9 -> M@6,10 -> ?@6,11 -> R@6,12 -> M@5,13 -> R@4,14: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 27 | complete | bottled_style | Rampage | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 27 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: M@6,10 -> ?@6,11 -> R@6,12 -> M@5,13 -> R@4,14: reward=4.60, survivability=1.00 |
| route | decision_trace | 27 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: M@6,10 -> ?@6,11 -> R@6,12 -> M@5,13 -> R@4,14: reward=4.60, survivability=1.00 |
| card_reward | decision_trace | 28 | complete | bottled_style | Burning Pact+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 28 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.70: ?@6,11 -> R@6,12 -> M@5,13 -> R@4,14: reward=4.70, survivability=1.00 |
| route | decision_trace | 28 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.70: ?@6,11 -> R@6,12 -> M@5,13 -> R@4,14: reward=4.70, survivability=1.00 |
| card_reward | decision_trace | 29 | complete | bottled_style | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 29 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: R@6,12 -> M@5,13 -> R@4,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 29 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: R@6,12 -> M@5,13 -> R@4,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 30 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@5,13 -> R@4,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 30 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@5,13 -> R@4,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 31 | complete | bottled_style | Spot Weakness+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 31 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 31 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 32 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 32 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@0,0 -> M@0,1 -> $@1,2 -> ?@1,3 -> M@0,4 -> R@1,5: reward=7.68, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@0,0 -> M@0,1 -> $@1,2 -> ?@1,3 -> M@0,4 -> R@1,5: reward=7.68, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.30: $@3,1 -> ?@3,2 -> ?@4,3 -> M@5,4 -> R@5,5 -> M@5,6: reward=7.30, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.30: $@3,1 -> ?@3,2 -> ?@4,3 -> M@5,4 -> R@5,5 -> M@5,6: reward=7.30, survivability=1.00 |
| shop | decision_trace | 2 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@3,2 -> ?@4,3 -> M@5,4 -> R@5,5 -> M@5,6 -> M@6,7: reward=6.10, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@3,2 -> ?@4,3 -> M@5,4 -> R@5,5 -> M@5,6 -> M@6,7: reward=6.10, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,3 -> M@5,4 -> R@5,5 -> M@5,6 -> M@6,7 -> T@5,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,3 -> M@5,4 -> R@5,5 -> M@5,6 -> M@6,7 -> T@5,8: reward=6.60, survivability=1.00 |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Play | choose 0: Play | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: card0 | choose 0: card0 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: card1 | choose 0: card1 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Writhe | choose 0: Writhe | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Finesse | choose 0: Finesse | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Writhe | choose 0: Writhe | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Finesse | choose 0: Finesse | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Writhe | choose 0: Writhe | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Finesse | choose 0: Finesse | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Writhe | choose 0: Writhe | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Finesse | choose 0: Finesse | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> R@5,5 -> M@5,6 -> M@6,7 -> T@5,8 -> M@4,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> R@5,5 -> M@5,6 -> M@6,7 -> T@5,8 -> M@4,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Pummel | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@5,5 -> M@5,6 -> M@6,7 -> T@5,8 -> M@4,9 -> E@5,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@5,5 -> M@5,6 -> M@6,7 -> T@5,8 -> M@4,9 -> E@5,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,6 -> M@6,7 -> T@5,8 -> M@4,9 -> E@5,10 -> M@6,11: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,6 -> M@6,7 -> T@5,8 -> M@4,9 -> E@5,10 -> M@6,11: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Sentinel | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@6,7 -> T@5,8 -> M@4,9 -> E@5,10 -> M@6,11 -> M@5,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@6,7 -> T@5,8 -> M@4,9 -> E@5,10 -> M@6,11 -> M@5,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@6,8 -> ?@6,9 -> E@5,10 -> R@4,11 -> M@5,12 -> M@4,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@6,8 -> ?@6,9 -> E@5,10 -> R@4,11 -> M@5,12 -> M@4,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@6,9 -> E@5,10 -> R@4,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@6,9 -> E@5,10 -> R@4,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=7.70, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | Pummel | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: E@5,10 -> R@4,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: E@5,10 -> R@4,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=5.60, survivability=1.00 |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 11 | complete | bottled_style | choose 1: Ignore | choose 0: Take and Give | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@6,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@6,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@5,12 -> M@4,13 -> R@4,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@5,12 -> M@4,13 -> R@4,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@5,13 -> R@6,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@5,13 -> R@6,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@6,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@6,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@4,0 -> $@5,1 -> ?@5,2 -> M@4,3 -> M@3,4 -> E@3,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@4,0 -> $@5,1 -> ?@5,2 -> M@4,3 -> M@3,4 -> E@3,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@0,1 -> M@1,2 -> M@1,3 -> ?@2,4 -> E@3,5 -> R@3,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@0,1 -> M@1,2 -> M@1,3 -> ?@2,4 -> E@3,5 -> R@3,6: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,2 -> ?@0,3 -> M@1,4 -> R@2,5 -> M@2,6 -> E@1,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,2 -> ?@0,3 -> M@1,4 -> R@2,5 -> M@2,6 -> E@1,7: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Combust | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 10.10: $@2,3 -> ?@2,4 -> R@2,5 -> M@2,6 -> E@1,7 -> T@2,8: reward=10.10, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 10.10: $@2,3 -> ?@2,4 -> R@2,5 -> M@2,6 -> E@1,7 -> T@2,8: reward=10.10, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@2,4 -> R@2,5 -> M@2,6 -> E@1,7 -> T@2,8 -> R@1,9: reward=8.20, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@2,4 -> R@2,5 -> M@2,6 -> E@1,7 -> T@2,8 -> R@1,9: reward=8.20, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 1: Purify | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.50: E@3,5 -> M@2,6 -> E@1,7 -> T@2,8 -> ?@3,9 -> M@4,10: reward=9.50, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.50: E@3,5 -> M@2,6 -> E@1,7 -> T@2,8 -> ?@3,9 -> M@4,10: reward=9.50, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@2,6 -> E@1,7 -> T@2,8 -> M@2,9 -> R@3,10 -> E@3,11: reward=9.60, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@2,6 -> E@1,7 -> T@2,8 -> M@2,9 -> R@3,10 -> E@3,11: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Carnage | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@1,7 -> T@2,8 -> M@2,9 -> R@3,10 -> E@3,11 -> ?@2,12: reward=9.60, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@1,7 -> T@2,8 -> M@2,9 -> R@3,10 -> E@3,11 -> ?@2,12: reward=9.60, survivability=1.00 |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@2,8 -> M@2,9 -> R@3,10 -> E@3,11 -> ?@2,12 -> M@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@2,8 -> M@2,9 -> R@3,10 -> E@3,11 -> ?@2,12 -> M@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@2,9 -> R@3,10 -> E@3,11 -> ?@2,12 -> M@2,13 -> R@3,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@2,9 -> R@3,10 -> E@3,11 -> ?@2,12 -> M@2,13 -> R@3,14: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: R@3,10 -> E@3,11 -> ?@2,12 -> M@2,13 -> R@3,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: R@3,10 -> E@3,11 -> ?@2,12 -> M@2,13 -> R@3,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@3,11 -> ?@2,12 -> M@2,13 -> R@3,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@3,11 -> ?@2,12 -> M@2,13 -> R@3,14: reward=4.50, survivability=1.00 |
| event | decision_trace | 12 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 12 | complete | bottled_style | choose 0: Touch | choose 0: Touch | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.58: $@5,12 -> M@4,13 -> R@4,14: reward=4.58, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.58: $@5,12 -> M@4,13 -> R@4,14: reward=4.58, survivability=1.00 |
| shop | decision_trace | 13 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 13 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@4,13 -> R@4,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@4,13 -> R@4,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Impervious | Impervious | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@1,0 -> M@2,1 -> ?@3,2 -> ?@4,3 -> ?@3,4 -> E@2,5: reward=9.00, survivability=1.00 |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@1,0 -> M@2,1 -> ?@3,2 -> ?@4,3 -> ?@3,4 -> E@2,5: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | bottled_style | Havoc | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@2,1 -> ?@3,2 -> ?@4,3 -> ?@3,4 -> E@2,5 -> M@3,6: reward=9.00, survivability=1.00 |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@2,1 -> ?@3,2 -> ?@4,3 -> ?@3,4 -> E@2,5 -> M@3,6: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 19 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@3,2 -> ?@4,3 -> ?@3,4 -> E@2,5 -> M@3,6 -> M@3,7: reward=9.00, survivability=1.00 |
| route | decision_trace | 19 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@3,2 -> ?@4,3 -> ?@3,4 -> E@2,5 -> M@3,6 -> M@3,7: reward=9.00, survivability=1.00 |
| route | decision_trace | 20 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@4,3 -> ?@3,4 -> E@2,5 -> M@3,6 -> M@3,7 -> T@2,8: reward=9.00, survivability=1.00 |
| route | decision_trace | 20 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@4,3 -> ?@3,4 -> E@2,5 -> M@3,6 -> M@3,7 -> T@2,8: reward=9.00, survivability=1.00 |
| event | decision_trace | 21 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 21 | complete | bottled_style | choose 0: Offer | choose 0: Offer | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 21 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 21 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@3,4 -> E@2,5 -> M@3,6 -> M@3,7 -> T@4,8 -> ?@3,9: reward=9.00, survivability=1.00 |
| route | decision_trace | 21 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@3,4 -> E@2,5 -> M@3,6 -> M@3,7 -> T@4,8 -> ?@3,9: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 22 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.10: R@3,5 -> M@3,6 -> M@3,7 -> T@4,8 -> ?@3,9 -> M@3,10: reward=7.10, survivability=1.00 |
| route | decision_trace | 22 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.10: R@3,5 -> M@3,6 -> M@3,7 -> T@4,8 -> ?@3,9 -> M@3,10: reward=7.10, survivability=1.00 |
| route | decision_trace | 23 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@3,6 -> M@3,7 -> T@2,8 -> R@1,9 -> M@1,10 -> $@1,11: reward=9.60, survivability=1.00 |
| route | decision_trace | 23 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@3,6 -> M@3,7 -> T@2,8 -> R@1,9 -> M@1,10 -> $@1,11: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | bottled_style | Cleave | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| card_reward | decision_trace | 24 | complete | bottled_style | Evolve | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 24 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@3,7 -> T@2,8 -> R@1,9 -> M@1,10 -> $@1,11 -> ?@1,12: reward=10.10, survivability=1.00 |
| route | decision_trace | 24 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@3,7 -> T@2,8 -> R@1,9 -> M@1,10 -> $@1,11 -> ?@1,12: reward=10.10, survivability=1.00 |
| card_reward | decision_trace | 25 | complete | bottled_style | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 25 | complete | bottled_style | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: T@2,8 -> R@1,9 -> M@1,10 -> $@1,11 -> ?@1,12 -> M@1,13: reward=10.10, survivability=1.00 |
| route | decision_trace | 25 | complete | bottled_style | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: T@2,8 -> R@1,9 -> M@1,10 -> $@1,11 -> ?@1,12 -> M@1,13: reward=10.10, survivability=1.00 |
| route | decision_trace | 26 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@3,9 -> M@3,10 -> ?@2,11 -> M@2,12 -> ?@3,13 -> R@2,14: reward=7.60, survivability=1.00 |
| route | decision_trace | 26 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@3,9 -> M@3,10 -> ?@2,11 -> M@2,12 -> ?@3,13 -> R@2,14: reward=7.60, survivability=1.00 |
| event | decision_trace | 27 | complete | bottled_style | choose 1: Leave | choose 1: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| event | decision_trace | 27 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 27 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@3,10 -> ?@2,11 -> M@2,12 -> ?@3,13 -> R@2,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 27 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@3,10 -> ?@2,11 -> M@2,12 -> ?@3,13 -> R@2,14: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 28 | complete | bottled_style | Ghostly Armor+ | Ghostly Armor+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor+. |
| route | decision_trace | 28 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@2,11 -> M@2,12 -> ?@3,13 -> R@2,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 28 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@2,11 -> M@2,12 -> ?@3,13 -> R@2,14: reward=5.10, survivability=1.00 |
| shop | decision_trace | 29 | complete | bottled_style | Membership Card | purge | high | Bottled REQUESTED_STRIKE shop priority removes curses first. |
| shop | decision_trace | 29 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority removes curses first. |
| shop | decision_trace | 29 | complete | bottled_style | wait | purge | high | Bottled REQUESTED_STRIKE shop priority removes curses first. |
| shop | decision_trace | 29 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 29 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.60: M@2,12 -> ?@3,13 -> R@2,14: reward=3.60, survivability=1.00 |
| route | decision_trace | 29 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.60: M@2,12 -> ?@3,13 -> R@2,14: reward=3.60, survivability=1.00 |
| card_reward | decision_trace | 30 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 30 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 2.60: ?@3,13 -> R@2,14: reward=2.60, survivability=1.00 |
| route | decision_trace | 30 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 2.60: ?@3,13 -> R@2,14: reward=2.60, survivability=1.00 |
| route | decision_trace | 31 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 31 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 32 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 32 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | bottled_style | Enlightenment | Blind | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Blind. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@2,0 -> M@3,1 -> M@4,2 -> $@5,3 -> ?@5,4 -> E@5,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@2,0 -> M@3,1 -> M@4,2 -> $@5,3 -> ?@5,4 -> E@5,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.68: ?@1,1 -> M@1,2 -> $@2,3 -> ?@2,4 -> R@3,5 -> M@2,6: reward=7.68, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.68: ?@1,1 -> M@1,2 -> $@2,3 -> ?@2,4 -> R@3,5 -> M@2,6: reward=7.68, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.18: M@1,2 -> $@2,3 -> ?@2,4 -> R@3,5 -> M@2,6 -> R@1,7: reward=8.18, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.18: M@1,2 -> $@2,3 -> ?@2,4 -> R@3,5 -> M@2,6 -> R@1,7: reward=8.18, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Sever Soul | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.72: $@2,3 -> ?@2,4 -> R@3,5 -> M@2,6 -> R@1,7 -> T@1,8: reward=8.72, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.72: $@2,3 -> ?@2,4 -> R@3,5 -> M@2,6 -> R@1,7 -> T@1,8: reward=8.72, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@2,4 -> R@3,5 -> ?@3,6 -> R@2,7 -> T@3,8 -> E@3,9: reward=8.20, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@2,4 -> R@3,5 -> ?@3,6 -> R@2,7 -> T@3,8 -> E@3,9: reward=8.20, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Play | choose 0: Play | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: spin | choose 0: spin | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Prize! | choose 0: Prize! | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@3,5 -> ?@3,6 -> R@2,7 -> T@3,8 -> E@3,9 -> ?@4,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@3,5 -> ?@3,6 -> R@2,7 -> T@3,8 -> E@3,9 -> ?@4,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,6 -> R@1,7 -> T@1,8 -> M@0,9 -> M@0,10 -> E@1,11: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,6 -> R@1,7 -> T@1,8 -> M@0,9 -> M@0,10 -> E@1,11: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@2,7 -> T@3,8 -> M@2,9 -> M@3,10 -> R@2,11 -> E@3,12: reward=8.20, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@2,7 -> T@3,8 -> M@2,9 -> M@3,10 -> R@2,11 -> E@3,12: reward=8.20, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@3,8 -> M@2,9 -> M@3,10 -> R@2,11 -> E@3,12 -> ?@4,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@3,8 -> M@2,9 -> M@3,10 -> R@2,11 -> E@3,12 -> ?@4,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@2,9 -> M@3,10 -> R@2,11 -> E@3,12 -> ?@4,13 -> R@4,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@2,9 -> M@3,10 -> R@2,11 -> E@3,12 -> ?@4,13 -> R@4,14: reward=7.70, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | True Grit | Reaper | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@3,10 -> R@2,11 -> E@3,12 -> ?@4,13 -> R@4,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@3,10 -> R@2,11 -> E@3,12 -> ?@4,13 -> R@4,14: reward=5.60, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: R@2,11 -> E@3,12 -> ?@4,13 -> R@4,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: R@2,11 -> E@3,12 -> ?@4,13 -> R@4,14: reward=3.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@5,12 -> ?@5,13 -> R@4,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@5,12 -> ?@5,13 -> R@4,14: reward=2.00, survivability=1.00 |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@5,13 -> R@4,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@5,13 -> R@4,14: reward=1.00, survivability=1.00 |
| event | decision_trace | 14 | complete | bottled_style | choose 0: Search | choose 0: Search | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Normalized Review Candidates

- Signature schema: `v1`
- These groups are diagnostic review evidence, not gameplay repair recommendations.
- Excluded rows: insufficient_distinct_occurrences=28, matched=289, retry_duplicate=18, unsupported_confidence=32

No normalized review group has two independent eligible occurrences yet.

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision candidate is available yet.
