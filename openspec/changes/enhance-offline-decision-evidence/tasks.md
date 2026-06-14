## 1. Evidence Capture
- [x] 1.1 Add compact decision-trace screen snapshots for card reward, shop, event, and map screens.
- [x] 1.2 Include deck, relic, gold, HP, and available command context needed by the comparator.
- [x] 1.3 Add focused trace serialization tests for all four operating-decision families.

## 2. Comparator Normalization
- [x] 2.1 Normalize enriched card-reward trace rows into complete samples when offered cards and deck are present.
- [x] 2.2 Normalize enriched shop trace rows into complete samples when offer, prices, gold, purge, and deck are present.
- [x] 2.3 Normalize enriched event trace rows into complete samples when event name, options, HP, and relics are present.
- [x] 2.4 Normalize enriched map trace rows into complete samples when candidate route context is available; otherwise keep them partial with explicit limitations.
- [x] 2.5 Add focused comparator loader tests covering complete trace rows and partial fallback behavior.

## 3. Local Report
- [x] 3.1 Run the comparator against recent local run/trace evidence and regenerate `reports/offline_decision_comparator_poc.md`.
- [x] 3.2 Inspect ranked non-fixture issues and document whether a repair is justified.

## 4. Repair Gate
- [x] 4.1 If repeated high-confidence non-fixture evidence exists, implement one minimal strategy fix with a red-green regression.
- [x] 4.2 If no such evidence exists, leave gameplay code unchanged and state the remaining evidence gaps. Not applicable for this report: repeated high-confidence evidence exists.

## 5. Verification
- [x] 5.1 Run focused pytest for decision trace and offline comparator tests.
- [x] 5.2 Run OpenSpec strict validation for this change.
- [x] 5.3 Run broader pytest only if gameplay decision code is changed. Full pytest passed after the shop strategy fix.
