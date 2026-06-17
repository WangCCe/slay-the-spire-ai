# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 413
- Differences: 280
- Categories: card_reward=113, event=54, route=214, shop=32
- Evidence quality: complete=321, partial=92

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| shop | fixture:shop | 5 | complete | Anger | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| event | fixture:event | 8 | complete | choose 0: Enter | choose 1: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | fixture:route | 1 | complete | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.68: safer shop rest: reward=4.68, survivability=1.00 |
| card_reward | fixture:card_reward | 10 | complete | SKIP | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| card_reward | run:1781723341.run | 1 | partial | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 3 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 7 | partial | Second Wind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 10 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 11 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 12 | partial | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 13 | partial | Carnage | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 14 | partial | Spot Weakness | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 16 | partial | Double Tap | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 18 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 19 | partial | SKIP | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 22 | partial | Armaments | Pommel Strike+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723341.run | 24 | partial | Headbutt+1 | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781723341.run | 4 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781723341.run | 21 | partial | Paid Fearfully | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781723341.run | 20 | partial | MealTicket | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723341.run | 2 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723341.run | 20 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781723341.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781723385.run | 1 | partial | Clothesline | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723385.run | 3 | partial | Flex | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723385.run | 5 | partial | Intimidate | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781723385.run | 4 | partial | Gather Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781723385.run | 2 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781723385.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781723548.run | 1 | partial | Anger | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 2 | partial | Disarm | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 4 | partial | Bloodletting+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 7 | partial | Shrug It Off+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 8 | partial | True Grit+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 10 | partial | Carnage | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 11 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 12 | partial | Burning Pact+1 | Flame Barrier+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 14 | partial | Shrug It Off+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 15 | partial | Shockwave+1 | Shockwave+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 16 | partial | Impervious+1 | Impervious+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 18 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723548.run | 20 | partial | SKIP | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781723548.run | 19 | partial | Stole From Cult | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781723548.run | 21 | partial | Traded Relic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781723548.run | 5 | partial | Block Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723548.run | 5 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723548.run | 13 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781723548.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781723677.run | 1 | partial | Burning Pact | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 2 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 3 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 4 | partial | Whirlwind | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 7 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 10 | partial | Second Wind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 11 | partial | Heavy Blade | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 12 | partial | Second Wind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 14 | partial | Clothesline | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 16 | partial | Brutality | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 18 | partial | Cleave+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723677.run | 19 | partial | Flame Barrier+1 | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| event | run:1781723677.run | 5 | partial | Offered Basic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781723677.run | 13 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781723677.run | 20 | partial | Inject Mutagens | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1781723677.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781723833.run | 1 | partial | True Grit | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 2 | partial | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 7 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 10 | partial | Spot Weakness | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 12 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 13 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 16 | partial | Impervious | Impervious | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 18 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 19 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 20 | partial | Dark Embrace | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 21 | partial | Ghostly Armor | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 28 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 29 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781723833.run | 31 | partial | Shrug It Off+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781723833.run | 4 | partial | Entered Light | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781723833.run | 5 | partial | Touch | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781723833.run | 24 | partial | Gave Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781723833.run | 3 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723833.run | 14 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723833.run | 22 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781723833.run | 30 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781723833.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@0,1 -> M@1,2 -> ?@1,3 -> ?@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@0,1 -> M@1,2 -> ?@1,3 -> ?@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: $@0,1 -> M@1,2 -> ?@1,3 -> ?@2,4 -> E@3,5 -> R@3,6: reward=8.80, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: $@0,1 -> M@1,2 -> ?@1,3 -> ?@2,4 -> E@3,5 -> R@3,6: reward=8.80, survivability=1.00 |
| shop | decision_trace | 2 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@1,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> M@2,6 -> R@2,7: reward=6.20, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@1,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> M@2,6 -> R@2,7: reward=6.20, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@1,3 -> M@1,4 -> R@1,5 -> M@2,6 -> R@2,7 -> T@2,8: reward=6.70, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@1,3 -> M@1,4 -> R@1,5 -> M@2,6 -> R@2,7 -> T@2,8: reward=6.70, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@1,4 -> R@1,5 -> M@2,6 -> R@2,7 -> T@2,8 -> M@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@1,4 -> R@1,5 -> M@2,6 -> R@2,7 -> T@2,8 -> M@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@3,5 -> M@2,6 -> R@2,7 -> T@2,8 -> M@2,9 -> E@3,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@3,5 -> M@2,6 -> R@2,7 -> T@2,8 -> M@2,9 -> E@3,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,6 -> R@2,7 -> T@2,8 -> M@2,9 -> E@3,10 -> M@4,11: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@2,6 -> R@2,7 -> T@2,8 -> M@2,9 -> E@3,10 -> M@4,11: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@2,7 -> T@2,8 -> M@2,9 -> E@3,10 -> M@4,11 -> E@3,12: reward=9.60, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@2,7 -> T@2,8 -> M@2,9 -> E@3,10 -> M@4,11 -> E@3,12: reward=9.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: T@2,8 -> M@2,9 -> M@1,10 -> M@0,11 -> M@1,12 -> M@0,13: reward=6.50, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: T@2,8 -> M@2,9 -> M@1,10 -> M@0,11 -> M@1,12 -> M@0,13: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@2,9 -> M@1,10 -> M@0,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@2,9 -> M@1,10 -> M@0,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: M@1,10 -> M@0,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: M@1,10 -> M@0,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=5.10, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@0,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@0,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@1,12 -> M@0,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@1,12 -> M@0,13 -> R@1,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@1,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@1,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Spot Weakness | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Double Tap | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@1,0 -> $@0,1 -> M@1,2 -> ?@1,3 -> M@2,4 -> E@2,5: reward=11.00, survivability=1.00 |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@1,0 -> $@0,1 -> M@1,2 -> ?@1,3 -> M@2,4 -> E@2,5: reward=11.00, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.75: $@0,1 -> M@1,2 -> ?@1,3 -> M@2,4 -> M@3,5 -> E@3,6: reward=11.00, survivability=0.92 |
| route | decision_trace | 18 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.75: $@0,1 -> M@1,2 -> ?@1,3 -> M@2,4 -> M@3,5 -> E@3,6: reward=11.00, survivability=0.92 |
| card_reward | decision_trace | 19 | complete | skip | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: $@3,2 -> ?@3,3 -> M@2,4 -> R@1,5 -> M@2,6 -> M@3,7: reward=9.60, survivability=1.00 |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: $@3,2 -> ?@3,3 -> M@2,4 -> R@1,5 -> M@2,6 -> M@3,7: reward=9.60, survivability=1.00 |
| shop | decision_trace | 20 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 20 | complete | Meal Ticket | Meal Ticket | high | Bottled shop relic list ranks Meal Ticket as buyable. |
| shop | decision_trace | 20 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,3 -> M@2,4 -> R@1,5 -> M@2,6 -> M@3,7 -> T@4,8: reward=7.10, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,3 -> M@2,4 -> R@1,5 -> M@2,6 -> M@3,7 -> T@4,8: reward=7.10, survivability=1.00 |
| event | decision_trace | 21 | complete | choose 0: Pay | choose 0: Pay | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 21 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@3,4 -> M@3,5 -> M@2,6 -> R@2,7 -> T@3,8 -> E@2,9: reward=7.50, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@3,4 -> M@3,5 -> M@2,6 -> R@2,7 -> T@3,8 -> E@2,9: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | Armaments | Pommel Strike+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike+. |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: R@1,5 -> M@2,6 -> M@3,7 -> T@4,8 -> R@4,9 -> ?@3,10: reward=6.10, survivability=1.00 |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: R@1,5 -> M@2,6 -> M@3,7 -> T@4,8 -> R@4,9 -> ?@3,10: reward=6.10, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@2,6 -> M@3,7 -> T@4,8 -> M@3,9 -> ?@3,10 -> ?@3,11: reward=7.50, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@2,6 -> M@3,7 -> T@4,8 -> M@3,9 -> ?@3,10 -> ?@3,11: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | Headbutt+ | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 24 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.25: M@3,7 -> T@4,8 -> R@4,9 -> ?@3,10 -> M@2,11 -> E@3,12: reward=7.50, survivability=0.98 |
| route | decision_trace | 24 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.25: M@3,7 -> T@4,8 -> R@4,9 -> ?@3,10 -> M@2,11 -> E@3,12: reward=7.50, survivability=0.98 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@1,1 -> M@1,2 -> M@1,3 -> M@0,4 -> E@0,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@1,1 -> M@1,2 -> M@1,3 -> M@0,4 -> E@0,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Clothesline | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.86: $@1,1 -> M@1,2 -> M@1,3 -> M@0,4 -> E@0,5 -> ?@1,6: reward=8.86, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.86: $@1,1 -> M@1,2 -> M@1,3 -> M@0,4 -> E@0,5 -> ?@1,6: reward=8.86, survivability=1.00 |
| shop | decision_trace | 2 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,2 -> M@1,3 -> M@0,4 -> E@0,5 -> ?@1,6 -> M@2,7: reward=7.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,2 -> M@1,3 -> M@0,4 -> E@0,5 -> ?@1,6 -> M@2,7: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Flex | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,3 -> M@0,4 -> E@0,5 -> ?@1,6 -> M@2,7 -> T@1,8: reward=8.00, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,3 -> M@0,4 -> E@0,5 -> ?@1,6 -> M@2,7 -> T@1,8: reward=8.00, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Gather Gold | choose 0: Gather Gold | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.90: M@2,4 -> E@1,5 -> ?@2,6 -> M@2,7 -> T@1,8 -> $@2,9: reward=10.90, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.90: M@2,4 -> E@1,5 -> ?@2,6 -> M@2,7 -> T@1,8 -> $@2,9: reward=10.90, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Intimidate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.94: E@1,5 -> ?@2,6 -> M@2,7 -> T@1,8 -> $@2,9 -> ?@2,10: reward=10.94, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.94: E@1,5 -> ?@2,6 -> M@2,7 -> T@1,8 -> $@2,9 -> ?@2,10: reward=10.94, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.24: M@3,6 -> M@2,7 -> T@1,8 -> $@2,9 -> ?@2,10 -> R@1,11: reward=9.24, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.24: M@3,6 -> M@2,7 -> T@1,8 -> $@2,9 -> ?@2,10 -> R@1,11: reward=9.24, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Enemies in your next three combats have 1 HP | choose 0: Enemies in your next three combats have 1 HP | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.68: M@0,0 -> M@1,1 -> M@2,2 -> M@1,3 -> $@2,4 -> E@2,5: reward=9.68, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.68: M@0,0 -> M@1,1 -> M@2,2 -> M@1,3 -> $@2,4 -> E@2,5: reward=9.68, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Anger | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.32: M@2,1 -> M@2,2 -> M@1,3 -> $@2,4 -> E@2,5 -> $@2,6: reward=9.32, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.32: M@2,1 -> M@2,2 -> M@1,3 -> $@2,4 -> E@2,5 -> $@2,6: reward=9.32, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Disarm | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.22: M@2,2 -> M@1,3 -> $@2,4 -> E@2,5 -> $@2,6 -> ?@3,7: reward=9.22, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.22: M@2,2 -> M@1,3 -> $@2,4 -> E@2,5 -> $@2,6 -> ?@3,7: reward=9.22, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.42: M@2,3 -> $@2,4 -> E@2,5 -> $@2,6 -> ?@3,7 -> T@2,8: reward=9.42, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.42: M@2,3 -> $@2,4 -> E@2,5 -> $@2,6 -> ?@3,7 -> T@2,8: reward=9.42, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Bloodletting+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.46: $@2,4 -> E@2,5 -> $@2,6 -> ?@3,7 -> T@2,8 -> M@1,9: reward=9.46, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.46: $@2,4 -> E@2,5 -> $@2,6 -> ?@3,7 -> T@2,8 -> M@1,9: reward=9.46, survivability=1.00 |
| shop | decision_trace | 5 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 5 | complete | Block Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 5 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.92: E@2,5 -> $@2,6 -> ?@3,7 -> T@2,8 -> M@1,9 -> M@1,10: reward=7.92, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.92: E@2,5 -> $@2,6 -> ?@3,7 -> T@2,8 -> M@1,9 -> M@1,10: reward=7.92, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,6 -> ?@3,7 -> T@2,8 -> M@1,9 -> M@1,10 -> E@0,11: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,6 -> ?@3,7 -> T@2,8 -> M@1,9 -> M@1,10 -> E@0,11: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Shrug It Off+ | Shrug It Off+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off+. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@3,7 -> T@2,8 -> M@1,9 -> M@1,10 -> E@0,11 -> ?@1,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@3,7 -> T@2,8 -> M@1,9 -> M@1,10 -> E@0,11 -> ?@1,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | True Grit+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@2,8 -> M@1,9 -> M@1,10 -> E@0,11 -> ?@1,12 -> ?@0,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@2,8 -> M@1,9 -> M@1,10 -> E@0,11 -> ?@1,12 -> ?@0,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,9 -> M@1,10 -> E@0,11 -> ?@1,12 -> ?@0,13 -> R@0,14: reward=7.60, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,9 -> M@1,10 -> E@0,11 -> ?@1,12 -> ?@0,13 -> R@0,14: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.42: M@1,10 -> M@1,11 -> $@2,12 -> M@2,13 -> R@2,14: reward=6.42, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.42: M@1,10 -> M@1,11 -> $@2,12 -> M@2,13 -> R@2,14: reward=6.42, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.32: M@1,11 -> $@2,12 -> M@2,13 -> R@2,14: reward=5.32, survivability=1.00 |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.32: M@1,11 -> $@2,12 -> M@2,13 -> R@2,14: reward=5.32, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Burning Pact+ | Flame Barrier+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier+. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.34: $@2,12 -> M@2,13 -> R@2,14: reward=4.34, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.34: $@2,12 -> M@2,13 -> R@2,14: reward=4.34, survivability=1.00 |
| shop | decision_trace | 13 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 13 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@2,13 -> R@2,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@2,13 -> R@2,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Shrug It Off+ | Shrug It Off+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off+. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| card_reward | decision_trace | 15 | complete | Shockwave+ | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Metallicize | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 16 | complete | Impervious+ | Impervious+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious+. |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: M@1,0 -> ?@2,1 -> M@3,2 -> $@3,3 -> M@4,4 -> E@5,5: reward=9.64, survivability=1.00 |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: M@1,0 -> ?@2,1 -> M@3,2 -> $@3,3 -> M@4,4 -> E@5,5: reward=9.64, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Evolve | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 18 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.44: ?@2,1 -> ?@2,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> $@0,6: reward=7.44, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.44: ?@2,1 -> ?@2,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> $@0,6: reward=7.44, survivability=1.00 |
| event | decision_trace | 19 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | choose 0: Smash and Grab | choose 0: Smash and Grab | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 19 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.17: ?@2,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> $@0,6 -> E@1,7: reward=10.42, survivability=0.98 |
| route | decision_trace | 19 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.17: ?@2,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> $@0,6 -> E@1,7: reward=10.42, survivability=0.98 |
| card_reward | decision_trace | 20 | complete | skip | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 20 | complete | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.26: $@3,3 -> M@4,4 -> R@4,5 -> ?@3,6 -> ?@4,7 -> T@5,8: reward=8.26, survivability=1.00 |
| route | decision_trace | 20 | complete | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.26: $@3,3 -> M@4,4 -> R@4,5 -> ?@3,6 -> ?@4,7 -> T@5,8: reward=8.26, survivability=1.00 |
| event | decision_trace | 21 | complete | choose 0: Offer: Neow's Lament | choose 0: Offer: Neow's Lament | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@4,4 -> R@4,5 -> ?@3,6 -> ?@4,7 -> T@5,8 -> M@5,9: reward=6.50, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@4,4 -> R@4,5 -> ?@3,6 -> ?@4,7 -> T@5,8 -> M@5,9: reward=6.50, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,0 -> M@2,1 -> ?@3,2 -> M@4,3 -> M@3,4 -> E@4,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,0 -> M@2,1 -> ?@3,2 -> M@4,3 -> M@3,4 -> E@4,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@2,1 -> ?@3,2 -> M@4,3 -> M@3,4 -> E@4,5 -> R@4,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@2,1 -> ?@3,2 -> M@4,3 -> M@3,4 -> E@4,5 -> R@4,6: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.50: ?@3,2 -> M@4,3 -> M@3,4 -> E@4,5 -> M@5,6 -> $@5,7: reward=10.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.50: ?@3,2 -> M@4,3 -> M@3,4 -> E@4,5 -> M@5,6 -> $@5,7: reward=10.50, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.40: M@2,3 -> M@1,4 -> R@0,5 -> M@1,6 -> $@1,7 -> T@1,8: reward=9.40, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.40: M@2,3 -> M@1,4 -> R@0,5 -> M@1,6 -> $@1,7 -> T@1,8: reward=9.40, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Whirlwind | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.40: M@1,4 -> R@0,5 -> M@1,6 -> $@1,7 -> T@1,8 -> ?@2,9: reward=9.40, survivability=1.00 |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.40: M@1,4 -> R@0,5 -> M@1,6 -> $@1,7 -> T@1,8 -> ?@2,9: reward=9.40, survivability=1.00 |
| event | decision_trace | 5 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Offer | choose 0: Offer | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.60: R@2,5 -> M@1,6 -> $@1,7 -> T@1,8 -> ?@2,9 -> E@3,10: reward=10.60, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.60: R@2,5 -> M@1,6 -> $@1,7 -> T@1,8 -> ?@2,9 -> E@3,10: reward=10.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@1,6 -> $@1,7 -> T@1,8 -> ?@2,9 -> M@1,10 -> M@1,11: reward=9.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@1,6 -> $@1,7 -> T@1,8 -> ?@2,9 -> M@1,10 -> M@1,11: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.40: $@1,7 -> T@1,8 -> ?@2,9 -> E@3,10 -> M@3,11 -> E@2,12: reward=11.90, survivability=0.97 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.40: $@1,7 -> T@1,8 -> ?@2,9 -> E@3,10 -> M@3,11 -> E@2,12: reward=11.90, survivability=0.97 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@0,8 -> ?@1,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@1,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@0,8 -> ?@1,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@1,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@1,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@1,13 -> R@0,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@1,9 -> M@1,10 -> ?@2,11 -> E@2,12 -> ?@1,13 -> R@0,14: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@1,10 -> ?@2,11 -> E@2,12 -> ?@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@1,10 -> ?@2,11 -> E@2,12 -> ?@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Heavy Blade | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 11 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: ?@2,11 -> E@2,12 -> ?@1,13 -> R@0,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: ?@2,11 -> E@2,12 -> ?@1,13 -> R@0,14: reward=4.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@0,12 -> M@0,13 -> R@0,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@0,12 -> M@0,13 -> R@0,14: reward=2.00, survivability=1.00 |
| event | decision_trace | 13 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@0,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@0,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Clothesline | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Brutality | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@0,0 -> M@1,1 -> ?@2,2 -> $@3,3 -> M@2,4 -> R@3,5: reward=9.60, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@0,0 -> M@1,1 -> ?@2,2 -> $@3,3 -> M@2,4 -> R@3,5: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Cleave+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@4,1 -> ?@3,2 -> M@4,3 -> ?@3,4 -> R@3,5 -> ?@3,6: reward=6.50, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@4,1 -> ?@3,2 -> M@4,3 -> ?@3,4 -> R@3,5 -> ?@3,6: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Flame Barrier+ | Flame Barrier+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier+. |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability -0.68: ?@3,2 -> M@4,3 -> ?@3,4 -> R@3,5 -> ?@3,6 -> M@3,7: reward=6.50, survivability=0.52 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability -0.68: ?@3,2 -> M@4,3 -> ?@3,4 -> R@3,5 -> ?@3,6 -> M@3,7: reward=6.50, survivability=0.52 |
| event | decision_trace | 20 | complete | choose 2: Ingest Mutagens | choose 0: Test J.A.X. | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.20: M@4,3 -> ?@3,4 -> R@3,5 -> M@2,6 -> M@3,7 -> T@2,8: reward=6.00, survivability=0.61 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.20: M@4,3 -> ?@3,4 -> R@3,5 -> M@2,6 -> M@3,7 -> T@2,8: reward=6.00, survivability=0.61 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@2,0 -> $@3,1 -> M@3,2 -> M@2,3 -> M@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@2,0 -> $@3,1 -> M@3,2 -> M@2,3 -> M@2,4 -> E@3,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | True Grit | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@4,1 -> M@3,2 -> M@2,3 -> M@2,4 -> E@3,5 -> M@3,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@4,1 -> M@3,2 -> M@2,3 -> M@2,4 -> E@3,5 -> M@3,6: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 2 | complete | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.20: $@5,2 -> M@5,3 -> M@4,4 -> E@3,5 -> M@3,6 -> R@2,7: reward=9.20, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.20: $@5,2 -> M@5,3 -> M@4,4 -> E@3,5 -> M@3,6 -> R@2,7: reward=9.20, survivability=1.00 |
| shop | decision_trace | 3 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@5,3 -> M@4,4 -> E@3,5 -> M@3,6 -> R@2,7 -> T@1,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@5,3 -> M@4,4 -> E@3,5 -> M@3,6 -> R@2,7 -> T@1,8: reward=8.10, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Enter | choose 0: Enter | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@5,4 -> R@4,5 -> M@3,6 -> M@3,7 -> T@3,8 -> E@3,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@5,4 -> R@4,5 -> M@3,6 -> M@3,7 -> T@3,8 -> E@3,9: reward=8.10, survivability=1.00 |
| event | decision_trace | 5 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Touch | choose 0: Touch | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@4,5 -> M@3,6 -> R@2,7 -> T@1,8 -> M@1,9 -> E@0,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@4,5 -> M@3,6 -> R@2,7 -> T@1,8 -> M@1,9 -> E@0,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@3,6 -> R@2,7 -> T@1,8 -> M@1,9 -> E@0,10 -> ?@1,11: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@3,6 -> R@2,7 -> T@1,8 -> M@1,9 -> E@0,10 -> ?@1,11: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@2,7 -> T@1,8 -> M@1,9 -> E@0,10 -> ?@1,11 -> M@1,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@2,7 -> T@1,8 -> M@1,9 -> E@0,10 -> ?@1,11 -> M@1,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@1,8 -> M@1,9 -> E@0,10 -> ?@1,11 -> M@1,12 -> $@1,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@1,8 -> M@1,9 -> E@0,10 -> ?@1,11 -> M@1,12 -> $@1,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.20: M@2,9 -> R@2,10 -> M@2,11 -> M@1,12 -> $@1,13 -> R@1,14: reward=9.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.20: M@2,9 -> R@2,10 -> M@2,11 -> M@1,12 -> $@1,13 -> R@1,14: reward=9.20, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Spot Weakness | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.10: R@2,10 -> M@2,11 -> M@1,12 -> $@1,13 -> R@1,14: reward=7.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.10: R@2,10 -> M@2,11 -> M@1,12 -> $@1,13 -> R@1,14: reward=7.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.00: M@2,11 -> M@1,12 -> $@1,13 -> R@1,14: reward=6.00, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.00: M@2,11 -> M@1,12 -> $@1,13 -> R@1,14: reward=6.00, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Shockwave | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@1,12 -> $@1,13 -> R@1,14: reward=5.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@1,12 -> $@1,13 -> R@1,14: reward=5.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.10: $@1,13 -> R@1,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.10: $@1,13 -> R@1,14: reward=5.10, survivability=1.00 |
| shop | decision_trace | 14 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Impervious | Impervious | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. |
| route | decision_trace | 17 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: M@1,0 -> M@2,1 -> M@2,2 -> M@3,3 -> $@4,4 -> E@4,5: reward=10.50, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: M@1,0 -> M@2,1 -> M@2,2 -> M@3,3 -> $@4,4 -> E@4,5: reward=10.50, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@3,1 -> M@2,2 -> M@3,3 -> $@4,4 -> E@4,5 -> ?@3,6: reward=11.00, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@3,1 -> M@2,2 -> M@3,3 -> $@4,4 -> E@4,5 -> ?@3,6: reward=11.00, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@3,2 -> M@3,3 -> ?@2,4 -> R@3,5 -> ?@3,6 -> E@2,7: reward=9.10, survivability=1.00 |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@3,2 -> M@3,3 -> ?@2,4 -> R@3,5 -> ?@3,6 -> E@2,7: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 20 | complete | Dark Embrace | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@3,3 -> ?@2,4 -> R@3,5 -> ?@3,6 -> E@2,7 -> T@1,8: reward=9.10, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@3,3 -> ?@2,4 -> R@3,5 -> ?@3,6 -> E@2,7 -> T@1,8: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 21 | complete | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: ?@2,4 -> R@3,5 -> ?@3,6 -> ?@4,7 -> T@3,8 -> ?@3,9: reward=8.60, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: ?@2,4 -> R@3,5 -> ?@3,6 -> ?@4,7 -> T@3,8 -> ?@3,9: reward=8.60, survivability=1.00 |
| shop | decision_trace | 22 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 22 | complete | leave | Anchor | high | Bottled shop relic list ranks Anchor as buyable. |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: R@3,5 -> ?@3,6 -> ?@4,7 -> T@3,8 -> ?@3,9 -> ?@2,10: reward=8.60, survivability=1.00 |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: R@3,5 -> ?@3,6 -> ?@4,7 -> T@3,8 -> ?@3,9 -> ?@2,10: reward=8.60, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@3,6 -> ?@4,7 -> T@3,8 -> ?@3,9 -> ?@2,10 -> M@2,11: reward=8.50, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@3,6 -> ?@4,7 -> T@3,8 -> ?@3,9 -> ?@2,10 -> M@2,11: reward=8.50, survivability=1.00 |
| event | decision_trace | 24 | complete | choose 0: Offer Gold | choose 0: Offer Gold | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 24 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 24 | complete | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@4,7 -> T@3,8 -> ?@3,9 -> ?@2,10 -> M@2,11 -> ?@2,12: reward=8.50, survivability=1.00 |
| route | decision_trace | 24 | complete | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@4,7 -> T@3,8 -> ?@3,9 -> ?@2,10 -> M@2,11 -> ?@2,12: reward=8.50, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@3,9 -> ?@2,10 -> M@2,11 -> ?@2,12 -> M@2,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@3,9 -> ?@2,10 -> M@2,11 -> ?@2,12 -> M@2,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@3,9 -> ?@2,10 -> M@2,11 -> ?@2,12 -> M@2,13 -> R@1,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@3,9 -> ?@2,10 -> M@2,11 -> ?@2,12 -> M@2,13 -> R@1,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: ?@2,10 -> M@2,11 -> ?@2,12 -> M@2,13 -> R@1,14: reward=5.00, survivability=1.00 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.00: ?@2,10 -> M@2,11 -> ?@2,12 -> M@2,13 -> R@1,14: reward=5.00, survivability=1.00 |
| card_reward | decision_trace | 28 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@2,11 -> ?@2,12 -> M@2,13 -> R@1,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@2,11 -> ?@2,12 -> M@2,13 -> R@1,14: reward=3.50, survivability=1.00 |
| card_reward | decision_trace | 29 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 29 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: ?@2,12 -> M@2,13 -> R@1,14: reward=2.50, survivability=1.00 |
| route | decision_trace | 29 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: ?@2,12 -> M@2,13 -> R@1,14: reward=2.50, survivability=1.00 |
| shop | decision_trace | 30 | complete | purge | Perfected Strike | high | Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. |
| shop | decision_trace | 30 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 30 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@2,13 -> R@1,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 30 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@2,13 -> R@1,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 31 | complete | Shrug It Off+ | Shrug It Off+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off+. |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

1. **route floor ?**: current `choice 1` vs reference `choice 0` (high). Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@1,1 -> M@1,2 -> M@1,3 -> M@0,4 -> E@0,5: reward=8.78, survivability=1.00 Repeated 2x in non-fixture evidence.
2. **card_reward floor 1**: current `Anger` vs reference `Thunderclap` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Repeated 5x in non-fixture evidence.
3. **card_reward floor 1**: current `Clothesline` vs reference `Twin Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Repeated 4x in non-fixture evidence.
4. **card_reward floor 4**: current `Whirlwind` vs reference `Pommel Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Repeated 2x in non-fixture evidence.
5. **card_reward floor 1**: current `Burning Pact` vs reference `skip` (medium). Bottled card reward handler skips when no desired card is offered. Repeated 28x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
