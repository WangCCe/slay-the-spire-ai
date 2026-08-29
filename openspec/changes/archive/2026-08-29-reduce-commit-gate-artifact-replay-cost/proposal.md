## Why

The latest conforming `commit` gate passed 4,468 outcomes in 209.529 seconds,
leaving only 30.471 seconds below the previous 240-second qualification target.
Six measured artifact-replay and bound-integration nodes account for 24.832
seconds while their containing files also provide fast ordinary regressions
that should remain in routine commits.

## What Changes

- Freeze the six measured node candidates from
  `reports/test_gate_timing_action_relative_successor_delta_ablation_20260829.json`
  before changing selection.
- Deselect only those nodes from `commit`, preserving every other test in the
  containing files and keeping direct pytest, domain profiles, and `full`
  inclusive.
- Record explicit source ownership so changes to an excluded node or its owned
  source require direct focused validation before `commit`.
- Run runner-focused validation, strict OpenSpec validation, and exactly one
  frozen timing-enabled `commit` qualification with a target of at most 190
  seconds.
- Roll back all six entries together if manifest correctness changes or the
  frozen qualification exceeds 190 seconds; preserve a slow or failed result
  without retrying or expanding the candidate set.
- Do not change test assertions, production code, simulator behavior, gameplay,
  models, training, pytest parallelism, subprocess pooling, or cache behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tiered-pytest-gates`: Requalify the routine commit boundary with six
  measured node-level artifact-replay exclusions and explicit focused-test
  ownership while preserving the inclusive full boundary.

## Impact

This changes only `tests/test_gate_manifest.json`, gate-selection regressions,
testing documentation, the tiered-gate contract, and immutable timing evidence.
The measured upper-bound saving is 24.832 seconds, corresponding to an expected
209.529-to-184.697-second boundary before machine-load variance. No dependency,
CommunicationMod, gameplay, native module, model, or training surface changes.
