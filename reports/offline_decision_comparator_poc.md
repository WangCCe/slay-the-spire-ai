# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 394
- Differences: 233
- Categories: card_reward=93, event=79, route=196, shop=26
- Evidence quality: complete=307, partial=87

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| shop | fixture:shop | 5 | complete | Anger | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| event | fixture:event | 8 | complete | choose 0: Enter | choose 1: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | fixture:route | 1 | complete | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.68: safer shop rest: reward=4.68, survivability=1.00 |
| card_reward | fixture:card_reward | 10 | complete | SKIP | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| card_reward | run:1781725754.run | 0 | partial | Good Instincts | Dramatic Entrance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dramatic Entrance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 1 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 2 | partial | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 4 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 5 | partial | Clothesline | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 7 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 11 | partial | Iron Wave | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 13 | partial | Sever Soul | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725754.run | 14 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781725754.run | 10 | partial | Relic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781725754.run | 3 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781725754.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781725871.run | 0 | partial | Dark Shackles | Flash of Steel | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 1 | partial | Uppercut | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 4 | partial | Sword Boomerang | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 5 | partial | SKIP | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 6 | partial | Headbutt | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 10 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 13 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 16 | partial | Offering | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 17 | partial | Armaments | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 18 | partial | Hemokinesis | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725871.run | 19 | partial | Clothesline+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781725871.run | 2 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725871.run | 3 | partial | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725871.run | 11 | partial | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725871.run | 20 | partial | Gave Potion | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781725871.run | 8 | partial | Shockwave | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781725871.run | 21 | partial | Block Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781725871.run | 8 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781725871.run | 21 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781725871.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781725951.run | 0 | partial | Finesse | Flash of Steel | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flash of Steel. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725951.run | 1 | partial | Thunderclap | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725951.run | 2 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725951.run | 4 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725951.run | 5 | partial | Thunderclap | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725951.run | 7 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781725951.run | 13 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781725951.run | 3 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781725951.run | 10 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781725951.run | 12 | partial | Block Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781725951.run | 12 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781725951.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781726053.run | 0 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 1 | partial | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 4 | partial | True Grit | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 8 | partial | Sever Soul | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 11 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 13 | partial | Havoc | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 14 | partial | Power Through | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 16 | partial | Reaper | Reaper | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 18 | partial | Cleave | Flame Barrier+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier+1. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726053.run | 19 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| event | run:1781726053.run | 2 | partial | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 3 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 5 | partial | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 7 | partial | Offered Basic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 20 | partial | Shed Blood | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 21 | partial | Obtained Relic | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 22 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726053.run | 25 | partial | Stole From Cult | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1781726053.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781726151.run | 0 | partial | Finesse | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726151.run | 1 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726151.run | 3 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726151.run | 4 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726151.run | 5 | partial | Sever Soul | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726151.run | 8 | partial | Uppercut | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781726151.run | 12 | partial | Iron Wave | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781726151.run | 2 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726151.run | 7 | partial | Transformed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726151.run | 10 | partial | Healed and dodged fight | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781726151.run | 11 | partial | Bought 1 Potion | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781726151.run | 14 | partial | Shockwave+1 | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781726151.run | 14 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781726151.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Good Instincts | Dramatic Entrance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dramatic Entrance. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@5,0 -> ?@5,1 -> ?@4,2 -> $@5,3 -> M@4,4 -> E@4,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@5,0 -> ?@5,1 -> ?@4,2 -> $@5,3 -> M@4,4 -> E@4,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 1 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.18: M@2,1 -> $@1,2 -> M@1,3 -> ?@2,4 -> E@2,5 -> ?@1,6: reward=9.18, survivability=1.00 |
| route | decision_trace | 1 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.18: M@2,1 -> $@1,2 -> M@1,3 -> ?@2,4 -> E@2,5 -> ?@1,6: reward=9.18, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Power Through | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.24: $@1,2 -> M@1,3 -> ?@2,4 -> E@2,5 -> ?@1,6 -> M@2,7: reward=9.24, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.24: $@1,2 -> M@1,3 -> ?@2,4 -> E@2,5 -> ?@1,6 -> M@2,7: reward=9.24, survivability=1.00 |
| shop | decision_trace | 3 | complete | purge | Perfected Strike | high | Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. |
| shop | decision_trace | 3 | complete | leave | Perfected Strike | high | Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,3 -> ?@2,4 -> E@2,5 -> ?@1,6 -> M@2,7 -> T@2,8: reward=8.00, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@1,3 -> ?@2,4 -> E@2,5 -> ?@1,6 -> M@2,7 -> T@2,8: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@2,4 -> E@2,5 -> ?@1,6 -> M@2,7 -> T@2,8 -> ?@1,9: reward=8.00, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@2,4 -> E@2,5 -> ?@1,6 -> M@2,7 -> T@2,8 -> ?@1,9: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Clothesline | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,5 -> M@0,6 -> R@0,7 -> T@0,8 -> ?@1,9 -> M@1,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,5 -> M@0,6 -> R@0,7 -> T@0,8 -> ?@1,9 -> M@1,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@0,6 -> R@0,7 -> T@0,8 -> ?@1,9 -> M@1,10 -> R@1,11: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@0,6 -> R@0,7 -> T@0,8 -> ?@1,9 -> M@1,10 -> R@1,11: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@0,7 -> T@0,8 -> ?@1,9 -> M@1,10 -> M@2,11 -> E@2,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@0,7 -> T@0,8 -> ?@1,9 -> M@1,10 -> M@2,11 -> E@2,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@0,8 -> ?@1,9 -> M@1,10 -> R@1,11 -> M@1,12 -> M@0,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@0,8 -> ?@1,9 -> M@1,10 -> R@1,11 -> M@1,12 -> M@0,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: ?@1,9 -> M@1,10 -> R@1,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=6.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: ?@1,9 -> M@1,10 -> R@1,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=6.20, survivability=1.00 |
| event | decision_trace | 10 | complete | choose 0: Play | choose 0: Play | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: spin | choose 0: spin | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Prize! | choose 0: Prize! | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@1,10 -> R@1,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@1,10 -> R@1,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Iron Wave | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: R@1,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: R@1,11 -> M@1,12 -> M@0,13 -> R@1,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@1,12 -> M@0,13 -> R@1,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@1,12 -> M@0,13 -> R@1,14: reward=2.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Sever Soul | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@0,13 -> R@1,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@0,13 -> R@1,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Dark Shackles | Dark Shackles | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dark Shackles. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@0,1 -> ?@0,2 -> M@1,3 -> M@1,4 -> E@0,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@0,1 -> ?@0,2 -> M@1,3 -> M@1,4 -> E@0,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Uppercut | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@5,1 -> ?@4,2 -> M@5,3 -> M@5,4 -> ?@5,5 -> R@6,6: reward=6.10, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: ?@5,1 -> ?@4,2 -> M@5,3 -> M@5,4 -> ?@5,5 -> R@6,6: reward=6.10, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.00: ?@4,2 -> M@5,3 -> M@5,4 -> M@4,5 -> M@4,6 -> ?@3,7: reward=6.00, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.00: ?@4,2 -> M@5,3 -> M@5,4 -> M@4,5 -> M@4,6 -> ?@3,7: reward=6.00, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 3 | complete | choose 0: Continue | choose 0: Continue | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@5,3 -> M@5,4 -> M@4,5 -> M@4,6 -> ?@3,7 -> T@4,8: reward=6.50, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@5,3 -> M@5,4 -> M@4,5 -> M@4,6 -> ?@3,7 -> T@4,8: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Sword Boomerang | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> M@4,5 -> M@4,6 -> ?@3,7 -> T@4,8 -> R@3,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@5,4 -> M@4,5 -> M@4,6 -> ?@3,7 -> T@4,8 -> R@3,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@4,5 -> M@4,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> E@6,10: reward=8.00, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@4,5 -> M@4,6 -> ?@3,7 -> T@4,8 -> M@5,9 -> E@6,10: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | Headbutt | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.32: R@6,6 -> $@5,7 -> T@6,8 -> M@5,9 -> E@6,10 -> M@6,11: reward=10.32, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.32: R@6,6 -> $@5,7 -> T@6,8 -> M@5,9 -> E@6,10 -> M@6,11: reward=10.32, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.22: $@5,7 -> T@6,8 -> M@5,9 -> E@6,10 -> M@6,11 -> ?@5,12: reward=10.22, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.22: $@5,7 -> T@6,8 -> M@5,9 -> E@6,10 -> M@6,11 -> ?@5,12: reward=10.22, survivability=1.00 |
| shop | decision_trace | 8 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 8 | complete | Shockwave | Shockwave | high | Bottled shop card list ranks Shockwave as buyable. |
| shop | decision_trace | 8 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@6,8 -> M@5,9 -> ?@5,10 -> R@4,11 -> M@4,12 -> ?@5,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@6,8 -> M@5,9 -> ?@5,10 -> R@4,11 -> M@4,12 -> ?@5,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.54: M@5,9 -> ?@5,10 -> R@4,11 -> M@4,12 -> $@4,13 -> R@4,14: reward=6.54, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.54: M@5,9 -> ?@5,10 -> R@4,11 -> M@4,12 -> $@4,13 -> R@4,14: reward=6.54, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: ?@5,10 -> R@4,11 -> M@4,12 -> $@4,13 -> R@4,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: ?@5,10 -> R@4,11 -> M@4,12 -> $@4,13 -> R@4,14: reward=5.60, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: R@4,11 -> M@4,12 -> $@4,13 -> R@4,14: reward=4.60, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: R@4,11 -> M@4,12 -> $@4,13 -> R@4,14: reward=4.60, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@4,12 -> $@4,13 -> R@4,14: reward=3.50, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.50: M@4,12 -> $@4,13 -> R@4,14: reward=3.50, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.58: $@4,13 -> R@4,14: reward=2.58, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.58: $@4,13 -> R@4,14: reward=2.58, survivability=1.00 |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Offering | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| card_reward | decision_trace | 17 | complete | Armaments | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 17 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@5,0 -> M@6,1 -> ?@5,2 -> $@5,3 -> ?@4,4 -> R@4,5: reward=10.10, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@5,0 -> M@6,1 -> ?@5,2 -> $@5,3 -> ?@4,4 -> R@4,5: reward=10.10, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Corruption | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 18 | complete | Hemokinesis | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@6,1 -> ?@5,2 -> M@4,3 -> $@3,4 -> R@2,5 -> M@3,6: reward=9.60, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: M@6,1 -> ?@5,2 -> M@4,3 -> $@3,4 -> R@2,5 -> M@3,6: reward=9.60, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Feel No Pain | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 19 | complete | Clothesline+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 19 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.00: M@6,2 -> $@5,3 -> ?@4,4 -> M@5,5 -> ?@4,6 -> M@3,7: reward=10.00, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.00: M@6,2 -> $@5,3 -> ?@4,4 -> M@5,5 -> ?@4,6 -> M@3,7: reward=10.00, survivability=1.00 |
| event | decision_trace | 20 | complete | choose 0: Give Potion | choose 0: Give Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: $@5,3 -> ?@4,4 -> R@4,5 -> ?@4,6 -> R@4,7 -> T@5,8: reward=9.60, survivability=1.00 |
| route | decision_trace | 20 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.60: $@5,3 -> ?@4,4 -> R@4,5 -> ?@4,6 -> R@4,7 -> T@5,8: reward=9.60, survivability=1.00 |
| shop | decision_trace | 21 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 21 | complete | Block Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 21 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@4,4 -> R@4,5 -> M@3,6 -> ?@2,7 -> T@1,8 -> E@0,9: reward=8.00, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@4,4 -> R@4,5 -> M@3,6 -> ?@2,7 -> T@1,8 -> E@0,9: reward=8.00, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Finesse | Finesse | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Finesse. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@0,0 -> M@0,1 -> $@1,2 -> ?@1,3 -> M@1,4 -> E@1,5: reward=9.08, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@0,0 -> M@0,1 -> $@1,2 -> ?@1,3 -> M@1,4 -> E@1,5: reward=9.08, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@4,1 -> ?@3,2 -> M@4,3 -> M@4,4 -> E@5,5 -> ?@5,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@4,1 -> ?@3,2 -> M@4,3 -> M@4,4 -> E@5,5 -> ?@5,6: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@3,2 -> M@4,3 -> M@4,4 -> E@5,5 -> ?@5,6 -> M@4,7: reward=7.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@3,2 -> M@4,3 -> M@4,4 -> E@5,5 -> ?@5,6 -> M@4,7: reward=7.50, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,3 -> M@4,4 -> R@3,5 -> M@3,6 -> R@3,7 -> T@2,8: reward=6.70, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,3 -> M@4,4 -> R@3,5 -> M@3,6 -> R@3,7 -> T@2,8: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,4 -> R@3,5 -> M@3,6 -> R@3,7 -> T@2,8 -> ?@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@4,4 -> R@3,5 -> M@3,6 -> R@3,7 -> T@2,8 -> ?@2,9: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: E@5,5 -> ?@5,6 -> M@4,7 -> T@4,8 -> M@4,9 -> M@5,10: reward=8.00, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.00: E@5,5 -> ?@5,6 -> M@4,7 -> T@4,8 -> M@4,9 -> M@5,10: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@3,6 -> R@3,7 -> T@2,8 -> ?@2,9 -> R@3,10 -> ?@3,11: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@3,6 -> R@3,7 -> T@2,8 -> ?@2,9 -> R@3,10 -> ?@3,11: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@4,7 -> T@4,8 -> M@4,9 -> M@5,10 -> R@5,11 -> E@4,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@4,7 -> T@4,8 -> M@4,9 -> M@5,10 -> R@5,11 -> E@4,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 11.10: T@4,8 -> M@4,9 -> M@5,10 -> R@5,11 -> E@4,12 -> $@3,13: reward=11.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 11.10: T@4,8 -> M@4,9 -> M@5,10 -> R@5,11 -> E@4,12 -> $@3,13: reward=11.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@2,9 -> M@2,10 -> ?@3,11 -> M@3,12 -> $@3,13 -> R@2,14: reward=9.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@2,9 -> M@2,10 -> ?@3,11 -> M@3,12 -> $@3,13 -> R@2,14: reward=9.10, survivability=1.00 |
| event | decision_trace | 10 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@3,10 -> ?@3,11 -> M@3,12 -> $@3,13 -> R@2,14: reward=8.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.20: R@3,10 -> ?@3,11 -> M@3,12 -> $@3,13 -> R@2,14: reward=8.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,11 -> M@3,12 -> $@3,13 -> R@2,14: reward=7.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: ?@3,11 -> M@3,12 -> $@3,13 -> R@2,14: reward=7.10, survivability=1.00 |
| shop | decision_trace | 12 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 12 | complete | Block Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 12 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.02: M@3,12 -> $@3,13 -> R@2,14: reward=4.02, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.02: M@3,12 -> $@3,13 -> R@2,14: reward=4.02, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 13 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.04: $@3,13 -> R@2,14: reward=3.04, survivability=1.00 |
| route | decision_trace | 13 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.04: $@3,13 -> R@2,14: reward=3.04, survivability=1.00 |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a Card to obtain | choose 0: Choose a Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 3 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@3,0 -> M@3,1 -> M@4,2 -> ?@4,3 -> $@4,4 -> E@4,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 3 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@3,0 -> M@3,1 -> M@4,2 -> ?@4,3 -> $@4,4 -> E@4,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Perfected Strike | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.96: ?@6,1 -> ?@5,2 -> M@6,3 -> M@5,4 -> R@6,5 -> $@6,6: reward=7.96, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.96: ?@6,1 -> ?@5,2 -> M@6,3 -> M@5,4 -> R@6,5 -> $@6,6: reward=7.96, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.46: ?@5,2 -> M@6,3 -> M@5,4 -> R@6,5 -> $@6,6 -> E@6,7: reward=9.46, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.46: ?@5,2 -> M@6,3 -> M@5,4 -> R@6,5 -> $@6,6 -> E@6,7: reward=9.46, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 1: Disagree | choose 0: Agree | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.96: M@6,3 -> M@5,4 -> R@6,5 -> $@6,6 -> E@6,7 -> T@5,8: reward=9.96, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.96: M@6,3 -> M@5,4 -> R@6,5 -> $@6,6 -> E@6,7 -> T@5,8: reward=9.96, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | True Grit | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 4 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.68: ?@6,4 -> R@6,5 -> $@6,6 -> E@6,7 -> T@5,8 -> R@6,9: reward=9.68, survivability=1.00 |
| route | decision_trace | 4 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.68: ?@6,4 -> R@6,5 -> $@6,6 -> E@6,7 -> T@5,8 -> R@6,9: reward=9.68, survivability=1.00 |
| event | decision_trace | 5 | complete | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 5 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: R@6,5 -> $@6,6 -> E@6,7 -> T@5,8 -> M@4,9 -> R@3,10: reward=8.98, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: R@6,5 -> $@6,6 -> E@6,7 -> T@5,8 -> M@4,9 -> R@3,10: reward=8.98, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.98: $@6,6 -> E@6,7 -> T@5,8 -> R@6,9 -> M@5,10 -> R@4,11: reward=8.98, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.98: $@6,6 -> E@6,7 -> T@5,8 -> R@6,9 -> M@5,10 -> R@4,11: reward=8.98, survivability=1.00 |
| event | decision_trace | 7 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | choose 0: Offer | choose 0: Offer | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@5,7 -> T@5,8 -> R@6,9 -> M@5,10 -> R@4,11 -> M@3,12: reward=6.70, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@5,7 -> T@5,8 -> R@6,9 -> M@5,10 -> R@4,11 -> M@3,12: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Sever Soul | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: T@5,8 -> R@6,9 -> M@5,10 -> R@4,11 -> M@3,12 -> M@2,13: reward=6.70, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: T@5,8 -> R@6,9 -> M@5,10 -> R@4,11 -> M@3,12 -> M@2,13: reward=6.70, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@6,9 -> M@5,10 -> R@4,11 -> M@3,12 -> M@2,13 -> R@2,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 9 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@6,9 -> M@5,10 -> R@4,11 -> M@3,12 -> M@2,13 -> R@2,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@5,10 -> R@4,11 -> M@3,12 -> M@2,13 -> R@2,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@5,10 -> R@4,11 -> M@3,12 -> M@2,13 -> R@2,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@4,11 -> M@3,12 -> M@2,13 -> R@2,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@4,11 -> M@3,12 -> M@2,13 -> R@2,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@3,12 -> M@2,13 -> R@2,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@3,12 -> M@2,13 -> R@2,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Havoc | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@5,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@5,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Power Through | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Demon Form | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 16 | complete | Reaper | Reaper | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. |
| route | decision_trace | 17 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@4,0 -> M@4,1 -> ?@4,2 -> ?@4,3 -> ?@5,4 -> E@5,5: reward=9.00, survivability=1.00 |
| route | decision_trace | 17 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@4,0 -> M@4,1 -> ?@4,2 -> ?@4,3 -> ?@5,4 -> E@5,5: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Cleave | Flame Barrier+ | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier+. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@3,1 -> M@3,2 -> M@3,3 -> M@4,4 -> E@5,5 -> M@5,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@3,1 -> M@3,2 -> M@3,3 -> M@4,4 -> E@5,5 -> M@5,6: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Shockwave | Shockwave | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@4,2 -> ?@4,3 -> M@4,4 -> M@4,5 -> M@5,6 -> ?@5,7: reward=7.50, survivability=1.00 |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@4,2 -> ?@4,3 -> M@4,4 -> M@4,5 -> M@5,6 -> ?@5,7: reward=7.50, survivability=1.00 |
| event | decision_trace | 20 | complete | choose 0: Locked | choose 0: Locked | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.13: $@5,3 -> ?@5,4 -> E@5,5 -> M@5,6 -> ?@5,7 -> T@6,8: reward=12.00, survivability=0.94 |
| route | decision_trace | 20 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.13: $@5,3 -> ?@5,4 -> E@5,5 -> M@5,6 -> ?@5,7 -> T@6,8: reward=12.00, survivability=0.94 |
| event | decision_trace | 21 | complete | choose 0: Offer Gold | choose 0: Offer Gold | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 21 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.21: ?@5,4 -> E@5,5 -> M@5,6 -> R@4,7 -> T@5,8 -> $@4,9: reward=10.50, survivability=0.98 |
| route | decision_trace | 21 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.21: ?@5,4 -> E@5,5 -> M@5,6 -> R@4,7 -> T@5,8 -> $@4,9: reward=10.50, survivability=0.98 |
| event | decision_trace | 22 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| event | decision_trace | 22 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| route | decision_trace | 22 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.71: E@5,5 -> M@5,6 -> R@4,7 -> T@5,8 -> $@4,9 -> M@4,10: reward=10.00, survivability=0.98 |
| route | decision_trace | 22 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.71: E@5,5 -> M@5,6 -> R@4,7 -> T@5,8 -> $@4,9 -> M@4,10: reward=10.00, survivability=0.98 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.80: M@5,6 -> R@4,7 -> T@5,8 -> $@4,9 -> M@4,10 -> ?@3,11: reward=9.80, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.80: M@5,6 -> R@4,7 -> T@5,8 -> $@4,9 -> M@4,10 -> ?@3,11: reward=9.80, survivability=1.00 |
| route | decision_trace | 24 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@5,7 -> T@6,8 -> M@5,9 -> M@4,10 -> E@5,11 -> ?@5,12: reward=9.00, survivability=1.00 |
| route | decision_trace | 24 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: ?@5,7 -> T@6,8 -> M@5,9 -> M@4,10 -> E@5,11 -> ?@5,12: reward=9.00, survivability=1.00 |
| event | decision_trace | 25 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 25 | complete | choose 0: Smash and Grab | choose 0: Smash and Grab | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 25 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@6,8 -> M@5,9 -> M@4,10 -> ?@3,11 -> ?@3,12 -> ?@3,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@6,8 -> M@5,9 -> M@4,10 -> ?@3,11 -> ?@3,12 -> ?@3,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,9 -> M@4,10 -> ?@3,11 -> ?@3,12 -> ?@3,13 -> R@2,14: reward=7.60, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@5,9 -> M@4,10 -> ?@3,11 -> ?@3,12 -> ?@3,13 -> R@2,14: reward=7.60, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Finesse | Finesse | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Finesse. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> ?@0,1 -> M@0,2 -> M@0,3 -> M@1,4 -> E@1,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> ?@0,1 -> M@0,2 -> M@0,3 -> M@1,4 -> E@1,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@0,1 -> M@0,2 -> M@0,3 -> M@1,4 -> E@1,5 -> R@2,6: reward=6.50, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@0,1 -> M@0,2 -> M@0,3 -> M@1,4 -> E@1,5 -> R@2,6: reward=6.50, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@0,2 -> M@0,3 -> M@1,4 -> E@1,5 -> R@2,6 -> M@1,7: reward=6.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: M@0,2 -> M@0,3 -> M@1,4 -> E@1,5 -> R@2,6 -> M@1,7: reward=6.50, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@0,3 -> M@1,4 -> E@1,5 -> R@2,6 -> M@1,7 -> T@1,8: reward=7.00, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@0,3 -> M@1,4 -> E@1,5 -> R@2,6 -> M@1,7 -> T@1,8: reward=7.00, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@1,4 -> E@1,5 -> R@2,6 -> M@1,7 -> T@1,8 -> M@2,9: reward=7.00, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@1,4 -> E@1,5 -> R@2,6 -> M@1,7 -> T@1,8 -> M@2,9: reward=7.00, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Sever Soul | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.25: E@1,5 -> R@2,6 -> M@1,7 -> T@1,8 -> M@2,9 -> $@2,10: reward=10.00, survivability=0.88 |
| route | decision_trace | 5 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.25: E@1,5 -> R@2,6 -> M@1,7 -> T@1,8 -> M@2,9 -> $@2,10: reward=10.00, survivability=0.88 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@1,6 -> ?@0,7 -> T@0,8 -> ?@0,9 -> ?@1,10 -> M@1,11: reward=6.50, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: ?@1,6 -> ?@0,7 -> T@0,8 -> ?@0,9 -> ?@1,10 -> M@1,11: reward=6.50, survivability=1.00 |
| event | decision_trace | 7 | complete | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@0,7 -> T@0,8 -> ?@0,9 -> ?@1,10 -> M@1,11 -> E@1,12: reward=8.00, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@0,7 -> T@0,8 -> ?@0,9 -> ?@1,10 -> M@1,11 -> E@1,12: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 8 | complete | Uppercut | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@0,8 -> ?@0,9 -> ?@1,10 -> M@1,11 -> E@1,12 -> $@0,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.00: T@0,8 -> ?@0,9 -> ?@1,10 -> M@1,11 -> E@1,12 -> $@0,13: reward=11.00, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: ?@0,9 -> ?@1,10 -> M@1,11 -> E@1,12 -> $@0,13 -> R@0,14: reward=9.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: ?@0,9 -> ?@1,10 -> M@1,11 -> E@1,12 -> $@0,13 -> R@0,14: reward=9.50, survivability=1.00 |
| event | decision_trace | 10 | complete | choose 1: Eat | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 10 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,10 -> M@1,11 -> E@1,12 -> $@0,13 -> R@0,14: reward=8.50, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,10 -> M@1,11 -> E@1,12 -> $@0,13 -> R@0,14: reward=8.50, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 0: Buy 1 Potion | choose 0: Buy 1 Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,11 -> E@1,12 -> $@0,13 -> R@0,14: reward=7.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@1,11 -> E@1,12 -> $@0,13 -> R@0,14: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 12 | complete | Iron Wave | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 12 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.50: E@1,12 -> $@0,13 -> R@0,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.50: E@1,12 -> $@0,13 -> R@0,14: reward=6.50, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.56: $@0,13 -> R@0,14: reward=3.56, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.56: $@0,13 -> R@0,14: reward=3.56, survivability=1.00 |
| shop | decision_trace | 14 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority removes curses first. |
| shop | decision_trace | 14 | complete | Shockwave+ | Shockwave+ | high | Bottled shop card list ranks Shockwave+ as buyable. |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@0,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

1. **shop floor 3**: current `purge` vs reference `Perfected Strike` (high). Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. Repeated 2x in non-fixture evidence.
2. **shop floor 12**: current `Block Potion` vs reference `leave` (high). Bottled shop handler leaves when no priority purchase is affordable. Repeated 2x in non-fixture evidence.
3. **card_reward floor 5**: current `Clothesline` vs reference `Perfected Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Repeated 3x in non-fixture evidence.
4. **card_reward floor 8**: current `Sever Soul` vs reference `Twin Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Repeated 3x in non-fixture evidence.
5. **card_reward floor 4**: current `True Grit` vs reference `Dropkick` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Repeated 2x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
