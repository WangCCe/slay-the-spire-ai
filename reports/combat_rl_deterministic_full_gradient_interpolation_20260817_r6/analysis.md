# Deterministic full-gradient interpolation r6

## Decision

**No-go.** No checkpoint was written. This result does not authorize fresh
replay collection, live evaluation, or a production-policy change.

## Result

All three replicate labels produced identical training and validation metrics,
confirming that the fixed `128`-row memory chunks, disabled dropout, and four
full-dataset Adam steps removed the earlier training-order variance.

The promoted parent development one-step SmoothL1 was `4.122797`. Every
interpolation was worse:

| alpha | SmoothL1 | parent agreement | off-target disagreement |
| ---: | ---: | ---: | ---: |
| 0.25 | 4.254042 | 0.971043 | 0.013395 |
| 0.50 | 4.414798 | 0.944785 | 0.027821 |
| 0.75 | 4.601653 | 0.917546 | 0.042761 |
| 1.00 | 4.810331 | 0.890061 | 0.058733 |

Even the smallest registered interpolation failed both the development-loss
and `0.98` parent-agreement requirements. The raw trained model had relative L2
distance `0.000440322` from the parent.

## Interpretation

Minibatch ordering and training-time dropout are not the main cause of the
cross-cohort failure. The deterministic r1+r2 one-step TD direction itself
moves away from the r3 objective. Bootstrapped TD fitting on the current replay
is retired: do not change step count, learning rate, TD weight, or interpolation
alpha against r3.

The next bounded investigation is cohort-gradient alignment across r1, r2, and
r3. It should determine whether the evidence sources disagree before another
candidate is fitted. A later candidate must change the evidence source or the
learning formulation and must reserve a new r4 replay as untouched evidence.
