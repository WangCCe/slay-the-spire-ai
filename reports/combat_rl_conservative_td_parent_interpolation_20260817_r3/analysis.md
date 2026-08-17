# Conservative TD Parent Interpolation

## Decision

No TD-only interpolation alpha passes across all three training schedules. No
checkpoint was emitted, and this experiment has no fresh-confirmation or live
authority.

## Development Result

Removing pairwise imitation reduced behavioral coupling but did not remove
schedule instability. Seed 101 worsened unseen SmoothL1 at the raw endpoint and
at every interpolation alpha. Seed 202 improved SmoothL1, but its smallest
`alpha=0.25` missed the 2% off-target ceiling by about 0.06 percentage points.
Seed 303 passed all TD-only conditions at `alpha=0.25`.

| Alpha | Seed 101 pass | Seed 202 pass | Seed 303 pass | Stable |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | no | no | yes | no |
| 0.50 | no | no | no | no |
| 0.75 | no | no | no | no |

The 98% parent-agreement threshold is not the primary blocker: seed 101 fails
the outcome condition itself at every alpha.

## Interpretation

Each existing schedule samples 64 independent batches of 128 from 7,111
training transitions. Sampling is without replacement inside a batch but with
replacement across batches, so a schedule is expected to expose only about 69%
of the replay. The unseen TD result is therefore sensitive to which transitions
each replicate happens to miss.

The next diagnostic should keep all loss weights and thresholds unchanged but
replace random repeated batches with one shuffled full-coverage epoch per
replicate. This tests whether complete replay coverage stabilizes TD
generalization without tuning against r3 metrics. r3 remains consumed
development data; any stable result still requires a new replay cohort.
