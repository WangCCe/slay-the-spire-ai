# Promoted-r16 bounded successor r18

## Decision

Freeze trust weight `0.25`, interpolation `alpha=0.5` as a candidate for one
fresh promoted-r16 replay confirmation. It has no live or promotion authority.

## Training

Starting from promoted r16, the candidate used eight full-gradient SGD updates
on the consumed r13 4,096-transition stored replay. The objective and fixed
trust-weight grid were unchanged. Weight `0.25` was the smallest positive value
passing every development replay. Relative L2 movement from r16 is
`7.6057e-6`.

## Cross-replay result

| Replay | Parent full-return | Candidate | Parent one-step | Candidate | Agreement | Off-target | Positive-energy End Turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.4790 | 46.4486 | 4.12461 | 4.10343 | 99.3046% | 0.7638% | 1,952 -> 1,942 |
| r8 | 50.6226 | 50.5940 | 4.31862 | 4.29979 | 99.4876% | 0.4035% | 1,625 -> 1,615 |
| r9 | 48.7118 | 48.6831 | 4.22394 | 4.20317 | 99.4292% | 0.7793% | 1,674 -> 1,669 |
| r10 | 54.6735 | 54.6535 | 4.41489 | 4.39555 | 99.4158% | 0.5886% | 1,604 -> 1,595 |
| r11 | 43.1948 | 43.1683 | 3.88942 | 3.87323 | 99.2920% | 0.8680% | 1,994 -> 1,984 |
| r12 | 44.2993 | 44.2699 | 4.16564 | 4.14532 | 99.4577% | 0.4675% | 1,804 -> 1,794 |

All six replays pass both loss improvements, at least `99%` parent agreement,
at most `1%` off-target disagreement, and the positive-energy End Turn guard.
The frozen checkpoint SHA-256 is
`0e2bd207f96a7640f2c379d5934d7ef46ef952f9aecc533a36015d035f2b8b06`.

## Fresh confirmation

Production r16 completed the registered r14 cohort naturally with 3,765
complete, untruncated transitions. Frozen r18 improved full-return SmoothL1
from `49.9499817` to `49.9241028` and one-step SmoothL1 from `4.1513276` to
`4.1313233`, retained `99.5219%` parent agreement, limited off-target
disagreement to `0.3850%`, and reduced positive-energy End Turns from 1,988 to
1,977.

## Live gate

The registered 20-pair matched live gate rejected r18. Candidate and parent
floors were identical on 19 pairs; on the remaining pair r18 reached floor 27
and r16 reached floor 33. R18 therefore lost paired wins 0 to 1, trailed total
floors 516 to 522, and reached the Act 2 boss six times versus seven. Both arms
entered Act 2 13 times and Act 3 once, neither won, and both completed without
runtime failure.

## Next step

Retain production r16. Do not rerun or tune r18 against the consumed live
cohort. R14 may be used only as fitting or development evidence for a new
frozen successor with a separately registered fresh confirmation.
