## Why

The registered Current-policy bridge still stops at the first event beyond its
Liars Game-only resolver, and its event action mapping incorrectly assumes that
a Current-visible option position is the same integer as a simulator choice
index. The completed source-bound observation contract now defines all 25
Current-relevant events, 47 aliases, sparse-index behavior, five Cursed Tome
phases, Mindbloom normalization, and the exact N'loth snapshot fields needed to
replace those two structural blockers without changing Current policy.

Current evidence is the immutable r2 Stage 2 failure at `The Cleric`, the
corrected event-semantics audit, and the strictly recomputed total observation
contract. Success means focused regressions prove total fail-closed resolution,
the native adapter exposes exact N'loth offer identity, Current positions map
reversibly to legal simulator candidates, and the repository commit gate passes.
No new native cohort or gameplay run is evidence for this change.

## What Changes

- **BREAKING**: advance the native non-combat adapter API to v3 for newly built
  modules and add exact N'loth `offered_relics` records sourced from
  `GameContext.info.relicIdx0/relicIdx1`; retain explicit read compatibility for
  historical v2 snapshots where the requested event does not need v3 context.
- Replace the Liars Game-only resolver with a resolver that loads and hash-checks
  the canonical total observation contract, validates exact simulator
  provenance, and resolves all 25 registered events without fuzzy or generic
  fallbacks.
- Emit each resolved event option with both contiguous `current_position` and
  original `simulator_choice_index`; hydrate Current with positions and map its
  returned action back through the same validated observation row.
- Normalize upstream `Mindbloom` to Current `MindBloom`, enforce all five
  Cursed Tome phase/candidate sets, and validate N'loth slot/id/name records
  against the snapshot relic list.
- Preserve valid legacy inline semantics only when their positions and simulator
  indices are unambiguous; reject sparse or inconsistent legacy rows rather than
  interpreting one integer in two coordinate systems.
- Add red regressions across the Python adapter, C++ source surface, resolver,
  hydration, mapping, non-mutation, and old-evidence compatibility boundaries.
- Do not execute a native simulator, consume or retry seeds, launch gameplay,
  alter Current policy, fit a model, change reward, train, or promote within this
  change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-adapter`: Version the snapshot extension for exact
  N'loth offered-relic identity and replace narrow event semantics with the
  hash-bound total observation contract while preserving historical evidence.
- `noncombat-current-policy-simulator-bridge`: Require separate Current-position
  and simulator-index coordinates for event hydration and action mapping, with
  total fail-closed contract resolution and bounded inline compatibility.

## Impact

- Affects `simulator_adapters/sts_lightspeed/noncombat_adapter.cpp`,
  `analysis_scripts/noncombat_simulator_adapter.py`,
  `analysis_scripts/noncombat_event_option_semantics.py`,
  `analysis_scripts/noncombat_current_policy_simulator_bridge.py`, and focused
  adapter/bridge tests. The external `D:\CLionProjects\sts_lightspeed` checkout
  is read for source verification and remains unmodified.
- Uses the immutable canonical contract under
  `reports/noncombat_event_option_observation_contract_20260802` as the only
  semantic catalogue; it does not alter that artifact or its all-false
  authority.
- Historical registrations and reports remain immutable. Any future native
  compatibility evaluation requires a separate registration after this change
  is implemented, verified, archived, and pushed.
- Rollback reverts only the adapter v3 extension, total resolver, bridge mapping,
  focused tests, and this OpenSpec change; prior adapter modules, registrations,
  contract evidence, and bridge failures remain valid records.
