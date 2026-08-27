# Inventory-embedding combat successor r1

## Decision

Freeze candidate SHA-256
`a1e631d5379adab9f55fe0ace993c49bba6576188e09cec4722f252971cbbb19`
for one separately collected fresh zero-update replay holdout. The candidate has
no gameplay, qualification, promotion, or production-replacement authority.

## Fixed training result

The runner split 267 terminal-delimited combat groups into 214 training groups
(2,764 transitions) and 53 validation groups (869 transitions). It performed
the single registered 16-epoch Adam dose and updated only nonzero potion and
relic embedding rows. There was no interpolation or same-corpus sweep.

Validation one-step SmoothL1 fell from `3.749052` to `3.718760`. The candidate
changed 10 of 869 parent greedy actions (`1.1507%`), inside the fixed
`0.5%..5%` materiality range. All ten changes moved away from End Turn while
energy was positive: seven selected card actions and three selected potion-slot
zero. Positive-energy End Turns fell from 395 to 385, and executed-action
agreement rose slightly from `38.665%` to `38.895%`.

The change is inventory-conditioned rather than uniform. Potion-present
validation states changed at `1.8470%` (7/379), compared with `0.6122%` (3/490)
when no potion was present. One-step loss improved in both strata.

## Isolation

Exactly 26 observed potion rows and 53 observed relic rows changed. Zero rows,
unobserved inventory rows, card embeddings, and every dense/value/advantage
tensor remained byte-exact to production r16. Relative L2 movement was `2.775%`
within the potion embedding, `2.745%` within the relic embedding, and `0.9389%`
across the complete network. This is materially larger than the prior r17-r19
near-neighbor candidates while remaining localized to the intended parameter
class.

## Limits and next step

R2 is training/development evidence and cannot confirm policy quality. Freeze
the exact candidate and recipe, collect a new disjoint zero-update real replay,
and evaluate the frozen candidate exactly once against production r16 on that
holdout. Do not tune this dose or its thresholds from r2.
