## 1. Objective And Tests

- [x] 1.1 Add tensor regressions covering clipping, legal-action filtering, parent EndTurn eligibility, violations, and differentiable zero.
- [x] 1.2 Implement the top-legal-action margin loss and default-off trainer configuration with immutable-parent validation and metrics.

## 2. Runner Integration

- [x] 2.1 Bind weight, cap, objective summaries, positive eligibility, and checkpoint metadata in the LightSTS smoke CLI/report.
- [x] 2.2 Run focused trainer/smoke/comparison tests and strict OpenSpec validation without repeating the same-day full suite.

## 3. Fresh Experiment

- [ ] 3.1 Register and execute one fresh-cohort top-action guard training run with guard-aware evaluation.
- [ ] 3.2 Compare the frozen candidate against production r16 and prior guarded candidates, publish the gate decision, and do not start gameplay.
