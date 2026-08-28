## 1. Regression Boundary

- [x] 1.1 Add focused coverage for exact registration, collection-report, checkpoint, and closed-R1 rejection
- [x] 1.2 Add focused coverage for correction-only balanced fitting, fixed update accounting, and parent immutability
- [x] 1.3 Add focused coverage for partitioned gate metrics, fixed eligibility checks, and exact artifact round trip

## 2. Source-Bound Runner

- [x] 2.1 Implement immutable input, recipe, checkpoint, report, and runner-binding validation
- [x] 2.2 Implement the fixed 128-update residual fit using deployment-consistent candidate-decision SMDP spans
- [x] 2.3 Implement training and validation evidence for TD, actions, gate strata, End Turn behavior, integrity, and provenance
- [x] 2.4 Implement atomic development artifact/report publication and one-shot failure semantics

## 3. Verification And Binding

- [x] 3.1 Run focused pytest with a scoped system-temp basetemp
- [x] 3.2 Run strict OpenSpec validation and the optimized commit gate once at the completed runner boundary
- [x] 3.3 Commit and push the runner without raw replay or production-compatible weights
- [x] 3.4 Publish a runner-binding supplement that preserves the registered recipe and gates exactly

## 4. One-Shot Development Result

- [x] 4.1 Execute the registered CPU development fit at most once
- [x] 4.2 Publish the immutable result, integrity evidence, and technical gate decision
- [x] 4.3 On pass, prepare a separate fresh-holdout registration; on failure, close the cohort without retry or tuning
