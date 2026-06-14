# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 356
- Differences: 218
- Categories: card_reward=79, event=62, route=187, shop=28
- Evidence quality: complete=276, partial=80

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| card_reward | run:1781455044.run | 0 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455044.run | 1 | partial | Armaments | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455044.run | 4 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455044.run | 12 | partial | Armaments | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455044.run | 13 | partial | Carnage | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781455044.run | 2 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455044.run | 3 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455044.run | 8 | partial | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781455044.run | 14 | partial | Block Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781455044.run | 5 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781455044.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781455140.run | 1 | partial | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455140.run | 2 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455140.run | 5 | partial | Clothesline | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455140.run | 7 | partial | Twin Strike | Ghostly Armor | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455140.run | 12 | partial | Iron Wave | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455140.run | 13 | partial | Twin Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455140.run | 14 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| event | run:1781455140.run | 3 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455140.run | 4 | partial | Got Potions | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781455140.run | 11 | partial | Fire Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781455140.run | 11 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781455140.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781455214.run | 1 | partial | Thunderclap | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455214.run | 3 | partial | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455214.run | 5 | partial | Burning Pact | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455214.run | 6 | partial | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455214.run | 13 | partial | Uppercut | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455214.run | 14 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781455214.run | 2 | partial | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455214.run | 8 | partial | Searched '0' times | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455214.run | 11 | partial | Transformed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781455214.run | 4 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781455214.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781455326.run | 0 | partial | Enlightenment | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 1 | partial | Carnage | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 3 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 10 | partial | Burning Pact | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 12 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 13 | partial | Headbutt | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 16 | partial | Impervious | Impervious | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 18 | partial | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455326.run | 19 | partial | Hemokinesis | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781455326.run | 2 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455326.run | 4 | partial | Banana | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455326.run | 7 | partial | Gave Potion | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455326.run | 14 | partial | Gather Gold | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455326.run | 20 | partial | Touch | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781455326.run | 5 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781455326.run | 11 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781455326.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1781455438.run | 1 | partial | Inflame | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 5 | partial | Whirlwind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 7 | partial | Seeing Red | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 11 | partial | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 12 | partial | Heavy Blade | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 13 | partial | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 14 | partial | Spot Weakness | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 16 | partial | Demon Form | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 18 | partial | SKIP | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 22 | partial | SKIP | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 25 | partial | SKIP | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781455438.run | 27 | partial | SKIP | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1781455438.run | 2 | partial | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455438.run | 19 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455438.run | 20 | partial | Heal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781455438.run | 24 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781455438.run | 8 | partial | Strength Potion | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781455438.run | 4 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781455438.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | decision_trace | 4 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.84: $@1,4 -> M@1,5 -> E@1,6 -> R@1,7 -> T@0,8 -> ?@0,9: reward=9.84, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.84: $@1,4 -> M@1,5 -> E@1,6 -> R@1,7 -> T@0,8 -> ?@0,9: reward=9.84, survivability=1.00 |
| shop | decision_trace | 5 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 5 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@1,5 -> E@1,6 -> R@1,7 -> T@0,8 -> M@1,9 -> R@1,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@1,5 -> E@1,6 -> R@1,7 -> T@0,8 -> M@1,9 -> R@1,10: reward=8.20, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,6 -> ?@3,7 -> T@2,8 -> ?@2,9 -> R@1,10 -> M@2,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: ?@3,6 -> ?@3,7 -> T@2,8 -> ?@2,9 -> R@1,10 -> M@2,11: reward=6.60, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@3,7 -> T@2,8 -> ?@2,9 -> R@1,10 -> M@2,11 -> E@3,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@3,7 -> T@2,8 -> ?@2,9 -> R@1,10 -> M@2,11 -> E@3,12: reward=8.10, survivability=1.00 |
| event | decision_trace | 8 | complete | choose 0: Pray | choose 0: Pray | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 8 | complete | choose 0: Continue | choose 0: Continue | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| event | decision_trace | 8 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@2,8 -> ?@2,9 -> R@1,10 -> M@2,11 -> E@3,12 -> ?@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: T@2,8 -> ?@2,9 -> R@1,10 -> M@2,11 -> E@3,12 -> ?@2,13: reward=8.10, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@2,9 -> R@1,10 -> M@2,11 -> E@3,12 -> ?@2,13 -> R@2,14: reward=7.70, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.70: ?@2,9 -> R@1,10 -> M@2,11 -> E@3,12 -> ?@2,13 -> R@2,14: reward=7.70, survivability=1.00 |
| shop | decision_trace | 10 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@1,10 -> M@2,11 -> E@3,12 -> ?@2,13 -> R@2,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: R@1,10 -> M@2,11 -> E@3,12 -> ?@2,13 -> R@2,14: reward=6.70, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@2,11 -> E@3,12 -> ?@2,13 -> R@2,14: reward=5.60, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.60: M@2,11 -> E@3,12 -> ?@2,13 -> R@2,14: reward=5.60, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Armaments | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 12 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.60: E@3,12 -> ?@2,13 -> R@2,14: reward=4.60, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.60: E@3,12 -> ?@2,13 -> R@2,14: reward=4.60, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Carnage | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@2,13 -> R@2,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@2,13 -> R@2,14: reward=2.10, survivability=1.00 |
| shop | decision_trace | 14 | complete | Block Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 14 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Remove a Card from your deck | choose 0: Remove a Card from your deck | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@1,1 -> ?@0,2 -> ?@0,3 -> ?@0,4 -> E@0,5: reward=7.50, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@0,0 -> M@1,1 -> ?@0,2 -> ?@0,3 -> ?@0,4 -> E@0,5: reward=7.50, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | True Grit | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@4,1 -> ?@3,2 -> ?@2,3 -> M@2,4 -> R@1,5 -> M@1,6: reward=6.10, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.10: M@4,1 -> ?@3,2 -> ?@2,3 -> M@2,4 -> R@1,5 -> M@1,6: reward=6.10, survivability=1.00 |
| card_reward | decision_trace | 2 | complete | Shrug It Off | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 2 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@5,2 -> ?@6,3 -> M@6,4 -> E@6,5 -> M@6,6 -> M@5,7: reward=7.50, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 7.50: M@5,2 -> ?@6,3 -> M@6,4 -> E@6,5 -> M@6,6 -> M@5,7: reward=7.50, survivability=1.00 |
| event | decision_trace | 3 | complete | choose 0: Forget | choose 0: Forget | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 3 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@2,3 -> M@2,4 -> R@1,5 -> M@1,6 -> R@1,7 -> T@1,8: reward=6.70, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.70: ?@2,3 -> M@2,4 -> R@1,5 -> M@1,6 -> R@1,7 -> T@1,8: reward=6.70, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Search | choose 0: Search | medium | Bottled common event handling takes the main Lab reward. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.74: M@2,4 -> R@1,5 -> M@1,6 -> R@1,7 -> T@2,8 -> $@3,9: reward=8.74, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.74: M@2,4 -> R@1,5 -> M@1,6 -> R@1,7 -> T@2,8 -> $@3,9: reward=8.74, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Clothesline | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: R@1,5 -> M@1,6 -> R@1,7 -> T@1,8 -> R@1,9 -> $@1,10: reward=8.92, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: R@1,5 -> M@1,6 -> R@1,7 -> T@1,8 -> R@1,9 -> $@1,10: reward=8.92, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.32: M@1,6 -> R@1,7 -> T@1,8 -> R@1,9 -> $@1,10 -> E@2,11: reward=10.32, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.32: M@1,6 -> R@1,7 -> T@1,8 -> R@1,9 -> $@1,10 -> E@2,11: reward=10.32, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.90: R@1,7 -> T@1,8 -> R@1,9 -> $@1,10 -> M@1,11 -> M@0,12: reward=8.90, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.90: R@1,7 -> T@1,8 -> R@1,9 -> $@1,10 -> M@1,11 -> M@0,12: reward=8.90, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: T@1,8 -> R@1,9 -> $@1,10 -> M@1,11 -> M@0,12 -> ?@1,13: reward=8.80, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.80: T@1,8 -> R@1,9 -> $@1,10 -> M@1,11 -> M@0,12 -> ?@1,13: reward=8.80, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.86: R@1,9 -> $@1,10 -> M@1,11 -> M@0,12 -> ?@1,13 -> R@2,14: reward=8.86, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.86: R@1,9 -> $@1,10 -> M@1,11 -> M@0,12 -> ?@1,13 -> R@2,14: reward=8.86, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.16: $@1,10 -> E@2,11 -> ?@2,12 -> ?@2,13 -> R@2,14: reward=8.16, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.16: $@1,10 -> E@2,11 -> ?@2,12 -> ?@2,13 -> R@2,14: reward=8.16, survivability=1.00 |
| shop | decision_trace | 11 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 11 | complete | Fire Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 11 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 11 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@2,11 -> ?@2,12 -> ?@2,13 -> R@2,14: reward=4.50, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.50: E@2,11 -> ?@2,12 -> ?@2,13 -> R@2,14: reward=4.50, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Iron Wave | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@0,12 -> ?@1,13 -> R@2,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@0,12 -> ?@1,13 -> R@2,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Twin Strike | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@1,13 -> R@2,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@1,13 -> R@2,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Pommel Strike | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@2,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 2 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@0,0 -> M@1,1 -> M@2,2 -> $@3,3 -> M@2,4 -> R@2,5: reward=7.98, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.98: M@0,0 -> M@1,1 -> M@2,2 -> $@3,3 -> M@2,4 -> R@2,5: reward=7.98, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Thunderclap | Twin Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.12: ?@2,1 -> M@2,2 -> $@3,3 -> M@2,4 -> R@2,5 -> E@2,6: reward=9.12, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.12: ?@2,1 -> M@2,2 -> $@3,3 -> M@2,4 -> R@2,5 -> E@2,6: reward=9.12, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Heal | choose 0: Heal | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.42: M@2,2 -> $@3,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7: reward=8.42, survivability=1.00 |
| route | decision_trace | 2 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.42: M@2,2 -> $@3,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7: reward=8.42, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Pommel Strike | Thunderclap | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. |
| route | decision_trace | 3 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.88: $@3,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7 -> T@0,8: reward=8.88, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.88: $@3,3 -> M@2,4 -> R@2,5 -> E@2,6 -> M@1,7 -> T@0,8: reward=8.88, survivability=1.00 |
| shop | decision_trace | 4 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 4 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@2,4 -> R@2,5 -> E@2,6 -> M@1,7 -> T@0,8 -> R@1,9: reward=8.20, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.20: M@2,4 -> R@2,5 -> E@2,6 -> M@1,7 -> T@0,8 -> R@1,9: reward=8.20, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.70: R@2,5 -> E@2,6 -> M@1,7 -> T@0,8 -> R@1,9 -> E@2,10: reward=9.70, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.70: R@2,5 -> E@2,6 -> M@1,7 -> T@0,8 -> R@1,9 -> E@2,10: reward=9.70, survivability=1.00 |
| card_reward | decision_trace | 6 | complete | Shrug It Off | Perfected Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.90: $@3,6 -> ?@2,7 -> T@1,8 -> R@1,9 -> E@2,10 -> M@3,11: reward=7.90, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.90: $@3,6 -> ?@2,7 -> T@1,8 -> R@1,9 -> E@2,10 -> M@3,11: reward=7.90, survivability=1.00 |
| shop | decision_trace | 7 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@2,7 -> T@1,8 -> R@1,9 -> E@2,10 -> M@3,11 -> ?@3,12: reward=8.10, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: ?@2,7 -> T@1,8 -> R@1,9 -> E@2,10 -> M@3,11 -> ?@3,12: reward=8.10, survivability=1.00 |
| event | decision_trace | 8 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| event | decision_trace | 8 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling avoids Dead Adventurer risk. |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: T@1,8 -> R@1,9 -> E@2,10 -> M@3,11 -> ?@3,12 -> E@4,13: reward=9.60, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: T@1,8 -> R@1,9 -> E@2,10 -> M@3,11 -> ?@3,12 -> E@4,13: reward=9.60, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@1,9 -> M@0,10 -> R@0,11 -> ?@0,12 -> M@0,13 -> R@0,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.30: R@1,9 -> M@0,10 -> R@0,11 -> ?@0,12 -> M@0,13 -> R@0,14: reward=6.30, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.00: E@2,10 -> M@3,11 -> ?@3,12 -> E@4,13 -> R@3,14: reward=7.00, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 7.00: E@2,10 -> M@3,11 -> ?@3,12 -> E@4,13 -> R@3,14: reward=7.00, survivability=1.00 |
| event | decision_trace | 11 | complete | choose 0: Pray | choose 0: Pray | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 11 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@0,11 -> ?@0,12 -> M@0,13 -> R@0,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.20: R@0,11 -> ?@0,12 -> M@0,13 -> R@0,14: reward=4.20, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@0,12 -> M@0,13 -> R@0,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@0,12 -> M@0,13 -> R@0,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Uppercut | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@0,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@0,13 -> R@0,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@0,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Secret Technique | Apotheosis | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Apotheosis. |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Choose a colorless Card to obtain | choose 0: Choose a colorless Card to obtain | medium | Bottled common event fallback chooses the first option. |
| card_reward | decision_trace | 0 | complete | Enlightenment | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@3,0 -> ?@4,1 -> ?@3,2 -> M@2,3 -> $@2,4 -> E@2,5: reward=9.08, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.08: M@3,0 -> ?@4,1 -> ?@3,2 -> M@2,3 -> $@2,4 -> E@2,5: reward=9.08, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Carnage | Pommel Strike | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.28: ?@4,1 -> ?@3,2 -> M@2,3 -> $@2,4 -> E@2,5 -> R@1,6: reward=9.28, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.28: ?@4,1 -> ?@3,2 -> M@2,3 -> $@2,4 -> E@2,5 -> R@1,6: reward=9.28, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 1: Leave | choose 0: Take | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.28: ?@3,2 -> M@2,3 -> $@2,4 -> E@2,5 -> R@1,6 -> M@2,7: reward=9.28, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.28: ?@3,2 -> M@2,3 -> $@2,4 -> E@2,5 -> R@1,6 -> M@2,7: reward=9.28, survivability=1.00 |
| card_reward | decision_trace | 3 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.42: ?@4,3 -> $@4,4 -> R@5,5 -> M@4,6 -> R@3,7 -> T@3,8: reward=8.42, survivability=1.00 |
| route | decision_trace | 3 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.42: ?@4,3 -> $@4,4 -> R@5,5 -> M@4,6 -> R@3,7 -> T@3,8: reward=8.42, survivability=1.00 |
| event | decision_trace | 4 | complete | choose 0: Banana | choose 0: Banana | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 4 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 4 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.92: $@4,4 -> R@5,5 -> ?@5,6 -> R@6,7 -> T@5,8 -> E@6,9: reward=9.92, survivability=1.00 |
| route | decision_trace | 4 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.92: $@4,4 -> R@5,5 -> ?@5,6 -> R@6,7 -> T@5,8 -> E@6,9: reward=9.92, survivability=1.00 |
| shop | decision_trace | 5 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 5 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.52: R@5,5 -> M@4,6 -> R@3,7 -> T@4,8 -> M@4,9 -> $@5,10: reward=7.52, survivability=1.00 |
| route | decision_trace | 5 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.52: R@5,5 -> M@4,6 -> R@3,7 -> T@4,8 -> M@4,9 -> $@5,10: reward=7.52, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.92: ?@5,6 -> R@6,7 -> T@5,8 -> E@6,9 -> $@5,10 -> M@5,11: reward=8.92, survivability=1.00 |
| route | decision_trace | 6 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.92: ?@5,6 -> R@6,7 -> T@5,8 -> E@6,9 -> $@5,10 -> M@5,11: reward=8.92, survivability=1.00 |
| event | decision_trace | 7 | complete | choose 0: Give Potion | choose 0: Give Potion | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 7 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: R@6,7 -> T@5,8 -> E@6,9 -> $@5,10 -> M@5,11 -> ?@6,12: reward=8.92, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.92: R@6,7 -> T@5,8 -> E@6,9 -> $@5,10 -> M@5,11 -> ?@6,12: reward=8.92, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.82: T@5,8 -> E@6,9 -> $@5,10 -> M@5,11 -> ?@6,12 -> ?@6,13: reward=8.82, survivability=1.00 |
| route | decision_trace | 8 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.82: T@5,8 -> E@6,9 -> $@5,10 -> M@5,11 -> ?@6,12 -> ?@6,13: reward=8.82, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.48: E@6,9 -> $@5,10 -> M@5,11 -> ?@6,12 -> ?@6,13 -> R@6,14: reward=9.48, survivability=1.00 |
| route | decision_trace | 9 | complete | choice map_node | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.48: E@6,9 -> $@5,10 -> M@5,11 -> ?@6,12 -> ?@6,13 -> R@6,14: reward=9.48, survivability=1.00 |
| card_reward | decision_trace | 10 | complete | Burning Pact | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.74: $@5,10 -> M@5,11 -> ?@6,12 -> ?@6,13 -> R@6,14: reward=6.74, survivability=1.00 |
| route | decision_trace | 10 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 6.74: $@5,10 -> M@5,11 -> ?@6,12 -> ?@6,13 -> R@6,14: reward=6.74, survivability=1.00 |
| shop | decision_trace | 11 | complete | purge | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| shop | decision_trace | 11 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@5,11 -> ?@6,12 -> ?@6,13 -> R@6,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@5,11 -> ?@6,12 -> ?@6,13 -> R@6,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Armaments | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@6,12 -> ?@6,13 -> R@6,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: ?@6,12 -> ?@6,13 -> R@6,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Headbutt | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@6,13 -> R@6,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: ?@6,13 -> R@6,14: reward=2.10, survivability=1.00 |
| event | decision_trace | 14 | complete | choose 0: Gather Gold | choose 0: Gather Gold | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| event | decision_trace | 14 | complete | choose 0: Leave | choose 0: Leave | high | Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@6,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@6,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Impervious | Impervious | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. |
| route | decision_trace | 17 | complete | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 11.50: M@5,0 -> ?@4,1 -> M@4,2 -> $@5,3 -> ?@6,4 -> E@6,5: reward=11.50, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 3 | high | Bottled common map scoring prefers reward-to-survivability 11.50: M@5,0 -> ?@4,1 -> M@4,2 -> $@5,3 -> ?@6,4 -> E@6,5: reward=11.50, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Headbutt | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@1,1 -> ?@2,2 -> M@3,3 -> ?@3,4 -> R@2,5 -> $@3,6: reward=10.10, survivability=1.00 |
| route | decision_trace | 18 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.10: M@1,1 -> ?@2,2 -> M@3,3 -> ?@3,4 -> R@2,5 -> $@3,6: reward=10.10, survivability=1.00 |
| card_reward | decision_trace | 19 | complete | Hemokinesis | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@2,2 -> M@3,3 -> ?@3,4 -> R@2,5 -> $@3,6 -> R@3,7: reward=9.10, survivability=1.00 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@2,2 -> M@3,3 -> ?@3,4 -> R@2,5 -> $@3,6 -> R@3,7: reward=9.10, survivability=1.00 |
| event | decision_trace | 20 | complete | choose 0: Continue | choose 0: Continue | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Touch | choose 0: Touch | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,3 -> ?@3,4 -> R@2,5 -> $@3,6 -> R@3,7 -> T@3,8: reward=8.00, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@3,3 -> ?@3,4 -> R@2,5 -> $@3,6 -> R@3,7 -> T@3,8: reward=8.00, survivability=1.00 |
| event | decision_trace | 0 | complete | choose 0: Talk | choose 0: Talk | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Transform a Card | choose 0: Transform a Card | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 0 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 0 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@4,0 -> M@4,1 -> M@5,2 -> $@4,3 -> ?@4,4 -> E@4,5: reward=9.38, survivability=1.00 |
| route | decision_trace | 0 | complete | choice 2 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.38: M@4,0 -> M@4,1 -> M@5,2 -> $@4,3 -> ?@4,4 -> E@4,5: reward=9.38, survivability=1.00 |
| card_reward | decision_trace | 1 | complete | Inflame | Dropkick | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.06: ?@6,1 -> M@5,2 -> $@4,3 -> ?@4,4 -> E@4,5 -> M@4,6: reward=9.06, survivability=1.00 |
| route | decision_trace | 1 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.06: ?@6,1 -> M@5,2 -> $@4,3 -> ?@4,4 -> E@4,5 -> M@4,6: reward=9.06, survivability=1.00 |
| event | decision_trace | 2 | complete | choose 0: Reach Inside | choose 0: Reach Inside | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Deeper | choose 0: Deeper | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 2 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.06: M@5,2 -> $@4,3 -> ?@4,4 -> E@4,5 -> M@4,6 -> ?@5,7: reward=9.06, survivability=1.00 |
| route | decision_trace | 2 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.06: M@5,2 -> $@4,3 -> ?@4,4 -> E@4,5 -> M@4,6 -> ?@5,7: reward=9.06, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,3 -> ?@4,4 -> E@4,5 -> M@4,6 -> ?@5,7 -> T@4,8: reward=8.00, survivability=1.00 |
| route | decision_trace | 3 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: M@5,3 -> ?@4,4 -> E@4,5 -> M@4,6 -> ?@5,7 -> T@4,8: reward=8.00, survivability=1.00 |
| shop | decision_trace | 4 | complete | purge | Perfected Strike | high | Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. |
| shop | decision_trace | 4 | complete | leave | Perfected Strike | high | Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,4 -> M@5,5 -> M@4,6 -> ?@5,7 -> T@5,8 -> R@6,9: reward=6.60, survivability=1.00 |
| route | decision_trace | 4 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 6.60: M@6,4 -> M@5,5 -> M@4,6 -> ?@5,7 -> T@5,8 -> R@6,9: reward=6.60, survivability=1.00 |
| card_reward | decision_trace | 5 | complete | Whirlwind | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 5 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@6,5 -> ?@5,6 -> ?@5,7 -> T@4,8 -> M@4,9 -> E@3,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 5 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.10: R@6,5 -> ?@5,6 -> ?@5,7 -> T@4,8 -> M@4,9 -> E@3,10: reward=8.10, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,6 -> ?@5,7 -> T@4,8 -> M@4,9 -> E@3,10 -> ?@2,11: reward=8.00, survivability=1.00 |
| route | decision_trace | 6 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.00: ?@5,6 -> ?@5,7 -> T@4,8 -> M@4,9 -> E@3,10 -> ?@2,11: reward=8.00, survivability=1.00 |
| card_reward | decision_trace | 7 | complete | Seeing Red | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.36: ?@5,7 -> T@4,8 -> M@4,9 -> E@3,10 -> R@4,11 -> $@3,12: reward=8.36, survivability=1.00 |
| route | decision_trace | 7 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.36: ?@5,7 -> T@4,8 -> M@4,9 -> E@3,10 -> R@4,11 -> $@3,12: reward=8.36, survivability=1.00 |
| shop | decision_trace | 8 | complete | Strength Potion | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| shop | decision_trace | 8 | complete | leave | leave | high | Bottled shop handler leaves when no priority purchase is affordable. |
| route | decision_trace | 8 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: T@4,8 -> M@4,9 -> E@3,10 -> ?@2,11 -> M@2,12 -> E@1,13: reward=9.50, survivability=0.93 |
| route | decision_trace | 8 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.50: T@4,8 -> M@4,9 -> E@3,10 -> ?@2,11 -> M@2,12 -> E@1,13: reward=9.50, survivability=0.93 |
| route | decision_trace | 9 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@4,9 -> E@3,10 -> ?@2,11 -> M@2,12 -> E@1,13 -> R@0,14: reward=8.00, survivability=0.93 |
| route | decision_trace | 9 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.00: M@4,9 -> E@3,10 -> ?@2,11 -> M@2,12 -> E@1,13 -> R@0,14: reward=8.00, survivability=0.93 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: M@5,10 -> M@6,11 -> M@6,12 -> M@5,13 -> R@5,14: reward=5.10, survivability=1.00 |
| route | decision_trace | 10 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 5.10: M@5,10 -> M@6,11 -> M@6,12 -> M@5,13 -> R@5,14: reward=5.10, survivability=1.00 |
| card_reward | decision_trace | 11 | complete | Anger | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@6,11 -> M@6,12 -> M@5,13 -> R@5,14: reward=4.10, survivability=1.00 |
| route | decision_trace | 11 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 4.10: M@6,11 -> M@6,12 -> M@5,13 -> R@5,14: reward=4.10, survivability=1.00 |
| card_reward | decision_trace | 12 | complete | Heavy Blade | Battle Trance | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@6,12 -> M@5,13 -> R@5,14: reward=3.10, survivability=1.00 |
| route | decision_trace | 12 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 3.10: M@6,12 -> M@5,13 -> R@5,14: reward=3.10, survivability=1.00 |
| card_reward | decision_trace | 13 | complete | Cleave | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@5,14: reward=2.10, survivability=1.00 |
| route | decision_trace | 13 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 2.10: M@5,13 -> R@5,14: reward=2.10, survivability=1.00 |
| card_reward | decision_trace | 14 | complete | Spot Weakness | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 14 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 1.10: R@5,14: reward=1.10, survivability=1.00 |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| route | decision_trace | 15 | partial | choice map_node | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate paths at decision time |
| card_reward | decision_trace | 16 | complete | Demon Form | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| card_reward | decision_trace | 17 | complete | skip | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| route | decision_trace | 17 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@4,0 -> ?@4,1 -> ?@4,2 -> ?@3,3 -> M@3,4 -> E@3,5: reward=9.00, survivability=1.00 |
| route | decision_trace | 17 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 9.00: M@4,0 -> ?@4,1 -> ?@4,2 -> ?@3,3 -> M@3,4 -> E@3,5: reward=9.00, survivability=1.00 |
| card_reward | decision_trace | 18 | complete | Disarm | Shrug It Off | high | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. |
| card_reward | decision_trace | 18 | complete | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 18 | complete | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 10.60: $@5,1 -> M@5,2 -> ?@4,3 -> ?@4,4 -> R@4,5 -> ?@5,6: reward=10.60, survivability=1.00 |
| route | decision_trace | 18 | complete | choice 1 | choice 2 | high | Bottled common map scoring prefers reward-to-survivability 10.60: $@5,1 -> M@5,2 -> ?@4,3 -> ?@4,4 -> R@4,5 -> ?@5,6: reward=10.60, survivability=1.00 |
| event | decision_trace | 19 | complete | choose 1: Leave | choose 0: Read | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 19 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.34: ?@4,2 -> ?@3,3 -> M@3,4 -> R@4,5 -> ?@5,6 -> E@5,7: reward=9.10, survivability=0.95 |
| route | decision_trace | 19 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.34: ?@4,2 -> ?@3,3 -> M@3,4 -> R@4,5 -> ?@5,6 -> E@5,7: reward=9.10, survivability=0.95 |
| event | decision_trace | 20 | complete | choose 1: Sleep | choose 0: Read | medium | Bottled common event fallback chooses the first option. |
| event | decision_trace | 20 | complete | choose 0: Leave | choose 0: Leave | medium | Bottled common event fallback chooses the first option. |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@3,3 -> M@3,4 -> R@4,5 -> ?@5,6 -> E@5,7 -> T@5,8: reward=9.10, survivability=1.00 |
| route | decision_trace | 20 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.10: ?@3,3 -> M@3,4 -> R@4,5 -> ?@5,6 -> E@5,7 -> T@5,8: reward=9.10, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@3,4 -> R@4,5 -> M@4,6 -> E@4,7 -> T@3,8 -> M@4,9: reward=8.10, survivability=1.00 |
| route | decision_trace | 21 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 8.10: M@3,4 -> R@4,5 -> M@4,6 -> E@4,7 -> T@3,8 -> M@4,9: reward=8.10, survivability=1.00 |
| card_reward | decision_trace | 22 | complete | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 22 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.60: R@4,5 -> M@4,6 -> E@4,7 -> T@3,8 -> M@4,9 -> ?@4,10: reward=8.60, survivability=1.00 |
| route | decision_trace | 22 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.60: R@4,5 -> M@4,6 -> E@4,7 -> T@3,8 -> M@4,9 -> ?@4,10: reward=8.60, survivability=1.00 |
| route | decision_trace | 23 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.44: ?@5,6 -> E@5,7 -> T@5,8 -> M@4,9 -> M@5,10 -> M@6,11: reward=8.50, survivability=1.00 |
| route | decision_trace | 23 | complete | choice 1 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 8.44: ?@5,6 -> E@5,7 -> T@5,8 -> M@4,9 -> M@5,10 -> M@6,11: reward=8.50, survivability=1.00 |
| event | decision_trace | 24 | complete | choose 1: Leave | choose 1: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| event | decision_trace | 24 | complete | choose 0: Leave | choose 0: Leave | high | Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse. |
| route | decision_trace | 24 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: E@5,7 -> T@5,8 -> M@4,9 -> ?@4,10 -> R@4,11 -> $@3,12: reward=10.50, survivability=1.00 |
| route | decision_trace | 24 | complete | choice 1 | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 10.50: E@5,7 -> T@5,8 -> M@4,9 -> ?@4,10 -> R@4,11 -> $@3,12: reward=10.50, survivability=1.00 |
| card_reward | decision_trace | 25 | complete | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: T@6,8 -> M@5,9 -> M@5,10 -> R@4,11 -> $@3,12 -> M@2,13: reward=9.60, survivability=1.00 |
| route | decision_trace | 25 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.60: T@6,8 -> M@5,9 -> M@5,10 -> R@4,11 -> $@3,12 -> M@2,13: reward=9.60, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.20: M@5,9 -> M@5,10 -> R@4,11 -> $@3,12 -> M@2,13 -> R@1,14: reward=9.20, survivability=1.00 |
| route | decision_trace | 26 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 9.20: M@5,9 -> M@5,10 -> R@4,11 -> $@3,12 -> M@2,13 -> R@1,14: reward=9.20, survivability=1.00 |
| card_reward | decision_trace | 27 | complete | skip | skip | medium | Bottled card reward handler skips when no desired card is offered. |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@5,10 -> R@4,11 -> $@3,12 -> M@2,13 -> R@1,14: reward=7.10, survivability=1.00 |
| route | decision_trace | 27 | complete | choice map_node | choice 0 | high | Bottled common map scoring prefers reward-to-survivability 7.10: M@5,10 -> R@4,11 -> $@3,12 -> M@2,13 -> R@1,14: reward=7.10, survivability=1.00 |

## Most Worth Fixing

1. **shop floor 8**: current `Strength Potion` vs reference `leave` (high). Bottled shop handler leaves when no priority purchase is affordable. Repeated 3x in non-fixture evidence.
2. **shop floor 4**: current `purge` vs reference `Perfected Strike` (high). Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge. Repeated 2x in non-fixture evidence.
3. **route floor ?**: current `choice 2` vs reference `choice 0` (high). Bottled common map scoring prefers reward-to-survivability 7.98: M@0,0 -> M@1,1 -> M@2,2 -> $@3,3 -> M@2,4 -> R@2,5: reward=7.98, survivability=1.00 Repeated 2x in non-fixture evidence.
4. **card_reward floor 1**: current `Thunderclap` vs reference `Twin Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Repeated 2x in non-fixture evidence.
5. **card_reward floor 1**: current `Carnage` vs reference `Pommel Strike` (high). Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Repeated 2x in non-fixture evidence.

## Repair Gate

Repair is justified by repeated high-confidence non-fixture evidence. This report does not change gameplay code; apply one minimal strategy fix test-first, starting from the top-ranked candidate.
