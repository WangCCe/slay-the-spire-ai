# Production r16 successor low-alpha analysis

## Decision

Stop the current one-step LightSTS recipe. No tested alpha is eligible for fresh confirmation, production packaging, or gameplay.

## Technical result

- Comparison verdict: `comparison_ready`; blockers: none
- Registered/reachable profiles per candidate: `1,024` / `832`
- Unreachable profiles: `192`, all `baseline_loss_before_requested_battle`
- Truncated and unsupported profiles: `0`
- Ranking: `parent`, `alpha_0p05`, `alpha_0p1`, `alpha_0p2`

## Matched result versus parent

| Candidate | Reward delta | HP delta | Candidate-only wins | Parent-only wins | Battle 0 reward | Battles 6+9 reward |
|---|---:|---:|---:|---:|---:|---:|
| alpha 0.05 | -1.234 | -0.544 | 3 | 23 | -1.590 | -0.740 |
| alpha 0.10 | -2.565 | -1.370 | 7 | 48 | -4.431 | -1.241 |
| alpha 0.20 | -4.064 | -2.529 | 11 | 72 | -6.669 | -1.713 |

The parent won `301/832` reachable profiles. The alpha candidates won `281`, `260`, and `240` respectively. Harm increases monotonically with alpha, and even alpha `0.05` fails every aggregate and early-combat guardrail.

## Interpretation

The full candidate was not bad only because 256 updates moved too far. The frozen update direction is already harmful close to production r16. Adding alpha `0.01`, reducing optimizer steps, or rerunning the same one-step recipe would now be post-outcome tuning with weak expected value.

The next useful work is a fresh-state action/Q-margin drift audit between production r16 and the frozen candidate direction. That audit should identify which action families and battle strata flip under small parameter changes, then motivate a different conservative objective, such as explicit action-margin preservation, before another training run.
