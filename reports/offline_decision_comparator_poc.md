# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 385
- Differences: 234
- Categories: card_reward=99, event=65, route=189, shop=32
- Evidence quality: complete=298, partial=87

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| card_reward | run:1781715242.run | 1 | partial | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 2 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 5 | partial | Iron Wave | Ghostly Armor | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 7 | partial | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 8 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 11 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 13 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715242.run | 14 | partial | Anger | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| event | run:1781715242.run | 3 | partial | Purged | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715242.run | 10 | partial | Searched '0' times | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781715242.run | 4 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781715242.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781715411.run | 0 | partial | Good Instincts | Dramatic Entrance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dramatic Entrance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 1 | partial | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 2 | partial | Intimidate | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 5 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 7 | partial | True Grit | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 12 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 13 | partial | Flex | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 14 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 16 | partial | Bludgeon | Impervious | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 18 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715411.run | 22 | partial | True Grit+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781715411.run | 3 | partial | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715411.run | 4 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715411.run | 11 | partial | Forge | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715411.run | 19 | partial | Heal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715411.run | 21 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715411.run | 24 | partial | Shed Blood | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781715411.run | 20 | partial | Fire Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781715411.run | 10 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781715411.run | 20 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781715411.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781715544.run | 0 | partial | Shockwave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 1 | partial | Reckless Charge | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 2 | partial | Shockwave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 3 | partial | Iron Wave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 5 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 8 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 10 | partial | Ghostly Armor | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 11 | partial | Uppercut | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 12 | partial | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715544.run | 14 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| shop | run:1781715544.run | 4 | partial | Fire Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781715544.run | 4 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781715544.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781715655.run | 1 | partial | Bloodletting | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 2 | partial | Metallicize | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 7 | partial | Carnage | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 8 | partial | Flame Barrier | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 11 | partial | Hemokinesis | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 14 | partial | Burning Pact | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 16 | partial | Feed | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 18 | partial | Anger | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715655.run | 19 | partial | Clothesline | Perfected Strike+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike+1. Limitations: missing deck snapshot at reward time |
| event | run:1781715655.run | 4 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715655.run | 5 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715655.run | 10 | partial | Full Heal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715655.run | 13 | partial | Gather Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715655.run | 20 | partial | Obtained Relic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781715655.run | 3 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781715655.run | 12 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781715655.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781715744.run | 1 | partial | Second Wind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 5 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 6 | partial | Headbutt | Ghostly Armor | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 7 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 8 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 11 | partial | Shrug It Off | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 12 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781715744.run | 13 | partial | Flame Barrier | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781715744.run | 2 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781715744.run | 3 | partial | Offered Basic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781715744.run | 14 | partial | Fire Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781715744.run | 4 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781715744.run | 10 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781715744.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@5,0 -> M@5,1 -> M@5,2 -> $@4,3 -> M@4,4 -> E@3,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@5,0 -> M@5,1 -> M@5,2 -> $@4,3 -> M@4,4 -> E@3,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@2,1 -> ?@3,2 -> $@4,3 -> M@4,4 -> E@3,5 -> M@3,6: reward=9.10, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@2,1 -> ?@3,2 -> $@4,3 -> M@4,4 -> E@3,5 -> M@3,6: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.60: M@2,2 -> M@1,3 -> M@0,4 -> R@1,5 -> E@1,6 -> $@2,7: reward=10.60, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.60: M@2,2 -> M@1,3 -> M@0,4 -> R@1,5 -> E@1,6 -> $@2,7: reward=10.60, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.52: M@3,3 -> ?@2,4 -> R@2,5 -> E@1,6 -> $@2,7 -> T@1,8: reward=10.52, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.52: M@3,3 -> ?@2,4 -> R@2,5 -> E@1,6 -> $@2,7 -> T@1,8: reward=10.52, survivability=1.00 |
| shop | decision_trace | 4 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.22: M@4,4 -> E@3,5 -> M@3,6 -> $@2,7 -> T@2,8 -> M@2,9: reward=9.22, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.22: M@4,4 -> E@3,5 -> M@3,6 -> $@2,7 -> T@2,8 -> M@2,9: reward=9.22, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Iron Wave | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.64: E@3,5 -> M@3,6 -> $@2,7 -> T@2,8 -> M@2,9 -> E@2,10: reward=10.64, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.64: E@3,5 -> M@3,6 -> $@2,7 -> T@2,8 -> M@2,9 -> E@2,10: reward=10.64, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@5,6 -> M@6,7 -> T@6,8 -> ?@6,9 -> M@6,10 -> ?@6,11: reward=6.50, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@5,6 -> M@6,7 -> T@6,8 -> ?@6,9 -> M@6,10 -> ?@6,11: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@6,7 -> T@6,8 -> ?@6,9 -> M@6,10 -> ?@6,11 -> M@5,12: reward=6.50, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@6,7 -> T@6,8 -> ?@6,9 -> M@6,10 -> ?@6,11 -> M@5,12: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: T@6,8 -> ?@6,9 -> M@6,10 -> ?@6,11 -> M@5,12 -> M@4,13: reward=6.50, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: T@6,8 -> ?@6,9 -> M@6,10 -> ?@6,11 -> M@5,12 -> M@4,13: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@6,9 -> M@6,10 -> ?@6,11 -> M@5,12 -> M@4,13 -> R@3,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@6,9 -> M@6,10 -> ?@6,11 -> M@5,12 -> M@4,13 -> R@3,14: reward=6.10, survivability=1.00 |
| event | decision_trace | 10 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| event | decision_trace | 10 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: M@6,10 -> ?@6,11 -> M@5,12 -> M@4,13 -> R@3,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: M@6,10 -> ?@6,11 -> M@5,12 -> M@4,13 -> R@3,14: reward=5.10, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@6,11 -> M@5,12 -> M@4,13 -> R@3,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@6,11 -> M@5,12 -> M@4,13 -> R@3,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@5,12 -> M@4,13 -> R@3,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@5,12 -> M@4,13 -> R@3,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@4,13 -> R@3,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@4,13 -> R@3,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Anger | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Good Instincts | Dramatic Entrance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dramatic Entrance. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@1,0 -> M@0,1 -> $@1,2 -> ?@0,3 -> M@1,4 -> E@0,5: reward=9.08, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@1,0 -> M@0,1 -> $@1,2 -> ?@0,3 -> M@1,4 -> E@0,5: reward=9.08, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@2,1 -> ?@2,2 -> M@2,3 -> M@2,4 -> E@2,5 -> M@2,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@2,1 -> ?@2,2 -> M@2,3 -> M@2,4 -> E@2,5 -> M@2,6: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Intimidate | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@2,2 -> M@2,3 -> M@2,4 -> E@2,5 -> M@2,6 -> R@3,7: reward=6.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@2,2 -> M@2,3 -> M@2,4 -> E@2,5 -> M@2,6 -> R@3,7: reward=6.50, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 3 | complete | choose 0: Continue | choose 0: Continue | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| route | decision_trace | 3 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,3 -> ?@4,4 -> R@3,5 -> E@4,6 -> R@5,7 -> T@4,8: reward=7.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,3 -> ?@4,4 -> R@3,5 -> E@4,6 -> R@5,7 -> T@4,8: reward=7.10, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 1: Leave | choose 0: Enter | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: M@2,4 -> E@2,5 -> M@2,6 -> R@3,7 -> T@4,8 -> $@4,9: reward=9.64, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.64: M@2,4 -> E@2,5 -> M@2,6 -> R@3,7 -> T@4,8 -> $@4,9: reward=9.64, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.74: E@2,5 -> M@2,6 -> R@3,7 -> T@4,8 -> $@4,9 -> ?@3,10: reward=9.74, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.74: E@2,5 -> M@2,6 -> R@3,7 -> T@4,8 -> $@4,9 -> ?@3,10: reward=9.74, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.74: M@2,6 -> R@3,7 -> T@4,8 -> $@4,9 -> ?@3,10 -> ?@3,11: reward=8.74, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.74: M@2,6 -> R@3,7 -> T@4,8 -> $@4,9 -> ?@3,10 -> ?@3,11: reward=8.74, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | True Grit | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.68: R@3,7 -> T@4,8 -> $@4,9 -> ?@3,10 -> ?@3,11 -> M@2,12: reward=8.68, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.68: R@3,7 -> T@4,8 -> $@4,9 -> ?@3,10 -> ?@3,11 -> M@2,12: reward=8.68, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.58: T@4,8 -> $@4,9 -> ?@3,10 -> ?@3,11 -> M@2,12 -> M@1,13: reward=8.58, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.58: T@4,8 -> $@4,9 -> ?@3,10 -> ?@3,11 -> M@2,12 -> M@1,13: reward=8.58, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.72: $@4,9 -> ?@3,10 -> ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=8.72, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.72: $@4,9 -> ?@3,10 -> ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=8.72, survivability=1.00 |
| shop | decision_trace | 10 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 10 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@3,10 -> ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@3,10 -> ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=5.10, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 0: Forge | choose 0: Forge | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@2,12 -> M@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@2,12 -> M@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Flex | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@1,13 -> R@0,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@1,13 -> R@0,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| card_reward | decision_trace | 14 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Demon Form | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 16 | complete | Juggernaut | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 16 | complete | Bludgeon | Impervious | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@0,0 -> ?@1,1 -> $@0,2 -> ?@1,3 -> M@1,4 -> R@1,5: reward=10.10, survivability=1.00 |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@0,0 -> ?@1,1 -> $@0,2 -> ?@1,3 -> M@1,4 -> R@1,5: reward=10.10, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 18 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.60: ?@1,1 -> $@0,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> E@0,6: reward=11.60, survivability=1.00 |
| route | decision_trace | 18 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.60: ?@1,1 -> $@0,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> E@0,6: reward=11.60, survivability=1.00 |
| event | decision_trace | 19 | complete | choose 1: Sleep | choose 0: Read | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: $@0,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> E@0,6 -> R@0,7: reward=10.10, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: $@0,2 -> ?@1,3 -> M@1,4 -> R@1,5 -> E@0,6 -> R@0,7: reward=10.10, survivability=1.00 |
| shop | decision_trace | 20 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 20 | complete | Fire Potion | Preserved Insect | high | Bottled shop relic list ranks Preserved Insect as buyable. |
| shop | decision_trace | 20 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 20 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@1,3 -> M@1,4 -> R@1,5 -> E@0,6 -> R@0,7 -> T@0,8: reward=7.60, survivability=1.00 |
| route | decision_trace | 20 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@1,3 -> M@1,4 -> R@1,5 -> E@0,6 -> R@0,7 -> T@0,8: reward=7.60, survivability=1.00 |
| event | decision_trace | 21 | complete | choose 1: Refuse | choose 0: Accept | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.32: M@1,4 -> R@1,5 -> E@0,6 -> R@0,7 -> T@0,8 -> $@1,9: reward=9.32, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.32: M@1,4 -> R@1,5 -> E@0,6 -> R@0,7 -> T@0,8 -> $@1,9: reward=9.32, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | True Grit+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.90: R@1,5 -> E@0,6 -> R@0,7 -> T@0,8 -> $@1,9 -> ?@2,10: reward=9.90, survivability=1.00 |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.90: R@1,5 -> E@0,6 -> R@0,7 -> T@0,8 -> $@1,9 -> ?@2,10: reward=9.90, survivability=1.00 |
| route | decision_trace | 23 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.30: E@0,6 -> R@0,7 -> T@0,8 -> $@1,9 -> ?@2,10 -> E@2,11: reward=11.30, survivability=1.00 |
| route | decision_trace | 23 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.30: E@0,6 -> R@0,7 -> T@0,8 -> $@1,9 -> ?@2,10 -> E@2,11: reward=11.30, survivability=1.00 |
| event | decision_trace | 24 | complete | choose 0: Locked | choose 0: Locked | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 24 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@2,7 -> T@1,8 -> $@1,9 -> ?@2,10 -> R@1,11 -> ?@1,12: reward=9.60, survivability=1.00 |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@2,7 -> T@1,8 -> $@1,9 -> ?@2,10 -> R@1,11 -> ?@1,12: reward=9.60, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a Card to obtain | choose 0: Choose a Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 3 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@6,0 -> M@5,1 -> M@4,2 -> $@5,3 -> M@5,4 -> R@6,5: reward=7.98, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 3 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@6,0 -> M@5,1 -> M@4,2 -> $@5,3 -> M@5,4 -> R@6,5: reward=7.98, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Reckless Charge | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.06: M@5,1 -> M@4,2 -> $@5,3 -> M@5,4 -> R@6,5 -> ?@5,6: reward=8.06, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.06: M@5,1 -> M@4,2 -> $@5,3 -> M@5,4 -> R@6,5 -> ?@5,6: reward=8.06, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.08: M@4,2 -> $@5,3 -> M@5,4 -> R@6,5 -> ?@5,6 -> M@5,7: reward=8.08, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.08: M@4,2 -> $@5,3 -> M@5,4 -> R@6,5 -> ?@5,6 -> M@5,7: reward=8.08, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: $@5,3 -> M@5,4 -> R@6,5 -> ?@5,6 -> M@5,7 -> T@4,8: reward=8.50, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: $@5,3 -> M@5,4 -> R@6,5 -> ?@5,6 -> M@5,7 -> T@4,8: reward=8.50, survivability=1.00 |
| shop | decision_trace | 4 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | Fire Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> R@6,5 -> ?@5,6 -> M@5,7 -> T@4,8 -> M@4,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> R@6,5 -> ?@5,6 -> M@5,7 -> T@4,8 -> M@4,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@6,5 -> ?@5,6 -> M@5,7 -> T@5,8 -> M@6,9 -> E@5,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@6,5 -> ?@5,6 -> M@5,7 -> T@5,8 -> M@6,9 -> E@5,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,6 -> M@5,7 -> T@5,8 -> M@6,9 -> E@5,10 -> M@6,11: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,6 -> M@5,7 -> T@5,8 -> M@6,9 -> E@5,10 -> M@6,11: reward=8.00, survivability=1.00 |
| shop | decision_trace | 7 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,7 -> T@5,8 -> M@6,9 -> E@5,10 -> M@6,11 -> M@5,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,7 -> T@5,8 -> M@6,9 -> E@5,10 -> M@6,11 -> M@5,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 8 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@5,8 -> M@6,9 -> E@5,10 -> M@6,11 -> M@5,12 -> M@5,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@5,8 -> M@6,9 -> E@5,10 -> M@6,11 -> M@5,12 -> M@5,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@4,9 -> M@3,10 -> M@3,11 -> R@4,12 -> M@5,13 -> R@4,14: reward=6.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@4,9 -> M@3,10 -> M@3,11 -> R@4,12 -> M@5,13 -> R@4,14: reward=6.20, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@3,10 -> M@3,11 -> R@4,12 -> M@5,13 -> R@4,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@3,10 -> M@3,11 -> R@4,12 -> M@5,13 -> R@4,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Inflame | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 11 | complete | Combust | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 11 | complete | Uppercut | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: M@3,11 -> R@4,12 -> M@5,13 -> R@4,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: M@3,11 -> R@4,12 -> M@5,13 -> R@4,14: reward=4.20, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.20: R@4,12 -> M@5,13 -> R@4,14: reward=3.20, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.20: R@4,12 -> M@5,13 -> R@4,14: reward=3.20, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@4,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@4,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@5,0 -> M@5,1 -> $@5,2 -> ?@4,3 -> ?@4,4 -> R@5,5: reward=7.68, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@5,0 -> M@5,1 -> $@5,2 -> ?@4,3 -> ?@4,4 -> R@5,5: reward=7.68, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Bloodletting | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@4,1 -> ?@3,2 -> M@3,3 -> M@3,4 -> E@4,5 -> M@4,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@4,1 -> ?@3,2 -> M@3,3 -> M@3,4 -> E@4,5 -> M@4,6: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Metallicize | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.12: $@5,2 -> ?@4,3 -> ?@4,4 -> R@5,5 -> M@4,6 -> E@5,7: reward=9.12, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.12: $@5,2 -> ?@4,3 -> ?@4,4 -> R@5,5 -> M@4,6 -> E@5,7: reward=9.12, survivability=1.00 |
| shop | decision_trace | 3 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,3 -> ?@4,4 -> R@5,5 -> M@4,6 -> E@5,7 -> T@5,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,3 -> ?@4,4 -> R@5,5 -> M@4,6 -> E@5,7 -> T@5,8: reward=8.10, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,4 -> R@5,5 -> M@4,6 -> E@5,7 -> T@5,8 -> ?@4,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,4 -> R@5,5 -> M@4,6 -> E@5,7 -> T@5,8 -> ?@4,9: reward=8.10, survivability=1.00 |
| event | decision_trace | 5 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@5,5 -> M@4,6 -> E@5,7 -> T@5,8 -> ?@4,9 -> ?@4,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@5,5 -> M@4,6 -> E@5,7 -> T@5,8 -> ?@4,9 -> ?@4,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: M@4,6 -> E@5,7 -> T@5,8 -> ?@4,9 -> ?@4,10 -> $@5,11: reward=8.92, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: M@4,6 -> E@5,7 -> T@5,8 -> ?@4,9 -> ?@4,10 -> $@5,11: reward=8.92, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: E@5,7 -> T@5,8 -> ?@4,9 -> ?@4,10 -> $@5,11 -> ?@6,12: reward=9.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: E@5,7 -> T@5,8 -> ?@4,9 -> ?@4,10 -> $@5,11 -> ?@6,12: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Flame Barrier | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@4,9 -> ?@4,10 -> M@4,11 -> ?@4,12 -> E@3,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@4,9 -> ?@4,10 -> M@4,11 -> ?@4,12 -> E@3,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@4,9 -> ?@4,10 -> M@4,11 -> ?@4,12 -> E@3,13 -> R@2,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@4,9 -> ?@4,10 -> M@4,11 -> ?@4,12 -> E@3,13 -> R@2,14: reward=6.50, survivability=1.00 |
| event | decision_trace | 10 | complete | choose 0: Play | choose 0: Play | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: spin | choose 0: spin | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Prize! | choose 0: Prize! | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,10 -> M@4,11 -> ?@4,12 -> E@3,13 -> R@2,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,10 -> M@4,11 -> ?@4,12 -> E@3,13 -> R@2,14: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Hemokinesis | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.62: $@5,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=5.62, survivability=1.00 |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.62: $@5,11 -> ?@6,12 -> M@6,13 -> R@5,14: reward=5.62, survivability=1.00 |
| shop | decision_trace | 12 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 12 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@6,12 -> M@6,13 -> R@5,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@6,12 -> M@6,13 -> R@5,14: reward=3.10, survivability=1.00 |
| event | decision_trace | 13 | complete | choose 0: Gather Gold | choose 0: Gather Gold | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 13 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Impatience | Hand of Greed | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Hand of Greed. |
| card_reward | decision_trace | 16 | complete | Feed | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 10.50: M@6,0 -> $@6,1 -> M@6,2 -> M@6,3 -> M@5,4 -> E@5,5: reward=10.50, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 10.50: M@6,0 -> $@6,1 -> M@6,2 -> M@6,3 -> M@5,4 -> E@5,5: reward=10.50, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Anger | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@3,1 -> ?@3,2 -> M@3,3 -> ?@3,4 -> R@3,5 -> ?@4,6: reward=6.50, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@3,1 -> ?@3,2 -> M@3,3 -> ?@3,4 -> R@3,5 -> ?@4,6: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Clothesline | Perfected Strike+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike+. |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,2 -> M@3,3 -> ?@3,4 -> R@3,5 -> ?@4,6 -> R@3,7: reward=6.60, survivability=1.00 |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,2 -> M@3,3 -> ?@3,4 -> R@3,5 -> ?@4,6 -> R@3,7: reward=6.60, survivability=1.00 |
| event | decision_trace | 20 | complete | choose 0: Offer Gold | choose 0: Offer Gold | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,3 -> ?@3,4 -> R@3,5 -> ?@4,6 -> R@3,7 -> T@4,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,3 -> ?@3,4 -> R@3,5 -> ?@4,6 -> R@3,7 -> T@4,8: reward=6.60, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> ?@1,1 -> M@0,2 -> ?@0,3 -> ?@0,4 -> E@1,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> ?@1,1 -> M@0,2 -> ?@0,3 -> ?@0,4 -> E@1,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@1,1 -> M@0,2 -> ?@0,3 -> ?@0,4 -> E@1,5 -> R@1,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@1,1 -> M@0,2 -> ?@0,3 -> ?@0,4 -> E@1,5 -> R@1,6: reward=7.60, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@0,2 -> ?@0,3 -> ?@0,4 -> E@1,5 -> R@1,6 -> ?@0,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@0,2 -> ?@0,3 -> ?@0,4 -> E@1,5 -> R@1,6 -> ?@0,7: reward=7.60, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Offer | choose 0: Offer | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@1,3 -> ?@0,4 -> E@1,5 -> R@1,6 -> ?@0,7 -> T@1,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@1,3 -> ?@0,4 -> E@1,5 -> R@1,6 -> ?@0,7 -> T@1,8: reward=8.10, survivability=1.00 |
| shop | decision_trace | 4 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@3,4 -> R@3,5 -> $@2,6 -> M@1,7 -> T@1,8 -> E@1,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@3,4 -> R@3,5 -> $@2,6 -> M@1,7 -> T@1,8 -> E@1,9: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.28: R@3,5 -> $@2,6 -> M@1,7 -> T@1,8 -> E@1,9 -> R@0,10: reward=8.28, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.28: R@3,5 -> $@2,6 -> M@1,7 -> T@1,8 -> E@1,9 -> R@0,10: reward=8.28, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | Headbutt | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.96: M@5,6 -> M@5,7 -> T@5,8 -> $@6,9 -> ?@6,10 -> E@5,11: reward=8.96, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.96: M@5,6 -> M@5,7 -> T@5,8 -> $@6,9 -> ?@6,10 -> E@5,11: reward=8.96, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.02: M@5,7 -> T@5,8 -> $@6,9 -> ?@6,10 -> E@5,11 -> M@5,12: reward=9.02, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.02: M@5,7 -> T@5,8 -> $@6,9 -> ?@6,10 -> E@5,11 -> M@5,12: reward=9.02, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: T@5,8 -> $@6,9 -> ?@6,10 -> E@5,11 -> M@5,12 -> ?@4,13: reward=8.92, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: T@5,8 -> $@6,9 -> ?@6,10 -> E@5,11 -> M@5,12 -> ?@4,13: reward=8.92, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.96: $@6,9 -> ?@6,10 -> E@5,11 -> M@5,12 -> ?@4,13 -> R@3,14: reward=7.96, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.96: $@6,9 -> ?@6,10 -> E@5,11 -> M@5,12 -> ?@4,13 -> R@3,14: reward=7.96, survivability=1.00 |
| shop | decision_trace | 10 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 10 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: ?@6,10 -> E@5,11 -> M@5,12 -> ?@4,13 -> R@3,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: ?@6,10 -> E@5,11 -> M@5,12 -> ?@4,13 -> R@3,14: reward=5.50, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Shrug It Off | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@5,11 -> M@5,12 -> ?@4,13 -> R@3,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@5,11 -> M@5,12 -> ?@4,13 -> R@3,14: reward=4.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 12 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@5,12 -> ?@4,13 -> R@3,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@5,12 -> ?@4,13 -> R@3,14: reward=2.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Flame Barrier | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 13 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability -2.00: M@5,13 -> R@4,14: reward=1.00, survivability=0.80 |
| route | decision_trace | 13 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability -2.00: M@5,13 -> R@4,14: reward=1.00, survivability=0.80 |
| shop | decision_trace | 14 | complete | Fire Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

1. **shop floor 4**: current `Fire Potion` vs reference `leave` (high). Bottled shop handler leaves when no priority purchase is affordable. Repeated 2x in non-fixture evidence.
2. **card_reward floor 5**: current `Iron Wave` vs reference `Ghostly Armor` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. Repeated 2x in non-fixture evidence.
3. **card_reward floor 11**: current `Shrug It Off` vs reference `Twin Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Repeated 2x in non-fixture evidence.
4. **event floor 2**: current `choose 1: Disagree` vs reference `choose 0: Agree` (medium). Bottled common event fallback chooses the first option. Repeated 2x in non-fixture evidence.
5. **card_reward floor 1**: current `True Grit` vs reference `skip` (medium). Bottled card reward handler skips when no desired card is offered. Repeated 25x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
