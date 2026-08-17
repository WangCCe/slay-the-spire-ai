# Targeted Candidate Interpolation Scan

## Decision

Select parent-to-candidate interpolation `alpha=0.9` for one fresh matched
zero-epsilon gameplay gate. This is an offline diagnostic selection, not a
promotion.

## Design

The scan linearly interpolated both online and target parameters from the
promoted parent (`alpha=0.0`) to the targeted-imitation candidate (`alpha=1.0`)
at increments of `0.1`. All 4,096 transitions in the candidate's final replay
were evaluated on CPU; 3,008 had positive energy and 1,816 met the targeted
parent-EndTurn correction condition.

An intermediate point had to retain at least half of the candidate's EndTurn
reduction, improve parent agreement and off-target drift over the candidate,
retain positive targeted correction, and not exceed the parent's Smooth L1.
The minimum qualifying alpha was selected to limit policy drift.

## Result

| Metric | Parent | Alpha 0.9 | Candidate |
| --- | ---: | ---: | ---: |
| Positive-energy EndTurn share | 0.624668 | 0.596742 | 0.583444 |
| Parent greedy-action agreement | 1.000000 | 0.903320 | 0.890137 |
| Targeted correction agreement | 0.000000 | 0.025330 | 0.033590 |
| Off-target parent disagreements | 0 | 254 | 274 |
| Smooth L1 | 3.945786 | 2.980145 | 2.929095 |
| Relative L2 from parent | 0.000000 | 0.006061 | 0.006735 |

Alpha `0.9` retains 67.7% of the endpoint EndTurn-share reduction while
recovering 20 off-target decisions and 1.32 percentage points of parent
agreement. Alpha `0.8` retains only 31.4% of the reduction and therefore fails
the predeclared half-retention condition. No lower point qualified.

The selected weights-only checkpoint round-tripped exactly and loaded through
`RLAgentV2` with the production game ID mapping on CPU.

## Authority

The replay includes training transitions and is not independent outcome
evidence. It authorizes only one fresh matched gameplay gate against the
promoted parent. Promotion still requires the complete matched gameplay rule;
no result from this scan can replace it.
