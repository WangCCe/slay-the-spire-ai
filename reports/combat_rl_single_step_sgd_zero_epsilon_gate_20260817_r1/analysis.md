# Single-step SGD matched live gate

## Decision

The frozen single-step SGD candidate passes every preregistered condition and
is qualified for a separate promotion decision. This gate did not modify the
production configuration.

| Metric | Candidate | Parent |
| --- | ---: | ---: |
| Games | 10 | 10 |
| Victories | 0 | 0 |
| Total floors | 210 | 204 |
| Mean floor | 21.0 | 20.4 |
| Median floor | 19 | 16 |
| Act 2 entered | 5 | 4 |
| Act 2 boss reached | 2 | 2 |
| Act 3 entered | 0 | 0 |

The paired result was `1` candidate win, `0` parent wins, and `9` ties. All
ten seed pairs matched, and the summed candidate-minus-parent floor delta was
`+6`.

## Divergent pair

The only non-tied pair was seed-pool index 8. Both arms used the same numeric
seed and made the same non-combat choices through floor 16. The candidate
entered The Guardian with `73` HP, survived with `13` HP, and later died to
Snake Plant on floor 22. The parent entered The Guardian with `61` HP and died
there on floor 16. This is a combat-policy trajectory difference rather than a
seed or route mismatch.

## Integrity

Both arms completed all ten games naturally. Neither arm produced an invalid
or failed RL action, agent fallback, training or expert action, traceback,
critical error, or post-start CommunicationMod error growth. The candidate and
parent decision traces contain `3093` and `2981` rows respectively. Production
configuration was restored to SHA-256
`7e923bba944c411512f5f8322a8494bc30f7edda47be0e3f404c5b25edde22b2`,
and the experiment processes were closed.

## Interpretation

The live effect is deliberately small: nine pairs were behaviorally equivalent
at the floor-outcome level. Promotion should therefore rely on the complete
evidence chain, not claim a large live uplift: deterministic r3 improvement,
untouched r4 replay improvement, high parent agreement, and this bounded live
non-inferiority result with one favorable divergence. A separate decision is
required before changing the production checkpoint.
