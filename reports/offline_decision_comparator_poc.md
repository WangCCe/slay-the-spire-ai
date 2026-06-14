# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 451
- Differences: 285
- Categories: card_reward=102, event=94, route=229, shop=26
- Evidence quality: complete=352, partial=99

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| card_reward | run:1781453351.run | 1 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453351.run | 3 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453351.run | 7 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453351.run | 10 | partial | Offering | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453351.run | 11 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781453351.run | 5 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453351.run | 8 | partial | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453351.run | 10 | partial | Fought Mushrooms | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781453351.run | 2 | partial | Shrug It Off | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781453351.run | 2 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781453351.run | 13 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781453351.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781453435.run | 1 | partial | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453435.run | 4 | partial | Reckless Charge | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453435.run | 7 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453435.run | 10 | partial | Hemokinesis | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453435.run | 12 | partial | Iron Wave | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453435.run | 13 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781453435.run | 3 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453435.run | 5 | partial | Touch | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453435.run | 14 | partial | Searched '0' times | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781453435.run | 2 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781453435.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781453557.run | 1 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453557.run | 2 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453557.run | 5 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453557.run | 7 | partial | Power Through | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453557.run | 12 | partial | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453557.run | 13 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453557.run | 14 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| event | run:1781453557.run | 3 | partial | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453557.run | 4 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453557.run | 13 | partial | Fought Mushrooms | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781453557.run | 11 | partial | Purity | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781453557.run | 11 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781453557.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781453811.run | 0 | partial | Purity | Flash of Steel | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 1 | partial | Headbutt | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 3 | partial | Sword Boomerang | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 6 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 11 | partial | Flame Barrier | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 12 | partial | Flame Barrier | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 14 | partial | Inflame | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 16 | partial | Fiend Fire | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 18 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 19 | partial | Clothesline | Twin Strike+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 20 | partial | Headbutt+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 21 | partial | Shrug It Off+1 | Shrug It Off+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 22 | partial | SKIP | Offering | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 24 | partial | Cleave | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 25 | partial | Anger+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781453811.run | 30 | partial | Disarm | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781453811.run | 2 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453811.run | 4 | partial | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453811.run | 8 | partial | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453811.run | 28 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453811.run | 29 | partial | Bought 1 Potion | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781453811.run | 31 | partial | 0 cards matched | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781453811.run | 27 | partial | Pommel Strike | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781453811.run | 5 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781453811.run | 27 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781453811.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781454026.run | 1 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 2 | partial | Bloodletting | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 3 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 5 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 7 | partial | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 10 | partial | Whirlwind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 14 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 16 | partial | Immolate | Reaper | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 18 | partial | Shockwave+1 | Flame Barrier | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 20 | partial | Cleave+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 21 | partial | SKIP | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 24 | partial | Havoc+1 | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 25 | partial | SKIP | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 28 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 30 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781454026.run | 31 | partial | SKIP | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781454026.run | 4 | partial | Touch | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781454026.run | 12 | partial | Healed and dodged fight | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781454026.run | 13 | partial | Entered Light | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781454026.run | 19 | partial | Heal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781454026.run | 22 | partial | Elegance | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781454026.run | 29 | partial | Copied | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1781454026.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@4,0 -> M@5,1 -> M@4,2 -> $@4,3 -> ?@4,4 -> R@3,5: reward=7.98, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@4,0 -> M@5,1 -> M@4,2 -> $@4,3 -> ?@4,4 -> R@3,5: reward=7.98, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.04: M@5,1 -> M@4,2 -> $@4,3 -> ?@4,4 -> R@3,5 -> M@4,6: reward=8.04, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.04: M@5,1 -> M@4,2 -> $@4,3 -> ?@4,4 -> R@3,5 -> M@4,6: reward=8.04, survivability=1.00 |
| shop | decision_trace | 2 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | Shrug It Off | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 2 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@4,2 -> M@3,3 -> ?@4,4 -> R@3,5 -> M@4,6 -> M@4,7: reward=6.10, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@4,2 -> M@3,3 -> ?@4,4 -> R@3,5 -> M@4,6 -> M@4,7: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,3 -> ?@4,4 -> R@3,5 -> M@4,6 -> M@4,7 -> T@3,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,3 -> ?@4,4 -> R@3,5 -> M@4,6 -> M@4,7 -> T@3,8: reward=6.60, survivability=1.00 |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,4 -> R@3,5 -> M@4,6 -> M@4,7 -> T@3,8 -> M@3,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,4 -> R@3,5 -> M@4,6 -> M@4,7 -> T@3,8 -> M@3,9: reward=6.60, survivability=1.00 |
| event | decision_trace | 5 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@3,5 -> M@4,6 -> M@4,7 -> T@3,8 -> M@3,9 -> M@4,10: reward=6.60, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@3,5 -> M@4,6 -> M@4,7 -> T@3,8 -> M@3,9 -> M@4,10: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@4,6 -> M@4,7 -> T@3,8 -> M@3,9 -> M@4,10 -> R@4,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@4,6 -> M@4,7 -> T@3,8 -> M@3,9 -> M@4,10 -> R@4,11: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,7 -> T@4,8 -> M@4,9 -> M@5,10 -> ?@5,11 -> E@5,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,7 -> T@4,8 -> M@4,9 -> M@5,10 -> ?@5,11 -> E@5,12: reward=8.00, survivability=1.00 |
| event | decision_trace | 8 | complete | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 8 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@4,8 -> M@4,9 -> M@5,10 -> R@4,11 -> M@3,12 -> E@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@4,8 -> M@4,9 -> M@5,10 -> R@4,11 -> M@3,12 -> E@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@4,9 -> M@5,10 -> R@4,11 -> M@3,12 -> E@2,13 -> R@2,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@4,9 -> M@5,10 -> R@4,11 -> M@3,12 -> E@2,13 -> R@2,14: reward=7.70, survivability=1.00 |
| event | decision_trace | 10 | complete | choose 0: Stomp | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Fight | choose 0: Fight | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 10 | complete | Offering | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@5,10 -> R@4,11 -> M@3,12 -> E@2,13 -> R@2,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@5,10 -> R@4,11 -> M@3,12 -> E@2,13 -> R@2,14: reward=5.60, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: R@4,11 -> M@3,12 -> E@2,13 -> R@2,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: R@4,11 -> M@3,12 -> E@2,13 -> R@2,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@3,12 -> E@2,13 -> R@2,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@3,12 -> E@2,13 -> R@2,14: reward=3.50, survivability=1.00 |
| shop | decision_trace | 13 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 13 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@2,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@2,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 3 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@3,0 -> M@3,1 -> M@4,2 -> ?@5,3 -> $@4,4 -> E@4,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 3 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@3,0 -> M@3,1 -> M@4,2 -> ?@5,3 -> $@4,4 -> E@4,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.32: M@4,1 -> M@4,2 -> ?@5,3 -> $@4,4 -> E@4,5 -> M@5,6: reward=9.32, survivability=1.00 |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.32: M@4,1 -> M@4,2 -> ?@5,3 -> $@4,4 -> E@4,5 -> M@5,6: reward=9.32, survivability=1.00 |
| shop | decision_trace | 2 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.22: ?@5,2 -> ?@5,3 -> $@4,4 -> E@4,5 -> M@5,6 -> R@4,7: reward=6.22, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.22: ?@5,2 -> ?@5,3 -> $@4,4 -> E@4,5 -> M@5,6 -> R@4,7: reward=6.22, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 1: Leave | choose 0: Take | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.72: ?@5,3 -> $@4,4 -> E@4,5 -> M@5,6 -> R@4,7 -> T@3,8: reward=6.72, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.72: ?@5,3 -> $@4,4 -> E@4,5 -> M@5,6 -> R@4,7 -> T@3,8: reward=6.72, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Reckless Charge | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@5,4 -> R@5,5 -> M@5,6 -> R@4,7 -> T@3,8 -> M@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@5,4 -> R@5,5 -> M@5,6 -> R@4,7 -> T@3,8 -> M@2,9: reward=6.70, survivability=1.00 |
| event | decision_trace | 5 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Touch | choose 0: Touch | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: R@5,5 -> M@5,6 -> R@4,7 -> T@3,8 -> M@2,9 -> $@1,10: reward=8.80, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: R@5,5 -> M@5,6 -> R@4,7 -> T@3,8 -> M@2,9 -> $@1,10: reward=8.80, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.20: M@5,6 -> R@4,7 -> T@3,8 -> M@2,9 -> $@1,10 -> E@1,11: reward=10.20, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.20: M@5,6 -> R@4,7 -> T@3,8 -> M@2,9 -> $@1,10 -> E@1,11: reward=10.20, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.14: R@4,7 -> T@3,8 -> M@2,9 -> $@1,10 -> E@1,11 -> M@1,12: reward=10.14, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.14: R@4,7 -> T@3,8 -> M@2,9 -> $@1,10 -> E@1,11 -> M@1,12: reward=10.14, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.04: T@3,8 -> M@2,9 -> $@1,10 -> E@1,11 -> M@1,12 -> M@1,13: reward=10.04, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.04: T@3,8 -> M@2,9 -> $@1,10 -> E@1,11 -> M@1,12 -> M@1,13: reward=10.04, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.54: M@2,9 -> $@1,10 -> E@1,11 -> M@1,12 -> M@1,13 -> R@1,14: reward=8.54, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.54: M@2,9 -> $@1,10 -> E@1,11 -> M@1,12 -> M@1,13 -> R@1,14: reward=8.54, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Hemokinesis | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 10 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.80: $@1,10 -> E@1,11 -> M@1,12 -> M@1,13 -> R@1,14: reward=7.54, survivability=0.95 |
| route | decision_trace | 10 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.80: $@1,10 -> E@1,11 -> M@1,12 -> M@1,13 -> R@1,14: reward=7.54, survivability=0.95 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: ?@2,11 -> ?@2,12 -> M@1,13 -> R@1,14: reward=3.00, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: ?@2,11 -> ?@2,12 -> M@1,13 -> R@1,14: reward=3.00, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Iron Wave | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@2,12 -> M@1,13 -> R@1,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@2,12 -> M@1,13 -> R@1,14: reward=2.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@1,13 -> R@1,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@1,13 -> R@1,14: reward=1.00, survivability=1.00 |
| event | decision_trace | 14 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| event | decision_trace | 14 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@5,0 -> $@6,1 -> M@6,2 -> M@5,3 -> M@6,4 -> E@6,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@5,0 -> $@6,1 -> M@6,2 -> M@5,3 -> M@6,4 -> E@6,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,1 -> ?@2,2 -> ?@1,3 -> M@0,4 -> R@0,5 -> E@0,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@1,1 -> ?@2,2 -> ?@1,3 -> M@0,4 -> R@0,5 -> E@0,6: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@2,2 -> ?@1,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7: reward=7.70, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@2,2 -> ?@1,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7: reward=7.70, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 3 | complete | choose 0: Continue | choose 0: Continue | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@1,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7 -> T@0,8: reward=8.20, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: ?@1,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7 -> T@0,8: reward=8.20, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: M@0,4 -> R@0,5 -> E@0,6 -> R@0,7 -> T@0,8 -> R@0,9: reward=8.30, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: M@0,4 -> R@0,5 -> E@0,6 -> R@0,7 -> T@0,8 -> R@0,9: reward=8.30, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.02: R@0,5 -> E@0,6 -> R@0,7 -> T@0,8 -> M@1,9 -> $@1,10: reward=11.02, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.02: R@0,5 -> E@0,6 -> R@0,7 -> T@0,8 -> M@1,9 -> $@1,10: reward=11.02, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.02: E@0,6 -> R@0,7 -> T@0,8 -> M@1,9 -> $@1,10 -> R@0,11: reward=11.02, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.02: E@0,6 -> R@0,7 -> T@0,8 -> M@1,9 -> $@1,10 -> R@0,11: reward=11.02, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Power Through | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.94: M@1,7 -> T@0,8 -> M@1,9 -> $@1,10 -> R@0,11 -> E@0,12: reward=10.94, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.94: M@1,7 -> T@0,8 -> M@1,9 -> $@1,10 -> R@0,11 -> E@0,12: reward=10.94, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.44: T@0,8 -> R@0,9 -> $@1,10 -> R@0,11 -> E@0,12 -> ?@0,13: reward=10.44, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.44: T@0,8 -> R@0,9 -> $@1,10 -> R@0,11 -> E@0,12 -> ?@0,13: reward=10.44, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.24: M@1,9 -> $@1,10 -> R@0,11 -> E@0,12 -> ?@0,13 -> R@0,14: reward=10.24, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.24: M@1,9 -> $@1,10 -> R@0,11 -> E@0,12 -> ?@0,13 -> R@0,14: reward=10.24, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.94: $@1,10 -> R@0,11 -> E@0,12 -> ?@0,13 -> R@0,14: reward=8.94, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.94: $@1,10 -> R@0,11 -> E@0,12 -> ?@0,13 -> R@0,14: reward=8.94, survivability=1.00 |
| shop | decision_trace | 11 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 11 | complete | Purity | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 11 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 11 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.70: R@0,11 -> E@0,12 -> ?@0,13 -> R@0,14: reward=5.70, survivability=1.00 |
| route | decision_trace | 11 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.70: R@0,11 -> E@0,12 -> ?@0,13 -> R@0,14: reward=5.70, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@1,12 -> M@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@1,12 -> M@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| event | decision_trace | 13 | complete | choose 0: Stomp | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | choose 0: Fight | choose 0: Fight | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 13 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@1,13 -> R@0,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@1,13 -> R@0,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Purity | Flash of Steel | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,0 -> ?@0,1 -> M@0,2 -> M@0,3 -> M@0,4 -> R@0,5: reward=6.10, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@0,0 -> ?@0,1 -> M@0,2 -> M@0,3 -> M@0,4 -> R@0,5: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Headbutt | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@0,1 -> M@0,2 -> M@0,3 -> M@0,4 -> R@0,5 -> E@0,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@0,1 -> M@0,2 -> M@0,3 -> M@0,4 -> R@0,5 -> E@0,6: reward=7.60, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@0,2 -> M@0,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7: reward=7.70, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@0,2 -> M@0,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7: reward=7.70, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Sword Boomerang | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@0,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7 -> T@1,8: reward=8.20, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@0,3 -> M@0,4 -> R@0,5 -> E@0,6 -> R@0,7 -> T@1,8: reward=8.20, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 4 | complete | choose 0: Continue | choose 0: Continue | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.52: M@0,4 -> R@0,5 -> E@0,6 -> ?@1,7 -> T@1,8 -> $@0,9: reward=10.52, survivability=1.00 |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.52: M@0,4 -> R@0,5 -> E@0,6 -> ?@1,7 -> T@1,8 -> $@0,9: reward=10.52, survivability=1.00 |
| shop | decision_trace | 5 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 5 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: M@1,5 -> E@0,6 -> ?@1,7 -> T@1,8 -> $@0,9 -> M@0,10: reward=8.92, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: M@1,5 -> E@0,6 -> ?@1,7 -> T@1,8 -> $@0,9 -> M@0,10: reward=8.92, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.90: E@0,6 -> R@0,7 -> T@1,8 -> $@0,9 -> M@0,10 -> ?@0,11: reward=7.90, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.90: E@0,6 -> R@0,7 -> T@1,8 -> $@0,9 -> M@0,10 -> ?@0,11: reward=7.90, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: ?@1,7 -> T@1,8 -> $@0,9 -> M@0,10 -> M@1,11 -> E@2,12: reward=8.30, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: ?@1,7 -> T@1,8 -> $@0,9 -> M@0,10 -> M@1,11 -> E@2,12: reward=8.30, survivability=1.00 |
| event | decision_trace | 8 | complete | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: T@1,8 -> $@0,9 -> M@0,10 -> ?@0,11 -> M@1,12 -> E@1,13: reward=8.30, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: T@1,8 -> $@0,9 -> M@0,10 -> ?@0,11 -> M@1,12 -> E@1,13: reward=8.30, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: $@0,9 -> M@0,10 -> ?@0,11 -> R@0,12 -> M@0,13 -> R@0,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: $@0,9 -> M@0,10 -> ?@0,11 -> R@0,12 -> M@0,13 -> R@0,14: reward=6.50, survivability=1.00 |
| shop | decision_trace | 10 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@0,10 -> ?@0,11 -> R@0,12 -> M@0,13 -> R@0,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@0,10 -> ?@0,11 -> R@0,12 -> M@0,13 -> R@0,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Flame Barrier | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 11 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: M@1,11 -> M@1,12 -> E@1,13 -> R@1,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: M@1,11 -> M@1,12 -> E@1,13 -> R@1,14: reward=4.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Flame Barrier | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.25: M@1,12 -> E@1,13 -> R@1,14: reward=3.50, survivability=0.98 |
| route | decision_trace | 12 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.25: M@1,12 -> E@1,13 -> R@1,14: reward=3.50, survivability=0.98 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@0,13 -> R@0,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@0,13 -> R@0,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Inflame | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Fiend Fire | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 17 | complete | choice 1 | choice 4 | high | Bottled common map scoring prefers reward-to-survivability 11.50: M@6,0 -> ?@6,1 -> M@6,2 -> $@5,3 -> ?@6,4 -> E@6,5: reward=11.50, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 4 | high | Bottled common map scoring prefers reward-to-survivability 11.50: M@6,0 -> ?@6,1 -> M@6,2 -> $@5,3 -> ?@6,4 -> E@6,5: reward=11.50, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@3,1 -> M@3,2 -> M@4,3 -> ?@3,4 -> R@2,5 -> ?@3,6: reward=7.10, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@3,1 -> M@3,2 -> M@4,3 -> ?@3,4 -> R@2,5 -> ?@3,6: reward=7.10, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Clothesline | Twin Strike+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike+. |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: M@3,2 -> M@4,3 -> ?@3,4 -> R@2,5 -> ?@3,6 -> E@2,7: reward=8.60, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: M@3,2 -> M@4,3 -> ?@3,4 -> R@2,5 -> ?@3,6 -> E@2,7: reward=8.60, survivability=1.00 |
| card_reward | decision_trace | 20 | complete | Headbutt+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@4,3 -> ?@3,4 -> R@2,5 -> ?@3,6 -> E@2,7 -> T@1,8: reward=9.10, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@4,3 -> ?@3,4 -> R@2,5 -> ?@3,6 -> E@2,7 -> T@1,8: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 21 | complete | Shrug It Off+ | Shrug It Off+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off+. |
| route | decision_trace | 21 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.50: ?@3,4 -> E@4,5 -> M@4,6 -> M@4,7 -> T@3,8 -> $@4,9: reward=11.50, survivability=1.00 |
| route | decision_trace | 21 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.50: ?@3,4 -> E@4,5 -> M@4,6 -> M@4,7 -> T@3,8 -> $@4,9: reward=11.50, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | skip | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: R@5,5 -> M@4,6 -> M@4,7 -> T@3,8 -> $@4,9 -> ?@3,10: reward=9.00, survivability=1.00 |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.00: R@5,5 -> M@4,6 -> M@4,7 -> T@3,8 -> $@4,9 -> ?@3,10: reward=9.00, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: M@4,6 -> M@4,7 -> T@3,8 -> $@4,9 -> ?@3,10 -> ?@2,11: reward=10.50, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: M@4,6 -> M@4,7 -> T@3,8 -> $@4,9 -> ?@3,10 -> ?@2,11: reward=10.50, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | Cleave | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@4,7 -> T@3,8 -> $@4,9 -> ?@3,10 -> ?@2,11 -> ?@2,12: reward=11.00, survivability=1.00 |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@4,7 -> T@3,8 -> $@4,9 -> ?@3,10 -> ?@2,11 -> ?@2,12: reward=11.00, survivability=1.00 |
| card_reward | decision_trace | 25 | complete | Anger+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.94: T@3,8 -> $@4,9 -> ?@3,10 -> ?@2,11 -> M@1,12 -> $@2,13: reward=11.94, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.94: T@3,8 -> $@4,9 -> ?@3,10 -> ?@2,11 -> M@1,12 -> $@2,13: reward=11.94, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.44: $@4,9 -> ?@3,10 -> ?@2,11 -> M@1,12 -> $@2,13 -> R@1,14: reward=10.44, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.44: $@4,9 -> ?@3,10 -> ?@2,11 -> M@1,12 -> $@2,13 -> R@1,14: reward=10.44, survivability=1.00 |
| shop | decision_trace | 27 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 27 | complete | Pommel Strike | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 27 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.92: ?@3,10 -> ?@2,11 -> M@1,12 -> $@2,13 -> R@1,14: reward=7.92, survivability=1.00 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.92: ?@3,10 -> ?@2,11 -> M@1,12 -> $@2,13 -> R@1,14: reward=7.92, survivability=1.00 |
| event | decision_trace | 28 | complete | choose 1: Refuse | choose 0: Accept | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 28 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.42: ?@2,11 -> M@1,12 -> $@2,13 -> R@1,14: reward=6.42, survivability=1.00 |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.42: ?@2,11 -> M@1,12 -> $@2,13 -> R@1,14: reward=6.42, survivability=1.00 |
| event | decision_trace | 29 | complete | choose 0: Buy 1 Potion | choose 0: Buy 1 Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 29 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 29 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.52: M@1,12 -> $@2,13 -> R@1,14: reward=4.52, survivability=1.00 |
| route | decision_trace | 29 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.52: M@1,12 -> $@2,13 -> R@1,14: reward=4.52, survivability=1.00 |
| card_reward | decision_trace | 30 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| card_reward | decision_trace | 30 | complete | Disarm | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 30 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.50: ?@3,13 -> R@2,14: reward=1.50, survivability=1.00 |
| route | decision_trace | 30 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.50: ?@3,13 -> R@2,14: reward=1.50, survivability=1.00 |
| event | decision_trace | 31 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Play | choose 0: Play | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: card0 | choose 0: card0 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: card1 | choose 0: card1 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Normality | choose 0: Normality | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Bandage Up | choose 0: Bandage Up | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Normality | choose 0: Normality | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Bandage Up | choose 0: Bandage Up | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Normality | choose 0: Normality | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Bandage Up | choose 0: Bandage Up | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Normality | choose 0: Normality | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Bandage Up | choose 0: Bandage Up | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 31 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> ?@1,1 -> ?@1,2 -> $@1,3 -> M@1,4 -> E@0,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> ?@1,1 -> ?@1,2 -> $@1,3 -> M@1,4 -> E@0,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,1 -> M@5,2 -> M@4,3 -> M@3,4 -> R@4,5 -> E@5,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,1 -> M@5,2 -> M@4,3 -> M@3,4 -> R@4,5 -> E@5,6: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Bloodletting | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> M@4,3 -> M@3,4 -> R@4,5 -> E@5,6 -> ?@6,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> M@4,3 -> M@3,4 -> R@4,5 -> E@5,6 -> ?@6,7: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,3 -> M@3,4 -> R@4,5 -> ?@3,6 -> R@4,7 -> T@3,8: reward=6.70, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,3 -> M@3,4 -> R@4,5 -> ?@3,6 -> R@4,7 -> T@3,8: reward=6.70, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Touch | choose 0: Touch | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@5,4 -> R@4,5 -> ?@3,6 -> R@4,7 -> T@3,8 -> ?@3,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@5,4 -> R@4,5 -> ?@3,6 -> R@4,7 -> T@3,8 -> ?@3,9: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@4,5 -> ?@3,6 -> M@3,7 -> T@2,8 -> ?@3,9 -> E@4,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@4,5 -> ?@3,6 -> M@3,7 -> T@2,8 -> ?@3,9 -> E@4,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,6 -> R@4,7 -> T@3,8 -> R@4,9 -> E@4,10 -> ?@3,11: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,6 -> R@4,7 -> T@3,8 -> R@4,9 -> E@4,10 -> ?@3,11: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@4,7 -> T@3,8 -> ?@3,9 -> E@4,10 -> ?@3,11 -> M@2,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@4,7 -> T@3,8 -> ?@3,9 -> E@4,10 -> ?@3,11 -> M@2,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@3,9 -> E@4,10 -> ?@3,11 -> M@2,12 -> M@1,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> ?@3,9 -> E@4,10 -> ?@3,11 -> M@2,12 -> M@1,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@4,9 -> E@4,10 -> M@4,11 -> E@4,12 -> M@3,13 -> R@2,14: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@4,9 -> E@4,10 -> M@4,11 -> E@4,12 -> M@3,13 -> R@2,14: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Whirlwind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.50: E@4,10 -> ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.50: E@4,10 -> ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@3,11 -> M@2,12 -> M@1,13 -> R@0,14: reward=4.10, survivability=1.00 |
| event | decision_trace | 12 | complete | choose 1: Eat | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@2,12 -> M@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@2,12 -> M@1,13 -> R@0,14: reward=3.10, survivability=1.00 |
| event | decision_trace | 13 | complete | choose 0: Enter | choose 0: Enter | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| event | decision_trace | 13 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@2,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@3,13 -> R@2,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Immolate | Reaper | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@0,0 -> ?@1,1 -> M@1,2 -> $@2,3 -> M@2,4 -> E@3,5: reward=11.00, survivability=1.00 |
| route | decision_trace | 17 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: M@0,0 -> ?@1,1 -> M@1,2 -> $@2,3 -> M@2,4 -> E@3,5: reward=11.00, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Apotheosis | Apotheosis | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Apotheosis. |
| card_reward | decision_trace | 18 | complete | Shockwave+ | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: ?@1,1 -> M@1,2 -> $@2,3 -> M@2,4 -> R@2,5 -> E@2,6: reward=11.10, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: ?@1,1 -> M@1,2 -> $@2,3 -> M@2,4 -> R@2,5 -> E@2,6: reward=11.10, survivability=1.00 |
| event | decision_trace | 19 | complete | choose 1: Sleep | choose 0: Read | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.60: M@1,2 -> $@2,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7: reward=10.60, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.60: M@1,2 -> $@2,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7: reward=10.60, survivability=1.00 |
| card_reward | decision_trace | 20 | complete | Cleave+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 20 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.60: $@2,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7 -> T@0,8: reward=11.10, survivability=0.97 |
| route | decision_trace | 20 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.60: $@2,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7 -> T@0,8: reward=11.10, survivability=0.97 |
| card_reward | decision_trace | 21 | complete | skip | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@1,4 -> R@2,5 -> M@1,6 -> M@1,7 -> T@1,8 -> ?@2,9: reward=6.50, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@1,4 -> R@2,5 -> M@1,6 -> M@1,7 -> T@1,8 -> ?@2,9: reward=6.50, survivability=1.00 |
| event | decision_trace | 22 | complete | choose 0: Elegance | choose 0: Elegance | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 22 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: R@2,5 -> M@1,6 -> M@1,7 -> T@0,8 -> R@0,9 -> $@0,10: reward=8.60, survivability=1.00 |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.60: R@2,5 -> M@1,6 -> M@1,7 -> T@0,8 -> R@0,9 -> $@0,10: reward=8.60, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: M@1,6 -> M@1,7 -> T@0,8 -> R@0,9 -> $@0,10 -> E@0,11: reward=10.00, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: M@1,6 -> M@1,7 -> T@0,8 -> R@0,9 -> $@0,10 -> E@0,11: reward=10.00, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | Havoc+ | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: M@1,7 -> T@0,8 -> R@0,9 -> $@0,10 -> E@0,11 -> M@1,12: reward=10.00, survivability=1.00 |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: M@1,7 -> T@0,8 -> R@0,9 -> $@0,10 -> E@0,11 -> M@1,12: reward=10.00, survivability=1.00 |
| card_reward | decision_trace | 25 | complete | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: T@0,8 -> R@0,9 -> M@1,10 -> ?@1,11 -> M@1,12 -> ?@0,13: reward=7.60, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: T@0,8 -> R@0,9 -> M@1,10 -> ?@1,11 -> M@1,12 -> ?@0,13: reward=7.60, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: R@0,9 -> M@1,10 -> ?@1,11 -> M@1,12 -> ?@0,13 -> R@0,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: R@0,9 -> M@1,10 -> ?@1,11 -> M@1,12 -> ?@0,13 -> R@0,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 27 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@1,10 -> ?@1,11 -> M@1,12 -> ?@0,13 -> R@0,14: reward=5.00, survivability=1.00 |
| route | decision_trace | 27 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.00: M@1,10 -> ?@1,11 -> M@1,12 -> ?@0,13 -> R@0,14: reward=5.00, survivability=1.00 |
| card_reward | decision_trace | 28 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@1,11 -> M@1,12 -> ?@0,13 -> R@0,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@1,11 -> M@1,12 -> ?@0,13 -> R@0,14: reward=5.10, survivability=1.00 |
| event | decision_trace | 29 | complete | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 29 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 29 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.60: M@1,12 -> ?@0,13 -> R@0,14: reward=3.60, survivability=1.00 |
| route | decision_trace | 29 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.60: M@1,12 -> ?@0,13 -> R@0,14: reward=3.60, survivability=1.00 |
| card_reward | decision_trace | 30 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 30 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.50: ?@0,13 -> R@0,14: reward=1.50, survivability=1.00 |
| route | decision_trace | 30 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.50: ?@0,13 -> R@0,14: reward=1.50, survivability=1.00 |
| card_reward | decision_trace | 31 | complete | skip | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

1. **shop floor 2**: current `Shrug It Off` vs reference `leave` (high). Bottled shop handler leaves when no priority purchase is affordable. Repeated 3x in non-fixture evidence.
2. **route floor 14**: current `choice map_node` vs reference `choice 0` (high). Bottled common map scoring prefers reward-to-survivability 0.00: R@2,14: reward=0.00, survivability=1.00 Repeated 2x in non-fixture evidence.
3. **route floor 14**: current `choice map_node` vs reference `choice 0` (high). Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 Repeated 2x in non-fixture evidence.
4. **card_reward floor 7**: current `Power Through` vs reference `Twin Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Repeated 3x in non-fixture evidence.
5. **card_reward floor 11**: current `Flame Barrier` vs reference `Perfected Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Repeated 3x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
