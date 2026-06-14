## 1. Investigation
- [x] 1.1 Confirm current repo decision surfaces for shop, event, route, and card reward.
- [x] 1.2 Confirm read-only Bottled reference files and strategy assumptions.
- [x] 1.3 Identify local sample sources and evidence limits for `.run`, decision trace, logs, and fixtures.

## 2. POC Implementation
- [x] 2.1 Define a neutral operating-decision sample model.
- [x] 2.2 Implement sample loaders for `.run` records, bounded decision-trace rows, and fixtures.
- [x] 2.3 Implement minimal Bottled-style adapters for shop, event, route, and card reward.
- [x] 2.4 Implement comparison, confidence labels, and Markdown report rendering.
- [x] 2.5 Add fixture samples that cover all four priority categories.

## 3. Verification
- [x] 3.1 Add focused unit tests for loaders, adapters, comparison rows, and report ranking.
- [x] 3.2 Run the comparator on local sample data and save or print a readable report.
- [x] 3.3 Run focused pytest for the new comparator tests.
- [x] 3.4 Run broader pytest if the implementation touches shared agent, model, or action code. Not required: the POC only adds an analysis script, fixtures, a report, and proposal docs.

## 4. Repair Gate
- [x] 4.1 List the top 3-5 worth-fixing decision issues, or fewer if evidence does not support five.
- [x] 4.2 Do not modify gameplay decision code unless a later review confirms repeated, high-confidence, first-win-relevant differences.
