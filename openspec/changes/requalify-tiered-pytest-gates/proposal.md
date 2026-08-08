## Why

The routine `commit` profile now passes 4,638 tests with 18 skips but takes
1,273.82 seconds, more than four times its five-minute contract. Fresh duration
measurements show that immutable evidence replay, full lifecycle, and
independent-verifier files added after the original 2026-07-21 qualification
dominate the drift, so routine iteration again needs a measured boundary
without weakening complete validation.

## What Changes

- Requalify `commit` against the unchanged five-minute ceiling using only
  measured whole-file `full_only` additions.
- Add 13 source-only evidence, lifecycle, replay, and verifier files to the two
  existing `full_only` files; retain direct focused execution whenever one of
  those files or its owned source changes.
- Keep `commit` inclusive for every ordinary test not explicitly listed and
  keep `full` byte-for-byte equivalent to the configured complete pytest set.
- Record the 2026-08-09 attribution inputs, candidate selection, final test
  counts, exclusions, wall time, and unchanged full-profile result in a durable
  qualification report.
- Make qualification drift explicit: a later observed `commit` duration above
  five minutes invalidates the prior timing claim and requires another
  measured requalification before the bounded-feedback claim may be repeated.
- Success requires focused runner regressions, each newly excluded file to
  have fresh measured evidence, a green `commit` at or below 300 seconds, and
  one green unchanged `full` invocation. No retry is permitted merely because
  a gate is slow.
- Non-goals are changing business tests, pytest semantics, test assertions,
  production code, gameplay, RL behavior, adding parallelism, installing a
  dependency, or reducing the complete suite.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tiered-pytest-gates`: Requalify the inclusive commit boundary after measured
  runtime drift and require timing claims to remain evidence-current.

## Impact

- Updates `tests/test_gate_manifest.json`, runner contract regressions,
  `docs/testing.md`, the tiered-gate qualification report, and project
  direction.
- Does not change `scripts/run_test_gate.py`, `pytest.ini`, any test body, the
  Windows interpreter, the repository-local basetemp policy, or the `full`
  profile command.
- Rollback removes the new manifest entries and requalification documentation;
  direct pytest and the unchanged `full` profile remain available throughout.
