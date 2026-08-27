## Why

The tiered pytest gate no longer provides bounded routine feedback: a fresh conforming `commit` profile on 2026-08-27 took 1,177.80 seconds and failed 20 tests, while a raw `full` run took 2,868.18 seconds and failed 230 tests. The repository is still spending routine iteration time on a complete boundary even though the existing tiered-gate contract intended focused plus sub-five-minute commit feedback.

## What Changes

- Repair the three independent commit-gate correctness drift clusters: Reaper test-state compatibility, historical current-baseline source binding, and reachable event-semantics source identity.
- Add opt-in, machine-readable per-test and per-file timing evidence to the existing gate runner without changing selected tests, retry behavior, or default profile commands.
- Use one fresh profiling run to freeze a measured whole-file `full_only` candidate boundary before one final commit requalification; do not tune exclusions after seeing the qualification result.
- Clarify that narrow coherent changes use focused tests plus `commit`, while `full` remains the complete release/phase-close boundary. Timing-only telemetry changes that prove selection-argument equivalence do not independently require another complete run.
- Record the invalidated 2026-08-09 qualification, the 2026-08-27 profiling evidence, the frozen replacement boundary, and the final one-shot result.
- Success metric: the final frozen `commit` profile passes and completes in at most 300 seconds on `D:\anaconda\envs\stsai\python.exe`; if it fails or exceeds the limit, preserve that result and leave timing/correctness unqualified.
- Non-goals: weakening or deleting tests, changing gameplay or RL behavior, making `full` exclude tests, automatically retrying, parallelizing pytest, starting Slay the Spire or CommunicationMod, or running training.
- Rollback boundary: remove the new telemetry option, manifest additions, documentation/report updates, and the three narrow drift repairs; the current five named profiles and unchanged complete pytest command remain available.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tiered-pytest-gates`: Add auditable timing telemetry, repair the invalidated commit qualification workflow, and narrow mandatory complete-suite use to boundaries where it adds selection or release evidence.

## Impact

- Affected code: `scripts/run_test_gate.py`, focused runner tests, the gate manifest, three narrowly owned correctness fixtures/contracts, testing documentation, and qualification reports.
- Affected workflow: routine OpenSpec verification should invoke focused coverage plus the registered `commit` profile instead of raw full pytest unless the change reaches an explicit complete boundary.
- Unaffected systems: production checkpoints, live gameplay, CommunicationMod, LightSTS fitting, RL training, test bodies outside the three observed drift clusters, and the `full` profile's inclusive selection.
