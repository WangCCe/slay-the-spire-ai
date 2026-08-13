## Why

The raw event-ranker overlay failed its paired full-trajectory gate after 74 of
331 overrides escaped the model's training event support. A separately bound
support-gated configuration is the shortest evidence path to determine whether
the learned signal helps whole simulator runs when unsupported extrapolation is
removed.

## What Changes

- Derive an exact event/candidate support set from the manifest-bound training
  dataset and verify that dataset before model loading.
- Overlay the frozen event ranker only on supported signatures; record explicit
  Current fallbacks for all unseen signatures.
- Run pure Current versus the supported overlay on one disjoint fixed paired
  cohort and evaluate the existing terminal value and paired-regression gates.
- Publish support coverage, fallback identities, per-pair traces, metrics, and a
  terminal simulator-integration go/no-go verdict.
- Do not fit, tune, retry the raw configuration, launch gameplay, qualify, or
  promote a policy.

## Capabilities

### New Capabilities

- `noncombat-supported-event-ranker-paired-trajectory-shadow`: Manifest-bound
  training-support gating, Current fallback accounting, and paired
  full-trajectory simulator evaluation for the frozen event ranker.

### Modified Capabilities

None.

## Impact

This adds one offline runner/configuration, focused tests, a spec, and one report.
It reuses the committed event model, training dataset, simulator adapter, and
Current bridge. Production checkpoints, CommunicationMod, live gameplay policy,
and the archived raw-overlay no-go evidence remain unchanged. Rollback removes
the new runner and evidence artifacts.
