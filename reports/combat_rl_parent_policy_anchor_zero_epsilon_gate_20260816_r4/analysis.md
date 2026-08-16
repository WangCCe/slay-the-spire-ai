# Combat RL parent-policy anchor zero-epsilon gate R4

## Decision

**Reject the anchored candidate and retain the promoted parent.** Both arms
completed cleanly, but the candidate failed two required promotion conditions:
paired floor wins did not exceed the parent, and total floors were lower.

## Integrity

- Candidate and parent each completed all `20` registered games.
- All `20` seed pairs matched in registered order.
- AI marker counts advanced `16008 -> 16028 -> 16048`.
- Each arm's error log stayed fixed after its normal startup output.
- No model, seed, route, epsilon, or threshold changed between arms.
- The production CommunicationMod configuration was restored to SHA-256
  `d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`.

## Aggregate results

| Metric | Candidate | Parent |
| --- | ---: | ---: |
| Total floors | 463 | 485 |
| Mean floor | 23.15 | 24.25 |
| Median floor | 18 | 16 |
| Victories | 0 | 0 |
| Act 2 entries | 10 | 9 |
| Act 2 boss reaches | 7 | 7 |
| Act 3 entries | 2 | 3 |

Paired floor outcomes were `5` candidate wins, `10` ties, and `5` parent wins.
The candidate's summed paired delta was `-22` floors.

## Paired floors

| Pair | Candidate | Parent | Delta |
| ---: | ---: | ---: | ---: |
| 1 | 16 | 16 | 0 |
| 2 | 11 | 33 | -22 |
| 3 | 33 | 33 | 0 |
| 4 | 27 | 16 | +11 |
| 5 | 39 | 44 | -5 |
| 6 | 16 | 16 | 0 |
| 7 | 33 | 37 | -4 |
| 8 | 33 | 50 | -17 |
| 9 | 16 | 16 | 0 |
| 10 | 33 | 31 | +2 |
| 11 | 16 | 16 | 0 |
| 12 | 33 | 33 | 0 |
| 13 | 11 | 16 | -5 |
| 14 | 16 | 11 | +5 |
| 15 | 38 | 33 | +5 |
| 16 | 16 | 16 | 0 |
| 17 | 24 | 16 | +8 |
| 18 | 16 | 16 | 0 |
| 19 | 16 | 16 | 0 |
| 20 | 20 | 20 | 0 |

## Promotion rule

| Requirement | Result |
| --- | --- |
| Candidate paired floor wins exceed parent | **FAIL** (`5 = 5`) |
| Candidate victories at least parent | PASS (`0 = 0`) |
| Candidate Act 2 entries at least parent | PASS (`10 > 9`) |
| Candidate Act 2 boss reaches at least parent | PASS (`7 = 7`) |
| Candidate total floors at least parent | **FAIL** (`463 < 485`) |
| Both arms complete and all seed pairs match | PASS |

The next training iteration should start from the retained parent rather than
continue from this rejected checkpoint. The largest paired regressions are
pairs 2 and 8 (`-22` and `-17` floors), while pairs 4 and 17 are the largest
candidate improvements (`+11` and `+8`).
