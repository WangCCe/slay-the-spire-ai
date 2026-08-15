# Combat RL expert-dominant zero-epsilon gate R1

## Decision

**Do not promote or continue the R3 candidate. Keep the exact entry checkpoint as production baseline.** The candidate improved replay diagnostics but did not beat the baseline on a fresh matched live cohort.

## Matched result

| Metric | Candidate | Baseline |
| --- | ---: | ---: |
| Victories | 0 | 0 |
| Total floors | 466 | 473 |
| Mean floor | 23.30 | 23.65 |
| Median floor | 19.0 | 21.5 |
| Act 2 entries | 10 | 11 |
| Act 2 boss reaches | 7 | 7 |
| Act 3 entries | 0 | 0 |

Across 20 exact seed pairs, the candidate won 4, the baseline won 7, and 9 tied. Mean paired floor delta was `-0.35`; the two-sided exact sign-test p-value was `0.5488`.

The candidate failed three preregistered requirements: paired wins did not exceed baseline, total floors regressed, and Act 2 entries regressed. Victory count, Act 2 boss coverage, seed identity, and runtime integrity passed.

## Integrity

- All 20 seed pairs matched by `seed_played` and order.
- Both arms completed exactly 20 games at epsilon zero with training and expert mix disabled.
- Candidate and baseline CommunicationMod error growth was 665 and 662 bytes respectively, both expected launch messages.
- Original configuration was restored and all game/Python processes were closed.

## Implication

Increasing expert mixture repaired the training data distribution and produced better in-replay fit, but that did not translate to live policy improvement. Do not spend another full cohort on the same recipe. The next training work should change the learning signal or schema, with the raw monster-slot representation gap as one concrete candidate.
