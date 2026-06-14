# Change: Add offline decision comparator

## Why
The first Ironclad win effort needs a way to find repeated, high-confidence operating-decision gaps without importing `bottled_ai`, rewriting the current agent, or guessing from isolated deaths.
An offline comparator can turn local traces, `.run` records, and small fixtures into explainable rows that show our current choice beside a Bottled-style reference choice.

## What Changes
- Add a read-only analysis tool that normalizes shop, event, route, and card-reward samples from local artifacts or fixtures.
- Add Bottled-style reference adapters derived from the local `C:\Users\20571\Documents\bottled_ai` handler/config behavior, prioritizing `REQUESTED_STRIKE` for Ironclad.
- Generate a human-readable report with our choice, reference choice, confidence, evidence source, and difference reason.
- Rank the top 3-5 repeated, high-confidence, first-win-relevant decision issues for later review.
- Keep combat card-play decisions, training, tuning, large refactors, and direct `agent.py` replacement out of scope.

## Impact
- Affected specs: offline-decision-comparator (new)
- Affected code: `analysis_scripts/`, focused tests under `tests/`, optional sample fixtures under `tests/fixtures/`
- External read-only reference: `C:\Users\20571\Documents\bottled_ai`
