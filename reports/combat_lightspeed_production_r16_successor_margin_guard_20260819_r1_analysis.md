# Production r16 margin-guarded successor analysis

## Decision

No-go. Retain production r16; do not package, confirm, or launch gameplay for this candidate. The registered cohort must not be retried.

## Technical result

- Runner verdict: `technical_smoke_ready`; blockers: none
- Source/prepared transitions: `67,340` / `84,148`
- Optimizer updates: `256`; parameter L2 delta: `1.1081`
- Guard eligible rows across updates: `10,538`; mean `41.16` per update
- Guard loss: `0.0758` first, `0.0256` last, `0.0481` mean
- Guard ranking violations: `988` across sampled updates
- Incomplete training profiles: `1` / `100` transitions, reason `decision_bound`
- Unsupported transitions and unexpected initialization failures: `0`

The experiment nevertheless fails its stricter preregistered technical gate: control and candidate each have one held-out undecided/truncated profile, while the registration required zero. The runner-level technical verdict does not override that condition.

## Matched result

The original runner aggregate included two pairs where one policy was `undecided`. Terminal-only recomputation excludes those rows. Across `849` terminal paired profiles, aggregate reward delta is `+0.027`, HP delta is `+0.131`, and victory exchange is `42` candidate-only versus `44` parent-only.

| Battle | Profiles | Reward delta | HP delta | Candidate-only wins | Parent-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 256 | +0.546 | +1.449 | 19 | 22 |
| 3 | 250 | +0.432 | -0.012 | 12 | 8 |
| 6 | 206 | +0.040 | -0.403 | 6 | 6 |
| 9 | 137 | -1.704 | -1.270 | 5 | 8 |

Battles `6+9` combined reward delta is `-0.657`. Therefore three outcome conditions fail: victory exchange, positive late-battle reward, and the `-1.0` worst-battle floor.

## Interpretation

The guard is directionally useful. Relative to the unguarded r1 successor, matched reward delta improves by `8.741`, HP delta by `5.122`, and the victory-exchange gap narrows from `-125` to `-2`. It converts a strongly harmful update into an aggregate near tie, but the residual harm is concentrated at battle 9 and remains outside the registered gate.

The next useful step is a fresh, read-only action/Q-margin drift audit of this guarded candidate, stratified by battle index. That audit should identify whether battle-9 harm still comes from non-end-turn actions being displaced or from a different action-family/card-ranking change before any new objective is registered.
