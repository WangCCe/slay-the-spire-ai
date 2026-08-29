## Why

The merged first-successor corpus fails when support is measured against every
r14/r15 replay transition, even though it passes every unchanged support gate
against 768 real guard-replacement opportunities from 20 no-takeover live
runs. The broad replay population includes ordinary card actions and
non-replaced end turns that the successor model can never serve, so the current
gate blocks fitting on a deployment-irrelevant mismatch.

## What Changes

- Add a source-bound live-opportunity context target that joins exact
  parent-policy guard-replacement telemetry to its raw decision state and
  publishes only the context fields needed for weighting.
- Freeze the target definition from the existing 20-run audit, then collect a
  new run- and session-disjoint 20-run parent-only holdout with no experimental
  action authority.
- Replace the successor ablation's all-transition r14/r15 support target with
  the fresh live-opportunity target while preserving the existing context
  cells and all coverage, ESS, concentration, floor, balance, integrity, and
  seed-isolation thresholds.
- If the current merged fit/calibration/fresh corpora pass against the fresh
  target, run the already specified current-state control and successor-delta
  paired fit once with the unchanged optimizer, updates, labels, calibration,
  fresh evaluation, and policy gates.
- If target construction, support, or integrity fails, close without fitting,
  additional gameplay, seed substitution, threshold changes, or tuning.

Success requires a complete 20-run parent-only target with exact joins and a
passing unchanged support gate. Model success remains the existing successor
hard policy gate or, separately, its descriptive paired-control signal; this
change grants no live candidate takeover or production promotion.

The rollback boundary is additive: the old r14/r15 replay gate, consumed
supplement, production r16 checkpoint, and live runtime remain immutable. The
new target, fit, and reports can be discarded without changing production.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-live-context-target`: Define parent-only live
  opportunity capture, exact state joining, immutable target publication, and
  fresh-holdout integrity.

### Modified Capabilities

- `combat-rl-action-relative-successor-delta-ablation`: Use a fresh real
  guard-replacement opportunity target for context support and permit the fixed
  paired fit only after that aligned gate passes.

## Impact

- Affected code: a focused live-context target builder, support-weight adapter,
  and a wrapper around the existing paired successor fit and evaluation path.
- Affected evidence: four new five-run parent-only live batches, one immutable
  context target, one aligned support report, and conditional paired model
  artifacts.
- Runtime: Windows CommunicationMod gameplay for the target holdout, followed
  by bounded offline model fitting only if support passes.
- Production: no checkpoint loading change, candidate action takeover,
  promotion, or production write; production r16 continues to choose every
  live action during collection.
