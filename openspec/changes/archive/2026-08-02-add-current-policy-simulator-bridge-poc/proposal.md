## Why

The formal non-combat RL readiness audit remains blocked because no non-teacher policy has demonstrated a credible independent simulator floor, while the SimpleAgent imitation path has already produced a valid negative result. Before spending untouched seeds on another policy study, the repository needs evidence that the existing Current `OptimizedAgent` can consume simulator decision states through an exact, deterministic, side-effect-bounded bridge.

Current evidence is frozen simulator demonstrations and the source-bound Current policy implementation, not a fresh live-game or simulator outcome cohort. Success means proving exact hydration and candidate mapping for supported route, shop, event, and card-reward rows, then optionally proving stateful own-trajectory compatibility on already-consumed seeds; it does not mean proving Current is a good baseline.

## What Changes

- Add an offline-only bridge that hydrates frozen `sts_lightspeed` non-combat snapshots into the objects required by the exact Current `OptimizedAgent` decision path.
- Map each emitted Current action to exactly one registered simulator candidate and fail closed on missing state semantics, ambiguous inventory identity, unavailable actions, policy fallback, or mutation of source evidence.
- Preserve one explicitly configured Current agent instance per episode so adaptive route and multi-step shop state are not silently reset.
- Register and hash-bind the Current source identity, bridge code, adapter schema, frozen demonstrations, external item metadata, configuration, and test artifacts.
- Run a frozen-row structural POC first. Permit one deterministic compatibility run over an already-consumed seed subset only if all structural gates pass.
- Publish a verdict that separates structural bridge compatibility from policy quality, reward validity, baseline-floor evidence, and training readiness.
- Keep rollback at deletion of the offline bridge, its tests, and generated report artifacts; no production gameplay configuration or policy behavior is changed.
- Do not fit a model, optimize reward, consume fresh seeds, launch live gameplay, promote a policy, claim a baseline floor, or authorize formal RL training.

## Capabilities

### New Capabilities

- `noncombat-current-policy-simulator-bridge`: Offline, fail-closed Current-policy snapshot hydration, exact candidate mapping, structural validation, provenance closure, and bounded compatibility gating.

### Modified Capabilities

None.

## Impact

- Adds analysis-only Python under `analysis_scripts/`, focused tests under `tests/`, and hash-closed reports under `reports/`.
- Reads existing frozen simulator evidence and the configured `sts_lightspeed` item metadata without modifying either source.
- Reuses the exact Current `OptimizedAgent` implementation with tracking and gameplay I/O disabled; production Communication Mod configuration, live decision behavior, simulator native policy, rewards, and training code remain unchanged.
