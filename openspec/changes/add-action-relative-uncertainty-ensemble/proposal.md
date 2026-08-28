## Why

The first action-relative residual intervened on 162 of 839 held-out states at
only 0.383 precision and then lost its matched live gate to the frozen r16
parent. Its holdout threshold curve shows ranking signal but does not justify
post-hoc threshold tuning, so the next candidate needs a preregistered estimate
of prediction uncertainty rather than another near-identical scalar fit.

## What Changes

- Add a development-only five-member bootstrap ensemble over the existing
  action-relative training corpus while keeping the r16 parent frozen.
- Select alternatives with a fixed lower-confidence score equal to ensemble
  mean minus one sample standard deviation and the existing 0.5 return-unit
  threshold.
- Keep the existing seed-disjoint evaluation corpus untouched by fitting and
  require at least 30 interventions, at least 0.65 intervention precision,
  higher mean selected true advantage and lower policy regret than the prior
  single residual, and zero illegal or forbidden selections.
- Permit at most one fresh, seed-disjoint matched LightSTS gate only after all
  offline conditions pass. Close the recipe without a sweep when any condition
  fails.
- Publish source-bound member identities, bootstrap identities, uncertainty
  telemetry, holdout metrics, and development-only authority in a distinct
  artifact and report.
- Do not start CommunicationMod gameplay, load the candidate in production, or
  promote a checkpoint as part of this change.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-uncertainty-ensemble`: Deterministic bootstrap
  ensemble fitting, lower-confidence abstention, source-bound artifacts, and
  fixed offline/fresh-simulator decisions for an action-relative candidate.

### Modified Capabilities

None.

## Impact

The change adds one isolated runtime model module, bounded CPU fit and
evaluation runners, committed registrations/reports, and focused tests. It
reuses the existing frozen r16 parent, guard-advantage corpora, state encoding,
and LightSTS adapter without changing the production checkpoint or live agent
configuration. A failed condition closes this candidate and leaves r16 and the
single-residual implementation unchanged.
