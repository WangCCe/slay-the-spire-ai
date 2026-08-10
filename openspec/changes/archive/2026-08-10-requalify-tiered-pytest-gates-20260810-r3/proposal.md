## Why

The qualified five-minute `commit` boundary is structurally invalid: an
unchanged-profile run already passed in 515.35 seconds, and the current tree
passed 3,918 tests with 16 skips in 528.59 seconds. The runner, manifest, and
pytest configuration have not drifted; post-qualification card-acceptance test
growth now makes routine feedback an iteration bottleneck.

## What Changes

- Preserve the current correctness-green/timing-invalid evidence, including the
  interrupted 424.37-second observation and completed 528.59-second gate.
- Freeze exactly the seven ordinary test files added after qualification and
  not already `full_only` as the complete r3 attribution/candidate set:
  `test_audit_card_acceptance_objective_interventions.py`,
  `test_noncombat_card_acceptance_empirical_successor_control.py`,
  `test_noncombat_card_acceptance_empirical_successor_runtime.py`,
  `test_noncombat_card_acceptance_empirical_successor_seed_inventory.py`,
  `test_noncombat_card_acceptance_empirical_successor_verifier.py`,
  `test_noncombat_card_acceptance_objective.py`, and
  `test_noncombat_card_acceptance_policy.py`.
- Run that exact seven-file set once with `--durations=50`, xUnit1 JUnit XML,
  and total-phase durations; preserve its result and aggregate every testcase
  duration by its explicit `file` attribute.
- Select a file only when its aggregate measured duration is at least 5.00
  seconds. Require the selected aggregate to explain at least 265.70 seconds,
  restoring the prior 37.11-second predicted margin; otherwise close as
  unqualified without changing the manifest.
- Add exactly the deterministically selected files to `full_only`; require
  direct affected-file or stricter focused coverage whenever their owned source
  changes. Do not change the runner, pytest configuration, assertions, five-
  minute ceiling, or complete-suite membership.
- Update exact-membership tests and testing documentation, then run focused
  manifest/runner checks. Freeze the gate-affecting file hashes, run one final
  `commit` qualification and one unchanged `full` boundary, and verify those
  hashes before and after both runs and before the selection commit. Do not
  retry, tune, or expand the candidate set after either final result.
- Success is a green `commit` at or below 300 seconds plus a green unchanged
  `full`, with exact counts/durations and ownership rules recorded. A slow or
  failed result remains terminal evidence and leaves timing unqualified.
- Non-goals are parallelism, dependency installation, test weakening, source
  behavior changes, inventory construction, RL training/evaluation, gameplay,
  CommunicationMod, qualification/promotion of a policy, or r3 authority.
- Rollback removes only the selected manifest entries, exact-membership updates,
  testing docs, report, and synced archived change; direct tests and unchanged
  `full` remain available.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tiered-pytest-gates`: Requalify bounded commit feedback from a frozen,
  measured seven-file candidate set and preregistered per-file selection rule
  while preserving direct ownership and complete-suite coverage.

## Impact

The change affects `tests/test_gate_manifest.json`,
`tests/test_run_test_gate.py`, `docs/testing.md`, a dated qualification report,
and OpenSpec records. It changes no production, simulator, RL, model,
checkpoint, gameplay, or CommunicationMod code.
