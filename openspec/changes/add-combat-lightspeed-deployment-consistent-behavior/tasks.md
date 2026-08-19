## 1. Collection Behavior

- [x] 1.1 Add configuration and selector regressions for default behavior, parent branch, exploration branch, forced EndTurn, and invalid prerequisites.
- [x] 1.2 Implement frozen-parent guarded epsilon collection while storing executed actions and keeping the parent immutable until fitting.

## 2. Evidence And Verification

- [x] 2.1 Add corpus branch/intervention telemetry and report/checkpoint configuration binding.
- [x] 2.2 Run focused smoke/comparison tests and strict OpenSpec validation without repeating the same-day full suite.

## 3. Fresh Experiment

- [ ] 3.1 Register and run one fresh guarded-parent behavior plus discounted-return training experiment.
- [ ] 3.2 Compare the frozen candidate against r16 and prior guarded candidates, publish the decision, and do not start gameplay.
