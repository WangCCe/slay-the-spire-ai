# Offline Decision Comparator POC

Reference: native Bottled Ironclad `REQUESTED_STRIKE` oracle from `C:\Users\20571\Documents\bottled_ai`; unsupported rows are explicit and not treated as high-confidence labels.
No gameplay-code fix is applied by this report.

## Summary

- Samples: 4
- Differences: 4
- Categories: card_reward=1, event=1, route=1, shop=1
- Evidence quality: complete=4
- Oracle modes: native_bottled=4

## Comparison Rows

| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |
|---|---|---:|---|---|---|---|---|---|
| shop | fixture:shop | 5 | complete | native_bottled | Anger | purge | high | Native Bottled shop priority prefers starter removal before optional purchases. |
| event | fixture:event | 8 | complete | native_bottled | choose 0: Enter | choose 1: Leave | high | Native Bottled REQUESTED_STRIKE event handler selected this option. |
| route | fixture:route | 1 | complete | native_bottled | choice 0 | choice 1 | high | Native Bottled route reward-to-survivability score 5.27: safer shop rest: reward=5.27, survivability=1.00 |
| card_reward | fixture:card_reward | 10 | complete | native_bottled | SKIP | Offering | high | Native Bottled REQUESTED_STRIKE desired-card config wants up to 1 copy/copies of Offering. |

## Most Worth Fixing

No repeated high-confidence operating-decision fix is recommended yet.

## Repair Gate

No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision candidate is available yet.
