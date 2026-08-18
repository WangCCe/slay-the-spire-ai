## Why

The current combat-RL loop spends real-game budget qualifying checkpoint changes that are only about `1e-5` away from production, while the existing `sts_lightspeed` integration hides combat behind its native SimpleAgent. A source-bound offline bridge is needed before simulator rollouts can generate useful combat candidates without treating simulator behavior as live evidence.

## What Changes

- Add an offline-only native combat environment over `sts_lightspeed` with deterministic reset, clone, snapshot, legal-action enumeration, stepping, and terminal reporting.
- Add a Python adapter that validates provenance and maps supported native combat states and actions into the existing RL v2 tensor and action-mask contract.
- Add a bounded source-only calibration runner and report that measures mapping coverage, determinism, and unsupported-state concentration before any simulator training or real-game comparison.
- Keep card-selection substates, arbitrary mid-combat live-state import, simulator training, model fitting/loading, gameplay, qualification, and promotion outside this POC.
- Preserve production r16 and make rollback consist of removing the new offline adapter and reports; no live runtime path changes.

## Capabilities

### New Capabilities
- `combat-lightspeed-bridge`: Offline native combat stepping, RL v2 mapping, and bounded bridge-calibration evidence.

### Modified Capabilities

None.

## Impact

- Adds a separate native target under `simulator_adapters/sts_lightspeed/` and Python tooling under `analysis_scripts/`.
- Reuses the local external checkout at `D:\CLionProjects\sts_lightspeed` without modifying or importing it into the CommunicationMod runtime.
- Adds focused tests and a source-only report; it does not alter gameplay policy, checkpoint bytes, training state, or production configuration.
- Success is a deterministic supported-state bridge with explicit coverage and unsupported-state accounting, not policy-quality or mechanics-equivalence proof.
