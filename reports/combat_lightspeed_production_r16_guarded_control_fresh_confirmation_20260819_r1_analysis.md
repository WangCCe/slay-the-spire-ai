# Guarded control fresh confirmation

## Result

The frozen guarded-control candidate replicated its LightSTS advantage over production r16 on `137000..137511`, a disjoint cohort twice the size of the development evaluation.

| Battle | Terminal pairs | Reward delta | HP delta | Candidate-only wins | Parent-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 512 | +4.741 | +4.053 | 65 | 29 |
| 3 | 486 | +0.902 | +0.864 | 27 | 22 |
| 6 | 396 | +1.008 | +0.669 | 17 | 10 |
| 9 | 289 | +1.091 | +0.817 | 9 | 10 |
| All | 1,683 | +2.127 | +1.780 | 118 | 71 |

Battles `6+9` combine to reward `+1.043` and HP `+0.731`. All registered outcome criteria pass. The fresh aggregate reward delta is nearly identical to development (`+2.1272` versus `+2.1277`).

## Technical verdict

The runner reports `comparison_not_ready` because each candidate has one decision-bound profile. Those two nonterminal rows are excluded from all values above. Every underlying registered technical limit passes: each count is `1 <= 4`, excluded pairs are `2 <= 8`, terminal pairs are `1,683 >= 1,600`, battle-9 pairs are `289 >= 200`, and unsupported counts are zero.

The registration is internally inconsistent: it requires the runner's zero-tolerance `comparison_ready` verdict while separately allowing up to four truncations per candidate. Preserve the strict formal result as a technical no-go, but do not spend another cohort merely to satisfy that wrapper condition.

## Decision

Keep production r16 active. The simulator evidence is sufficient to proceed to a separate, deterministic production-packaging compatibility review of this exact frozen checkpoint. Do not retrain, rerun this cohort, package implicitly, or start gameplay yet.
