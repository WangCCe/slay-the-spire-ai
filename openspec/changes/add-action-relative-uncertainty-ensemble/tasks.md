## 1. Ensemble Contract

- [x] 1.1 Add RED tests for five-member scoring, sample-standard-deviation LCB selection, abstention, forbidden actions, and shared-parent freezing
- [x] 1.2 Implement the development-only ensemble model and exact source-bound artifact roundtrip
- [x] 1.3 Add RED tests for deterministic bootstrap identities, fixed holdout conditions, and registration validation

## 2. Bounded Fit And Holdout

- [x] 2.1 Implement the fixed five-member bootstrap fit and untouched-holdout evaluator with member, uncertainty, value, regret, legality, and latency telemetry
- [ ] 2.2 Create and validate a committed source/input-bound fit registration using the existing r16 parent and train/evaluation corpora
- [ ] 2.3 Execute the registered CPU fit once and publish its development artifact, report, and offline go/no-go decision

## 3. Conditional Fresh LightSTS Gate

- [ ] 3.1 If offline conditions pass, add focused tests and a source-bound runner for one new seed-disjoint matched LightSTS comparison
- [ ] 3.2 If offline conditions pass, commit and execute one fixed evaluation registration; otherwise record that simulator execution was not authorized
- [ ] 3.3 Publish the fresh simulator decision without retry, retraining, seed replacement, or parameter sweep

## 4. Verification And Closure

- [ ] 4.1 Run focused ensemble and runner tests plus strict OpenSpec validation
- [ ] 4.2 Run exactly one timed commit gate for the complete behavior-class boundary
- [ ] 4.3 Sync and archive the completed OpenSpec change, commit the coherent evidence boundary, and push master
