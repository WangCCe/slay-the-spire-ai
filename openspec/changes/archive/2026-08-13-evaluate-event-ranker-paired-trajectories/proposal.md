## Why

The bound event ranker improved one-step counterfactual regret on both
development and a disjoint fresh shadow cohort, but those outcomes branch at a
single event and then freeze Current downstream. A paired full-trajectory test
is needed to learn whether repeatedly applying the event ranker improves whole
simulator runs before any gameplay integration.

## What Changes

- Run paired trajectories from identical fresh seeds: pure Current versus
  Current with the exact bound event ranker overlay.
- Preserve Current for route, shop, card reward, and all event decisions where
  the bound selected policy agrees or does not meet its stored threshold.
- Compare victory, floor progress, strict terminal return, event overrides, and
  unsupported trajectory rate under fixed gates.
- Publish canonical per-pair traces, metrics, identities, and a terminal
  integration go/no-go verdict.
- Do not fit, tune, promote, or launch gameplay.

## Capabilities

### New Capabilities

- `noncombat-event-ranker-paired-trajectory-shadow`: Bound event-policy overlay,
  paired full-trajectory simulator evaluation, and integration readiness gates.

### Modified Capabilities

None.

## Impact

This adds one offline paired runner, focused tests, a spec, and one report. It
loads the committed event model and uses the registered simulator/Current bridge;
production checkpoints, CommunicationMod, and live policy behavior are unchanged.
Rollback removes the runner and artifacts.
