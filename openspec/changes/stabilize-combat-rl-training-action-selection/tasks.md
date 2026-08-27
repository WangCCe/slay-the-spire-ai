## 1. Regression Coverage

- [x] 1.1 Add a failing regression proving a train-mode online network observes eval mode during greedy action selection and is restored before return.
- [x] 1.2 Add failing regressions for exception-safe train-mode restoration and preservation of an existing eval mode.
- [x] 1.3 Prove repeated zero-epsilon greedy selections are deterministic for a Dropout-bearing network while epsilon exploration remains unchanged.

## 2. Action-Selection Mode Boundary

- [x] 2.1 Capture the online network's prior module mode, select the greedy action under eval semantics, and restore the exact prior mode in `finally`.
- [x] 2.2 Confirm optimizer updates, target-network mode, action masks, weights, and checkpoint serialization are unchanged.

## 3. Verification And Fresh Evidence

- [x] 3.1 Run focused RL v2 trainer/action-selection tests with an isolated Windows pytest temp scope.
- [x] 3.2 Run the qualified `commit` test gate; reserve the raw inclusive `full` gate for phase close under the documented baseline policy.
- [x] 3.3 Commit and push the implementation before fresh gameplay evidence collection.
- [ ] 3.4 Register and collect one bounded fresh zero-update production-r16 provenance cohort on unused seeds.
- [ ] 3.5 Publish a report requiring 100% direct unmarked eval-parent agreement, legal nonzero overrides, exact trace reconciliation, and zero optimizer updates before approving separate training.
