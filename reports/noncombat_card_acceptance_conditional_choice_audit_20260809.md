# Card Acceptance And Conditional Choice Audit

## Decision

The bounded descriptive verdict is `acceptance_pressure_with_conditional_concentration_but_mixed_direct_pressure`.
It grants no training, evaluation, OPE, model loading, gameplay,
qualification, promotion, policy-quality, causal, or formal-RL authority.

## Verified Evidence

- Trajectories: 512
- Decisions: 11729
- Eligible card rewards: 3536
- Chunks: 8

## Mechanism Split

- Acceptance pressure consistent: `True`
- Conditional concentration progresses: `True`
- Conditional pressure consistent: `False`
- Support: `supported`

| Chunk | Rows | Acceptance pressure | Conditional margin pressure | Normalized take entropy | Top-two gap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 431 | 0.000732140210644647 | -0.000554812359239992 | 0.999970640453427 | 0.0027413173734076 |
| 1 | 451 | 0.00133740885067405 | -0.000574123315817045 | 0.999963921995903 | 0.0030771446665023 |
| 2 | 443 | 0.000390305815039908 | -0.00241388972468302 | 0.999952776826301 | 0.00360540287809077 |
| 3 | 437 | 0.00216993724708837 | -4.47630456653671e-06 | 0.999945659205942 | 0.00388549654937325 |
| 4 | 449 | 0.00121550364348373 | -0.000404374314179256 | 0.999930232175228 | 0.00437472839644192 |
| 5 | 457 | 0.00160653392308612 | 0.0018187518467834 | 0.999909123775689 | 0.0049032244044614 |
| 6 | 449 | 0.00196901991124757 | -0.00144275997371082 | 0.999893886245927 | 0.00519616422271834 |
| 7 | 419 | 0.000318201137773141 | 0.00129044525563934 | 0.999861251832957 | 0.00596556637524744 |

## Limits

The conditional trend and row-local pressure are separate observations.
Shared-parameter gradients cannot identify a candidate-score effect
without retained per-row score Jacobians.

## Next Gate

Any objective, architecture, coefficient, experiment, evaluation, or
live-policy change requires a separate reviewed proposal.
