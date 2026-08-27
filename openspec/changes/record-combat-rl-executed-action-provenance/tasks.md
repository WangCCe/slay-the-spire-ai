## 1. Regression Coverage

- [x] 1.1 Add a failing regression proving an unchanged direct RL action stores an override value of false.
- [x] 1.2 Add failing regressions proving a changed same-state action and a legal no-proposal fallback action store override values of true.
- [x] 1.3 Cover illegal or non-combat emitted actions and replay checkpoint round-trip preservation.

## 2. Provenance Binding

- [x] 2.1 Carry executed-action anchor provenance on `PendingTransition` and pass it into replay storage.
- [x] 2.2 Derive provenance at `commit_executed_action()` from encoded proposal/emitted action identity while preserving current discard and legality behavior.
- [x] 2.3 Confirm no action-selection, CommunicationMod command, reward, or checkpoint-weight behavior changes.

## 3. Verification And Evidence

- [x] 3.1 Run focused RL v2 transition and combat-RL guard tests with an isolated Windows pytest temp scope.
- [x] 3.2 Run the qualified `commit` test gate; use the configured inclusive `full` boundary only at phase close or document the governing full-baseline blocker per `docs/testing.md`.
- [ ] 3.3 Commit and push the implementation before fresh gameplay evidence collection.
- [ ] 3.4 Register and collect one bounded fresh zero-update production-r16 replay cohort, retaining `.run`, decision trace, guard logs, and checkpoint evidence without training.
- [ ] 3.5 Publish a report reconciling nonzero legal override rows with direct, replacement, and takeover evidence, then make a separate training go/no-go decision.
