## 1. Pair Labels And Model Contract

- [x] 1.1 Add RED tests for tensor-aligned supported-row filtering and exact severe, neutral, and beneficial label boundaries
- [x] 1.2 Add RED tests for deterministic class-balanced sampling, within-state ranking pairs, and frozen-parent preservation
- [x] 1.3 Implement the pair classifier, evidence scoring, abstaining selection, and exact development artifact roundtrip

## 2. Calibration And Fixed Runner

- [x] 2.1 Add RED tests for seed-disjoint fit/calibration splits and the finite-sample higher 95th-percentile negative threshold
- [x] 2.2 Implement one CPU runner that fits only on fit rows, calibrates only on calibration rows, then loads the untouched holdout
- [x] 2.3 Add fixed coverage, precision, value, regret, severe-harm, legality, and provenance gates with focused runner tests

## 3. Registered Training And Evaluation

- [x] 3.1 Commit the audit, OpenSpec artifacts, source, tests, and one registration binding r16, corpus bytes, recipe, split, and output path
- [ ] 3.2 Execute the registered 4,096-update CPU fit/calibration/holdout decision once and publish its artifact and report
- [ ] 3.3 If offline conditions pass, implement, register, and execute one fresh matched LightSTS gate; otherwise record that native loading was not authorized
- [ ] 3.4 Publish the decision without retry, retraining, seed replacement, threshold change, loss change, or sweep

## 4. Verification And Closure

- [ ] 4.1 Run focused tests, strict OpenSpec validation, and exactly one timed commit gate for the complete source boundary
- [ ] 4.2 Sync and archive the change, commit the coherent evidence boundary, and push master
