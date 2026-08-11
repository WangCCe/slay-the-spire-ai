## Why

The reviewed r6 training request is pushed, but the repository exposes no
registered command that composes the existing request/authorization checks,
execution context, lease, journal, resource ledger, runtime training loop,
checkpoints, and terminal publication. Publishing training authority before
that command exists would authorize an unlaunchable and unauditable workflow.

## What Changes

- Add one narrow CPU training runner with a closed `preflight`, `run-training`,
  and `terminalize-dead-owner` command set.
- Publish one tracked r6 bootstrap control anchor before the launch manifest:
  the exact canonical zero-progress paired training checkpoint and exact
  experiment configuration. Two fresh isolated CPU processes must reproduce
  the same bytes and restore/re-encode the checkpoint exactly. This bounded
  publication may construct the registered fixed initialization but may not
  load native code, open the empirical seed inventory, construct an
  environment, take an optimizer step, fit, train, evaluate, or create the
  training output root.
- Add a canonical launch manifest that binds the pushed r6 registration,
  training request/review, runner source, interpreter, registered experiment
  source, additive seed-inventory producer and independent registration
  verifier sources, exact r6-bound source-inventory
  path/hash, exact native module path/hash/size, recursive PE import graph,
  every non-host dependent DLL path/hash/size, explicit trusted-host imports,
  DLL directories, adapter API,
  provenance/hash, output root, resource ceilings, and
  exact command set before any authorization is accepted. The manifest also
  binds one canonical rollback authority, including the candidate-disabled
  control target and read-only production-isolation identities.
- Add command-specific canonical execution envelopes. A run envelope is
  rendered only after complete stage authority exists and binds the manifest/
  command/rollback composite through the existing standing-delegation resolver
  or an exact external-human approval. A separate dead-owner envelope is
  rendered only after a failed owner and immutable prefix exist. Each envelope
  cannot broaden the request and must be reviewed and pushed before its command.
- Compose the existing validated execution context, exclusive lease,
  write-ahead access/resource accounting, registered 512-seed schedule,
  the fixed chunk-level paired runtime, eight complete-boundary checkpoints, and one
  terminal or rollback publication.
- Add a fully authorized dead-owner terminalization path that can close an
  existing partial prefix after proving the prior process is dead, without
  runtime/model/native loading, seed access, environment construction, or
  training replay.
- Keep runtime/native imports behind complete registration, request,
  authorization, approval/launch-observation, source, production-isolation,
  output-root, and process-liveness validation.
- Add source-only dry-run and failure-path tests that prove malformed, changed,
  incomplete, partial-chunk, or over-budget launches fail before native/model/
  environment/seed access.
- Preserve the pushed r6 registration and request as immutable request-only
  evidence. Do not publish task 6.4 authorization or run task 6.5 training in
  this change.

Success means a reviewed pushed runner and deterministic bootstrap control
anchor can reproduce one exact preflight and closed command set, and focused
plus repository gates prove lifecycle closure. Source-only preflight remains
free of native/model/runtime execution dependencies; the earlier anchor
publication is restricted to deterministic zero-progress model construction
and serialization. The rollback boundary is
the first runner process invocation: before it, remove only uncommitted runner
planning/preflight artifacts; after it, preserve every receipt, lease,
checkpoint, journal, terminal, complete, or partial output and never substitute
or retry the identity outside the existing complete-boundary continuation rule
or an idempotent same-envelope closure-only resume that performs no empirical
operation.

## Capabilities

### New Capabilities

- `noncombat-card-acceptance-training-runner`: Exact source-bound launch
  manifest, command set, lifecycle composition, dead-owner terminalization,
  publication, and fail-closed
  verification for the paired card-acceptance training stage.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Require a reviewed pushed
  training runner and launch manifest before training authorization or
  execution becomes eligible.

## Impact

- New source-only runner module and focused tests under `analysis_scripts/` and
  `tests/`.
- Narrow integration with the existing card-acceptance control, runtime,
  registration validator, simulator adapter, and standalone verifier APIs.
- New bounded bootstrap-control, launch-manifest, and preflight reports only;
  no CommunicationMod,
  gameplay policy, production checkpoint, training hyperparameter, cohort,
  model architecture, native dependency, or resource-ceiling change.
