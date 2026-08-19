## 1. Objective Regression Coverage

- [x] 1.1 Add tensor-level regressions for card-action filtering, positive-margin clipping, candidate ranking violations, and differentiable zero eligibility.
- [x] 1.2 Add trainer configuration regressions for default compatibility, invalid weight/cap, immutable parent requirements, and separate objective metrics.

## 2. Trainer And Runner Integration

- [x] 2.1 Implement the frozen-parent best-card-versus-best-alternative margin loss in RL v2 trainer and compose it with existing objectives.
- [x] 2.2 Add default-off smoke/CLI configuration, loss summaries, checkpoint source binding, and positive-eligibility blocker.

## 3. Verification And Experiment

- [x] 3.1 Run focused trainer and LightSTS smoke tests plus strict OpenSpec validation; rely on the same-day full-suite baseline unless focused failures indicate broader impact.
- [x] 3.2 Register and run one same-cohort card-ranking objective ablation with guard-aware evaluation and immutable production r16 shadow parent.
- [x] 3.3 Compare the frozen candidate against production r16 shadow and the prior guarded control, publish the go/no-go conclusion, and do not start gameplay.
