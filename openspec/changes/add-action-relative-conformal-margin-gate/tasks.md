## 1. Split And Calibration Contract

- [x] 1.1 Add RED tests for exact seed-level fit/calibration splitting, tensor alignment, family support, and exclusion of calibration rows from bootstrap fitting
- [x] 1.2 Add RED tests for finite-sample higher-quantile corrections, zero clamping, card/potion family routing, calibrated abstention, and unsupported-action rejection
- [x] 1.3 Implement the conformal wrapper and exact source-bound artifact roundtrip around a refitted five-member ensemble

## 2. Bounded Fit And Holdout

- [x] 2.1 Implement one fixed CPU runner that fits only on fit rows, calibrates only on calibration rows, then loads and evaluates the untouched holdout
- [x] 2.2 Add fixed offline conditions for coverage, precision, value, regret, severe-harm, legality, and provenance with focused runner tests
- [x] 2.3 Commit source and one registration binding r16, corpus bytes, baseline evidence, audit evidence, recipe, split, and output path
- [x] 2.4 Execute r1 once and record its pre-holdout tensor/metadata alignment failure with no artifact or quality decision
- [x] 2.5 Add a regression and minimal tensor-aligned supported-row repair, then commit one replacement source snapshot
- [ ] 2.6 Register and execute one r2 replacement with unchanged recipe, inputs, seeds, alpha, threshold, and gates

## 3. Conditional Fresh LightSTS Gate

- [ ] 3.1 If offline conditions pass, implement and test one source-bound matched LightSTS runner on a new fixed seed interval
- [ ] 3.2 If offline conditions pass, commit and execute one evaluation registration; otherwise record that native loading was not authorized
- [ ] 3.3 Publish the decision without retry, retraining, seed replacement, alpha change, family change, threshold change, or sweep

## 4. Verification And Closure

- [ ] 4.1 Run focused tests, strict OpenSpec validation, and exactly one timed commit gate for the complete source boundary
- [ ] 4.2 Sync and archive the change, commit the coherent evidence boundary, and push master
