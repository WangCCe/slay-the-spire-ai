# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 275
- Differences: 65
- Categories: card_reward=52, event=39, route=174, shop=10
- Evidence quality: complete=265, partial=10
- Oracle modes: bottled_style=275

## Comparison Rows

| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|---|
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@0,0 -> M@0,1 -> M@0,2 -> $@0,3 -> ?@1,4 -> R@0,5: reward=7.98, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@0,0 -> M@0,1 -> M@0,2 -> $@0,3 -> ?@1,4 -> R@0,5: reward=7.98, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.06: M@0,1 -> M@0,2 -> $@0,3 -> ?@1,4 -> R@0,5 -> M@1,6: reward=8.06, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.06: M@0,1 -> M@0,2 -> $@0,3 -> ?@1,4 -> R@0,5 -> M@1,6: reward=8.06, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Perfected Strike | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.02: M@0,2 -> $@0,3 -> ?@1,4 -> R@0,5 -> M@1,6 -> M@0,7: reward=8.02, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.02: M@0,2 -> $@0,3 -> ?@1,4 -> R@0,5 -> M@1,6 -> M@0,7: reward=8.02, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: $@0,3 -> ?@1,4 -> R@0,5 -> M@1,6 -> M@0,7 -> T@1,8: reward=8.50, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: $@0,3 -> ?@1,4 -> R@0,5 -> M@1,6 -> M@0,7 -> T@1,8: reward=8.50, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@1,4 -> R@0,5 -> M@1,6 -> M@0,7 -> T@1,8 -> M@1,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@1,4 -> R@0,5 -> M@1,6 -> M@0,7 -> T@1,8 -> M@1,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,5 -> M@1,6 -> M@0,7 -> T@1,8 -> M@1,9 -> R@0,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,5 -> M@1,6 -> M@0,7 -> T@1,8 -> M@1,9 -> R@0,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@1,6 -> M@0,7 -> T@1,8 -> M@1,9 -> R@0,10 -> E@1,11: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@1,6 -> M@0,7 -> T@1,8 -> M@1,9 -> R@0,10 -> E@1,11: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@2,7 -> T@2,8 -> M@2,9 -> R@3,10 -> M@4,11 -> E@5,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@2,7 -> T@2,8 -> M@2,9 -> R@3,10 -> M@4,11 -> E@5,12: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Corruption | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@2,8 -> M@2,9 -> M@2,10 -> M@2,11 -> R@2,12 -> E@3,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@2,8 -> M@2,9 -> M@2,10 -> M@2,11 -> R@2,12 -> E@3,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@2,9 -> M@2,10 -> M@2,11 -> R@2,12 -> E@3,13 -> R@3,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@2,9 -> M@2,10 -> M@2,11 -> R@2,12 -> E@3,13 -> R@3,14: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@2,10 -> M@2,11 -> R@2,12 -> E@3,13 -> R@3,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@2,10 -> M@2,11 -> R@2,12 -> E@3,13 -> R@3,14: reward=5.60, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@2,11 -> R@2,12 -> E@3,13 -> R@3,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@2,11 -> R@2,12 -> E@3,13 -> R@3,14: reward=3.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Offering | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: R@2,12 -> E@3,13 -> R@3,14: reward=2.50, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: R@2,12 -> E@3,13 -> R@3,14: reward=2.50, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 2.50: E@3,13 -> R@3,14: reward=2.50, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 2.50: E@3,13 -> R@3,14: reward=2.50, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Armaments | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | bottled_style | Trip | Trip | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Trip. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 3 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 7.28: M@5,0 -> $@5,1 -> ?@4,2 -> M@5,3 -> ?@4,4 -> M@3,5: reward=7.28, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 3 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 7.28: M@5,0 -> $@5,1 -> ?@4,2 -> M@5,3 -> ?@4,4 -> M@3,5: reward=7.28, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.28: $@5,1 -> ?@4,2 -> M@5,3 -> ?@4,4 -> M@3,5 -> M@3,6: reward=7.28, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.28: $@5,1 -> ?@4,2 -> M@5,3 -> ?@4,4 -> M@3,5 -> M@3,6: reward=7.28, survivability=1.00 |
| shop | decision_trace | 2 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@4,2 -> M@5,3 -> ?@4,4 -> ?@4,5 -> M@4,6 -> R@4,7: reward=6.10, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@4,2 -> M@5,3 -> ?@4,4 -> ?@4,5 -> M@4,6 -> R@4,7: reward=6.10, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 1: Donut | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,3 -> ?@4,4 -> ?@4,5 -> M@4,6 -> R@4,7 -> T@3,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,3 -> ?@4,4 -> ?@4,5 -> M@4,6 -> R@4,7 -> T@3,8: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.42: ?@4,4 -> M@3,5 -> M@3,6 -> M@2,7 -> T@1,8 -> $@0,9: reward=7.42, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.42: ?@4,4 -> M@3,5 -> M@3,6 -> M@2,7 -> T@1,8 -> $@0,9: reward=7.42, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 2: Grow | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,5 -> M@4,6 -> R@4,7 -> T@3,8 -> ?@4,9 -> E@5,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,5 -> M@4,6 -> R@4,7 -> T@3,8 -> ?@4,9 -> E@5,10: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.44: M@3,6 -> M@2,7 -> T@1,8 -> $@0,9 -> ?@1,10 -> R@1,11: reward=7.44, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.44: M@3,6 -> M@2,7 -> T@1,8 -> $@0,9 -> ?@1,10 -> R@1,11: reward=7.44, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.88: M@2,7 -> T@1,8 -> R@1,9 -> ?@2,10 -> $@3,11 -> E@3,12: reward=8.88, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.88: M@2,7 -> T@1,8 -> R@1,9 -> ?@2,10 -> $@3,11 -> E@3,12: reward=8.88, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.96: T@1,8 -> R@1,9 -> ?@2,10 -> $@3,11 -> E@3,12 -> ?@2,13: reward=8.96, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.96: T@1,8 -> R@1,9 -> ?@2,10 -> $@3,11 -> E@3,12 -> ?@2,13: reward=8.96, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.56: R@1,9 -> ?@2,10 -> $@3,11 -> E@3,12 -> ?@2,13 -> R@1,14: reward=9.56, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.56: R@1,9 -> ?@2,10 -> $@3,11 -> E@3,12 -> ?@2,13 -> R@1,14: reward=9.56, survivability=1.00 |
| shop | decision_trace | 10 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 10 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: ?@1,10 -> R@1,11 -> M@0,12 -> M@0,13 -> R@1,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: ?@1,10 -> R@1,11 -> M@0,12 -> M@0,13 -> R@1,14: reward=5.20, survivability=1.00 |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@1,11 -> M@0,12 -> M@0,13 -> R@1,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@1,11 -> M@0,12 -> M@0,13 -> R@1,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@0,12 -> M@0,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@0,12 -> M@0,13 -> R@1,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@1,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@1,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Clothesline | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Impatience | Flash of Steel | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@2,0 -> M@2,1 -> M@3,2 -> $@4,3 -> M@5,4 -> E@4,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@2,0 -> M@2,1 -> M@3,2 -> $@4,3 -> M@5,4 -> E@4,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Bloodletting | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.44: M@2,1 -> M@3,2 -> $@4,3 -> M@5,4 -> E@4,5 -> R@4,6: reward=9.44, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.44: M@2,1 -> M@3,2 -> $@4,3 -> M@5,4 -> E@4,5 -> R@4,6: reward=9.44, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.94: M@3,2 -> $@4,3 -> M@5,4 -> E@4,5 -> ?@3,6 -> E@4,7: reward=10.94, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.94: M@3,2 -> $@4,3 -> M@5,4 -> E@4,5 -> ?@3,6 -> E@4,7: reward=10.94, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.62: $@4,3 -> M@5,4 -> E@4,5 -> R@4,6 -> E@4,7 -> T@3,8: reward=11.62, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.62: $@4,3 -> M@5,4 -> E@4,5 -> R@4,6 -> E@4,7 -> T@3,8: reward=11.62, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Clothesline | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,4 -> R@2,5 -> ?@3,6 -> E@4,7 -> T@3,8 -> ?@3,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,4 -> R@2,5 -> ?@3,6 -> E@4,7 -> T@3,8 -> ?@3,9: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: R@2,5 -> ?@3,6 -> E@4,7 -> T@3,8 -> ?@3,9 -> M@3,10: reward=7.00, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: R@2,5 -> ?@3,6 -> E@4,7 -> T@3,8 -> ?@3,9 -> M@3,10: reward=7.00, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.25: ?@3,6 -> E@4,7 -> T@3,8 -> ?@3,9 -> M@3,10 -> E@2,11: reward=9.50, survivability=0.92 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.25: ?@3,6 -> E@4,7 -> T@3,8 -> ?@3,9 -> M@3,10 -> E@2,11: reward=9.50, survivability=0.92 |
| event | decision_trace | 7 | complete | bottled_style | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: M@2,7 -> T@2,8 -> ?@1,9 -> R@2,10 -> E@2,11 -> $@1,12: reward=11.10, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: M@2,7 -> T@2,8 -> ?@1,9 -> R@2,10 -> E@2,11 -> $@1,12: reward=11.10, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: T@2,8 -> ?@1,9 -> R@2,10 -> E@2,11 -> $@1,12 -> M@1,13: reward=10.00, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: T@2,8 -> ?@1,9 -> R@2,10 -> E@2,11 -> $@1,12 -> M@1,13: reward=10.00, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,9 -> R@2,10 -> E@2,11 -> $@1,12 -> M@1,13 -> R@0,14: reward=8.50, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,9 -> R@2,10 -> E@2,11 -> $@1,12 -> M@1,13 -> R@0,14: reward=8.50, survivability=1.00 |
| event | decision_trace | 10 | complete | bottled_style | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: R@2,10 -> E@2,11 -> $@1,12 -> M@1,13 -> R@0,14: reward=7.50, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: R@2,10 -> E@2,11 -> $@1,12 -> M@1,13 -> R@0,14: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: ?@0,11 -> ?@0,12 -> M@1,13 -> R@0,14: reward=3.00, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: ?@0,11 -> ?@0,12 -> M@1,13 -> R@0,14: reward=3.00, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Whirlwind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@0,12 -> M@1,13 -> R@0,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@0,12 -> M@1,13 -> R@0,14: reward=2.00, survivability=1.00 |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Take | choose 0: Take | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 2: Hide | choose 0: Outrun | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@1,13 -> R@0,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@1,13 -> R@0,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Metallicize | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@5,0 -> M@6,1 -> ?@6,2 -> M@6,3 -> $@5,4 -> E@6,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@5,0 -> M@6,1 -> ?@6,2 -> M@6,3 -> $@5,4 -> E@6,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Dual Wield | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@3,1 -> ?@3,2 -> M@3,3 -> M@2,4 -> R@2,5 -> M@2,6: reward=6.10, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@3,1 -> ?@3,2 -> M@3,3 -> M@2,4 -> R@2,5 -> M@2,6: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Clothesline | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@3,2 -> M@3,3 -> M@2,4 -> R@2,5 -> M@2,6 -> ?@3,7: reward=6.10, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@3,2 -> M@3,3 -> M@2,4 -> R@2,5 -> M@2,6 -> ?@3,7: reward=6.10, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Search | choose 0: Search | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,3 -> M@2,4 -> R@2,5 -> M@2,6 -> ?@3,7 -> T@3,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,3 -> M@2,4 -> R@2,5 -> M@2,6 -> ?@3,7 -> T@3,8: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@2,4 -> R@2,5 -> M@2,6 -> ?@3,7 -> T@3,8 -> R@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@2,4 -> R@2,5 -> M@2,6 -> ?@3,7 -> T@3,8 -> R@2,9: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Immolate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 5 | complete | bottled_style | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@2,5 -> M@2,6 -> ?@3,7 -> T@3,8 -> R@2,9 -> M@1,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@2,5 -> M@2,6 -> ?@3,7 -> T@3,8 -> R@2,9 -> M@1,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@2,6 -> ?@3,7 -> T@3,8 -> R@2,9 -> M@1,10 -> M@2,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@2,6 -> ?@3,7 -> T@3,8 -> R@2,9 -> M@1,10 -> M@2,11: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.56: ?@3,7 -> T@3,8 -> R@2,9 -> M@1,10 -> M@2,11 -> $@3,12: reward=9.56, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.56: ?@3,7 -> T@3,8 -> R@2,9 -> M@1,10 -> M@2,11 -> $@3,12: reward=9.56, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Corruption | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: T@3,8 -> R@2,9 -> M@1,10 -> M@2,11 -> $@3,12 -> M@3,13: reward=8.50, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: T@3,8 -> R@2,9 -> M@1,10 -> M@2,11 -> $@3,12 -> M@3,13: reward=8.50, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@2,9 -> M@1,10 -> M@2,11 -> $@3,12 -> M@3,13 -> R@3,14: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@2,9 -> M@1,10 -> M@2,11 -> $@3,12 -> M@3,13 -> R@3,14: reward=8.10, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@1,10 -> M@2,11 -> $@3,12 -> M@3,13 -> R@3,14: reward=8.10, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@1,10 -> M@2,11 -> $@3,12 -> M@3,13 -> R@3,14: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Flame Barrier | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@2,11 -> $@3,12 -> M@3,13 -> R@3,14: reward=7.10, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@2,11 -> $@3,12 -> M@3,13 -> R@3,14: reward=7.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Anger | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: $@3,12 -> M@3,13 -> R@3,14: reward=5.00, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: $@3,12 -> M@3,13 -> R@3,14: reward=5.00, survivability=1.00 |
| shop | decision_trace | 13 | complete | bottled_style | Membership Card | Membership Card | high | Bottled shop priority buys affordable Membership Card. |
| shop | decision_trace | 13 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 13 | complete | bottled_style | wait | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 13 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@3,13 -> R@3,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@3,13 -> R@3,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Impervious | Impervious | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@4,0 -> ?@4,1 -> ?@4,2 -> M@3,3 -> ?@4,4 -> E@4,5: reward=9.00, survivability=1.00 |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@4,0 -> ?@4,1 -> ?@4,2 -> M@3,3 -> ?@4,4 -> E@4,5: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.19: $@5,1 -> ?@4,2 -> M@3,3 -> ?@4,4 -> E@4,5 -> R@3,6: reward=8.44, survivability=0.98 |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.19: $@5,1 -> ?@4,2 -> M@3,3 -> ?@4,4 -> E@4,5 -> R@3,6: reward=8.44, survivability=0.98 |
| event | decision_trace | 19 | complete | bottled_style | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 19 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.04: ?@4,2 -> $@4,3 -> M@5,4 -> R@6,5 -> ?@6,6 -> M@5,7: reward=8.04, survivability=1.00 |
| route | decision_trace | 19 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.04: ?@4,2 -> $@4,3 -> M@5,4 -> R@6,5 -> ?@6,6 -> M@5,7: reward=8.04, survivability=1.00 |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@4,0 -> $@3,1 -> ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@4,0 -> $@3,1 -> ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,1 -> ?@0,2 -> M@0,3 -> M@1,4 -> R@1,5 -> E@0,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,1 -> ?@0,2 -> M@0,3 -> M@1,4 -> R@1,5 -> E@0,6: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@0,2 -> M@0,3 -> M@1,4 -> R@1,5 -> E@0,6 -> M@0,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@0,2 -> M@0,3 -> M@1,4 -> R@1,5 -> E@0,6 -> M@0,7: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Reckless Charge | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@0,3 -> M@1,4 -> R@1,5 -> E@0,6 -> M@0,7 -> T@0,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@0,3 -> M@1,4 -> R@1,5 -> E@0,6 -> M@0,7 -> T@0,8: reward=8.10, survivability=1.00 |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,4 -> R@2,5 -> E@1,6 -> M@0,7 -> T@0,8 -> M@0,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,4 -> R@2,5 -> E@1,6 -> M@0,7 -> T@0,8 -> M@0,9: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@2,5 -> E@1,6 -> M@0,7 -> T@0,8 -> M@0,9 -> ?@0,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@2,5 -> E@1,6 -> M@0,7 -> T@0,8 -> M@0,9 -> ?@0,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.34: M@2,6 -> ?@3,7 -> T@2,8 -> M@2,9 -> R@2,10 -> $@3,11: reward=9.34, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.34: M@2,6 -> ?@3,7 -> T@2,8 -> M@2,9 -> R@2,10 -> $@3,11: reward=9.34, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.44: ?@3,7 -> T@2,8 -> M@2,9 -> R@2,10 -> $@3,11 -> ?@2,12: reward=9.44, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.44: ?@3,7 -> T@2,8 -> M@2,9 -> R@2,10 -> $@3,11 -> ?@2,12: reward=9.44, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Immolate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: T@2,8 -> M@2,9 -> R@2,10 -> $@3,11 -> ?@2,12 -> M@1,13: reward=9.60, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: T@2,8 -> M@2,9 -> R@2,10 -> $@3,11 -> ?@2,12 -> M@1,13: reward=9.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@4,9 -> M@5,10 -> ?@6,11 -> E@5,12 -> M@4,13 -> R@4,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@4,9 -> M@5,10 -> ?@6,11 -> E@5,12 -> M@4,13 -> R@4,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@5,10 -> ?@6,11 -> E@5,12 -> M@4,13 -> R@4,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@5,10 -> ?@6,11 -> E@5,12 -> M@4,13 -> R@4,14: reward=5.50, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | bottled_style | Inflame | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 11 | complete | bottled_style | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: ?@6,11 -> E@5,12 -> M@4,13 -> R@4,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: ?@6,11 -> E@5,12 -> M@4,13 -> R@4,14: reward=4.50, survivability=1.00 |
| event | decision_trace | 12 | complete | bottled_style | choose 1: Purify | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: E@5,12 -> M@4,13 -> R@4,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: E@5,12 -> M@4,13 -> R@4,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@6,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@6,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@6,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@6,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Corruption | Reaper | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. |
| route | decision_trace | 17 | complete | bottled_style | choice 0 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 10.25: M@3,0 -> ?@4,1 -> $@4,2 -> ?@5,3 -> M@6,4 -> E@5,5: reward=11.50, survivability=0.92 |
| route | decision_trace | 17 | complete | bottled_style | choice 0 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 10.25: M@3,0 -> ?@4,1 -> $@4,2 -> ?@5,3 -> M@6,4 -> E@5,5: reward=11.50, survivability=0.92 |
| card_reward | decision_trace | 18 | complete | bottled_style | Clothesline | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@0,1 -> M@0,2 -> M@0,3 -> M@1,4 -> R@1,5 -> M@2,6: reward=5.00, survivability=1.00 |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@0,1 -> M@0,2 -> M@0,3 -> M@1,4 -> R@1,5 -> M@2,6: reward=5.00, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | bottled_style | Inflame | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 19 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability -4.50: ?@1,2 -> M@0,3 -> ?@0,4 -> E@0,5 -> M@0,6 -> ?@1,7: reward=9.00, survivability=0.10 |
| route | decision_trace | 19 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability -4.50: ?@1,2 -> M@0,3 -> ?@0,4 -> E@0,5 -> M@0,6 -> ?@1,7: reward=9.00, survivability=0.10 |
| event | decision_trace | 20 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 20 | complete | bottled_style | choose 0: Adjustments | choose 0: Adjustments | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 20 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.00: ?@2,3 -> M@1,4 -> R@1,5 -> M@2,6 -> M@2,7 -> T@1,8: reward=6.00, survivability=1.00 |
| route | decision_trace | 20 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.00: ?@2,3 -> M@1,4 -> R@1,5 -> M@2,6 -> M@2,7 -> T@1,8: reward=6.00, survivability=1.00 |

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision candidate is available yet.
