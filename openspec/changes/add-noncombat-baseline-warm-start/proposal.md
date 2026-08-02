## Why

The registered policy-validity study showed that the smoke-trained ranker
learned relative to its seeded initialization but remained materially worse
than native SimpleAgent on untouched simulator seeds. Before formal non-combat
RL is reconsidered, the project needs a bounded baseline-anchored warm-start
that proves the current representation and optimizer can recover a credible
simulator policy floor without converting the baseline into reward or permanent
ground truth.

## What Changes

- Add an offline-only collector for native SimpleAgent demonstrations on
  preregistered simulator train seeds, retaining complete candidate sets,
  canonical state/action features, legality, and source provenance.
- Add one deterministic candidate-masked supervised warm-start runner that
  trains a distinct ranker from those demonstrations without reward, live data,
  checkpoint discovery, or production-policy loading.
- Separate train, validation, and final test cohorts. Use exactly one
  preregistered v1 model configuration, treat validation only as a pre-test
  stop gate, and evaluate the frozen result exactly once on the untouched test
  cohort plus one identical replay.
- Require both held-out teacher-state action-fit evidence and independent
  candidate-policy rollout evidence against native SimpleAgent. Record a
  preregistered non-inferiority gate rather than claiming optimality.
- Publish hash-closed demonstrations, model, trajectories, metrics, report,
  manifest, and a separate noncanonical timing journal. Keep all formal RL,
  live gameplay, loading, OPE, qualification, and promotion authority false.
- Treat SimpleAgent labels as auxiliary supervision only. Preserve every legal
  candidate at inference, and keep Current and Bottled excluded until a
  separately validated simulator feature/action bridge exists.

No live evidence is collected by this change. Existing `.run`, trace,
CommunicationMod, gameplay, checkpoint, smoke, and policy-validity artifacts
remain immutable. Success means deterministic reproduction, complete
four-category coverage, a preregistered held-out action-fit gate, and a
preregistered paired terminal-floor non-inferiority gate against native
SimpleAgent on untouched seeds. Failure or ambiguity stops the change without
alternate cohorts, tuning after test observation, formal RL, or live rollout.

## Capabilities

### New Capabilities

- `noncombat-baseline-warm-start`: Defines preregistered native-baseline
  demonstrations, bounded supervised candidate ranking, untouched evaluation,
  deterministic artifacts, and no-authority verdicts.

### Modified Capabilities

- `noncombat-simulator-adapter`: Allows the native target-action API to support
  a separately reviewed demonstration and warm-start study under exact bounds.
- `noncombat-rl-decision-loop`: Keeps demonstration labels, warm-start models,
  and simulator parity metrics separate from live evidence and makes a credible
  baseline floor a prerequisite for any later formal-RL proposal.

## Impact

- Adds a dedicated offline evaluator/trainer under `analysis_scripts/`, focused
  pure and opt-in native tests, checked-in registrations, and simulator-only
  reports.
- Reuses adapter API v2 and the existing candidate feature projection without
  changing CommunicationMod, live agent selection, gameplay launch defaults,
  checkpoint discovery, or the external `sts_lightspeed` checkout.
- Introduces no production dependency and no model-loading path. Rollback is
  deletion of the new offline script, tests, registrations, reports, and docs;
  prior smoke and policy-validity evidence remains byte-identical.
