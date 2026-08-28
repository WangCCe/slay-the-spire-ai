## Why

The action-relative r1 live shadow ran on the production agent's CUDA device
and recorded p50/p95 latency of `22.631ms`/`41.090ms`, while an exact dual-device
POC over 256 measured rows found CPU p50/p95 of `2.232ms`/`3.432ms` versus CUDA
`12.957ms`/`16.313ms`. CPU and CUDA produced zero action, gate, or telemetry
mismatches and a maximum prediction delta of `2.145768e-6`, so device placement,
not repeated parent computation, is the supported latency cause.

## What Changes

- Add a schema-v2 action-relative live registration that explicitly binds
  `inference_device: cpu` while retaining schema-v1 read compatibility.
- Build a frozen CPU mirror for the shadow residual without moving or mutating
  the production-r16 CUDA parent, and verify identical parent state hashes.
- Preserve the dual-device POC as diagnostic-only evidence and add initialization,
  device, parent-neutrality, prediction, and latency regressions.
- Run one source-bound five-game behavior-neutral CPU shadow under the unchanged
  512-decision, 100-eligible, zero-error, and 20ms p95 readiness conditions.
- Do not retrain, change scorer/threshold/artifact, alter production action
  selection, grant candidate authority, or relax any live readiness gate.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-action-relative-live-shadow`: Allow an explicitly registered CPU
  inference mirror that preserves the production parent and behavior-neutral
  shadow contract.

## Impact

Affected code is limited to the action-relative live registration/initializer,
its tests and readiness evidence, a compact dual-device POC report, and one new
live registration. Production gameplay remains on CUDA and executes the exact
r16 action. Rollback removes the CPU registration and restores same-device
schema-v1 shadow initialization; no checkpoint or persistent config migration
is required.
