# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 70
- Differences: 39
- Categories: card_reward=49, event=11, route=5, shop=5
- Evidence quality: partial=70
- Oracle modes: bottled_style=70

## Comparison Rows

| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|---|
| card_reward | run:1784714975.run | 1 | partial | bottled_style | Shrug It Off | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 2 | partial | bottled_style | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 3 | partial | bottled_style | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 5 | partial | bottled_style | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 7 | partial | bottled_style | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 8 | partial | bottled_style | Corruption | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 10 | partial | bottled_style | True Grit | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 11 | partial | bottled_style | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 12 | partial | bottled_style | Offering | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784714975.run | 14 | partial | bottled_style | Armaments | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| shop | run:1784714975.run | 4 | partial | bottled_style | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1784714975.run | 1 | partial | bottled_style | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1784715079.run | 0 | partial | bottled_style | Trip | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 1 | partial | bottled_style | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 4 | partial | bottled_style | Twin Strike | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 6 | partial | bottled_style | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 7 | partial | bottled_style | Second Wind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 8 | partial | bottled_style | Carnage | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 13 | partial | bottled_style | Battle Trance | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715079.run | 14 | partial | bottled_style | Clothesline | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| event | run:1784715079.run | 3 | partial | bottled_style | Donut | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715079.run | 5 | partial | bottled_style | Grow | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715079.run | 11 | partial | bottled_style | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1784715079.run | 2 | partial | bottled_style | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1784715079.run | 10 | partial | bottled_style | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1784715079.run | 1 | partial | bottled_style | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1784715199.run | 1 | partial | bottled_style | Bloodletting | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 2 | partial | bottled_style | Thunderclap | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 3 | partial | bottled_style | Iron Wave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 4 | partial | bottled_style | Clothesline | Shrug It Off | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shrug It Off. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 5 | partial | bottled_style | Heavy Blade | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 8 | partial | bottled_style | Anger | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 11 | partial | bottled_style | Thunderclap | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 12 | partial | bottled_style | Whirlwind | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715199.run | 14 | partial | bottled_style | Metallicize | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1784715199.run | 7 | partial | bottled_style | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715199.run | 10 | partial | bottled_style | Healed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715199.run | 13 | partial | bottled_style | Lose Max HP | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1784715199.run | 1 | partial | bottled_style | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1784715356.run | 1 | partial | bottled_style | Dual Wield | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 2 | partial | bottled_style | Clothesline | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 4 | partial | bottled_style | Clothesline | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 5 | partial | bottled_style | Shockwave | Shockwave | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Shockwave. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 7 | partial | bottled_style | Battle Trance | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 8 | partial | bottled_style | Corruption | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 11 | partial | bottled_style | Flame Barrier | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 12 | partial | bottled_style | Anger | Twin Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Twin Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 14 | partial | bottled_style | Pommel Strike | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 16 | partial | bottled_style | Impervious | Impervious | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Impervious. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715356.run | 18 | partial | bottled_style | Pommel Strike | Battle Trance+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance+1. Limitations: missing deck snapshot at reward time |
| event | run:1784715356.run | 3 | partial | bottled_style | Got Potions | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715356.run | 19 | partial | bottled_style | Transformed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1784715356.run | 13 | partial | bottled_style | Membership Card | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1784715356.run | 13 | partial | bottled_style | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1784715356.run | 1 | partial | bottled_style | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |
| card_reward | run:1784715504.run | 1 | partial | bottled_style | Cleave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 2 | partial | bottled_style | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 3 | partial | bottled_style | Reckless Charge | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 5 | partial | bottled_style | Headbutt | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 7 | partial | bottled_style | Power Through | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 8 | partial | bottled_style | Immolate | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 11 | partial | bottled_style | Pommel Strike | Pommel Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Pommel Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 14 | partial | bottled_style | Battle Trance | Battle Trance | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Battle Trance. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 16 | partial | bottled_style | Corruption | Reaper | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Reaper. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 18 | partial | bottled_style | Clothesline | Ghostly Armor | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Ghostly Armor. Limitations: missing deck snapshot at reward time |
| card_reward | run:1784715504.run | 19 | partial | bottled_style | Inflame | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| event | run:1784715504.run | 4 | partial | bottled_style | Upgraded | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715504.run | 12 | partial | bottled_style | Card Removal | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1784715504.run | 20 | partial | bottled_style | Upgraded Two | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| route | run:1784715504.run | 1 | partial | bottled_style | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision candidate is available yet.
