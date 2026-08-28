# Pytest Node-Deselect Qualification - 2026-08-28

## Decision

The schema-v2 routine `commit` profile is qualified. It retains all ordinary
tests from the affected files while deselecting 21 measured fresh-process
import-isolation nodes. The frozen boundary passed in 171.75 runner seconds,
well below both the 240-second change target and the five-minute contract.

This report changes test workflow only. It grants no gameplay, model,
simulator, training, evaluation, promotion, or policy-quality claim.

## Profiling Evidence

The source profile ran before candidate selection:

- Result: 4,195 passed, 26 skipped.
- Pytest time: 271.65 seconds.
- Runner time: 274.770631 seconds.
- Attributed testcases: 4,221 across 198 files.
- Selected nodes: exactly 21 isolated-process import checks, each at least 4.5
  seconds and 103.649 aggregate testcase seconds.
- Evidence: `reports/pytest_gate_commit_profile_20260828_r2.json`.
- Evidence SHA-256:
  `81141395d0568e1cb8df033491d6f559178a32289a7cf8d5b11a9ab26920b67e`.

The candidate list was frozen before qualification. No node was added or
removed in response to the final result.

## Qualification

The boundary was committed and pushed as
`1c5a5c5ec` before the single final invocation:

- Result: 4,182 passed, 26 skipped, 21 deselected; zero failures and errors.
- Pytest time: 168.62 seconds.
- Runner time: 171.753911 seconds.
- Target margin: 68.246089 seconds below 240 seconds.
- Contract margin: 128.246089 seconds below five minutes.
- Evidence: `reports/pytest_gate_commit_qualification_20260828_r2.json`.
- Evidence SHA-256:
  `116c6a2d225806268ea920b206f2681cb48e65ffa0d3fb252939e797a4d6d850`.

Runner-focused validation passed 52 tests. Strict OpenSpec validation passed
132 items. The repository-manifest `full --dry-run` emitted neither
`--ignore` nor `--deselect`.

## Full Boundary

Raw `full` remains inclusive and unchanged. Its current recorded baseline is
the 2026-08-27 invocation: 6,423 passed, 28 skipped, 230 failed in 2,868.18
pytest seconds. It was not repeated solely for commit-selection equivalence,
because runner regressions and the dry-run prove the complete argv is
unchanged. Raw `full` remains required at a real phase close, release, broad
cross-domain refactor, or any change that can alter its configured test
universe.

## Operating Rule

New tests remain in `commit` by default. A `commit_deselect` entry requires
fresh node timing and a rationale. Changing a deselected node or the source
entrypoint it imports or executes requires direct focused validation before
`commit`; `full` always includes it. Rollback removes `commit_deselect`,
restores manifest schema version 1, and changes no test or production code.
