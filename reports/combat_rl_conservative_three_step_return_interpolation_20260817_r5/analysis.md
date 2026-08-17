# Conservative three-step return interpolation r5

## Decision

**No-go.** The experiment did not produce a checkpoint and does not authorize
fresh replay collection, live evaluation, or a production-policy change.

## Result

The promoted parent had development three-step SmoothL1 `8.387680`. Every
trained interpolation was worse:

| seed | alpha 0.25 | alpha 0.50 | alpha 0.75 |
| --- | ---: | ---: | ---: |
| 101 | 8.388603 | 8.390079 | 8.392253 |
| 202 | 8.396197 | 8.406265 | 8.417738 |
| 303 | 8.389775 | 8.392463 | 8.395747 |

At alpha `0.25`, parent-action agreement remained above `0.98` for all three
replicates, but seed 101 exceeded the `0.02` off-target disagreement limit and
none improved the three-step objective. Larger alphas increased both policy
drift and development error. The final seed was therefore not fitted and no
checkpoint was written.

## Interpretation

Replacing the one-step target with a fixed three-step return did not resolve
the cross-cohort generalization failure. The r3 replay is now consumed
development evidence; changing the horizon, weight, learning rate, or
interpolation grid in response to these results would be tuning on that same
cohort.

Sequential-minibatch one-step and three-step interpolation work on r3 stops
here. A distinct deterministic full-dataset-gradient check may test whether
minibatch order and dropout were the remaining source of instability. If that
check also fails, the next combat-learning experiment must change the evidence
source or learning formulation rather than retune this replay.
