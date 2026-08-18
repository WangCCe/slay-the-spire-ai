## Why

The combat LightSTS bridge now maps and steps supported RL v2 states deterministically, but no simulator transition has entered the existing replay/trainer path. Running a bounded disposable training smoke now provides more useful evidence than returning immediately to costly live qualification, while keeping simulator evidence separate from production.

## What Changes

- Add a source-bound simulator combat transition generator using fixed train seeds, explicit unsupported-state exclusions, and a documented native-snapshot reward subset.
- Add a CPU-only disposable RL v2 training runner that starts from a fresh deterministic initialization and never reads a production checkpoint.
- Compare the same initialized policy before and after training on disjoint fixed LightSTS evaluation seeds and publish paired technical and combat metrics.
- Save the simulator-only candidate and report under a run-scoped report directory with hashes and explicit non-production authority.
- Treat successful replay insertion, finite optimizer updates, non-zero parameter change, and complete held-out evaluation as the smoke success metric; policy uplift is reported but not required.
- Keep real-game collection, CommunicationMod, production checkpoint loading, transfer claims, qualification, and promotion outside this change.
- Rollback consists of removing the new runner, tests, and run-scoped artifacts; the production r16 path and combat policy remain unchanged.

## Capabilities

### New Capabilities
- `combat-lightspeed-training-smoke`: Bounded simulator transition generation, disposable RL v2 fitting, and paired held-out LightSTS evaluation.

### Modified Capabilities

None.

## Impact

- Adds an offline analysis runner and focused tests; reuses the existing combat LightSTS bridge, `DQNTrainerV2`, and Windows CPU Python environment.
- Produces a simulator-only checkpoint that is structurally and path-isolated from production checkpoints.
- Grants authority only for the bounded simulator smoke itself. Real-game divergence evidence remains required before any transfer, qualification, or promotion claim.
