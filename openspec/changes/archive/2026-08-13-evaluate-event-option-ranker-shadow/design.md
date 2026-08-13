## Context

The event model passed one fixed development cohort, but its selected `0.50`
confidence threshold accepts every learned disagreement. A fresh cohort is
needed to test whether the raw ranking benefit replicates rather than relying on
an ineffective fallback or reusing development.

## Goals / Non-Goals

**Goals:**

- Verify and load the exact committed model and its manifest binding.
- Evaluate its selected policy once on fresh event-option counterfactual rows.
- Apply fixed support and Current-relative regret gates without fitting.

**Non-Goals:**

- Training, threshold calibration, model selection, or retries.
- Gameplay, CommunicationMod, production loading, or policy promotion.
- Event-specific patches inferred from the fresh cohort.

## Decisions

### Fixed fresh cohort

The original `94300..94363` attempt stopped before a verdict at a previously
unregistered Current shop candidate-mapping boundary and is permanently
consumed. Use replacement seeds `94400..94463`, disjoint from POC, train,
development, and the failed attempt. Collect at
most two multi-option event sources per seed, with limits of 128 complete rows,
512 action branches, and 32 registered Courier censors. Require at least 96
complete rows, 32 informative rows, and 12 distinct event ids.

### Exact selected-policy binding

Require the source training directory's artifact manifest to bind `model.json`.
Verify the model schema, architecture, selected epoch, selected threshold, and
state round-trip before native loading. Evaluate the stored threshold exactly;
do not substitute a new threshold even though its prior calibration was weak.

### Terminal replication gates

Compare selected policy with Current on fresh rows. Replication requires mean
regret to improve strictly, p95 and maximum regret to be no worse, at least one
action change and correction, and corrections to be at least as numerous as
regressions. Publish the confidence distribution and per-event changes as
diagnostics, but do not use them to change the fixed verdict.

## Risks / Trade-offs

- [Fresh outcomes have high variance] -> Require 64 seeds, tail metrics, and
event diversity; keep the conclusion at simulator shadow level.
- [A Current continuation selects a visible but simulator-illegal shop item] ->
  Censor only the exact registered `shop + candidate_mapping_absent` boundary;
  all other mapping failures remain fatal.
- [Confidence remains uncalibrated] -> Bind the selected threshold and report
  its behavior; do not claim the fallback is conservative.
- [A single event dominates aggregate benefit] -> Publish per-event changes and
  regret while retaining preregistered aggregate gates.
- [Fresh cohort fails] -> Stop this model without rerun, seed replacement, or
  tuning.

## Migration Plan

Add one offline evaluator, tests, and report. No production migration occurs.
Rollback removes those files.

## Open Questions

If replication passes, the next decision is whether to run a simulator policy
shadow over full trajectories or redesign confidence calibration first.
