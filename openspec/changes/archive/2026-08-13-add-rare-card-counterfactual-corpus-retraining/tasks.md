## 1. Targeted Collection Contract

- [x] 1.1 Add regressions for target-card eligibility, non-target pass-through, per-seed limits, and unchanged default collector behavior.
- [x] 1.2 Add the optional fixed card-ID eligibility filter to the existing counterfactual partition collector.

## 2. Bounded Collection Runner

- [x] 2.1 Implement the fixed rare-card train/development/audit schedule, source/native/isolation preflight, and canonical terminal artifacts.
- [x] 2.2 Enforce support floors, all-16-card coverage, source-state disjointness, branch/censor/deadline bounds, and no audit access.

## 3. Merged Residual Training

- [x] 3.1 Restore and verify the existing corpus, merge corresponding partitions, and reject seed/source identity overlap.
- [x] 3.2 Reuse the fixed train-only residual selection and one-shot development evaluation with rare-only diagnostics and no downstream authority.

## 4. Verification And Execution

- [x] 4.1 Run focused collector/runner regressions, adjacent tests, compilation, strict OpenSpec validation, and one final full pytest gate.
- [x] 4.2 Commit and push the implementation, then publish a source-bound execution registration for the fresh fixed schedule.
- [x] 4.3 Execute the bounded native collection and residual fit once, verify canonical artifacts and production isolation, and publish the evidence.
- [x] 4.4 Decide whether a separate fresh simulator/live-shadow evaluation is justified; do not run a live action canary in this change.
