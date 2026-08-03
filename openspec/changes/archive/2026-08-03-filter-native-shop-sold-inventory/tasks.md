## 1. Planning And Isolation

- [x] 1.1 Strict-validate the accepted proposal, design, delta spec, and task boundary.
- [x] 1.2 Commit and push the planning artifacts before native execution or implementation.

## 2. Regression And Repair

- [x] 2.1 Add red source-contract regressions for exact `-1` filtering, below-`-1` rejection, nonnegative inventory preservation, and original-slot retention.
- [x] 2.2 Add bridge regressions proving sparse visible slots hydrate and map back to original candidate slots without accepting negative item prices.
- [x] 2.3 Implement the minimal card, relic, and potion snapshot filter in the native C++ adapter.
- [x] 2.4 Run focused pure-Python tests and review the scoped diff before committing and pushing the repair.

## 3. Successor Build And Bounded Smoke

- [x] 3.1 Record the frozen predecessor module hash, configure a distinct ignored API v3 build directory, and build the successor without modifying the external checkout.
- [x] 3.2 Record successor source, module, simulator, compiler, and dependency identities and prove the predecessor module hash is unchanged.
- [x] 3.3 Run only reused development-smoke seeds against the successor and verify that emitted shop item prices are nonnegative and source slots remain candidate-compatible.
- [x] 3.4 Preserve any bounded-smoke blocker exactly; do not consume a fresh formal cohort or broaden into gameplay, policy, or training changes.

## 4. Verification And Closeout

- [x] 4.1 Run focused native/bridge pytest, the partitioned repository commit gate, and strict OpenSpec validation without invoking the raw unpartitioned full suite.
- [x] 4.2 Publish a provenance-bound closeout with every live, training, OPE, qualification, loading, and promotion authority set to false.
- [x] 4.3 Sync the delta spec, archive the completed change, commit and push a clean `master`, then reassess whether a third formal native gate is justified.
