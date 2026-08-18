# Stratified LightSTS replay training decision

## Decision

Approve exactly one fresh simulator replication with the same r4 parent, anchor weight, replay preparation, and optimizer budget. This candidate has no live-transfer authority yet.

## Replay evidence

| Battle index | Source transitions | Prepared transitions | Duplicates |
|---:|---:|---:|---:|
| 0 | 3,815 | 5,024 | 1,209 |
| 3 | 4,635 | 5,024 | 389 |
| 6 | 5,024 | 5,024 | 0 |
| 9 | 3,298 | 5,024 | 1,726 |

All `16,772` source transitions were retained. Deterministic oversampling produced `20,096` prepared rows and equalized all four strata to the largest source count. Index 9 was materially underrepresented in the source replay despite its longer combats.

## Training and held-out result

- Optimizer updates: `256/256`
- Mean TD loss: `2.4683378427`
- Mean parent-policy anchor loss: `0.6889008465`
- Candidate parameter L2 delta: `1.8035754105`
- Reachable matched profiles: `215/256`
- Mean reward delta: `+0.3712928386`
- Mean player HP delta: `+0.6279069767`
- Candidate-only victories: `3`
- R4-only victories: `3`

| Battle index | Reward delta | HP delta | Candidate-only wins | R4-only wins |
|---:|---:|---:|---:|---:|
| 0 | +0.0344 | +0.0625 | 0 | 0 |
| 3 | +0.5000 | +0.8254 | 0 | 0 |
| 6 | +1.0955 | +0.4808 | 2 | 1 |
| 9 | -0.3011 | +1.5000 | 1 | 2 |

Every technical, aggregate, early-combat, and material per-index criterion passed. The replication must use untouched train and held-out cohorts and must not alter balancing, anchor weight, or optimizer budget.

