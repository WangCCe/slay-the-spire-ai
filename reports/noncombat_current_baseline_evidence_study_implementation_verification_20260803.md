# Current Baseline Evidence Study Implementation Verification

Date: 2026-08-03

## Scope

This verification covers source and tests for the fixed post-repair Current
baseline study only. It does not authorize or perform native loading,
environment construction, study-seed execution, gameplay, model fitting,
reward work, OPE, training, qualification, policy loading, or promotion.

## Contract Regressions

- The initial focused run failed during collection with
  `ModuleNotFoundError` for the absent study runner.
- The completed focused suite passed 57 tests. It covers exact registration
  and authorization identity, Current/control isolation, production-shaped
  candidates, source/action hashes, terminal and exact Courier rows,
  unexpected failures, replay identity, resource bounds, canary and holdout
  thresholds, deterministic 10,000-resample bootstrap, one-shot journal
  behavior, canonical publication, and no-native reconstruction.
- The adjacent Current bridge, consumed diagnostic, adapter, event semantics,
  shop, and metadata suite passed 245 tests with 5 expected skips.
- The seed-inventory owner module passed 17 additional focused tests after the
  managed preregistration-path exclusions were added.

## Static And OpenSpec Verification

- `py_compile` passed for the new runner, its tests, and the seed inventory
  source.
- `git diff --check` passed before staging.
- The active change passed strict validation.
- Global strict OpenSpec validation passed all 62 items.

## Consumed Diagnostic Preservation

In a fresh no-bytecode process, both consumed diagnostic registrations were
loaded and their canonical artifacts were recomputed byte-for-byte:

| Profile | Preserved verdict | Source-bound execution status |
|---|---|---|
| v1 | `current_bridge_diagnostic_failed` | blocked by `implementation_source_hash_mismatch` |
| r2 | `current_bridge_diagnostic_failed` | blocked by `implementation_source_hash_mismatch` |

The verifier replaced `load_native_module` with a function that raises on any
call and confirmed `sts_lightspeed_noncombat_adapter` was absent from
`sys.modules` before and after both checks. The implementation verification
therefore used no native module, constructed no native environment, and did
not execute a study seed against the simulator.

## Repository Commit Gate

The registered partitioned `commit` gate passed 3,664 tests with 11 expected
skips. The final post-review rerun completed pytest in 268.75 seconds and the
complete gate in 271.96 seconds. No unregistered raw full-suite run was used.
