# Full-Coverage Conservative TD

## Decision

One full-coverage epoch does not produce a stable conservative TD candidate.
No interpolation alpha passes across all three schedules, no checkpoint was
emitted, and no fresh confirmation or live gate is authorized.

## Development Result

Each replicate visited all 7,111 r1+r2 replay transitions exactly once in 56
batches. This removed cross-batch sampling omissions but did not remove unseen
instability on r3.

At `alpha=0.25`, seed 101 improved SmoothL1 but exceeded the 2% off-target
ceiling by about 0.009 percentage points. Seed 202 remained within the drift
and agreement limits but worsened SmoothL1. Seed 303 passed all conditions.
Larger alphas increased policy drift and did not create a shared passing
region.

| Alpha | Seed 101 pass | Seed 202 pass | Seed 303 pass | Stable |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | no | no | yes | no |
| 0.50 | no | no | no | no |
| 0.75 | no | no | no | no |

The mean `alpha=0.25` SmoothL1 is about `4.1244`, slightly worse than the parent
baseline `4.1228`. Full replay coverage therefore does not reveal a positive
average unseen TD effect hidden by the earlier random schedule.

## Interpretation

Stop tuning learning rate, alpha, update count, or gate thresholds on r3. The
current one-step frozen-target TD objective does not generalize reliably from
r1+r2 to r3, even without imitation and without replay omissions.

The next step should inspect reward and terminal structure across the three
immutable replay cohorts. If combat boundaries and returns are sufficiently
well formed, test a more direct n-step or Monte Carlo outcome target with the
same Q-value parent anchor. That is a new learning signal and must start with a
separate fixed design rather than another adjustment to this failed gate.
