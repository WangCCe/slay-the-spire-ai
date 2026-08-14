# Combat RL schema-2 R2 zero-epsilon gate

## Decision

**FAIL: do not promote the R2 checkpoint.** The candidate missed the preregistered Act 2 boss-reach guardrail, reaching floor 33 three times versus six for the frozen entry baseline. All preregistered conditions were conjunctive, so the otherwise favorable aggregate results cannot override that failure.

## Result

| Metric | R2 candidate | Entry baseline | Gate condition |
| --- | ---: | ---: | --- |
| Paired floor wins | 8 | 4 | PASS |
| Ties | 8 | 8 | Informational |
| Total floors | 456 | 441 | PASS |
| Mean floor | 22.80 | 22.05 | Informational |
| Median floor | 21.5 | 17.5 | Informational |
| Act 2 entries | 13 | 10 | PASS |
| Act 2 boss reaches | 3 | 6 | **FAIL** |
| Victories | 0 | 0 | PASS |
| Integrity warnings | 0 | 0 | PASS |

The mean paired floor delta was `+0.75`. Among the 12 non-tied seeds, the candidate won 8 and the baseline won 4; the two-sided exact sign-test p-value is `0.3877`, so this cohort does not establish a statistically reliable general improvement.

## Interpretation

The update was not uniformly harmful: it improved more seeds, raised total floors by 15, and produced three additional Act 2 entries. The failure is concentrated in converting Act 2 progress into boss reaches. Three baseline floor-33 outcomes fell to candidate floors 24, 19, and 16, while candidate gains on other seeds mostly stopped before floor 33.

This is evidence of a mixed checkpoint, not evidence that schema-2 replay training is inert. The R2 checkpoint should remain an experiment artifact rather than become the production default or the starting point for an unqualified continuation.

## Integrity

- Both arms completed exactly 20 games in the preregistered seed order.
- All 20 `seed_played` values matched between candidate, baseline, and seed pool.
- Both arms logged exactly one `Max games reached (20)` exit.
- No replay rejection, episode-close failure, checkpoint-save failure, nonzero RL failure count, or NaN was found across the gate logs.
- CommunicationMod error-log growth was limited to the expected wrapper command and dependency-load messages: 658 bytes for candidate and 657 bytes for baseline.
- CommunicationMod configuration was restored to SHA-256 `b42093ae...03c1`, and no Python or Java game process remained after the gate.

## Next step

Do not spend another cycle tuning dropout, clipping, or optimizer state: the offline ablations already found no supported default change. Use the two independent schema-2 training results and their matched gates to isolate whether the floor-33 conversion loss is repeatable across checkpoints. Only then preregister either a fresh same-recipe replication or a narrow training-objective change; do not continue this failed R2 checkpoint by default.
