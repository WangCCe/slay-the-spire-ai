# Non-Combat RL Mismatch Triage

## Fresh Eval Batch

- Batch window: `since-unix 1781786000`
- Launch mode: direct `main.py` with clean trace environment after the batch wrapper stalled before game-state exchange.
- Runs: 25
- Victories: 0
- Best floor reached: 33
- Common late deaths: Collector, Champ, Automaton, Act 2 hallway fights.

## Readiness Metrics

- Promotion status: allowed
- Samples: 389
- Categories: route=242, card_reward=64, event=57, shop=26
- Evidence quality: complete=375, partial=14
- Matched live outcomes included in gate: 184
- Formal non-combat RL training: still blocked by guard.

## Fixed Data Issue

- Symptom: 10 high-confidence shop mismatches reported current action as `None` while Bottled chose `shop:purge:strike`.
- Cause: live trace purge actions can be recorded as generic `purge` without `card_to_purge`; the exporter required a specific purge target to map the selected action id.
- Fix: generic shop purge now maps to the unique purge candidate, preserving `shop:purge:strike` when the shop candidate list contains starter removal.
- Result: high-confidence shop mismatches dropped from 14 to 4.

## Remaining Mismatch Triage

- Shop: 4 high-confidence mismatches, all singletons. Two prefer Offering over relic buys, one prefers Offering over a generic wait/unknown action, and one prefers Perfected Strike over leaving. This is not enough for a gameplay policy change yet.
- Card reward: 14 high-confidence mismatches. Only `take Anger` vs `take Twin Strike` repeats twice; the rest are singletons. Treat as watchlist, not a patch.
- Event: no high-confidence mismatches.
- Route: 46 high-confidence mismatches, but route labels are path-index comparisons with high attribution noise. Keep route out of first policy-fix pass.

## Decision

Do not change gameplay policy from this batch alone. The only high-confidence repeated shop cluster was a data-mapping false positive and is fixed. Next policy work should require either repeated shop/card-reward mismatches across another fresh batch or direct run evidence that the current choice caused a worse live outcome.
