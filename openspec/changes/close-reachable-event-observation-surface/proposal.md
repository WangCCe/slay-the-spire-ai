## Why

The immutable API v3 compatibility cohort failed before its first completed
seed because simulator-reachable `Scrap Ooze` is absent from the contract that
was complete only for Current's 25 explicit event branches. The project must
reconcile those two surface definitions before spending another seed or using
the bridge as a baseline-floor input.

## What Changes

- Add a deterministic, provenance-bound static audit that inventories every
  event reachable from the registered Ironclad A0 simulator pools, including
  phases, legal indices, display cases, execution cases, Current aliases, and
  whether Current uses an explicit branch or its generic position-zero default.
- Publish a successor observation contract that keeps the 25 policy-sensitive
  rules explicit and adds an exact source-bound set for reachable generic
  events. Generic semantics may use ordered native candidates only when the
  event is registered as reachable and the bound Current AST proves that no
  branch or risky alias handles it.
- Extend the resolver and bridge to emit contiguous Current positions and exact
  simulator indices for those generic events without weakening explicit,
  phased, dynamic, provenance, or fail-closed rules.
- Add regressions for `Scrap Ooze`, dynamic generic phases, sparse legal
  indices, unknown events, Current-branch drift, source mutation, and historical
  contract isolation. Publish a source-only closeout after focused tests, the
  repository commit gate, and strict OpenSpec validation.
- Keep native module construction, seed access, compatibility reruns, gameplay,
  policy changes, model fitting, reward changes, formal RL, training,
  qualification, loading, and promotion out of scope.

Success means the static reachable inventory and successor contract reconcile
without overlap or unaccounted events, every generic rule is proven to take
Current's default path, and resolver/bridge tests cover the complete registered
surface. This change grants no execution or policy-quality authority.

Rollback removes the new audit, successor contract, and resolver/bridge
successor path while preserving the frozen 25-event contract, the consumed
`7000..7007` cohort, and its `Scrap Ooze` blocker unchanged.

## Capabilities

### New Capabilities

- `noncombat-reachable-event-surface-audit`: Define source-complete static
  accounting for simulator-reachable event identities, pools, phases, option
  cases, and Current explicit-versus-generic handling.

### Modified Capabilities

- `noncombat-event-option-observation-contract`: Add a successor contract that
  distinguishes explicit policy-sensitive rules from registered generic-default
  events while preserving exact provenance and fail-closed behavior.
- `noncombat-current-policy-simulator-bridge`: Allow source-bound generic event
  hydration only for the audited reachable set and preserve dual-coordinate
  diagnostics.

## Impact

- New read-only audit module, tests, registration, canonical artifacts, and
  closeout report under `analysis_scripts/`, `tests/`, and `reports/`.
- Successor contract validation and artifacts plus a versioned update to
  `analysis_scripts/noncombat_event_option_semantics.py`.
- Event enrichment and diagnostics in
  `analysis_scripts/noncombat_current_policy_simulator_bridge.py` with no
  change to Current gameplay policy.
- Read-only access to the existing `D:\CLionProjects\sts_lightspeed` source
  checkout; no native build or execution dependency.
