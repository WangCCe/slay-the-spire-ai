## 1. Preserve The Live Failure As Red Regressions

- [x] 1.1 Add GRID queue-contract tests for `choose`, positioned `click`, and `key` fallback transports, including response-wait and one-frame settle requirements.
- [x] 1.2 Add default-contract tests proving shared choose, click, wait, and HAND_SELECT actions retain their pre-change behavior.
- [x] 1.3 Add a parsed-state coordinator regression that reproduces the stale pre-selection frame, stale post-confirm frame, duplicate callback, and rejected-confirm command sequence.
- [x] 1.4 Run the focused regression set before implementation and record failures that demonstrate the missing GRID ordering boundaries.

## 2. Implement GRID Protocol Serialization

- [x] 2.1 Add backward-compatible readiness and response-wait options to `WaitAction`, `ClickAction`, and `ChooseAction`.
- [x] 2.2 Add backward-compatible response-wait and post-confirm-settle options to `OptionalCardSelectConfirmAction`.
- [x] 2.3 Queue a serialized selector and waiting one-frame settle action for every GRID card selected by `CardSelectAction`.
- [x] 2.4 Serialize the terminal GRID optional confirm and queue a waiting one-frame transition settle action after a sent confirm.
- [x] 2.5 Run the focused GRID/action/coordinator tests and confirm the regression emits exactly one selector, one low-level confirm, and no callback from either stale frame.

## 3. Verify And Review The Fix

- [x] 3.1 Run the full pytest suite with cache disabled and a writable repository-local basetemp.
- [x] 3.2 Run `openspec validate fix-grid-confirm-transition-race --strict` and `git diff --check`.
- [x] 3.3 Obtain independent spec-compliance and code-quality review of the behavior diff.
- [x] 3.4 Resolve every accepted review finding and rerun focused tests, full pytest, strict OpenSpec validation, and diff checks.
- [x] 3.5 Commit the reviewed GRID ordering fix as one cohesive behavior commit without staging unrelated historical reports.

## 4. Run The Fresh No-Training Qualification Retry

- [x] 4.1 Re-read the live CommunicationMod command, confirm Windows Python and no `--train`, record a new cutoff, marker/completion baselines, log sizes, trace sizes, and eligible Batch 1 report hashes.
- [x] 4.2 Launch exactly one fresh 25-game conservative eval batch and monitor markers, debug/error logs, decision trace, and sim-divergence trace at bounded intervals.
- [x] 4.3 Stop immediately on an A-class invalid command, uncaught gameplay exception, GRID/HAND_SELECT cardinality failure, or repeated demonstrated mechanics cluster; otherwise allow exactly 25 completed games.
- [x] 4.4 Produce a durable Batch 2 retry report with marker/run pairing, outcomes, command legality, HAND_SELECT/GRID ordering, lethal acknowledgement, sim-divergence classes, and promotion decision.
- [x] 4.5 Obtain independent raw-evidence review of the complete retry and correct any report inaccuracies.
- [x] 4.6 If and only if the complete retry is eligible, mark lethal-investigation task 5.5 complete and record two consecutive clean batches; otherwise preserve the failure and leave promotion blocked.
- [ ] 4.7 Commit only the reviewed qualification evidence and task-state changes; do not train, tune, create checkpoints, or archive either change during the retry.
