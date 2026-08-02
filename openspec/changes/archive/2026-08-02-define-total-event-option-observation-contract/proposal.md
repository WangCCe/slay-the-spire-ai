## Why

The registered Current-policy bridge passes its frozen four-row gate but its
only Stage 2 execution stops at unsupported `The Cleric` event semantics. The
corrected static audit covers all 25 Current-relevant events, yet a total
adapter cannot safely be implemented from its label table alone: Current
chooses positional options while `sts_lightspeed` exposes sparse simulator
indices, `Cursed Tome` changes those indices by phase, `N'loth` embeds offered
relic names in labels, and upstream `Mindbloom` needs an exact Current identity.

## What Changes

- Define a versioned, source-bound Current event-option observation contract
  for all 25 canonical events and all 47 Current aliases without executing the
  native simulator or changing runtime policy.
- Separate Current-facing option position from simulator choice index and
  require a deterministic reversible mapping for every legal candidate set.
- Register static index-to-label mappings, the exact five-state `Cursed Tome`
  phase table, the `N'loth` offered-relic context requirement and label
  template, and the `Mindbloom` Current-id normalization.
- Bind the contract to the corrected r2 audit, exact Current source, exact
  upstream sources, and all-false authority; publish a concise deterministic
  coverage report that fails closed on any missing event, index, phase,
  dynamic input, identity, or provenance.
- Keep the existing one-event resolver and bridge implementation unchanged.
  Resolver extension, adapter schema changes, native execution, compatibility
  evaluation, baseline measurement, gameplay, reward changes, model fitting,
  formal RL, training, and promotion remain out of scope.

Success means the registered contract accounts for all 25 events and 47
aliases, identifies every Current-observable label and source-index mapping,
records every required dynamic snapshot field, reports zero unaccounted
surfaces, and recomputes byte-for-byte. The rollback boundary is removal of the
new contract validator and artifacts; the r2 audit, bridge evidence, simulator
adapter, resolver, and Current policy remain unchanged.

## Capabilities

### New Capabilities

- `noncombat-event-option-observation-contract`: Define deterministic,
  provenance-bound event identity, option-position, simulator-index, label,
  phase, and dynamic-context requirements for a future total Current bridge
  resolver.

### Modified Capabilities

None.

## Impact

- Adds a read-only contract validator, focused tests, one explicit registration,
  canonical contract/report artifacts, and a closeout.
- Consumes the corrected event-semantics r2 inventory and bound Current/upstream
  source identities without mutating either repository.
- Does not modify `analysis_scripts/noncombat_event_option_semantics.py`,
  `analysis_scripts/noncombat_current_policy_simulator_bridge.py`,
  `simulator_adapters/sts_lightspeed/noncombat_adapter.cpp`, gameplay behavior,
  or any RL policy or training path.
