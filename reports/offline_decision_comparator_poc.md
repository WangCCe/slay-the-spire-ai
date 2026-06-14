# Offline Decision Comparator POC

Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 28
- Differences: 14
- Categories: card_reward=12, event=9, route=2, shop=5
- Evidence quality: complete=4, partial=24

## Comparison Rows

| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|
| shop | fixture:shop | 5 | complete | Anger | purge | high | Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases. |
| event | fixture:event | 8 | complete | choose 0: Enter | choose 1: Leave | high | Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves. |
| route | fixture:route | 1 | complete | choice 0 | choice 1 | high | Bottled common map scoring prefers reward-to-survivability 4.68: safer shop rest: reward=4.68, survivability=1.00 |
| card_reward | fixture:card_reward | 10 | complete | SKIP | Offering | high | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. |
| card_reward | run:1781445184.run | 0 | partial | Mind Blast | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 1 | partial | Perfected Strike | Perfected Strike | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 4 | partial | Shrug It Off | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 10 | partial | Armaments | Thunderclap | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Thunderclap. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 13 | partial | Ghostly Armor | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 14 | partial | Disarm | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 16 | partial | Fiend Fire | Offering | low | Bottled REQUESTED_STRIKE desired-card list wants up to 1 copy/copies of Offering. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 18 | partial | Shrug It Off | Dropkick | low | Bottled REQUESTED_STRIKE desired-card list wants up to 2 copy/copies of Dropkick. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 20 | partial | Armaments | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 22 | partial | Iron Wave | skip | low | Bottled card reward handler skips when no desired card is offered. Limitations: missing deck snapshot at reward time |
| card_reward | run:1781445184.run | 30 | partial | SKIP | Perfected Strike+1 | low | Bottled REQUESTED_STRIKE desired-card list wants up to 5 copy/copies of Perfected Strike+1. Limitations: missing deck snapshot at reward time |
| event | run:1781445184.run | 2 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 3 | partial | Forget | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 7 | partial | Success | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 12 | partial | Transformed | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 19 | partial | Stole From Cult | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 21 | partial | Got Potions | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 24 | partial | Inject Mutagens | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| event | run:1781445184.run | 28 | partial | Ignored | unknown | low | Partial event evidence: option labels and hp at decision time are required for high-confidence comparison. Limitations: missing event option labels and hp at decision time |
| shop | run:1781445184.run | 5 | partial | Anger | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781445184.run | 29 | partial | Impervious | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781445184.run | 5 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| shop | run:1781445184.run | 29 | partial | Strike_R | unknown | low | Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison. Limitations: missing full shop offer |
| route | run:1781445184.run | 1 | partial | actual path | unknown | low | Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring. Limitations: missing route candidate map at decision time |

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. Treat these rows as candidates for later test-first review only when they repeat, remain high confidence, and are relevant to the first Ironclad win objective.
