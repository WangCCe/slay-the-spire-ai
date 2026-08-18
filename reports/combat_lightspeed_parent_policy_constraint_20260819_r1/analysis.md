# Parent-policy-constrained LightSTS training decision

## Decision

Retain r4 and do not replicate this candidate. The fixed parent-action objective executed correctly, but the candidate fails aggregate HP, early-combat HP, and material battle-index regression criteria.

## Objective evidence

- Frozen parent and control parameter SHA-256: `1ecca8b19803d56f8bbed1b9ddbc1c8f26638f80bb0ccb50f21ece65e3dfc2f9`
- Parent-policy anchor weight: `1.0`
- Optimizer updates: `256/256`
- Mean TD loss: `2.5176943336`
- Mean parent-policy anchor loss: `0.6928935556`
- First-to-last anchor loss: `0.9825950265` to `0.6021026969`
- Candidate parameter L2 delta from r4: `1.7729393397`

The positive finite loss and exact frozen hash show that the constraint was active. This is not a wiring or zero-gradient failure.

## Held-out result

- Reachable matched profiles: `217/256`
- Mean reward delta: `+0.4915782179`
- Mean player HP delta: `-0.1152073733`
- Candidate-only victories: `6`
- R4-only victories: `4`

| Battle index | Reachable profiles | Reward delta | HP delta | Candidate-only wins | R4-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 64 | -0.1129 | -0.1719 | 0 | 0 |
| 3 | 63 | +1.2933 | -0.1270 | 2 | 1 |
| 6 | 54 | +1.5844 | +0.9630 | 3 | 2 |
| 9 | 36 | -1.4760 | -1.6111 | 1 | 1 |

## Implication

Do not scan a larger anchor weight. Initialized training-profile coverage declines from `256` at index 0 to `154` at index 9, while optimization currently samples transitions without an explicit battle-index stratum contract. The next bounded experiment should measure and equalize replay transition representation by battle index while retaining the same fixed parent objective. It requires new train and held-out seeds and remains simulator-only.

