## 1. Regression Coverage

- [ ] 1.1 Add LightSTS behavior regressions proving that frozen-parent guarded target actions are deterministic across parent and epsilon branches, preserve forced-EndTurn semantics, and do not change the executed exploration action.
- [ ] 1.2 Add trajectory-target regressions for contiguous next-action alignment, terminal rows, horizon boundaries, guarded parent-Q gathering, and raw-greedy default compatibility.
- [ ] 1.3 Add fail-fast regressions for missing or duplicate successor rows, out-of-range or masked bootstrap actions, incompatible behavior/target/parent/guard configuration, and non-finite gathered values.
- [ ] 1.4 Add report/checkpoint regressions for bootstrap policy mode, target-action identity, replacement counts, Q-gap summaries, parent binding, and unchanged simulator-only authority.

## 2. Guarded Target-Action Collection

- [ ] 2.1 Refactor guarded-parent collection to compute one deterministic frozen-parent deployment-guard target action per state independently of the epsilon behavior branch.
- [ ] 2.2 Retain current target-policy action and target guard-replacement provenance on in-memory complete-trajectory rows without changing generic replay or production checkpoint schemas.
- [ ] 2.3 Canonically summarize and hash target-policy action provenance while preserving existing source-transition identity semantics.

## 3. Guard-Aware Bootstrap Targets

- [ ] 3.1 Add explicit `frozen-parent-raw-greedy-v1` and `frozen-parent-deployment-guard-v1` bootstrap policy modes with raw-greedy as the default.
- [ ] 3.2 Align each nonterminal bootstrap state to the next contiguous target-policy action, validate its range and stored next-action mask, and gather Q from the immutable initialized parent.
- [ ] 3.3 Integrate guard-aware values with bounded n-step target transformation and bind mode, parent identity, action identity, replacement counts, and raw-max Q-gap telemetry in reports and simulator-only checkpoints.
- [ ] 3.4 Bump generated report/checkpoint/manifest schema versions and preserve all existing one-step, discounted-return, and raw-greedy n-step behavior by default.

## 4. Verification

- [ ] 4.1 Run the focused LightSTS training-smoke tests with an isolated Windows pytest basetemp.
- [ ] 4.2 Run the repository full pytest gate once, recording known unrelated or infrastructure failures separately and not repeating the gate for cleanup alone.
- [ ] 4.3 Run strict OpenSpec validation and review the scoped diff for default compatibility, production isolation, and absence of fitting or gameplay authority.
- [ ] 4.4 Record verification evidence in this task file; do not run a simulator fit, Slay the Spire, or CommunicationMod as part of implementation.
