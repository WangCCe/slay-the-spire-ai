# Card Uplift Live Shadow R2

## Result

The bounded no-training cohort completed five fresh Ironclad games. The frozen
candidate produced 54 complete card-reward comparisons and disagreed with
Current 34 times. It never substituted an action and produced no runtime error.

| Metric | Result | Gate |
| --- | ---: | ---: |
| Complete rows | 54 | >= 12 |
| Disagreements | 34 | >= 3 |
| Runtime errors | 0 | 0 |
| Action substitutions | 0 | 0 |
| Median latency | 60.05 ms | informational |
| P95 latency | 68.49 ms | informational |
| Maximum latency | 127.81 ms | <= 200 ms |

All four ineligible rows were generated combat card choices, which are outside
the registered ordinary non-combat reward boundary. Every row was canonical,
finite, source/model/config bound, and unique.

## Gameplay Context

The five Current-owned runs reached floors 16, 33, 22, 33, and 16. All five
lost. Shadow mode did not choose any action, so these outcomes neither measure
candidate policy quality nor provide a causal candidate-versus-Current result.

## Decision

The live adapter is structurally ready for a separate, bounded card-intervention
canary proposal. This result grants no action-selection, training, qualification,
promotion, policy-quality, or causal-claim authority.

R1 did not start a game or create shadow output because the initial menu state
arrived before callbacks were registered. Commit `d537b7a45` moved the deferred
stdin reader behind callback registration; R2 then completed normally.
