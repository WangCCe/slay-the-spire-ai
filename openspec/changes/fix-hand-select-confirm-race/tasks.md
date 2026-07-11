## 1. Evidence And Design

- [x] 1.1 Capture the fresh HAND_SELECT duplicate-confirm failure from the Batch 1 retry logs and decision trace.
- [x] 1.2 Trace the failure through `CardSelectAction`, `OptionalCardSelectConfirmAction`, and coordinator deferred callbacks.
- [x] 1.3 Identify `ae01dcd0` as the change that removed terminal HAND_SELECT ready serialization.
- [x] 1.4 Validate this OPSX change in strict mode.

## 2. Regression Tests

- [x] 2.1 Update the HAND_SELECT queue-contract test to require readiness on the terminal optional confirm.
- [x] 2.2 Add a failing coordinator regression for the final-key response arriving before terminal confirmation.
- [x] 2.3 Assert the regression emits no early confirm, invokes no stale agent callback, and emits exactly one confirm after the final-key response.
- [x] 2.4 Preserve a focused assertion that GRID optional confirmation remains non-blocking.

## 3. Minimal Fix

- [x] 3.1 Restore `requires_game_ready=True` for the terminal optional confirm on HAND_SELECT only.
- [x] 3.2 Keep GRID confirmation timing and all agent selection policies unchanged.
- [x] 3.3 Run the red regressions to green without coordinator state-machine changes.

## 4. Verification And Review

- [x] 4.1 Run focused card-select, deferred-callback, and HAND_SELECT agent tests with an isolated writable basetemp.
- [x] 4.2 Run full pytest with cache disabled and an isolated writable basetemp.
- [x] 4.3 Run strict OPSX validation after updating completed task state.
- [x] 4.4 Commit the regression-backed behavior fix as one cohesive commit.
- [x] 4.5 Obtain independent review of the implementation, tests, scope, and verification evidence.

## 5. Live Validation

- [ ] 5.1 Run a fresh conservative 25-game Batch 1 retry without training.
- [ ] 5.2 Confirm zero HAND_SELECT duplicate confirmations, invalid commands, GRID cardinality exceptions, and new uncaught gameplay exceptions.
- [ ] 5.3 Inspect fresh decision and sim-divergence evidence for A-class failures.
- [ ] 5.4 Commit a separate retry report while preserving both earlier failed reports.
