# Promoted-r15 bounded successor r16

## Decision

Freeze trust weight `0.25`, interpolation `alpha=0.5` as a candidate for one
fresh promoted-r15 replay confirmation. It has no live or promotion authority.

## Training

Starting from promoted r15, the candidate used eight full-gradient SGD updates
on the consumed r11 4,096-transition replay window. The objective and fixed
trust-weight grid were unchanged. Weight `0.25` was the smallest positive value
passing every development replay. Relative L2 movement from r15 is
`6.9547e-6`.

## Cross-replay result

| Replay | Parent full-return | Candidate | Parent one-step | Candidate | Agreement | Off-target | Positive-energy End Turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.5047 | 46.4790 | 4.1318 | 4.1137 | 99.4993% | 0.5316% | 1,961 -> 1,952 |
| r8 | 50.6467 | 50.6226 | 4.3252 | 4.3090 | 99.2465% | 0.9270% | 1,634 -> 1,625 |
| r9 | 48.7360 | 48.7118 | 4.2306 | 4.2129 | 99.2661% | 0.6859% | 1,686 -> 1,674 |
| r10 | 54.6908 | 54.6735 | 4.4214 | 4.4047 | 99.3833% | 0.5270% | 1,614 -> 1,604 |

All four replays pass both loss improvements, at least `99%` parent agreement,
at most `1%` off-target disagreement, and the positive-energy End Turn guard.

The selection's metadata-only `source_commit` value has the correct
`a7fddfb1a` prefix but an incorrectly expanded suffix. The raw output is
preserved and an adjacent erratum binds the actual promotion commit; training
was not rerun and checkpoint bytes are unchanged.

## Next step

Collect one new 20-game zero-update replay under promoted r15 and evaluate this
frozen r16 candidate exactly once. Do not fit, select, or change thresholds
against that fresh cohort.
