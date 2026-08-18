# Encounter-aware LightSTS training decision

## Decision

Retain the r4 parent and reject this candidate for frozen confirmation or live
use. Encounter identity substantially reduced the late-battle regression but
did not pass the preregistered index 9 reward and victory guardrails. Do not
retry this cohort or tune the hash bucket count.

## Migration and replay evidence

- Source parent parameter hash: `1ecca8b19803d56f8bbed1b9ddbc1c8f26638f80bb0ccb50f21ece65e3dfc2f9`
- Migrated parent parameter hash: `f7cb1f8557188328b2aaaf499b19461a4e9e07675c7eb7e8978994ebaa3b1f08`
- Inserted encounter-column maximum absolute value: `0.0`
- Equivalence probes: `16`, maximum masked Q delta `3.5762786865e-7`
- Greedy action mismatches: `0`
- Source replay transitions: `65,700`
- Prepared replay transitions: `78,852`
- Optimizer updates: `256/256`
- Candidate parameter L2 delta: `1.7711336186`

All technical migration, replay, optimizer, and isolation criteria passed.

## Held-out result

- Reachable matched profiles: `847/1024`
- Mean reward delta: `+0.5276438644`
- Mean player HP delta: `+0.6410861865`
- Candidate-only victories: `15`
- R4-only victories: `15`

| Battle index | Reachable | Reward delta | HP delta | Candidate-only wins | R4-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 256 | +0.0691 | +0.1289 | 0 | 0 |
| 3 | 246 | +0.4287 | +0.6341 | 1 | 1 |
| 6 | 205 | +1.6187 | +1.6049 | 9 | 8 |
| 9 | 140 | -0.0577 | +0.1786 | 5 | 6 |

Aggregate, early-combat, reachability, HP, and material-regression criteria
passed. Index 9 failed because its reward delta was negative and candidate-only
victories were fewer than r4-only victories. A passing result requires every
registered criterion, so the near tie does not authorize confirmation.

## Structural finding

The training corpus contained `42` encounter identities but the hash encoding
occupied only `31/64` buckets. Eight buckets collided; bucket 48 merged five
encounters (`COLLECTOR`, `HEXAGHOST`, `SENTRY_AND_SPHERE`, `SHELL_PARASITE`, and
`TWO_FUNGI_BEASTS`). This is a concrete information-loss mechanism and not a
reason to retune the bucket count after outcome access.

A distinct follow-up may test a source-bound collision-free encounter
vocabulary with the same parent migration and training recipe on fresh cohorts.
That requires a new registration and still grants no live authority.
