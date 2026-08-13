# Rare-Card Uplift Residual Postmortem

## Decision

The residual is not ready for fresh simulator or live-shadow evaluation. The
canonical verdict is `rare_card_uplift_residual_not_ready`; no live action,
promotion, qualification, or policy-quality authority is granted.

## Evidence

- Targeted collection produced 283 train and 67 development states, covering
  all 16 Ironclad rare cards. Frozen-action projection retained 276 train and
  64 development states.
- The fitted residual covered all 16 target IDs and had zero unseen
  development take actions.
- Rare development mean regret improved from `0.121162` to `0.088268` and
  best-take-to-skip errors fell from 18 to 11.
- Merged development maximum regret worsened from `2.315789` to `2.491228`, so
  the preregistered maximum-regret gate failed.

## Worst Regression

At seed `92309`, decision index 29, the frozen entry model correctly selected
`Impervious` with counterfactual return `2.614035`. The per-card residual instead
selected `Bludgeon`, whose return was `0.122807`, producing regret `2.491228`.
This is evidence that a global card-ID uplift cannot represent the observed
state-dependent choice between rare cards.

## Next Boundary

Do not tune or rerun the per-card residual against the exposed development
partition. A separate change may train the existing state-conditioned card
policy on the merged compatible train rows and use the still-unaccessed
`92320..92383` schedule as a one-shot independent gate. Fresh simulator or live
shadow remains blocked until that gate passes.
