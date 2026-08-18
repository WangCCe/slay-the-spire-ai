# Large-diversity stratified replay decision

## Decision

Retain the r4 parent and reject this candidate for frozen confirmation or live
use. Fourfold unique train and held-out seed diversity did not stabilize the
late-battle result. Do not repeat or further scale the same fixed recipe.

## Replay evidence

| Battle index | Source transitions | Prepared transitions | Duplicates |
|---:|---:|---:|---:|
| 0 | 15,270 | 20,030 | 4,760 |
| 3 | 17,167 | 20,030 | 2,863 |
| 6 | 20,030 | 20,030 | 0 |
| 9 | 12,978 | 20,030 | 7,052 |

All `65,445` source transitions were retained. Deterministic oversampling
produced `80,120` prepared rows, below the `100,000` replay capacity, and
equalized all four strata. Index 9 still required `35.2%` duplicated rows.

## Training and held-out result

- Optimizer updates: `256/256`
- Mean TD loss: `2.4629660733`
- Mean parent-policy anchor loss: `0.7007632921`
- Candidate parameter L2 delta: `1.7382103422`
- Reachable matched profiles: `856/1024`
- Mean reward delta: `+0.5488355402`
- Mean player HP delta: `+0.3130841121`
- Candidate-only victories: `16`
- R4-only victories: `11`

| Battle index | Reachable | Reward delta | HP delta | Candidate-only wins | R4-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 256 | +0.1727 | +0.2734 | 0 | 0 |
| 3 | 249 | +0.8154 | +0.5663 | 3 | 0 |
| 6 | 199 | +1.6544 | +0.4523 | 7 | 0 |
| 9 | 152 | -0.7017 | -0.2171 | 6 | 10 |

The run passed its technical, aggregate, early-combat, reachability, and
material-regression criteria. It failed all three late-combat uplift criteria:
index 9 reward and HP deltas were negative, and candidate-only victories were
fewer than r4-only victories.

## Implication

The larger cohort reduced uncertainty but confirmed that replay balancing plus
the parent-policy anchor is not sufficient for later battles. The next combat
RL experiment must change the information or objective available to learning,
not tune this oversampling ratio, add another random seed, or transfer this
checkpoint. No game or CommunicationMod run is authorized by this result.
