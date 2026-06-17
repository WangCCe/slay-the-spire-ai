# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 336
- Differences: 211
- Categories: card_reward=94, event=60, route=166, shop=16
- Evidence quality: complete=261, partial=75

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| shop | fixture:shop | 5 | complete | Anger | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| event | fixture:event | 8 | complete | choose 0: Enter | choose 1: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | fixture:route | 1 | complete | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.68: safer shop rest: reward=4.68, survivability=1.00 |
| card_reward | fixture:card_reward | 10 | complete | SKIP | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| card_reward | run:1781724756.run | 1 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 4 | partial | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 5 | partial | Pommel Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 7 | partial | Sentinel | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 8 | partial | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 10 | partial | Carnage | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 11 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 12 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 13 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 14 | partial | Offering | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724756.run | 15 | partial | Pommel Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781724756.run | 2 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781724756.run | 3 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1781724756.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781724861.run | 0 | partial | Bandage Up | Flash of Steel | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 1 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 3 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 5 | partial | Anger | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 7 | partial | Twin Strike | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 10 | partial | Twin Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 12 | partial | Bloodletting | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 13 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724861.run | 14 | partial | Twin Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781724861.run | 6 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781724861.run | 8 | partial | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781724861.run | 4 | partial | Block Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781724861.run | 2 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781724861.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781724941.run | 1 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724941.run | 2 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724941.run | 5 | partial | Uppercut | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724941.run | 8 | partial | Seeing Red | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724941.run | 10 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724941.run | 13 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781724941.run | 14 | partial | Battle Trance | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| event | run:1781724941.run | 4 | partial | Bought 1 Potion | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781724941.run | 11 | partial | Got Potions | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781724941.run | 3 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781724941.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781725014.run | 1 | partial | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 2 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 4 | partial | Heavy Blade | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 5 | partial | Inflame | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 7 | partial | Cleave | Impervious | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 8 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 10 | partial | Flame Barrier | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725014.run | 12 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| event | run:1781725014.run | 3 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725014.run | 13 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725014.run | 14 | partial | 1 cards matched | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1781725014.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781725093.run | 0 | partial | Swift Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 1 | partial | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 3 | partial | Iron Wave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 4 | partial | Inflame | Flame Barrier | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 5 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 7 | partial | Reckless Charge | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 8 | partial | Second Wind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 10 | partial | Bloodletting | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725093.run | 13 | partial | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781725093.run | 2 | partial | Touch | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725093.run | 11 | partial | Searched '0' times | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781725093.run | 14 | partial | Centennial Puzzle | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781725093.run | 14 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781725093.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 3 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.68: M@3,0 -> M@3,1 -> M@2,2 -> M@3,3 -> $@3,4 -> E@2,5: reward=9.68, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 3 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.68: M@3,0 -> M@3,1 -> M@2,2 -> M@3,3 -> $@3,4 -> E@2,5: reward=9.68, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@5,1 -> ?@5,2 -> M@4,3 -> M@4,4 -> R@3,5 -> E@4,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@5,1 -> ?@5,2 -> M@4,3 -> M@4,4 -> R@3,5 -> E@4,6: reward=7.60, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.34: M@6,2 -> M@5,3 -> ?@6,4 -> E@6,5 -> M@6,6 -> $@6,7: reward=10.34, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.34: M@6,2 -> M@5,3 -> ?@6,4 -> E@6,5 -> M@6,6 -> $@6,7: reward=10.34, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@4,3 -> M@4,4 -> R@3,5 -> E@4,6 -> M@3,7 -> T@3,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@4,3 -> M@4,4 -> R@3,5 -> E@4,6 -> M@3,7 -> T@3,8: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,4 -> R@3,5 -> E@4,6 -> M@3,7 -> T@3,8 -> R@3,9: reward=8.20, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,4 -> R@3,5 -> E@4,6 -> M@3,7 -> T@3,8 -> R@3,9: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@3,5 -> E@4,6 -> M@3,7 -> T@3,8 -> R@3,9 -> M@3,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@3,5 -> E@4,6 -> M@3,7 -> T@3,8 -> R@3,9 -> M@3,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: E@4,6 -> M@3,7 -> T@3,8 -> R@3,9 -> M@3,10 -> R@3,11: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: E@4,6 -> M@3,7 -> T@3,8 -> R@3,9 -> M@3,10 -> R@3,11: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Sentinel | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@3,7 -> T@3,8 -> R@3,9 -> M@3,10 -> M@2,11 -> E@2,12: reward=7.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@3,7 -> T@3,8 -> R@3,9 -> M@3,10 -> M@2,11 -> E@2,12: reward=7.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Flame Barrier | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| card_reward | decision_trace | 8 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: T@3,8 -> R@3,9 -> M@3,10 -> M@2,11 -> E@2,12 -> M@1,13: reward=7.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: T@3,8 -> R@3,9 -> M@3,10 -> M@2,11 -> E@2,12 -> M@1,13: reward=7.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: R@3,9 -> M@3,10 -> M@2,11 -> E@2,12 -> M@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: R@3,9 -> M@3,10 -> M@2,11 -> E@2,12 -> M@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Carnage | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@3,10 -> M@2,11 -> E@2,12 -> M@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: M@3,10 -> M@2,11 -> E@2,12 -> M@1,13 -> R@0,14: reward=5.50, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.10: R@3,11 -> M@3,12 -> M@2,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.10: R@3,11 -> M@3,12 -> M@2,13 -> R@1,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@3,12 -> M@2,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@3,12 -> M@2,13 -> R@1,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@2,13 -> R@1,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@2,13 -> R@1,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Offering | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@1,14: reward=1.10, survivability=1.00 |
| card_reward | decision_trace | 15 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Bandage Up | Flash of Steel | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@0,0 -> M@1,1 -> ?@2,2 -> M@2,3 -> $@1,4 -> E@0,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@0,0 -> M@1,1 -> ?@2,2 -> M@2,3 -> $@1,4 -> E@0,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.48: M@4,1 -> M@4,2 -> $@4,3 -> M@3,4 -> E@3,5 -> M@3,6: reward=9.48, survivability=1.00 |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.48: M@4,1 -> M@4,2 -> $@4,3 -> M@3,4 -> E@3,5 -> M@3,6: reward=9.48, survivability=1.00 |
| shop | decision_trace | 2 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 2 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> ?@6,3 -> M@6,4 -> R@6,5 -> E@6,6 -> M@6,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> ?@6,3 -> M@6,4 -> R@6,5 -> E@6,6 -> M@6,7: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@6,3 -> M@6,4 -> R@6,5 -> E@6,6 -> M@6,7 -> T@6,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@6,3 -> M@6,4 -> R@6,5 -> E@6,6 -> M@6,7 -> T@6,8: reward=8.10, survivability=1.00 |
| shop | decision_trace | 4 | complete | Block Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@6,4 -> R@6,5 -> E@6,6 -> M@6,7 -> T@6,8 -> M@6,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@6,4 -> R@6,5 -> E@6,6 -> M@6,7 -> T@6,8 -> M@6,9: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Anger | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,5 -> M@3,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> R@6,10: reward=6.60, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,5 -> M@3,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> R@6,10: reward=6.60, survivability=1.00 |
| event | decision_trace | 6 | complete | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 6 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> R@6,10 -> M@6,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@3,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> R@6,10 -> M@6,11: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Twin Strike | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@3,7 -> T@4,8 -> M@5,9 -> R@6,10 -> M@6,11 -> R@5,12: reward=6.70, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@3,7 -> T@4,8 -> M@5,9 -> R@6,10 -> M@6,11 -> R@5,12: reward=6.70, survivability=1.00 |
| event | decision_trace | 8 | complete | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@4,8 -> M@5,9 -> M@5,10 -> ?@5,11 -> R@5,12 -> ?@5,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@4,8 -> M@5,9 -> M@5,10 -> ?@5,11 -> R@5,12 -> ?@5,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@5,9 -> M@5,10 -> ?@5,11 -> R@5,12 -> ?@5,13 -> R@4,14: reward=6.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: M@5,9 -> M@5,10 -> ?@5,11 -> R@5,12 -> ?@5,13 -> R@4,14: reward=6.20, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.30: R@6,10 -> M@6,11 -> R@5,12 -> ?@5,13 -> R@4,14: reward=5.30, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.30: R@6,10 -> M@6,11 -> R@5,12 -> ?@5,13 -> R@4,14: reward=5.30, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: M@6,11 -> R@5,12 -> ?@5,13 -> R@4,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: M@6,11 -> R@5,12 -> ?@5,13 -> R@4,14: reward=4.20, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Bloodletting | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.20: R@5,12 -> ?@5,13 -> R@4,14: reward=3.20, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.20: R@5,12 -> ?@5,13 -> R@4,14: reward=3.20, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| card_reward | decision_trace | 13 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Twin Strike | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@0,0 -> M@1,1 -> $@1,2 -> M@1,3 -> M@2,4 -> E@1,5: reward=9.08, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@0,0 -> M@1,1 -> $@1,2 -> M@1,3 -> M@2,4 -> E@1,5: reward=9.08, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: M@1,1 -> $@1,2 -> M@1,3 -> M@2,4 -> E@1,5 -> M@2,6: reward=8.98, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: M@1,1 -> $@1,2 -> M@1,3 -> M@2,4 -> E@1,5 -> M@2,6: reward=8.98, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.50: $@1,2 -> M@1,3 -> M@2,4 -> E@1,5 -> M@2,6 -> E@2,7: reward=10.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.50: $@1,2 -> M@1,3 -> M@2,4 -> E@1,5 -> M@2,6 -> E@2,7: reward=10.50, survivability=1.00 |
| shop | decision_trace | 3 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@1,3 -> M@2,4 -> E@1,5 -> M@2,6 -> E@2,7 -> T@2,8: reward=9.50, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@1,3 -> M@2,4 -> E@1,5 -> M@2,6 -> E@2,7 -> T@2,8: reward=9.50, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Buy 1 Potion | choose 0: Buy 1 Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@2,4 -> E@1,5 -> M@2,6 -> E@2,7 -> T@2,8 -> M@1,9: reward=9.50, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@2,4 -> E@1,5 -> M@2,6 -> E@2,7 -> T@2,8 -> M@1,9: reward=9.50, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Uppercut | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@1,5 -> M@2,6 -> R@1,7 -> T@0,8 -> M@1,9 -> E@2,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: E@1,5 -> M@2,6 -> R@1,7 -> T@0,8 -> M@1,9 -> E@2,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: $@3,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> ?@6,10 -> R@6,11: reward=6.50, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: $@3,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> ?@6,10 -> R@6,11: reward=6.50, survivability=1.00 |
| shop | decision_trace | 7 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,7 -> T@4,8 -> M@5,9 -> ?@6,10 -> R@6,11 -> ?@5,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,7 -> T@4,8 -> M@5,9 -> ?@6,10 -> R@6,11 -> ?@5,12: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Seeing Red | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: T@4,8 -> $@3,9 -> ?@3,10 -> ?@4,11 -> M@4,12 -> M@4,13: reward=6.70, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: T@4,8 -> $@3,9 -> ?@3,10 -> ?@4,11 -> M@4,12 -> M@4,13: reward=6.70, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: $@3,9 -> ?@3,10 -> ?@4,11 -> M@4,12 -> M@4,13 -> R@5,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: $@3,9 -> ?@3,10 -> ?@4,11 -> M@4,12 -> M@4,13 -> R@5,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 10 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.02: ?@6,10 -> M@5,11 -> ?@5,12 -> M@5,13 -> R@5,14: reward=4.00, survivability=0.93 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.02: ?@6,10 -> M@5,11 -> ?@5,12 -> M@5,13 -> R@5,14: reward=4.00, survivability=0.93 |
| event | decision_trace | 11 | complete | choose 0: Search | choose 0: Search | medium | Bottled common event handling takes the main Lab reward. |
| route | decision_trace | 11 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: M@5,11 -> ?@5,12 -> M@5,13 -> R@5,14: reward=3.00, survivability=0.97 |
| route | decision_trace | 11 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.50: M@5,11 -> ?@5,12 -> M@5,13 -> R@5,14: reward=3.00, survivability=0.97 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@5,12 -> M@5,13 -> R@5,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@5,12 -> M@5,13 -> R@5,14: reward=2.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@5,13 -> R@5,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@5,13 -> R@5,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@5,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@5,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,0 -> M@1,1 -> M@1,2 -> ?@1,3 -> M@2,4 -> E@2,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,0 -> M@1,1 -> M@1,2 -> ?@1,3 -> M@2,4 -> E@2,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@5,1 -> M@5,2 -> M@5,3 -> ?@4,4 -> R@4,5 -> M@5,6: reward=6.10, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@5,1 -> M@5,2 -> M@5,3 -> ?@4,4 -> R@4,5 -> M@5,6: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> M@5,3 -> ?@4,4 -> R@4,5 -> M@5,6 -> E@4,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,2 -> M@5,3 -> ?@4,4 -> R@4,5 -> M@5,6 -> E@4,7: reward=7.60, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,3 -> M@6,4 -> R@6,5 -> M@6,6 -> ?@5,7 -> T@4,8: reward=6.60, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,3 -> M@6,4 -> R@6,5 -> M@6,6 -> ?@5,7 -> T@4,8: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Heavy Blade | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,4 -> R@6,5 -> M@6,6 -> ?@5,7 -> T@4,8 -> M@5,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,4 -> R@6,5 -> M@6,6 -> ?@5,7 -> T@4,8 -> M@5,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Inflame | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@6,5 -> M@6,6 -> M@6,7 -> T@5,8 -> M@5,9 -> $@6,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: R@6,5 -> M@6,6 -> M@6,7 -> T@5,8 -> M@5,9 -> $@6,10: reward=9.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@6,6 -> M@6,7 -> T@5,8 -> M@5,9 -> $@6,10 -> R@5,11: reward=9.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@6,6 -> M@6,7 -> T@5,8 -> M@5,9 -> $@6,10 -> R@5,11: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Pummel | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| card_reward | decision_trace | 7 | complete | Cleave | Impervious | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. |
| route | decision_trace | 7 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.10: M@6,7 -> T@5,8 -> M@5,9 -> $@6,10 -> R@5,11 -> E@4,12: reward=11.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.10: M@6,7 -> T@5,8 -> M@5,9 -> $@6,10 -> R@5,11 -> E@4,12: reward=11.10, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Shockwave | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: T@5,8 -> M@5,9 -> $@6,10 -> R@5,11 -> E@4,12 -> ?@3,13: reward=10.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: T@5,8 -> M@5,9 -> $@6,10 -> R@5,11 -> E@4,12 -> ?@3,13: reward=10.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@5,9 -> $@6,10 -> R@5,11 -> E@4,12 -> ?@3,13 -> R@4,14: reward=8.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@5,9 -> $@6,10 -> R@5,11 -> E@4,12 -> ?@3,13 -> R@4,14: reward=8.50, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Flame Barrier | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: $@6,10 -> R@5,11 -> E@4,12 -> ?@3,13 -> R@4,14: reward=7.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: $@6,10 -> R@5,11 -> E@4,12 -> ?@3,13 -> R@4,14: reward=7.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.25: M@4,11 -> E@4,12 -> M@4,13 -> R@5,14: reward=4.50, survivability=0.98 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.25: M@4,11 -> E@4,12 -> M@4,13 -> R@5,14: reward=4.50, survivability=0.98 |
| card_reward | decision_trace | 12 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@3,12 -> ?@3,13 -> R@4,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: ?@3,12 -> ?@3,13 -> R@4,14: reward=2.00, survivability=1.00 |
| event | decision_trace | 13 | complete | choose 1: Leave | choose 0: Take | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@3,13 -> R@4,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@3,13 -> R@4,14: reward=1.00, survivability=1.00 |
| event | decision_trace | 14 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Play | choose 0: Play | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: card0 | choose 0: card0 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: card1 | choose 0: card1 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: card2 | choose 0: card2 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: card3 | choose 0: card3 | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Bash | choose 0: Bash | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Double Tap | choose 0: Double Tap | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Bash | choose 0: Bash | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Double Tap | choose 0: Double Tap | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Bash | choose 0: Bash | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Double Tap | choose 0: Double Tap | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 14 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@4,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Battle Trance | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Swift Strike | Swift Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Swift Strike. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@6,0 -> M@6,1 -> M@6,2 -> $@6,3 -> ?@6,4 -> R@6,5: reward=7.98, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@6,0 -> M@6,1 -> M@6,2 -> $@6,3 -> ?@6,4 -> R@6,5: reward=7.98, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@0,1 -> M@1,2 -> ?@1,3 -> ?@1,4 -> R@0,5 -> E@0,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@0,1 -> M@1,2 -> ?@1,3 -> ?@1,4 -> R@0,5 -> E@0,6: reward=7.60, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Touch | choose 0: Touch | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,2 -> ?@1,3 -> ?@1,4 -> E@2,5 -> R@2,6 -> E@2,7: reward=8.00, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,2 -> ?@1,3 -> ?@1,4 -> E@2,5 -> R@2,6 -> E@2,7: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@2,3 -> ?@1,4 -> E@2,5 -> R@2,6 -> E@2,7 -> T@2,8: reward=8.50, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@2,3 -> ?@1,4 -> E@2,5 -> R@2,6 -> E@2,7 -> T@2,8: reward=8.50, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Inflame | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,4 -> E@2,5 -> R@2,6 -> E@2,7 -> T@2,8 -> M@2,9: reward=8.50, survivability=1.00 |
| route | decision_trace | 4 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,4 -> E@2,5 -> R@2,6 -> E@2,7 -> T@2,8 -> M@2,9: reward=8.50, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: E@2,5 -> R@2,6 -> E@2,7 -> T@2,8 -> M@2,9 -> ?@1,10: reward=8.50, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: E@2,5 -> R@2,6 -> E@2,7 -> T@2,8 -> M@2,9 -> ?@1,10: reward=8.50, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,6 -> M@3,7 -> T@3,8 -> M@3,9 -> M@4,10 -> E@4,11: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,6 -> M@3,7 -> T@3,8 -> M@3,9 -> M@4,10 -> E@4,11: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Reckless Charge | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@4,7 -> T@4,8 -> M@3,9 -> M@4,10 -> E@4,11 -> ?@4,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@4,7 -> T@4,8 -> M@3,9 -> M@4,10 -> E@4,11 -> ?@4,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Second Wind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@3,8 -> M@3,9 -> M@4,10 -> E@4,11 -> ?@4,12 -> $@4,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@3,8 -> M@3,9 -> M@4,10 -> E@4,11 -> ?@4,12 -> $@4,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@3,9 -> M@4,10 -> E@4,11 -> ?@4,12 -> $@4,13 -> R@3,14: reward=9.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@3,9 -> M@4,10 -> E@4,11 -> ?@4,12 -> $@4,13 -> R@3,14: reward=9.50, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Bloodletting | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@4,10 -> E@4,11 -> ?@4,12 -> $@4,13 -> R@3,14: reward=8.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@4,10 -> E@4,11 -> ?@4,12 -> $@4,13 -> R@3,14: reward=8.50, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| event | decision_trace | 11 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.20: R@3,11 -> M@3,12 -> $@4,13 -> R@3,14: reward=7.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.20: R@3,11 -> M@3,12 -> $@4,13 -> R@3,14: reward=7.20, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@3,12 -> $@4,13 -> R@3,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@3,12 -> $@4,13 -> R@3,14: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.10: $@4,13 -> R@3,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.10: $@4,13 -> R@3,14: reward=5.10, survivability=1.00 |
| shop | decision_trace | 14 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 14 | complete | Centennial Puzzle | Centennial Puzzle | high | Bottled shop relic list ranks Centennial Puzzle as buyable. |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@3,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

1. **card_reward floor 4**: current `Heavy Blade` vs reference `Perfected Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Repeated 2x in non-fixture evidence.
2. **card_reward floor 5**: current `Anger` vs reference `Pommel Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Repeated 2x in non-fixture evidence.
3. **card_reward floor 5**: current `Uppercut` vs reference `Dropkick` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Repeated 2x in non-fixture evidence.
4. **card_reward floor 7**: current `Twin Strike` vs reference `Battle Trance` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Repeated 2x in non-fixture evidence.
5. **card_reward floor 7**: current `Reckless Charge` vs reference `Shrug It Off` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Repeated 2x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
