## Why

The routine `commit` gate has regressed from a qualified 229.33 seconds to a
recent 318.74 seconds as isolated-import tests accumulated inside otherwise
fast files. A fresh profiled pass took 274.77 seconds, and 23 isolated-process
nodes accounted for 96.66 seconds of its 100 slowest tests, leaving too little
margin for useful iteration without justifying whole-file exclusions.

## What Changes

- Extend the gate manifest with measured, reasoned node-level entries that are
  deselected only from the default-minus-full-only `commit` profile.
- Freeze the initial entries from the 2026-08-28 timing report before final
  qualification; new tests remain included by default.
- Keep direct focused pytest and the inclusive `full` profile unchanged.
- Require one runner-focused validation and one frozen-boundary qualification
  at no more than 240 seconds including orchestration.
- Do not add parallel pytest, caching, automatic timing-based mutation, skip
  markers, test deletion, gameplay, or training as part of this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tiered-pytest-gates`: Allow explicit measured node-level commit exclusions
  without weakening their containing files or the inclusive full boundary.

## Impact

This changes `scripts/run_test_gate.py`, `tests/test_gate_manifest.json`, its
runner regressions, the testing documentation, and the tiered-gate contract.
No production AI, simulator, gameplay, model, or dependency behavior changes.
Rollback is removal of the node entries and schema support, restoring the
current whole-file-only commit selection.
