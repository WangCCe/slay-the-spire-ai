# Inventory Embedding Fresh Holdout R1

## Result

The registered production-r16 collection completed all 20 disjoint seeds in
order and produced 3,433 untouched combat transitions. No optimizer update ran:
the optimizer state is empty, the last loss is null, and both online and target
networks remain exactly equal to production r16.

The repaired replay boundary and inventory paths both held on fresh gameplay.
All 3,433 decision-trace rows joined one-to-one with zero potion or relic
identity mismatch, and there are no stored or adjacent cross-floor nonterminal
transitions.

## Frozen Gate

The exact frozen inventory-embedding candidate was evaluated once without
fitting or threshold changes. One-step Smooth L1 improved from `4.278684` to
`4.248425`; parent action agreement was `99.417%`; off-target disagreement was
`0.651%` (11/1,691); and positive-energy EndTurn decisions decreased from
1,791 to 1,783. Every preregistered condition passed.

The candidate is therefore eligible for a separately registered bounded
matched live gate. It is not promoted and must not replace the production
checkpoint yet.

## Scope

The cohort itself had zero victories with a mean floor of `21.45`. That is a
description of the parent-policy holdout, not a candidate-versus-parent result.
The next evidence step is one fresh paired live comparison; if it does not show
a material advantage, this candidate line should stop rather than spawning
mechanical near-neighbor retries.
