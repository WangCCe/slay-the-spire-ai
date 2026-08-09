## Why

The newly requalified `commit` profile was invalidated by its next conforming
invocation: it reported one unrelated runtime failure after 3,638 passes and
16 skips, and required 303.60 seconds, above the fixed five-minute ceiling.
The failure also exposed a deterministic float-rounding defect in default
episode-deadline construction; that unrelated bug must be closed as a separate
direct fix before this timing boundary can be requalified.

## What Changes

- Preserve the failed invocation exactly: pytest completed in 300.24 seconds
  and the gate in 303.60 seconds; it is neither retried nor treated as source-
  audit RED evidence.
- Requalify `commit` without changing the 300-second ceiling, runner, pytest
  configuration, assertions, or complete-suite membership.
- Add the newly measured 46-test card acceptance audit file (7.39 seconds) and
  the previously measured 22-test cross-fitted runtime file (19.17 seconds) to
  `full_only`; require direct focused validation for either file or its owned
  source.
- Run one final `commit` qualification and one unchanged `full` boundary,
  record exact counts and durations, and do not tune or retry for slowness.
- Success means the separately committed deadline regression and both direct
  files are green, the final `commit` is green at or below 300 seconds, and
  unchanged `full` is green. Fresh gameplay validation is not applicable
  because no live policy behavior changes.
- Non-goals are changing the five-minute limit, adding parallelism, installing
  dependencies, weakening tests, changing RL objectives or policy, running
  training/evaluation/gameplay, or reinterpreting the pending audit verdict.
- Rollback removes the two manifest entries, manifest-contract updates,
  testing/direction/report records, and synced specification delta; direct
  pytest and unchanged `full` remain available. The separate deadline fix is
  not part of this rollback.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tiered-pytest-gates`: Replace the invalidated timing qualification with a
  fresh measured boundary while preserving inclusive-default and full-suite
  semantics.

## Impact

- Updates `tests/test_gate_manifest.json`, its exact-membership regression,
  `docs/testing.md`, project direction, and a dated requalification report.
- Does not change `scripts/run_test_gate.py`, `pytest.ini`, model checkpoints,
  consumed r2 evidence, gameplay configuration, or CommunicationMod.
- The prerequisite runtime bug fix is a separate direct behavior commit and is
  not specified, archived, or rolled back by this gate capability change.
