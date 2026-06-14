# Change: Enhance offline decision evidence

## Why
The offline decision comparator POC can compare fixtures and `.run` summaries, but recent real runs still produce mostly low-confidence partial rows. The first-win loop needs non-fixture, decision-time evidence before route, shop, event, or card-reward mismatches can safely drive gameplay changes.

## What Changes
- Extend decision traces with compact decision-time snapshots for card rewards, shops, events, and map choices.
- Teach the offline comparator to normalize those enriched trace rows into complete or partial samples.
- Generate a recent-run report that separates real high-confidence candidates from remaining evidence gaps.
- Preserve the repair gate: apply at most one minimal gameplay strategy fix only when repeated, high-confidence, non-fixture evidence proves it.

## Impact
- Affected specs: offline-decision-comparator
- Affected code: `spirecomm/ai/decision_trace.py`, `analysis_scripts/offline_decision_comparator.py`, focused tests, generated comparator report
- Out of scope: training, tuning, large agent rewrites, and combat play sequencing comparison
