# Fresh-Replay Pairwise Margin Matched Gate

## Decision

Retain the promoted parent. The pairwise-margin candidate moved the targeted
live behavior in the intended direction and improved aggregate floors, but it
failed two preregistered conditions: paired floor wins and Act 2 boss reaches.
The all-conditions promotion rule therefore rejects it.

## Matched Result

Across 20 fresh matched seeds:

| Metric | Pairwise candidate | Parent | Gate |
| --- | ---: | ---: | --- |
| Victories | 0 | 0 | pass |
| Total floors | 464 | 441 | pass |
| Mean floor | 23.20 | 22.05 | context |
| Median floor | 23 | 20 | context |
| Paired floor wins | 3 | 4 | fail |
| Act 2 entered | 12 | 10 | pass |
| Act 2 boss reached | 3 | 4 | fail |
| Act 3 entered | 1 | 0 | pass |
| EndTurn share among positive-energy raw RL decisions | 0.471678 | 0.533627 | pass |

Thirteen seed pairs tied. The candidate's total-floor advantage was `+23`, but
it came mainly from two large wins (`+13` and `+17`). The parent won four pairs
while the candidate won three, and the candidate lost one Act 2 boss reach.
This is exactly the kind of tail-sensitive result that the paired and
progression gates were intended to prevent from being hidden by an aggregate
mean.

## Behavioral Result

The candidate reduced positive-energy raw-RL EndTurn decisions from
`849 / 1591` (`53.36%`) to `866 / 1836` (`47.17%`). It therefore passed the
intervention's defining behavioral condition on fresh trajectories. The older
EndTurn-only denominator also moved in the intended direction (`86.25%` versus
`87.71%`).

Both arms completed all 20 seeds in the registered order. Neither arm produced
an invalid or failed RL action, agent fallback, traceback, critical error, or
post-start CommunicationMod error growth. Production configuration was restored
to SHA-256 `7e923bba944c411512f5f8322a8494bc30f7edda47be0e3f404c5b25edde22b2`,
and all experiment/game processes were closed.

Rotated debug logs contained historical rows, so raw-action metrics were
computed only inside each arm's clean decision-trace time window. Run outcomes
and seed matching came from the 20 arm-local `.run` files.

## Interpretation

Pairwise Q-margin distillation is a better behavioral target than the earlier
cross-entropy variants: it transferred the requested EndTurn reduction without
an aggregate floor regression. It is not yet reliable enough to replace the
parent, because the gain is concentrated in a few seeds and did not preserve
Act 2 boss coverage.

Do not tune another weight from this cohort. The next training iteration should
retain the Q-preserving anchor and pairwise objective, but train on a broader
mixture of independently collected parent on-policy replay so the intervention
is less dependent on one 3,856-transition cohort. A new candidate should then
face a newly registered seed pool, not reuse these outcomes.
