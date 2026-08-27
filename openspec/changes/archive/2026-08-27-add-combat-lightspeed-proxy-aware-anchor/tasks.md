## 1. Regression Coverage

- [x] 1.1 Add RL v2 replay regressions for default-false storage, mixed v2 round trips, and v1 all-false compatibility.
- [x] 1.2 Add trainer regressions for mixed frozen-parent and executed-action anchor labels, invalid override masks, zero-weight telemetry, and immutable parent parameters.
- [x] 1.3 Add LightSTS runner regressions for replacement-only provenance, incompatible mode validation, preservation through target preparation, and report telemetry.

## 2. Replay And Trainer Implementation

- [x] 2.1 Extend `ReplayBufferV2` and trainer transition insertion with backward-compatible executed-action anchor override metadata.
- [x] 2.2 Select mixed anchor targets in `RLTrainerV2.train_step`, enforce mask validity, and expose latest override usage.

## 3. LightSTS Integration

- [x] 3.1 Add explicit anchor label mode configuration and fail-fast compatibility validation to the LightSTS runner.
- [x] 3.2 Propagate confirmed guard-replacement provenance through collection, target preparation, balancing, and replay insertion.
- [x] 3.3 Bind label mode and override usage in report, checkpoint, and candidate source evidence without changing simulator authority.

## 4. Verification

- [x] 4.1 Run focused RL v2 transition and LightSTS smoke tests with an isolated Windows pytest basetemp.
- [x] 4.2 Run the repository full pytest gate once, recording pre-existing or infrastructure failures separately from regressions.
- [x] 4.3 Run strict OpenSpec validation and review the scoped diff for legacy compatibility and authority boundaries.

## Verification Record

- Focused gate: `103 passed, 5 skipped` for the complete RL v2 transition and LightSTS smoke test files.
- Full gate: `6613 passed, 28 skipped, 32 failed` in `47:44`; failures were confined to untouched Reaper fixture, historical noncombat source/AST identity, reachable-event semantics, and live CommunicationMod binding checks.
- Strict OpenSpec validation passed; `git diff --check` reported no whitespace errors.
