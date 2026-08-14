# Combat RL schema-2 R3 zero-epsilon gate

## Decision

**FAIL: do not promote or continue the R3 checkpoint.** The candidate failed three preregistered conditions: paired floor wins, Act 2 entries, and total floors. The favorable Act 2 boss count does not override a conjunctive gate.

## Result

| Metric | R3 candidate | Entry baseline | Gate condition |
| --- | ---: | ---: | --- |
| Paired floor wins | 6 | 7 | **FAIL** |
| Ties | 7 | 7 | Informational |
| Total floors | 443 | 483 | **FAIL** |
| Mean floor | 22.15 | 24.15 | Informational |
| Median floor | 16.0 | 23.5 | Informational |
| Act 2 entries | 9 | 11 | **FAIL** |
| Act 2 boss reaches | 7 | 6 | PASS |
| Act 3 entries | 0 | 1 | Informational |
| Victories | 0 | 0 | PASS |
| Integrity warnings | 0 | 0 | PASS |

The mean paired floor delta was `-2.0`. Among 13 non-tied seeds, the candidate won 6 and the baseline won 7; the two-sided exact sign-test p-value is `1.0`. The largest regression was floor 5 versus floor 33, and the baseline also produced the cohort's only Act 3 entry, reaching floor 50 before dying to Awakened One.

## Cross-replicate evidence

R2 and R3 are the two clean evaluations against the exact frozen entry checkpoint under the repaired shared event policy. Both failed the same conjunctive gate, although their failure shapes differed.

Descriptively combining the two independent recipes' outcomes gives 899 candidate floors versus 924 baseline floors, 14 candidate paired wins versus 11 baseline wins with 15 ties, 22 versus 21 Act 2 entries, and 10 versus 12 Act 2 boss reaches. This is not a pooled single-policy estimate because R2 and R3 are different checkpoints. It does show that repeating the unchanged training recipe produces high-variance policy changes with unsupported downside in the right tail.

## Integrity

- Both arms completed exactly 20 games in the preregistered seed order.
- All 20 `seed_played` values matched between candidate, baseline, and seed pool.
- Both arms logged exactly one `Max games reached (20)` exit.
- No replay rejection, episode-close failure, checkpoint-save failure, nonzero RL failure count, or NaN was found across the gate logs.
- CommunicationMod error-log growth was limited to expected wrapper/dependency messages: 658 bytes for candidate and 657 bytes for baseline.
- CommunicationMod configuration was restored to SHA-256 `b42093ae...03c1`, and no Python or Java game process remained after the gate.

## Next step

Stop launching unchanged fourth replicates. The next candidate should reduce replicate-specific action noise while retaining the shared learned direction. Evaluate checkpoint weight averaging across R1/R2/R3 on all three retained replay panels as a CPU-only diagnostic. Only if the averaged checkpoint improves TD loss without increasing divergence from entry or collapsing action margins should it receive a fresh live gate.
