## Why

The approved non-combat policy pilot has 1,453 samples but only 14 uniquely matched trajectories, zero victories, and no recorded behavior propensities. The next useful step is therefore not formal RL or more deterministic imitation data, but a bounded way to collect replayable action overlap with exact behavior probabilities while preserving the existing live policy by default.

## What Changes

- Add a shadow-first non-combat proposal and mixing contract that records the baseline action, guard-approved alternatives, the complete action distribution, the selected action probability, deterministic draw provenance, and explicit ineligibility reasons.
- Add an opt-in exploration mode that is disabled by default, has a hard probability ceiling and per-run exploration budget, and initially permits executed exploration only for `shop` and `card_reward`; `event` and `route` remain shadow-only until separate category evidence gates pass.
- Derive initial alternatives only from actions accepted by existing Current-policy legality and safety guards. Bottled and pilot-model outputs remain offline labels and diagnostics, not live dependencies or mandatory targets.
- Add an exploration session manifest, append-only decision records, deterministic replay validation, conservative `.run` outcome joins, and a report covering unique trajectories, propensity coverage, action overlap, effective support, category coverage, terminal outcomes, and victories.
- Require a bounded fresh evidence batch with at least 25 uniquely joined trajectories, 100 percent replay-valid known propensities for eligible executed decisions, legal selected actions, and observed support for both baseline and alternative actions in every enabled category before the data loop can be called qualified.
- Keep OPE, causal uplift claims, live policy promotion, reward optimization, and formal non-combat RL blocked. A qualified exploration batch only proves that later evaluation has auditable behavior data.
- Preserve the rollback boundary: disabling the explicit exploration option restores the existing selected-action behavior; removing the isolated exploration records and module does not alter CommunicationMod configuration, combat checkpoints, or existing policy-learning artifacts.

## Capabilities

### New Capabilities
- `noncombat-exploration-data-loop`: Defines guarded action proposals, exact propensity sampling, replayable exploration sessions, and the bounded evidence qualification report.

### Modified Capabilities
- `noncombat-rl-decision-loop`: Replaces unknown behavior-probability evidence with verified known-propensity coverage when available, while retaining the reward, OPE, formal-RL, and promotion gates.

## Impact

- Live-facing changes are limited to an explicit opt-in wrapper/configuration path around non-combat decisions; the normal `optimized` and `combat_rl` defaults remain unchanged.
- Expected implementation areas are a new isolated exploration module, `main.py`/batch-runner opt-in configuration, decision trace metadata, canonical sample export and validation, offline reporting, and focused regression tests.
- Fresh evidence is evaluated from the real Windows gameplay environment using `.run` files, `ai_debug.log`, `communication_mod_errors.log`, and the exploration/decision traces. No WSL gameplay path or new external runtime dependency is introduced.
- Failure or replay mismatch fails closed to the Current action, marks the decision unsupported, and cannot emit a fabricated known propensity.
