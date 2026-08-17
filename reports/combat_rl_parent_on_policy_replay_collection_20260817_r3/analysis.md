# Third Parent On-Policy Replay Collection

## Decision

Accept r3 as the unseen offline development cohort for the next
outcome-constrained combat training experiment. The collection completed 20
registered seeds naturally and stored all 4,075 transitions without optimizer
updates or replay truncation.

## Zero-Update Verification

The terminal checkpoint has `episode=20`, `total_steps=4075`,
`learning_starts=100000`, an empty optimizer state, and null TD/total losses.
Its online and target tensors exactly equal the promoted parent and each other.
All 20 run seeds match the registered pool in order.

## Independent Signal

The third cohort reproduces the same policy mismatch seen in r1 and r2:

| Metric | r1 | r2 | r3 |
| --- | ---: | ---: | ---: |
| Replay transitions | 3,856 | 3,255 | 4,075 |
| Parent positive-energy EndTurn share | 69.67% | 70.32% | 70.64% |
| Executed positive-energy EndTurn share | 2.66% | 2.34% | 2.07% |
| Positive-energy parent-EndTurn interventions | 2,002 | 1,674 | 2,134 |

r3 reached 491 total floors, including 15 Act 2 entries and seven Act 2 boss
reaches. These outcomes are collection context only because the policy did not
change, but they provide useful deep-state coverage for unseen offline
validation.

## Runtime

There were no optimizer/loss log entries, expert actions, invalid actions, RL
failures, replay failures, tracebacks, critical errors, or post-start
CommunicationMod error growth. Production configuration was restored to
SHA-256
`7e923bba944c411512f5f8322a8494bc30f7edda47be0e3f404c5b25edde22b2`,
and the experiment/game processes were closed.

## Next Step

Use r1+r2 only for fitting a bounded grid of low-TD, Q-anchored pairwise
candidates. Evaluate every candidate on the untouched r3 replay. The gate must
require lower unseen SmoothL1, high parent agreement, and a limited EndTurn
distribution shift; pairwise imitation remains secondary and cannot authorize
live evaluation by itself.
