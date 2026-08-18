# Promoted-r16 bounded successor r17

## Decision

Freeze trust weight `0.25`, interpolation `alpha=0.5` as a candidate for one
fresh promoted-r16 replay confirmation. It has no live or promotion authority.

## Training

Starting from promoted r16, the candidate used eight full-gradient SGD updates
on the consumed r12 3,688-transition replay. The objective and fixed
trust-weight grid were unchanged. Weight `0.25` was the smallest positive value
passing every development replay. Relative L2 movement from r16 is
`7.5350e-6`.

## Cross-replay result

| Replay | Parent full-return | Candidate | Parent one-step | Candidate | Agreement | Off-target | Positive-energy End Turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.4790 | 46.4512 | 4.12461 | 4.10505 | 99.2211% | 0.8226% | 1,952 -> 1,939 |
| r8 | 50.6226 | 50.5966 | 4.31862 | 4.30132 | 99.3972% | 0.4611% | 1,625 -> 1,613 |
| r9 | 48.7118 | 48.6858 | 4.22394 | 4.20502 | 99.3477% | 0.8281% | 1,674 -> 1,667 |
| r10 | 54.6735 | 54.6550 | 4.41489 | 4.39711 | 99.2210% | 0.7848% | 1,604 -> 1,592 |
| r11 | 43.1948 | 43.1708 | 3.88942 | 3.87465 | 99.2676% | 0.7766% | 1,994 -> 1,981 |

All five replays pass both loss improvements, at least `99%` parent agreement,
at most `1%` off-target disagreement, and the positive-energy End Turn guard.
The frozen checkpoint SHA-256 is
`bb863ec1e6e2f87df8b12649d6bec353bd09b5ff44646e1a0ee600ccc8a2a382`.

## Fresh confirmation

Production r16 completed the registered r13 cohort naturally. Its terminal
checkpoint stored 4,096 of 4,137 source transitions under the fixed replay
serialization limit. Frozen r17 improved full-return SmoothL1 from `40.4774399`
to `40.4488678` and one-step SmoothL1 from `4.0149384` to `3.9985926`, retained
`99.3164%` parent agreement, limited off-target disagreement to `0.7163%`, and
reduced positive-energy End Turns from 2,047 to 2,034.

The raw confirmation has a metadata-only source-commit suffix error. Its
adjacent erratum binds the actual registration commit; the one allowed
evaluation was not rerun.

## Next step

Register one new 20-pair matched live gate comparing frozen r17 with production
r16. The fresh replay grants no automatic promotion authority.
