# Three-quarter-step End Turn trust candidate r15

## Decision

Freeze interpolation `alpha=0.75` and trust weight `0.25` for one fresh
production-r8 replay confirmation. The candidate has no live-evaluation or
promotion authority.

## Cross-cohort result

| Replay | Parent full-return | Candidate | Parent one-step | Candidate | Agreement | Off-target | Positive-energy End Turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.5518 | 46.5047 | 4.1432 | 4.1104 | 99.3046% | 0.6552% | 1,975 -> 1,961 |
| r8 | 50.6912 | 50.6467 | 4.3358 | 4.3066 | 99.5178% | 0.4077% | 1,643 -> 1,634 |
| r9 | 48.7806 | 48.7360 | 4.2415 | 4.2091 | 99.2389% | 0.7396% | 1,699 -> 1,686 |
| r10 | 54.7218 | 54.6908 | 4.4318 | 4.4019 | 99.3184% | 0.7294% | 1,624 -> 1,614 |

All four replays pass both loss improvements, at least `99%` parent agreement,
at most `1%` off-target disagreement, and the positive-energy End Turn guard.
Relative L2 movement from r8 is `1.1742e-5`, approximately 50% larger than r13
while remaining below the rejected r14 full step.

## Selection

Weight zero failed behavior guards on every replay. Trust weight `0.25` is the
smallest positive value passing all four cohorts and was selected without
changing any optimizer or eligibility threshold. The frozen checkpoint is
`rl_combat_model_return_end_turn_trust_three_quarter_step_candidate.pth`,
SHA-256
`fcef143b8387fcee27e5f29cd53283e509cc5fbd3eec5c6b77cdebbdf4645b73`.

## Next step

Collect one new 20-game, zero-update replay under production r8 and evaluate
this frozen candidate exactly once. Do not fit, select, or change interpolation
against that fresh cohort.
