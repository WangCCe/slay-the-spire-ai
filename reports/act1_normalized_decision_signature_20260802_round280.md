# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 288
- Differences: 62
- Categories: card_reward=38, event=60, route=176, shop=14
- Evidence quality: complete=280, partial=8
- Oracle modes: bottled_style=288

## Comparison Rows

| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|---|
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.68: M@3,0 -> M@3,1 -> M@4,2 -> M@4,3 -> $@4,4 -> E@5,5: reward=9.68, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 0 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.68: M@3,0 -> M@3,1 -> M@4,2 -> M@4,3 -> $@4,4 -> E@5,5: reward=9.68, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,1 -> M@0,2 -> ?@0,3 -> ?@0,4 -> R@0,5 -> ?@0,6: reward=6.10, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,1 -> M@0,2 -> ?@0,3 -> ?@0,4 -> R@0,5 -> ?@0,6: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,2 -> ?@0,3 -> ?@0,4 -> R@0,5 -> ?@0,6 -> M@0,7: reward=6.10, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,2 -> ?@0,3 -> ?@0,4 -> R@0,5 -> ?@0,6 -> M@0,7: reward=6.10, survivability=1.00 |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@1,3 -> ?@0,4 -> R@0,5 -> ?@0,6 -> M@0,7 -> T@1,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@1,3 -> ?@0,4 -> R@0,5 -> ?@0,6 -> M@0,7 -> T@1,8: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@0,4 -> R@0,5 -> ?@0,6 -> M@0,7 -> T@1,8 -> E@2,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@0,4 -> R@0,5 -> ?@0,6 -> M@0,7 -> T@1,8 -> E@2,9: reward=8.10, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 2: Grow | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@0,5 -> ?@0,6 -> M@0,7 -> T@1,8 -> E@2,9 -> M@1,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@0,5 -> ?@0,6 -> M@0,7 -> T@1,8 -> E@2,9 -> M@1,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@0,6 -> M@0,7 -> T@1,8 -> E@2,9 -> M@1,10 -> R@1,11: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@0,6 -> M@0,7 -> T@1,8 -> E@2,9 -> M@1,10 -> R@1,11: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | True Grit | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,7 -> T@2,8 -> E@2,9 -> M@1,10 -> M@2,11 -> M@3,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,7 -> T@2,8 -> E@2,9 -> M@1,10 -> M@2,11 -> M@3,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@2,8 -> E@2,9 -> M@1,10 -> M@2,11 -> M@3,12 -> $@2,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@2,8 -> E@2,9 -> M@1,10 -> M@2,11 -> M@3,12 -> $@2,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@2,9 -> M@1,10 -> R@1,11 -> M@0,12 -> $@0,13 -> R@1,14: reward=9.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@2,9 -> M@1,10 -> R@1,11 -> M@0,12 -> $@0,13 -> R@1,14: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | bottled_style | Flex | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@3,10 -> ?@3,11 -> M@3,12 -> $@2,13 -> R@2,14: reward=8.10, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@3,10 -> ?@3,11 -> M@3,12 -> $@2,13 -> R@2,14: reward=8.10, survivability=1.00 |
| event | decision_trace | 11 | complete | bottled_style | choose 1: Leave | choose 1: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,11 -> M@3,12 -> $@2,13 -> R@2,14: reward=7.10, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,11 -> M@3,12 -> $@2,13 -> R@2,14: reward=7.10, survivability=1.00 |
| event | decision_trace | 12 | complete | bottled_style | choose 0: Take | choose 0: Take | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | bottled_style | choose 1: Smash | choose 0: Outrun | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@3,12 -> $@2,13 -> R@2,14: reward=5.00, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@3,12 -> $@2,13 -> R@2,14: reward=5.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Carnage | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.00: $@2,13 -> R@2,14: reward=4.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.00: $@2,13 -> R@2,14: reward=4.00, survivability=1.00 |
| shop | decision_trace | 14 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 14 | complete | bottled_style | Block Potion | Happy Flower | high | Bottled shop relic list ranks Happy Flower as buyable. |
| shop | decision_trace | 14 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Immolate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.66: M@0,0 -> $@0,1 -> ?@1,2 -> M@1,3 -> M@2,4 -> $@3,5: reward=10.66, survivability=1.00 |
| route | decision_trace | 17 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.66: M@0,0 -> $@0,1 -> ?@1,2 -> M@1,3 -> M@2,4 -> $@3,5: reward=10.66, survivability=1.00 |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | bottled_style | Trip | Trip | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Trip. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@1,0 -> $@1,1 -> M@1,2 -> ?@2,3 -> ?@3,4 -> E@3,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@1,0 -> $@1,1 -> M@1,2 -> ?@2,3 -> ?@3,4 -> E@3,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Clothesline | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: $@1,1 -> M@1,2 -> ?@2,3 -> ?@3,4 -> E@3,5 -> R@3,6: reward=8.98, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: $@1,1 -> M@1,2 -> ?@2,3 -> ?@3,4 -> E@3,5 -> R@3,6: reward=8.98, survivability=1.00 |
| shop | decision_trace | 2 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@1,2 -> ?@2,3 -> ?@3,4 -> E@3,5 -> R@3,6 -> E@3,7: reward=9.10, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@1,2 -> ?@2,3 -> ?@3,4 -> E@3,5 -> R@3,6 -> E@3,7: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: ?@2,3 -> ?@3,4 -> E@3,5 -> R@3,6 -> E@3,7 -> T@2,8: reward=9.60, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: ?@2,3 -> ?@3,4 -> E@3,5 -> R@3,6 -> E@3,7 -> T@2,8: reward=9.60, survivability=1.00 |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@3,4 -> E@3,5 -> R@3,6 -> E@3,7 -> T@2,8 -> M@2,9: reward=8.50, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@3,4 -> E@3,5 -> R@3,6 -> E@3,7 -> T@2,8 -> M@2,9: reward=8.50, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | bottled_style | Anger | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.80: R@1,5 -> ?@2,6 -> R@2,7 -> T@1,8 -> R@0,9 -> ?@0,10: reward=6.80, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.80: R@1,5 -> ?@2,6 -> R@2,7 -> T@1,8 -> R@0,9 -> ?@0,10: reward=6.80, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@2,6 -> R@2,7 -> T@1,8 -> R@0,9 -> ?@0,10 -> M@1,11: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@2,6 -> R@2,7 -> T@1,8 -> R@0,9 -> ?@0,10 -> M@1,11: reward=6.70, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@2,7 -> T@1,8 -> R@0,9 -> M@1,10 -> ?@2,11 -> E@2,12: reward=8.20, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@2,7 -> T@1,8 -> R@0,9 -> M@1,10 -> ?@2,11 -> E@2,12: reward=8.20, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@1,8 -> R@0,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@1,8 -> R@0,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@0,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@2,13 -> R@1,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@0,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@2,13 -> R@1,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@1,10 -> ?@2,11 -> E@2,12 -> ?@2,13 -> R@1,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@1,10 -> ?@2,11 -> E@2,12 -> ?@2,13 -> R@1,14: reward=5.50, survivability=1.00 |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Play | choose 0: Play | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: spin | choose 0: spin | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Prize! | choose 0: Prize! | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@1,11 -> M@0,12 -> M@1,13 -> R@1,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@1,11 -> M@0,12 -> M@1,13 -> R@1,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@0,12 -> M@1,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@0,12 -> M@1,13 -> R@1,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Offering | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@1,13 -> R@1,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@1,13 -> R@1,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Dropkick | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| card_reward | decision_trace | 14 | complete | bottled_style | Sever Soul | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | bottled_style | Double Tap | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.50: M@0,0 -> ?@1,1 -> ?@2,2 -> $@3,3 -> M@3,4 -> E@4,5: reward=11.50, survivability=1.00 |
| route | decision_trace | 17 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.50: M@0,0 -> ?@1,1 -> ?@2,2 -> $@3,3 -> M@3,4 -> E@4,5: reward=11.50, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | bottled_style | Headbutt+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: ?@1,1 -> ?@2,2 -> $@3,3 -> M@3,4 -> E@4,5 -> R@4,6: reward=10.50, survivability=1.00 |
| route | decision_trace | 18 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: ?@1,1 -> ?@2,2 -> $@3,3 -> M@3,4 -> E@4,5 -> R@4,6: reward=10.50, survivability=1.00 |
| event | decision_trace | 19 | complete | bottled_style | choose 0: Offer Gold | choose 0: Offer Gold | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 19 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.70: ?@2,2 -> $@3,3 -> M@3,4 -> R@2,5 -> M@2,6 -> R@1,7: reward=9.70, survivability=1.00 |
| route | decision_trace | 19 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.70: ?@2,2 -> $@3,3 -> M@3,4 -> R@2,5 -> M@2,6 -> R@1,7: reward=9.70, survivability=1.00 |
| event | decision_trace | 20 | complete | bottled_style | choose 1: Leave | choose 1: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| event | decision_trace | 20 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 20 | complete | bottled_style | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 10.50: $@3,3 -> M@3,4 -> E@4,5 -> R@4,6 -> ?@5,7 -> T@4,8: reward=10.50, survivability=1.00 |
| route | decision_trace | 20 | complete | bottled_style | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 10.50: $@3,3 -> M@3,4 -> E@4,5 -> R@4,6 -> ?@5,7 -> T@4,8: reward=10.50, survivability=1.00 |
| event | decision_trace | 21 | complete | bottled_style | choose 1: Fight! | choose 0: Pay | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 21 | complete | bottled_style | Iron Wave | Perfected Strike+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike+. |
| route | decision_trace | 21 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.80: M@2,4 -> R@2,5 -> M@2,6 -> R@1,7 -> T@1,8 -> R@0,9: reward=6.80, survivability=1.00 |
| route | decision_trace | 21 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.80: M@2,4 -> R@2,5 -> M@2,6 -> R@1,7 -> T@1,8 -> R@0,9: reward=6.80, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | bottled_style | Second Wind | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 22 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: R@2,5 -> M@2,6 -> R@1,7 -> T@1,8 -> R@0,9 -> ?@0,10: reward=6.20, survivability=1.00 |
| route | decision_trace | 22 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: R@2,5 -> M@2,6 -> R@1,7 -> T@1,8 -> R@0,9 -> ?@0,10: reward=6.20, survivability=1.00 |
| route | decision_trace | 23 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@2,6 -> R@1,7 -> T@1,8 -> R@0,9 -> ?@0,10 -> E@1,11: reward=8.70, survivability=0.97 |
| route | decision_trace | 23 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@2,6 -> R@1,7 -> T@1,8 -> R@0,9 -> ?@0,10 -> E@1,11: reward=8.70, survivability=0.97 |
| card_reward | decision_trace | 24 | complete | bottled_style | skip | Twin Strike+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike+. |
| route | decision_trace | 24 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.35: R@1,7 -> T@1,8 -> R@0,9 -> ?@0,10 -> E@1,11 -> M@2,12: reward=7.60, survivability=0.98 |
| route | decision_trace | 24 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.35: R@1,7 -> T@1,8 -> R@0,9 -> ?@0,10 -> E@1,11 -> M@2,12: reward=7.60, survivability=0.98 |
| route | decision_trace | 25 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.12: T@1,8 -> R@0,9 -> ?@0,10 -> E@1,11 -> M@2,12 -> M@1,13: reward=8.60, survivability=0.90 |
| route | decision_trace | 25 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.12: T@1,8 -> R@0,9 -> ?@0,10 -> E@1,11 -> M@2,12 -> M@1,13: reward=8.60, survivability=0.90 |
| route | decision_trace | 26 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,9 -> ?@0,10 -> M@0,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 26 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,9 -> ?@0,10 -> M@0,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 27 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: ?@0,10 -> M@0,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 27 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: ?@0,10 -> M@0,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=5.60, survivability=1.00 |
| event | decision_trace | 28 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 28 | complete | bottled_style | choose 0: Fight | choose 0: Fight | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 28 | complete | bottled_style | choose 0: COWARDICE | choose 0: COWARDICE | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 28 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: M@0,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=3.00, survivability=1.00 |
| route | decision_trace | 28 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: M@0,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=3.00, survivability=1.00 |
| card_reward | decision_trace | 29 | complete | bottled_style | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 29 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@0,12 -> M@0,13 -> R@0,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 29 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@0,12 -> M@0,13 -> R@0,14: reward=2.00, survivability=1.00 |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@1,0 -> M@2,1 -> $@1,2 -> M@1,3 -> M@0,4 -> E@1,5: reward=9.08, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@1,0 -> M@2,1 -> $@1,2 -> M@1,3 -> M@0,4 -> E@1,5: reward=9.08, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Shrug It Off | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.24: M@2,1 -> $@1,2 -> M@1,3 -> ?@1,4 -> R@2,5 -> E@3,6: reward=9.24, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.24: M@2,1 -> $@1,2 -> M@1,3 -> ?@1,4 -> R@2,5 -> E@3,6: reward=9.24, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.72: $@1,2 -> M@1,3 -> M@0,4 -> E@1,5 -> M@1,6 -> E@1,7: reward=10.72, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.72: $@1,2 -> M@1,3 -> M@0,4 -> E@1,5 -> M@1,6 -> E@1,7: reward=10.72, survivability=1.00 |
| shop | decision_trace | 3 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@1,3 -> M@0,4 -> E@1,5 -> M@1,6 -> E@1,7 -> T@0,8: reward=9.50, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@1,3 -> M@0,4 -> E@1,5 -> M@1,6 -> E@1,7 -> T@0,8: reward=9.50, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 4 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: ?@1,4 -> R@2,5 -> M@1,6 -> E@1,7 -> T@0,8 -> E@1,9: reward=9.60, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: ?@1,4 -> R@2,5 -> M@1,6 -> E@1,7 -> T@0,8 -> E@1,9: reward=9.60, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 5 | complete | bottled_style | choose 1: Ignore | choose 0: Take and Give | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.66: R@2,5 -> M@1,6 -> E@1,7 -> T@0,8 -> E@1,9 -> $@2,10: reward=11.66, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.66: R@2,5 -> M@1,6 -> E@1,7 -> T@0,8 -> E@1,9 -> $@2,10: reward=11.66, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.56: M@1,6 -> E@1,7 -> T@0,8 -> E@1,9 -> $@2,10 -> ?@3,11: reward=11.56, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.56: M@1,6 -> E@1,7 -> T@0,8 -> E@1,9 -> $@2,10 -> ?@3,11: reward=11.56, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.56: R@0,7 -> T@0,8 -> E@1,9 -> $@2,10 -> ?@3,11 -> M@2,12: reward=8.56, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.56: R@0,7 -> T@0,8 -> E@1,9 -> $@2,10 -> ?@3,11 -> M@2,12: reward=8.56, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.56: T@0,8 -> E@1,9 -> $@2,10 -> ?@3,11 -> M@2,12 -> M@2,13: reward=9.56, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.56: T@0,8 -> E@1,9 -> $@2,10 -> ?@3,11 -> M@2,12 -> M@2,13: reward=9.56, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.06: E@1,9 -> $@2,10 -> ?@3,11 -> M@2,12 -> M@2,13 -> R@2,14: reward=8.06, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.06: E@1,9 -> $@2,10 -> ?@3,11 -> M@2,12 -> M@2,13 -> R@2,14: reward=8.06, survivability=1.00 |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Enemies in your next three combats have 1 HP | choose 0: Enemies in your next three combats have 1 HP | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@2,0 -> $@2,1 -> ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@2,0 -> $@2,1 -> ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: $@2,1 -> ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5 -> R@2,6: reward=8.80, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: $@2,1 -> ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5 -> R@2,6: reward=8.80, survivability=1.00 |
| shop | decision_trace | 2 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5 -> R@2,6 -> M@3,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@2,2 -> ?@1,3 -> M@2,4 -> E@3,5 -> R@2,6 -> M@3,7: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | bottled_style | skip | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: $@3,3 -> M@3,4 -> E@3,5 -> R@2,6 -> M@3,7 -> T@2,8: reward=8.00, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: $@3,3 -> M@3,4 -> E@3,5 -> R@2,6 -> M@3,7 -> T@2,8: reward=8.00, survivability=1.00 |
| shop | decision_trace | 4 | complete | bottled_style | Shrug It Off | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 4 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@3,4 -> E@3,5 -> R@2,6 -> M@3,7 -> T@2,8 -> E@1,9: reward=9.60, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@3,4 -> E@3,5 -> R@2,6 -> M@3,7 -> T@2,8 -> E@1,9: reward=9.60, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 1: Donut | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@3,5 -> R@2,6 -> M@3,7 -> T@2,8 -> E@1,9 -> M@0,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@3,5 -> R@2,6 -> M@3,7 -> T@2,8 -> E@1,9 -> M@0,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,6 -> M@4,7 -> T@3,8 -> R@3,9 -> ?@3,10 -> M@3,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,6 -> M@4,7 -> T@3,8 -> R@3,9 -> ?@3,10 -> M@3,11: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | bottled_style | Anger | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@4,7 -> T@3,8 -> M@2,9 -> ?@3,10 -> M@3,11 -> E@3,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@4,7 -> T@3,8 -> M@2,9 -> ?@3,10 -> M@3,11 -> E@3,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@5,8 -> M@4,9 -> M@4,10 -> M@3,11 -> E@3,12 -> M@3,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@5,8 -> M@4,9 -> M@4,10 -> M@3,11 -> E@3,12 -> M@3,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.70: R@3,9 -> ?@3,10 -> M@3,11 -> E@3,12 -> M@3,13 -> R@2,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.70: R@3,9 -> ?@3,10 -> M@3,11 -> E@3,12 -> M@3,13 -> R@2,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,10 -> M@3,11 -> E@3,12 -> M@3,13 -> R@2,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,10 -> M@3,11 -> E@3,12 -> M@3,13 -> R@2,14: reward=6.60, survivability=1.00 |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Take | choose 0: Take | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | bottled_style | choose 1: Smash | choose 0: Outrun | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: M@3,11 -> E@3,12 -> M@3,13 -> R@2,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: M@3,11 -> E@3,12 -> M@3,13 -> R@2,14: reward=4.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | bottled_style | Impervious+ | Impervious+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious+. |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.50: E@3,12 -> M@3,13 -> R@2,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.50: E@3,12 -> M@3,13 -> R@2,14: reward=3.50, survivability=1.00 |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@1,13 -> R@1,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@1,13 -> R@1,14: reward=1.00, survivability=1.00 |
| event | decision_trace | 14 | complete | bottled_style | choose 0: Stomp | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | bottled_style | choose 0: Fight | choose 0: Fight | low | Forced single available event option; not a strategic Bottled choice. |
| card_reward | decision_trace | 14 | complete | bottled_style | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Talk | choose 0: Talk | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@2,0 -> M@3,1 -> $@4,2 -> M@4,3 -> ?@4,4 -> R@3,5: reward=7.68, survivability=1.00 |
| route | decision_trace | 0 | complete | bottled_style | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@2,0 -> M@3,1 -> $@4,2 -> M@4,3 -> ?@4,4 -> R@3,5: reward=7.68, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | bottled_style | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@3,1 -> ?@2,2 -> M@1,3 -> M@1,4 -> E@1,5 -> R@0,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@3,1 -> ?@2,2 -> M@1,3 -> M@1,4 -> E@1,5 -> R@0,6: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | bottled_style | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 2 | complete | bottled_style | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.16: $@4,2 -> M@4,3 -> ?@4,4 -> R@3,5 -> E@3,6 -> M@4,7: reward=9.16, survivability=1.00 |
| route | decision_trace | 2 | complete | bottled_style | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.16: $@4,2 -> M@4,3 -> ?@4,4 -> R@3,5 -> E@3,6 -> M@4,7: reward=9.16, survivability=1.00 |
| shop | decision_trace | 3 | complete | bottled_style | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@4,3 -> ?@4,4 -> R@3,5 -> E@3,6 -> M@4,7 -> T@4,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@4,3 -> ?@4,4 -> R@3,5 -> E@3,6 -> M@4,7 -> T@4,8: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | bottled_style | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: ?@4,4 -> R@3,5 -> E@3,6 -> M@4,7 -> T@5,8 -> E@6,9: reward=9.60, survivability=1.00 |
| route | decision_trace | 4 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: ?@4,4 -> R@3,5 -> E@3,6 -> M@4,7 -> T@5,8 -> E@6,9: reward=9.60, survivability=1.00 |
| event | decision_trace | 5 | complete | bottled_style | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.36: R@3,5 -> E@3,6 -> M@4,7 -> T@5,8 -> E@6,9 -> $@5,10: reward=11.36, survivability=1.00 |
| route | decision_trace | 5 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.36: R@3,5 -> E@3,6 -> M@4,7 -> T@5,8 -> E@6,9 -> $@5,10: reward=11.36, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.16: E@3,6 -> M@4,7 -> T@5,8 -> ?@5,9 -> $@5,10 -> M@6,11: reward=9.16, survivability=1.00 |
| route | decision_trace | 6 | complete | bottled_style | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.16: E@3,6 -> M@4,7 -> T@5,8 -> ?@5,9 -> $@5,10 -> M@6,11: reward=9.16, survivability=1.00 |
| event | decision_trace | 7 | complete | bottled_style | choose 0: Continue | choose 0: Continue | low | Forced single available event option; not a strategic Bottled choice. |
| event | decision_trace | 7 | complete | bottled_style | choose 1: Ignore | choose 0: Take and Give | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.86: ?@5,7 -> T@5,8 -> ?@5,9 -> $@5,10 -> R@5,11 -> M@4,12: reward=6.86, survivability=1.00 |
| route | decision_trace | 7 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.86: ?@5,7 -> T@5,8 -> ?@5,9 -> $@5,10 -> R@5,11 -> M@4,12: reward=6.86, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | bottled_style | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.26: T@5,8 -> ?@5,9 -> $@5,10 -> R@5,11 -> M@4,12 -> M@3,13: reward=7.26, survivability=1.00 |
| route | decision_trace | 8 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.26: T@5,8 -> ?@5,9 -> $@5,10 -> R@5,11 -> M@4,12 -> M@3,13: reward=7.26, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.86: E@6,9 -> $@5,10 -> R@5,11 -> M@4,12 -> M@3,13 -> R@4,14: reward=7.86, survivability=1.00 |
| route | decision_trace | 9 | complete | bottled_style | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.86: E@6,9 -> $@5,10 -> R@5,11 -> M@4,12 -> M@3,13 -> R@4,14: reward=7.86, survivability=1.00 |
| event | decision_trace | 10 | complete | bottled_style | choose 1: Leave It | choose 1: Leave It | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 10 | complete | bottled_style | choose 0: Leave | choose 0: Leave | low | Forced single available event option; not a strategic Bottled choice. |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: $@5,10 -> R@5,11 -> M@4,12 -> M@3,13 -> R@4,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: $@5,10 -> R@5,11 -> M@4,12 -> M@3,13 -> R@4,14: reward=5.20, survivability=1.00 |
| shop | decision_trace | 11 | complete | bottled_style | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@5,11 -> M@4,12 -> M@3,13 -> R@4,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@5,11 -> M@4,12 -> M@3,13 -> R@4,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@4,12 -> M@3,13 -> R@4,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@4,12 -> M@3,13 -> R@4,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | bottled_style | Impatience | Flash of Steel | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@4,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@4,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | bottled_style | Intimidate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | bottled_style | choice 0 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | bottled_style | choice 0 | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Normalized Review Candidates

- Signature schema: `v1`
- These groups are diagnostic review evidence, not gameplay repair recommendations.
- Excluded rows: insufficient_distinct_occurrences=29, matched=226, retry_duplicate=15, unsupported_confidence=18

No normalized review group has two independent eligible occurrences yet.

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision candidate is available yet.
