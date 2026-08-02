## Why

The completed frozen Current-policy bridge POC stopped because the registered
`Liars Game` snapshot contains only generic event-option indices, while Current
reads semantic labels before selecting a safe option. The upstream
`sts_lightspeed` source now provides enough read-only evidence to bind this one
event's exact id, legal indices, display labels, and execution branches without
inventing text or changing gameplay behavior.

Current evidence is the immutable four-row Stage 1 registration, its
`missing_event_option_semantics` verdict, and the locally bound upstream
`sts_lightspeed` source. Success means that a successor registration changes
only the implementation and event-semantics identities, proves the original
rows and settings unchanged, and deterministically maps all four frozen rows;
it is not evidence of policy quality.

## What Changes

- Add a versioned, fail-closed adapter-layer event-option semantics resolver for
  the exact `Liars Game` event state used by the frozen Stage 1 row.
- Bind each supported semantic option to the upstream event id and legal action
  index, with labels verified against `ConsoleSimulator::printEventActions` and
  effects verified against `GameContext::chooseEventOption`.
- Require exact candidate-index coverage and reject unknown events, phases,
  duplicate indices, missing indices, or changed upstream provenance.
- Let the Current bridge consume the resolver only when a snapshot does not
  already carry valid `option_semantics`; generic index labels remain invalid.
- Create a hash-bound successor registration because the original registration
  binds the old implementation commit and source digest. Preserve the original
  four row hashes, source snapshot hashes, category minimums, replay count,
  Current configuration, thresholds, and Stage 2 seeds.
- Recompute only the frozen Stage 1 gate. Run the already-registered reused-seed
  Stage 2 check only if every Stage 1 structural gate passes.
- Keep gameplay, fresh simulator cohorts, model fitting, reward changes, formal
  RL training, baseline-floor claims, and policy promotion out of scope.
- Keep rollback at deletion of the resolver, bridge integration, successor
  registration, focused tests, and generated structural reports.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-adapter`: Define source-bound, versioned, fail-closed
  semantic resolution for supported event options without broad event-coverage
  claims.
- `noncombat-current-policy-simulator-bridge`: Permit a registered adapter
  semantics contract to hydrate missing event labels and require immutable
  predecessor-to-successor registration comparison before recomputation.

## Impact

- Adds a separate offline adapter-semantics module and affects the Current
  bridge, focused adapter/bridge tests, OpenSpec capability specs, project
  direction, and new hash-closed report artifacts. The historically hash-bound
  core simulator adapter remains byte-identical.
- Reads the external `D:\CLionProjects\sts_lightspeed` checkout only for source
  audit and provenance. It does not modify or vendor that checkout.
- Does not change `OptimizedAgent`, Communication Mod configuration, live
  gameplay decisions, native simulator behavior, training code, or reward
  definitions.
