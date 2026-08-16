# Positive-energy action imitation combat RL matched gate

## Decision

Retain the promoted parent. The candidate reduced positive-energy EndTurn
dependence as intended, but failed three pre-registered gameplay outcome
conditions and is not promoted.

## Matched outcomes

All 20 seed pairs matched. The candidate won six floor pairs, the parent won
four, and ten tied. Candidate total floors were `497` versus `518`; it entered
Act 2 twelve times versus fifteen and reached an Act 2 boss seven times versus
eight. The candidate entered Act 3 once versus three times for the parent.
Neither arm won a run.

The outcome gap is concentrated in three large losses (`-34`, `-25`, and
`-17` floors). The candidate also produced four meaningful gains (`+17`,
`+15`, `+12`, and `+8`), so the objective changed behavior rather than simply
collapsing the policy.

## Imitation objective

The candidate returned EndTurn with positive energy on 1,015 of 1,150 raw
EndTurn decisions (`88.26%`). The parent did so on 1,127 of 1,249
(`90.23%`). This passes the required non-increase and reverses the failure that
motivated direct action imitation.

Both arms completed all 20 games with matching seed order. Neither arm logged
an invalid or failed RL action, traceback, or post-start CommunicationMod error
growth. Production configuration was restored and all evaluation processes
were closed.

## Interpretation

Direct positive-energy action imitation successfully moved the targeted action
distribution without destroying parent-policy agreement offline. It did not
improve the matched gameplay distribution: fewer Act 2 entries, fewer Act 2
boss reaches, and 21 fewer total floors fail the promotion rule.

The next experiment should preserve the demonstrated action correction while
reducing catastrophic regressions. The highest-value analysis is seed-level:
compare the three large-loss trajectories against the four large gains and
test whether imitation should be restricted by state context or confidence.
Do not continue the same global weight-0.25 recipe unchanged.
