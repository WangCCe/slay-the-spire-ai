## Why

The terminal route/card residual POC did not materially improve held-out
SimpleAgent imitation, but that negative does not identify whether the limiting
factor is the adapter representation, the supervised learner, or a teacher that
is too narrow to serve as a policy-quality target. A read-only audit is needed
before spending more evidence or authorizing any further model work.

## What Changes

- Add a hash-bound static dependency audit for the local `sts_lightspeed`
  SimpleAgent route and card-reward decisions, including hidden agent state,
  constants, tie behavior, and adapter action mapping.
- Compare every teacher input with the adapter snapshot/candidate schema, the
  legacy policy projection, and the structured semantic projection, recording
  represented, derivable, intentionally excluded, and missing dependencies.
- Add deterministic exact and preregistered bounded-coarsening collision audits
  over the preserved train-only corpus. Report repeated observable keys,
  conflicting teacher labels, label entropy, and majority-label irreducible
  disagreement separately for route and card reward.
- Publish a fail-closed verdict that distinguishes an actionable adapter
  representation gap from a teacher-policy limitation or an inconclusive
  corpus, and selects only a next proposal class. No verdict grants training,
  simulator, gameplay, or policy authority.
- Close the baseline-imitation question without fitting another model or
  collecting another seed. A later adapter repair, auxiliary-target change, or
  RL study requires its own OpenSpec change.

No live evidence is collected. The only empirical input is the existing
hash-closed `4000..4031` train corpus; the external C++ checkout is read as
source evidence and is never built, loaded, or modified. Success means that the
published dependency matrix and alias metrics reproduce exactly and support one
bounded next-step verdict, not that any policy has improved.

## Capabilities

### New Capabilities

- `noncombat-state-action-teacher-sufficiency-audit`: Defines source dependency
  tracing, representation coverage, deterministic corpus alias analysis,
  teacher-suitability classification, hash-closed publication, and no-authority
  next-step verdicts for route and card-reward imitation.

### Modified Capabilities

None.

## Impact

- Adds one offline analysis script, focused fixtures/tests, a frozen audit
  registration, and generated JSON/Markdown reports under `analysis_scripts/`,
  `tests/`, and `reports/`.
- Reads the existing train-only gzip/manifest, current adapter and projection
  sources, and selected files from `D:\CLionProjects\sts_lightspeed`; it does
  not modify the external checkout or prior artifacts.
- Changes no agent behavior, native adapter, build output, CommunicationMod
  configuration, checkpoint, dependency, or formal-RL path. Rollback is
  deletion of only the new audit code, tests, registration, reports, and
  OpenSpec artifacts.
