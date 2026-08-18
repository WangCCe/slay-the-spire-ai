# Promoted-r16 bounded successor r19

## Decision

Freeze trust weight `0.25`, interpolation `alpha=0.5` as a candidate for one
fresh promoted-r16 replay confirmation. It has no live or promotion authority.

## Training

Starting from promoted r16, the candidate used eight full-gradient SGD updates
on the consumed r14 3,765-transition replay. The objective and fixed
trust-weight grid were unchanged. Weight `0.25` was the smallest positive value
passing every development replay. Relative L2 movement from r16 is
`6.8058e-6`.

## Cross-replay result

| Replay | Parent full-return | Candidate | Parent one-step | Candidate | Agreement | Off-target | Positive-energy End Turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.4790 | 46.4540 | 4.12461 | 4.10694 | 99.3880% | 0.6463% | 1,952 -> 1,942 |
| r8 | 50.6226 | 50.5990 | 4.31862 | 4.30283 | 99.4575% | 0.4611% | 1,625 -> 1,615 |
| r9 | 48.7118 | 48.6881 | 4.22394 | 4.20665 | 99.5107% | 0.6332% | 1,674 -> 1,669 |
| r10 | 54.6735 | 54.6566 | 4.41489 | 4.39855 | 99.3509% | 0.6540% | 1,604 -> 1,594 |
| r11 | 43.1948 | 43.1731 | 3.88942 | 3.87589 | 99.4385% | 0.5939% | 1,994 -> 1,986 |
| r12 | 44.2993 | 44.2752 | 4.16564 | 4.14874 | 99.4306% | 0.4675% | 1,804 -> 1,792 |
| r13 | 40.4774 | 40.4515 | 4.01494 | 4.00001 | 99.3896% | 0.6686% | 2,047 -> 2,036 |

All seven replays pass both loss improvements, at least `99%` parent agreement,
at most `1%` off-target disagreement, and the positive-energy End Turn guard.
The frozen checkpoint SHA-256 is
`ca40182ca9f8da185c4d722380e451433294d3f6f14b8b2d5840258431dc31a2`.

## Fresh confirmation

Production r16 completed the registered r15 cohort naturally with 3,920
complete, untruncated transitions. Frozen r19 improved full-return SmoothL1
from `42.1685371` to `42.1447563` and one-step SmoothL1 from `4.0497952` to
`4.0337324`, retained `99.5153%` parent agreement, limited off-target
disagreement to `0.3619%`, and reduced positive-energy End Turns from 2,043 to
2,031.

## Next step

The registered matched live cohort was externally interrupted during candidate
game 16 after 15 completed games; the parent arm was not started. The cohort is
closed without qualification, rejection, or promotion. Retain r16 and reassess
simulator and offline candidate generation before deciding whether a separate
new r19 gate is worth the real-game cost. Do not start r20 mechanically.
