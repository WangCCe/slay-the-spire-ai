# Conservative LightSTS step screen decision

## Decision

Retain r4 and stop before confirmation. None of the preregistered intermediate alpha candidates passed all development criteria, so the reserved `98000..98063` cohort remains untouched.

## Development comparison

All five candidates completed on `217` reachable matched profiles with no unsupported state, truncation, or unexpected initialization failure.

| Candidate | Reward delta vs r4 | HP delta vs r4 | Candidate-only wins | R4-only wins | Material index regression |
|---|---:|---:|---:|---:|---|
| alpha 0.25 | -0.1424 | +0.3825 | 1 | 3 | index 6: -1.3025 |
| alpha 0.50 | -1.1531 | -0.5069 | 0 | 5 | index 6: -3.5121; index 9: -2.8267 |
| alpha 0.75 | -0.4306 | -0.4055 | 2 | 3 | index 9: -3.1168 |
| full step | +0.1789 | -0.0415 | 4 | 2 | none below -1.0 |

The full step again shows a small aggregate reward and victory gain, but still fails the HP and early-combat guardrails. Intermediate policies are not behaviorally monotonic in alpha: smaller parameter distance does not reliably retain the full-step battle improvements.

## Implication

Do not scan more alpha values and do not run the confirmation cohort. The next training attempt should constrain parent-policy action ordering during optimization, using a single predeclared existing objective rather than post-hoc parameter interpolation. Any such candidate remains simulator-only and requires new train and held-out cohorts.

