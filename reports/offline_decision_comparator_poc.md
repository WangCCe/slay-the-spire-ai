# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 411
- Differences: 252
- Categories: card_reward=93, event=78, route=222, shop=18
- Evidence quality: complete=320, partial=91

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| card_reward | run:1781716984.run | 1 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 3 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 5 | partial | Anger | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 7 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 10 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 11 | partial | Uppercut | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 13 | partial | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781716984.run | 14 | partial | Iron Wave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781716984.run | 2 | partial | Gather Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781716984.run | 8 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781716984.run | 12 | partial | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781716984.run | 4 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781716984.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781717072.run | 0 | partial | Blind | Dramatic Entrance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Dramatic Entrance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717072.run | 1 | partial | Whirlwind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717072.run | 3 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717072.run | 5 | partial | Ghostly Armor | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717072.run | 7 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717072.run | 12 | partial | Sword Boomerang | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717072.run | 14 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| event | run:1781717072.run | 2 | partial | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717072.run | 6 | partial | Forge | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781717072.run | 11 | partial | Battle Trance | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781717072.run | 11 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781717072.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781717218.run | 1 | partial | Headbutt | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 4 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 5 | partial | Carnage | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 10 | partial | Iron Wave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 11 | partial | Disarm | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 12 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 13 | partial | True Grit | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 14 | partial | Burning Pact | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 16 | partial | Corruption | Reaper | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 18 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 19 | partial | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717218.run | 24 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781717218.run | 2 | partial | Gather Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717218.run | 7 | partial | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717218.run | 11 | partial | Fought Mushrooms | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717218.run | 20 | partial | Paid Fearfully | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717218.run | 22 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717218.run | 27 | partial | Fight | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717218.run | 27 | partial | Fled From Nobs | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781717218.run | 3 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781717218.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781717307.run | 1 | partial | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717307.run | 3 | partial | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717307.run | 4 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717307.run | 5 | partial | Uppercut | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717307.run | 7 | partial | Clothesline | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717307.run | 11 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717307.run | 13 | partial | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781717307.run | 2 | partial | Purged | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717307.run | 14 | partial | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1781717307.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781717464.run | 1 | partial | Anger | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 2 | partial | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 4 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 5 | partial | Demon Form | Flame Barrier | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 11 | partial | Blood for Blood | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 14 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 16 | partial | Immolate | Reaper | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 18 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 22 | partial | Whirlwind+1 | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 24 | partial | Disarm | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 29 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781717464.run | 30 | partial | SKIP | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781717464.run | 11 | partial | Fought Mushrooms | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717464.run | 12 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717464.run | 13 | partial | Paid Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717464.run | 20 | partial | Heal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781717464.run | 21 | partial | Paid Fearfully | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781717464.run | 3 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781717464.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Obtain a random rare Card | choose 0: Obtain a random rare Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.68: M@2,0 -> ?@1,1 -> M@2,2 -> $@1,3 -> M@0,4 -> R@0,5: reward=7.68, survivability=1.00 |
| route | decision_trace | 0 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 0 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 1 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.76: ?@1,1 -> M@2,2 -> $@1,3 -> M@0,4 -> R@0,5 -> M@1,6: reward=7.76, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.76: ?@1,1 -> M@2,2 -> $@1,3 -> M@0,4 -> R@0,5 -> M@1,6: reward=7.76, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Gather Gold | choose 0: Gather Gold | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@2,2 -> $@1,3 -> M@0,4 -> R@0,5 -> M@1,6 -> ?@1,7: reward=9.10, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: M@2,2 -> $@1,3 -> M@0,4 -> R@0,5 -> M@1,6 -> ?@1,7: reward=9.10, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: $@1,3 -> M@0,4 -> R@0,5 -> M@1,6 -> ?@1,7 -> T@0,8: reward=9.60, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: $@1,3 -> M@0,4 -> R@0,5 -> M@1,6 -> ?@1,7 -> T@0,8: reward=9.60, survivability=1.00 |
| shop | decision_trace | 4 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@0,4 -> R@0,5 -> M@1,6 -> ?@1,7 -> T@1,8 -> R@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@0,4 -> R@0,5 -> M@1,6 -> ?@1,7 -> T@1,8 -> R@2,9: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Anger | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,5 -> M@1,6 -> ?@1,7 -> T@1,8 -> R@2,9 -> M@2,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@0,5 -> M@1,6 -> ?@1,7 -> T@1,8 -> R@2,9 -> M@2,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@1,6 -> ?@1,7 -> T@1,8 -> R@2,9 -> M@2,10 -> R@1,11: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@1,6 -> ?@1,7 -> T@1,8 -> R@2,9 -> M@2,10 -> R@1,11: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@1,7 -> T@1,8 -> R@2,9 -> M@2,10 -> R@1,11 -> ?@1,12: reward=6.70, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@1,7 -> T@1,8 -> R@2,9 -> M@2,10 -> R@1,11 -> ?@1,12: reward=6.70, survivability=1.00 |
| event | decision_trace | 8 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 8 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 8 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.20: T@1,8 -> R@2,9 -> M@2,10 -> R@1,11 -> ?@1,12 -> E@1,13: reward=8.20, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.20: T@1,8 -> R@2,9 -> M@2,10 -> R@1,11 -> ?@1,12 -> E@1,13: reward=8.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@1,9 -> M@2,10 -> R@1,11 -> ?@1,12 -> E@1,13 -> R@1,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: M@1,9 -> M@2,10 -> R@1,11 -> ?@1,12 -> E@1,13 -> R@1,14: reward=7.70, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@2,10 -> R@1,11 -> ?@1,12 -> E@1,13 -> R@1,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@2,10 -> R@1,11 -> ?@1,12 -> E@1,13 -> R@1,14: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Uppercut | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.60: ?@3,11 -> M@3,12 -> E@2,13 -> R@1,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 5.60: ?@3,11 -> M@3,12 -> E@2,13 -> R@1,14: reward=5.60, survivability=1.00 |
| event | decision_trace | 12 | complete | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: M@3,12 -> E@2,13 -> R@1,14: reward=4.60, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.60: M@3,12 -> E@2,13 -> R@1,14: reward=4.60, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.60: E@2,13 -> R@1,14: reward=3.60, survivability=1.00 |
| route | decision_trace | 13 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.60: E@2,13 -> R@1,14: reward=3.60, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@4,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Blind | Blind | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Blind. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@1,1 -> M@1,2 -> M@2,3 -> M@1,4 -> E@2,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@1,1 -> M@1,2 -> M@2,3 -> M@1,4 -> E@2,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Whirlwind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@4,1 -> M@4,2 -> ?@4,3 -> M@5,4 -> E@4,5 -> M@4,6: reward=7.50, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: ?@4,1 -> M@4,2 -> ?@4,3 -> M@5,4 -> E@4,5 -> M@4,6: reward=7.50, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@4,2 -> ?@4,3 -> M@5,4 -> E@4,5 -> M@4,6 -> R@5,7: reward=7.60, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: M@4,2 -> ?@4,3 -> M@5,4 -> E@4,5 -> M@4,6 -> R@5,7: reward=7.60, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,3 -> M@5,4 -> E@4,5 -> M@4,6 -> R@5,7 -> T@4,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@4,3 -> M@5,4 -> E@4,5 -> M@4,6 -> R@5,7 -> T@4,8: reward=8.10, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@5,4 -> E@4,5 -> M@4,6 -> R@5,7 -> T@4,8 -> R@3,9: reward=8.20, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@5,4 -> E@4,5 -> M@4,6 -> R@5,7 -> T@4,8 -> R@3,9: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Ghostly Armor | Ghostly Armor | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. |
| route | decision_trace | 5 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: E@4,5 -> M@4,6 -> R@5,7 -> T@4,8 -> M@4,9 -> $@5,10: reward=11.10, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.10: E@4,5 -> M@4,6 -> R@5,7 -> T@4,8 -> M@4,9 -> $@5,10: reward=11.10, survivability=1.00 |
| event | decision_trace | 6 | complete | choose 0: Forge | choose 0: Forge | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 6 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.94: E@6,6 -> R@5,7 -> T@4,8 -> M@4,9 -> $@5,10 -> M@5,11: reward=10.94, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.94: E@6,6 -> R@5,7 -> T@4,8 -> M@4,9 -> $@5,10 -> M@5,11: reward=10.94, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@6,7 -> T@6,8 -> R@5,9 -> ?@6,10 -> M@5,11 -> $@6,12: reward=8.50, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.50: M@6,7 -> T@6,8 -> R@5,9 -> ?@6,10 -> M@5,11 -> $@6,12: reward=8.50, survivability=1.00 |
| route | decision_trace | 8 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.04: T@6,8 -> R@5,9 -> $@5,10 -> M@5,11 -> M@5,12 -> M@4,13: reward=9.04, survivability=1.00 |
| route | decision_trace | 8 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.04: T@6,8 -> R@5,9 -> $@5,10 -> M@5,11 -> M@5,12 -> M@4,13: reward=9.04, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.64: R@5,9 -> $@5,10 -> M@5,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=8.64, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.64: R@5,9 -> $@5,10 -> M@5,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=8.64, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.84: ?@6,10 -> M@5,11 -> $@6,12 -> M@6,13 -> R@5,14: reward=7.84, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.84: ?@6,10 -> M@5,11 -> $@6,12 -> M@6,13 -> R@5,14: reward=7.84, survivability=1.00 |
| shop | decision_trace | 11 | complete | purge | Membership Card | high | Bottled shop priority buys affordable Membership Card. |
| shop | decision_trace | 11 | complete | Battle Trance | Battle Trance | high | Bottled shop card list ranks Battle Trance as buyable. |
| shop | decision_trace | 11 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@5,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@5,11 -> M@5,12 -> M@4,13 -> R@4,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Sword Boomerang | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@5,12 -> M@4,13 -> R@4,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@5,12 -> M@4,13 -> R@4,14: reward=2.00, survivability=1.00 |
| shop | decision_trace | 13 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@6,13 -> R@5,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: M@6,13 -> R@5,14: reward=1.00, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Shrug It Off | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@5,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@5,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@5,0 -> M@6,1 -> M@6,2 -> $@5,3 -> M@4,4 -> E@3,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@5,0 -> M@6,1 -> M@6,2 -> $@5,3 -> M@4,4 -> E@3,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Headbutt | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: ?@1,1 -> $@2,2 -> ?@1,3 -> ?@1,4 -> E@0,5 -> R@0,6: reward=8.92, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: ?@1,1 -> $@2,2 -> ?@1,3 -> ?@1,4 -> E@0,5 -> R@0,6: reward=8.92, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Gather Gold | choose 0: Gather Gold | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.82: $@2,2 -> ?@1,3 -> ?@1,4 -> E@0,5 -> R@0,6 -> E@0,7: reward=10.82, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.82: $@2,2 -> ?@1,3 -> ?@1,4 -> E@0,5 -> R@0,6 -> E@0,7: reward=10.82, survivability=1.00 |
| shop | decision_trace | 3 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,3 -> ?@1,4 -> E@0,5 -> R@0,6 -> E@0,7 -> T@0,8: reward=8.50, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: ?@1,3 -> ?@1,4 -> E@0,5 -> R@0,6 -> E@0,7 -> T@0,8: reward=8.50, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@2,4 -> R@1,5 -> ?@2,6 -> R@1,7 -> T@1,8 -> M@2,9: reward=6.70, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: M@2,4 -> R@1,5 -> ?@2,6 -> R@1,7 -> T@1,8 -> M@2,9: reward=6.70, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@1,5 -> ?@2,6 -> R@1,7 -> T@1,8 -> M@2,9 -> ?@1,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@1,5 -> ?@2,6 -> R@1,7 -> T@1,8 -> M@2,9 -> ?@1,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@2,6 -> R@1,7 -> T@1,8 -> M@2,9 -> ?@1,10 -> M@1,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@2,6 -> R@1,7 -> T@1,8 -> M@2,9 -> ?@1,10 -> M@1,11: reward=6.60, survivability=1.00 |
| event | decision_trace | 7 | complete | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@1,7 -> T@1,8 -> M@2,9 -> ?@1,10 -> M@1,11 -> M@0,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@1,7 -> T@1,8 -> M@2,9 -> ?@1,10 -> M@1,11 -> M@0,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: T@1,8 -> M@2,9 -> ?@1,10 -> M@1,11 -> M@0,12 -> M@0,13: reward=6.50, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: T@1,8 -> M@2,9 -> ?@1,10 -> M@1,11 -> M@0,12 -> M@0,13: reward=6.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@2,9 -> ?@1,10 -> M@1,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=6.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@2,9 -> ?@1,10 -> M@1,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Iron Wave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@1,10 -> M@1,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@1,10 -> M@1,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=5.10, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 0: Stomp | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | choose 0: Fight | choose 0: Fight | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 11 | complete | Disarm | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: M@1,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=3.00, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: M@1,11 -> M@0,12 -> M@0,13 -> R@0,14: reward=3.00, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@0,12 -> M@0,13 -> R@0,14: reward=2.00, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.00: M@0,12 -> M@0,13 -> R@0,14: reward=2.00, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | True Grit | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@0,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@0,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Corruption | Reaper | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. |
| route | decision_trace | 17 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@2,0 -> M@2,1 -> ?@1,2 -> $@2,3 -> ?@3,4 -> R@2,5: reward=10.10, survivability=1.00 |
| route | decision_trace | 17 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@2,0 -> M@2,1 -> ?@1,2 -> $@2,3 -> ?@3,4 -> R@2,5: reward=10.10, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.00: M@0,1 -> ?@1,2 -> M@1,3 -> ?@1,4 -> R@1,5 -> M@2,6: reward=6.00, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.00: M@0,1 -> ?@1,2 -> M@1,3 -> ?@1,4 -> R@1,5 -> M@2,6: reward=6.00, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Shockwave | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.26: ?@1,2 -> $@2,3 -> ?@3,4 -> R@2,5 -> M@3,6 -> R@3,7: reward=8.00, survivability=0.95 |
| route | decision_trace | 19 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.26: ?@1,2 -> $@2,3 -> ?@3,4 -> R@2,5 -> M@3,6 -> R@3,7: reward=8.00, survivability=0.95 |
| event | decision_trace | 20 | complete | choose 0: Pay | choose 0: Pay | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.50: $@2,3 -> ?@3,4 -> R@2,5 -> M@3,6 -> R@3,7 -> T@2,8: reward=4.00, survivability=0.97 |
| route | decision_trace | 20 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 3.50: $@2,3 -> ?@3,4 -> R@2,5 -> M@3,6 -> R@3,7 -> T@2,8: reward=4.00, survivability=0.97 |
| shop | decision_trace | 21 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 21 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.25: ?@3,4 -> R@2,5 -> M@3,6 -> R@3,7 -> T@2,8 -> E@1,9: reward=6.50, survivability=0.98 |
| route | decision_trace | 21 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.25: ?@3,4 -> R@2,5 -> M@3,6 -> R@3,7 -> T@2,8 -> E@1,9: reward=6.50, survivability=0.98 |
| event | decision_trace | 22 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| event | decision_trace | 22 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: R@2,5 -> M@3,6 -> R@3,7 -> T@2,8 -> E@1,9 -> ?@1,10: reward=6.50, survivability=1.00 |
| route | decision_trace | 22 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.50: R@2,5 -> M@3,6 -> R@3,7 -> T@2,8 -> E@1,9 -> ?@1,10: reward=6.50, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.40: M@3,6 -> R@3,7 -> T@2,8 -> E@1,9 -> ?@1,10 -> $@2,11: reward=7.40, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.40: M@3,6 -> R@3,7 -> T@2,8 -> E@1,9 -> ?@1,10 -> $@2,11: reward=7.40, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.08: R@3,7 -> T@2,8 -> E@1,9 -> ?@1,10 -> $@2,11 -> R@1,12: reward=6.40, survivability=0.58 |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.08: R@3,7 -> T@2,8 -> E@1,9 -> ?@1,10 -> $@2,11 -> R@1,12: reward=6.40, survivability=0.58 |
| route | decision_trace | 25 | complete | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.00: T@4,8 -> ?@4,9 -> ?@4,10 -> M@5,11 -> R@4,12 -> ?@4,13: reward=7.00, survivability=1.00 |
| route | decision_trace | 25 | complete | choice 2 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.00: T@4,8 -> ?@4,9 -> ?@4,10 -> M@5,11 -> R@4,12 -> ?@4,13: reward=7.00, survivability=1.00 |
| route | decision_trace | 26 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,9 -> ?@4,10 -> M@5,11 -> R@4,12 -> ?@4,13 -> R@5,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 26 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@4,9 -> ?@4,10 -> M@5,11 -> R@4,12 -> ?@4,13 -> R@5,14: reward=6.60, survivability=1.00 |
| event | decision_trace | 27 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 27 | complete | choose 0: Fight | choose 0: Fight | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 27 | complete | choose 0: COWARDICE | choose 0: COWARDICE | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability -2.58: ?@4,10 -> M@5,11 -> R@4,12 -> ?@4,13 -> R@5,14: reward=4.00, survivability=0.56 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability -2.58: ?@4,10 -> M@5,11 -> R@4,12 -> ?@4,13 -> R@5,14: reward=4.00, survivability=0.56 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Upgrade a Card | choose 0: Upgrade a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@1,1 -> M@0,2 -> M@0,3 -> ?@1,4 -> E@0,5: reward=8.78, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.78: M@0,0 -> $@1,1 -> M@0,2 -> M@0,3 -> ?@1,4 -> E@0,5: reward=8.78, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Clothesline | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@4,1 -> ?@4,2 -> M@4,3 -> M@4,4 -> E@3,5 -> R@2,6: reward=7.60, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.60: ?@4,1 -> ?@4,2 -> M@4,3 -> M@4,4 -> E@3,5 -> R@2,6: reward=7.60, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@4,2 -> M@4,3 -> M@4,4 -> R@5,5 -> E@6,6 -> R@5,7: reward=7.70, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@4,2 -> M@4,3 -> M@4,4 -> R@5,5 -> E@6,6 -> R@5,7: reward=7.70, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,3 -> M@4,4 -> R@5,5 -> E@6,6 -> R@5,7 -> T@4,8: reward=8.20, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@4,3 -> M@4,4 -> R@5,5 -> E@6,6 -> R@5,7 -> T@4,8: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: M@4,4 -> R@5,5 -> E@6,6 -> R@5,7 -> T@4,8 -> R@3,9: reward=8.30, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.30: M@4,4 -> R@5,5 -> E@6,6 -> R@5,7 -> T@4,8 -> R@3,9: reward=8.30, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Uppercut | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.10: R@5,5 -> E@6,6 -> ?@6,7 -> T@5,8 -> M@4,9 -> $@4,10: reward=11.10, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 11.10: R@5,5 -> E@6,6 -> ?@6,7 -> T@5,8 -> M@4,9 -> $@4,10: reward=11.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: E@6,6 -> R@5,7 -> T@5,8 -> M@4,9 -> $@4,10 -> M@4,11: reward=10.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: E@6,6 -> R@5,7 -> T@5,8 -> M@4,9 -> $@4,10 -> M@4,11: reward=10.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Clothesline | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.50: ?@6,7 -> T@5,8 -> M@4,9 -> $@4,10 -> M@4,11 -> ?@5,12: reward=9.50, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.50: ?@6,7 -> T@5,8 -> M@4,9 -> $@4,10 -> M@4,11 -> ?@5,12: reward=9.50, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.50: T@5,8 -> M@4,9 -> $@4,10 -> M@4,11 -> ?@5,12 -> M@5,13: reward=9.50, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.50: T@5,8 -> M@4,9 -> $@4,10 -> M@4,11 -> ?@5,12 -> M@5,13: reward=9.50, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@3,9 -> M@3,10 -> R@3,11 -> M@4,12 -> ?@3,13 -> R@3,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@3,9 -> M@3,10 -> R@3,11 -> M@4,12 -> ?@3,13 -> R@3,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@3,10 -> R@3,11 -> M@4,12 -> ?@3,13 -> R@3,14: reward=5.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.20: M@3,10 -> R@3,11 -> M@4,12 -> ?@3,13 -> R@3,14: reward=5.20, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@3,11 -> M@4,12 -> ?@3,13 -> R@3,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@3,11 -> M@4,12 -> ?@3,13 -> R@3,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@4,12 -> ?@3,13 -> R@3,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@4,12 -> ?@3,13 -> R@3,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@3,13 -> R@3,14: reward=1.00, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.00: ?@3,13 -> R@3,14: reward=1.00, survivability=1.00 |
| event | decision_trace | 14 | complete | choose 0: Pray | choose 1: Destroy | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 14 | complete | choose 0: Continue | choose 1: 1 | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 14 | complete | choose 0: Leave | choose 1: 1 | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@3,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@2,0 -> M@3,1 -> $@4,2 -> M@5,3 -> ?@5,4 -> E@4,5: reward=9.08, survivability=1.00 |
| route | decision_trace | 0 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@2,0 -> M@3,1 -> $@4,2 -> M@5,3 -> ?@5,4 -> E@4,5: reward=9.08, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Anger | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: M@3,1 -> $@4,2 -> M@5,3 -> ?@5,4 -> E@4,5 -> ?@3,6: reward=8.98, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.98: M@3,1 -> $@4,2 -> M@5,3 -> ?@5,4 -> E@4,5 -> ?@3,6: reward=8.98, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Heavy Blade | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 2 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.58: $@4,2 -> M@5,3 -> ?@5,4 -> E@4,5 -> ?@3,6 -> E@2,7: reward=10.58, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.58: $@4,2 -> M@5,3 -> ?@5,4 -> E@4,5 -> ?@3,6 -> E@2,7: reward=10.58, survivability=1.00 |
| shop | decision_trace | 3 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 3 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@5,3 -> ?@5,4 -> E@4,5 -> ?@3,6 -> E@2,7 -> T@1,8: reward=9.50, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: M@5,3 -> ?@5,4 -> E@4,5 -> ?@3,6 -> E@2,7 -> T@1,8: reward=9.50, survivability=1.00 |
| card_reward | decision_trace | 4 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: ?@5,4 -> E@4,5 -> ?@3,6 -> E@2,7 -> T@2,8 -> M@3,9: reward=9.50, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: ?@5,4 -> E@4,5 -> ?@3,6 -> E@2,7 -> T@2,8 -> M@3,9: reward=9.50, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Demon Form | Flame Barrier | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Flame Barrier. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: E@4,5 -> ?@3,6 -> E@2,7 -> T@1,8 -> R@2,9 -> E@2,10: reward=10.00, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.00: E@4,5 -> ?@3,6 -> E@2,7 -> T@1,8 -> R@2,9 -> E@2,10: reward=10.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: E@4,6 -> ?@4,7 -> T@4,8 -> M@3,9 -> E@2,10 -> ?@1,11: reward=9.50, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.50: E@4,6 -> ?@4,7 -> T@4,8 -> M@3,9 -> E@2,10 -> ?@1,11: reward=9.50, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,7 -> T@5,8 -> R@4,9 -> ?@4,10 -> ?@4,11 -> ?@5,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,7 -> T@5,8 -> R@4,9 -> ?@4,10 -> ?@4,11 -> ?@5,12: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@5,8 -> R@4,9 -> ?@4,10 -> ?@4,11 -> ?@5,12 -> M@6,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: T@5,8 -> R@4,9 -> ?@4,10 -> ?@4,11 -> ?@5,12 -> M@6,13: reward=6.60, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: R@4,9 -> ?@4,10 -> ?@4,11 -> ?@5,12 -> M@6,13 -> R@5,14: reward=6.20, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.20: R@4,9 -> ?@4,10 -> ?@4,11 -> ?@5,12 -> M@6,13 -> R@5,14: reward=6.20, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@4,10 -> ?@4,11 -> ?@5,12 -> M@6,13 -> R@5,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: ?@4,10 -> ?@4,11 -> ?@5,12 -> M@6,13 -> R@5,14: reward=5.10, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 0: Stomp | choose 0: Stomp | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | choose 0: Fight | choose 0: Fight | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 11 | complete | Blood for Blood | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@4,11 -> ?@5,12 -> M@6,13 -> R@5,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: ?@4,11 -> ?@5,12 -> M@6,13 -> R@5,14: reward=4.10, survivability=1.00 |
| event | decision_trace | 12 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 12 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@5,12 -> M@6,13 -> R@5,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@5,12 -> M@6,13 -> R@5,14: reward=3.10, survivability=1.00 |
| event | decision_trace | 13 | complete | choose 0: Locked | choose 0: Locked | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 13 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@6,13 -> R@5,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Thunderclap | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Immolate | Reaper | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. |
| route | decision_trace | 17 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.68: M@1,0 -> ?@2,1 -> ?@3,2 -> ?@2,3 -> $@1,4 -> E@2,5: reward=10.68, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 10.68: M@1,0 -> ?@2,1 -> ?@3,2 -> ?@2,3 -> $@1,4 -> E@2,5: reward=10.68, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Pommel Strike | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.48: ?@2,1 -> ?@3,2 -> ?@2,3 -> M@3,4 -> E@3,5 -> $@3,6: reward=11.48, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 11.48: ?@2,1 -> ?@3,2 -> ?@2,3 -> M@3,4 -> E@3,5 -> $@3,6: reward=11.48, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.98: ?@3,2 -> ?@2,3 -> M@3,4 -> E@3,5 -> $@3,6 -> M@3,7: reward=10.98, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.98: ?@3,2 -> ?@2,3 -> M@3,4 -> E@3,5 -> $@3,6 -> M@3,7: reward=10.98, survivability=1.00 |
| event | decision_trace | 20 | complete | choose 1: Sleep | choose 0: Read | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.98: ?@2,3 -> M@3,4 -> E@3,5 -> $@3,6 -> M@3,7 -> T@3,8: reward=10.98, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.98: ?@2,3 -> M@3,4 -> E@3,5 -> $@3,6 -> M@3,7 -> T@3,8: reward=10.98, survivability=1.00 |
| event | decision_trace | 21 | complete | choose 0: Pay | choose 0: Pay | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 21 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 21 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.40: M@3,4 -> E@3,5 -> $@3,6 -> M@3,7 -> T@3,8 -> ?@4,9: reward=8.40, survivability=1.00 |
| route | decision_trace | 21 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.40: M@3,4 -> E@3,5 -> $@3,6 -> M@3,7 -> T@3,8 -> ?@4,9: reward=8.40, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | Whirlwind+ | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 22 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@4,5 -> M@4,6 -> $@4,7 -> T@3,8 -> R@3,9 -> ?@2,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 22 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@4,5 -> M@4,6 -> $@4,7 -> T@3,8 -> R@3,9 -> ?@2,10: reward=6.70, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@4,6 -> $@4,7 -> T@3,8 -> R@3,9 -> ?@2,10 -> M@1,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 23 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@4,6 -> $@4,7 -> T@3,8 -> R@3,9 -> ?@2,10 -> M@1,11: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 24 | complete | Disarm | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: $@4,7 -> T@3,8 -> M@2,9 -> ?@2,10 -> M@1,11 -> ?@1,12: reward=7.10, survivability=1.00 |
| route | decision_trace | 24 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: $@4,7 -> T@3,8 -> M@2,9 -> ?@2,10 -> M@1,11 -> ?@1,12: reward=7.10, survivability=1.00 |
| shop | decision_trace | 25 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> M@2,9 -> ?@2,10 -> M@1,11 -> ?@1,12 -> ?@2,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: T@3,8 -> M@2,9 -> ?@2,10 -> M@1,11 -> ?@1,12 -> ?@2,13: reward=8.00, survivability=1.00 |
| route | decision_trace | 26 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@3,9 -> ?@2,10 -> M@1,11 -> ?@1,12 -> ?@2,13 -> R@1,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 26 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.60: R@3,9 -> ?@2,10 -> M@1,11 -> ?@1,12 -> ?@2,13 -> R@1,14: reward=6.60, survivability=1.00 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: ?@2,10 -> M@1,11 -> ?@1,12 -> ?@2,13 -> R@1,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.50: ?@2,10 -> M@1,11 -> ?@1,12 -> ?@2,13 -> R@1,14: reward=5.50, survivability=1.00 |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.00: M@1,11 -> ?@1,12 -> ?@2,13 -> R@1,14: reward=4.00, survivability=1.00 |
| route | decision_trace | 28 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.00: M@1,11 -> ?@1,12 -> ?@2,13 -> R@1,14: reward=4.00, survivability=1.00 |
| card_reward | decision_trace | 29 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 29 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: ?@1,12 -> ?@2,13 -> R@1,14: reward=3.00, survivability=1.00 |
| route | decision_trace | 29 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.00: ?@1,12 -> ?@2,13 -> R@1,14: reward=3.00, survivability=1.00 |
| card_reward | decision_trace | 30 | complete | skip | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 30 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 1.50: ?@2,13 -> R@1,14: reward=1.50, survivability=1.00 |
| route | decision_trace | 30 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 1.50: ?@2,13 -> R@1,14: reward=1.50, survivability=1.00 |
| shop | decision_trace | 31 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 31 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 0.00: R@1,14: reward=0.00, survivability=1.00 |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 32 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |

## Most Worth Fixing

1. **event floor 14**: current `choose 0: Continue` vs reference `choose 1: 1` (high). Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. Repeated 2x in non-fixture evidence.
2. **card_reward floor 5**: current `Anger` vs reference `Perfected Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Repeated 3x in non-fixture evidence.
3. **card_reward floor 13**: current `True Grit` vs reference `Pommel Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Repeated 3x in non-fixture evidence.
4. **card_reward floor 1**: current `Headbutt` vs reference `Dropkick` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Repeated 2x in non-fixture evidence.
5. **card_reward floor 16**: current `Corruption` vs reference `Reaper` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. Repeated 2x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
