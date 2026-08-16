# Alpha-0.20 combat interpolation fresh gate

## Gate result

The alpha-0.20 weights-only interpolation passes every preregistered promotion condition against the existing promoted parent. The gate qualifies it for a separate promotion decision; the gate itself did not modify production configuration.

| Metric | Candidate | Parent |
|---|---:|---:|
| Games | 20 | 20 |
| Victories | 0 | 0 |
| Total floors | 492 | 444 |
| Mean floor | 24.60 | 22.20 |
| Median floor | 21 | 16 |
| Act 2 entries | 11 | 9 |
| Act 2 boss reaches | 7 | 6 |
| Act 3 entries | 2 | 0 |

All 20 seed pairs matched. The paired result was 5 candidate wins, 13 ties, and 2 parent wins, with a summed candidate-minus-parent floor delta of `+48`.

## Integrity

Both arms completed naturally. After each wrapper startup, the CommunicationMod error log did not grow. The previous production configuration was restored and all exact Java/Python processes were closed before qualification was calculated.

## Qualification

- Passed: candidate paired floor wins exceeded parent wins (`5 > 2`).
- Passed: victories were non-inferior (`0 = 0`).
- Passed: Act 2 entries improved (`11 > 9`).
- Passed: Act 2 boss reaches improved (`7 > 6`).
- Passed: total floors improved (`492 > 444`).
- Passed: both arms completed 20 games and every seed pair matched.

The candidate was chosen by exploratory replay analysis, but this gate used a fully fresh cohort and fixed rules. Promotion must be recorded separately because the preregistration prohibited automatic promotion.
