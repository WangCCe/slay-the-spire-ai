# Combat RL Direct Drift Margin Audit R1

## Finding

The direct-policy failure is not explained by a few near-tie Q values. R1
changed `20/77` direct validation actions and R2 changed `38/106`. In R2, only
`21%` of changed rows had parent margin at most `0.1`; five changed rows had
margin above `1.0`, with a maximum of `1.84`.

Every cross-family change moved toward `play_card`:

- R1: 2 End Turn and 5 potion parent actions became Play Card;
- R2: 4 End Turn and 7 potion parent actions became Play Card.

Play-card-to-play-card substitutions account for the remaining 13 and 27
changes. The candidate also lowered the parent's selected Q by a mean `1.06`
in R1 and `0.83` in R2.

## Interpretation

Both corpora contain roughly 80% executed-action override rows. The current
global anchor cross entropy therefore gives most of its gradient mass to the
override stratum. The repeated play-card shift supports cross-stratum
interference in the shared network; it does not establish causality because R1
and R2 are different cohorts.

Lowering optimizer steps again is not the right next experiment. The next
offline exploration should balance direct and override anchor losses and add a
top-action margin guard only on direct rows. A bounded ablation may reuse the
development corpus only with no candidate, holdout, gameplay, or promotion
authority. A final candidate still requires a newly registered replay after the
objective is selected.
