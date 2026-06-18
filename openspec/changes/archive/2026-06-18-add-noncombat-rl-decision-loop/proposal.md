# Change: Add non-combat RL decision loop

## Why
The first-win effort is now limited less by raw combat execution and more by operating decisions such as shop purchases, events, routing, and card rewards. Before training a non-combat RL policy, the project needs a repeatable data and evaluation loop that records those decisions as trainable samples, compares current policy behavior with Bottled-style labels, and gates promotion on live outcomes instead of ad hoc observations.

## What Changes
- Define a canonical non-combat decision sample for shop, event, route, and card-reward decisions.
- Export decision samples from existing decision traces with candidate actions, selected action, state snapshot, current-policy label, Bottled-style reference label, and evidence quality.
- Join decision samples to bounded live outcomes from `.run` files when the run can be identified reliably, while marking missing or ambiguous outcomes explicitly.
- Add an offline evaluation report and fixed fresh-eval promotion gate that combine sample coverage, Bottled agreement, repeated high-confidence gaps, and live run outcomes.
- Allow only small combat RL smoke training to verify the training pipeline remains healthy; do not start formal non-combat RL training until state, action, reward, and evaluation definitions are covered by tests and reports.

## Impact
- Affected specs: noncombat-rl-decision-loop (new)
- Affected code: `analysis_scripts/`, `spirecomm/ai/decision_trace.py`, `scripts/run_training_batch.py`, focused tests under `tests/`, reports under `reports/`
- Builds on: `add-offline-decision-comparator`
- Out of scope: direct gameplay policy rewrites, importing Bottled as the live policy, formal non-combat RL training, broad combat RL redesign
