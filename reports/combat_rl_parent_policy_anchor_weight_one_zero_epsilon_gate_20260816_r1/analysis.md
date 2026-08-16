# Weight-one parent-policy anchor fresh gate

## Decision

Reject the weight-one successor and retain the promoted parent checkpoint. The candidate failed three preregistered promotion conditions, so no production configuration or checkpoint is changed.

## Matched result

| Metric | Candidate | Parent |
|---|---:|---:|
| Games | 20 | 20 |
| Victories | 0 | 0 |
| Total floors | 440 | 457 |
| Mean floor | 22.00 | 22.85 |
| Median floor | 16 | 19 |
| Act 2 entries | 8 | 10 |
| Act 2 boss reaches | 5 | 5 |
| Act 3 entries | 0 | 0 |

All 20 seed pairs matched. The paired result was 3 candidate wins, 13 ties, and 4 parent wins, with a summed candidate-minus-parent floor delta of `-17`.

## Gate result

- Failed: candidate paired floor wins did not exceed parent wins (`3 < 4`).
- Failed: candidate Act 2 entries did not match parent (`8 < 10`).
- Failed: candidate total floors did not match parent (`440 < 457`).
- Passed: victories, Act 2 boss reaches, complete arm counts, and seed pairing.

Both arms completed naturally. After each wrapper startup, the CommunicationMod error log did not grow. The production configuration was restored to SHA-256 `d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`, and the exact Java/Python processes were closed.

## Implication

Raising the scalar parent-anchor weight from `0.5` to `1.0` recovered the preregistered replay agreement threshold, but did not improve fresh deterministic gameplay. Do not continue a scalar anchor-weight sweep. The next training change should constrain policy-order changes directly, especially on high-margin parent actions, while retaining the observed TD-fit improvement.
