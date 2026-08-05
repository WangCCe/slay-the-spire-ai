# Non-Combat Action-Family Counterfactual Audit

## Evidence Boundary

This report recomputes distributions from hash-bound frozen scores. It
does not open checkpoints, replay seeds, inspect holdout rows, construct
an environment, load a production model, train, select, or promote a policy.

## Inputs

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `noncombat_state_conditioned_card_reward_collapse_audit_20260805.json` | 928451 | `1392d10a1d3f3746b63285677c3f269b9064959222b275bd2805eb791bf206d6` |
| `evaluation.json` | 20492084 | `bf76b4684e9c993c0fe6527d02e0c889521449bf525fabe8d36d2bd119042579` |
| `training_rows.json` | 126834076 | `1d19779b44ff5c8b2ea598307017af7b892b8b875395e22feb4b3d4eb5061eea` |

## Counterfactual Summary

| Phase | Category | Rows | Multi-family | Score-to-joint changes | Rate | Family H | Conditional H | Joint H |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| training | card_reward | 31571 | 31571 | 27106 | 0.858573 | 0.653692 | 0.666707 | 1.320399 |
| training | event | 9097 | 0 | 0 | 0.000000 | 0.000000 | 0.829041 | 0.829041 |
| training | route | 57256 | 0 | 0 | 0.000000 | 0.000000 | 0.314859 | 0.314859 |
| training | shop | 9180 | 6745 | 5724 | 0.623529 | 0.888494 | 0.445145 | 1.333640 |
| initial_canary | card_reward | 967 | 967 | 904 | 0.934850 | 0.693104 | 0.551525 | 1.244628 |
| initial_canary | event | 250 | 0 | 0 | 0.000000 | 0.000000 | 0.826072 | 0.826072 |
| initial_canary | route | 1699 | 0 | 0 | 0.000000 | 0.000000 | 0.329903 | 0.329903 |
| initial_canary | shop | 203 | 168 | 99 | 0.487685 | 1.089459 | 0.500325 | 1.589784 |
| trained_canary | card_reward | 1458 | 1458 | 353 | 0.242112 | 0.549058 | 0.800952 | 1.350010 |
| trained_canary | event | 564 | 0 | 0 | 0.000000 | 0.000000 | 0.817782 | 0.817782 |
| trained_canary | route | 3000 | 0 | 0 | 0.000000 | 0.000000 | 0.294958 | 0.294958 |
| trained_canary | shop | 663 | 455 | 380 | 0.573152 | 0.801717 | 0.437728 | 1.239445 |

## Family Mass

Means are conditioned on the family being available in the row.

| Phase | Category | Family | Opportunities | Flat | Hierarchical | Delta |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| training | card_reward | bowl | 265 | 0.202700 | 0.406086 | 0.203387 |
| training | card_reward | skip | 31306 | 0.191486 | 0.387540 | 0.196054 |
| training | card_reward | take | 31571 | 0.808420 | 0.612305 | -0.196115 |
| training | event | event_option | 9097 | 1.000000 | 1.000000 | 0.000000 |
| training | route | map_node | 57256 | 1.000000 | 1.000000 | 0.000000 |
| training | shop | buy_card | 6728 | 0.583361 | 0.356513 | -0.226848 |
| training | shop | buy_potion | 3542 | 0.264850 | 0.239920 | -0.024930 |
| training | shop | buy_relic | 2082 | 0.170591 | 0.218140 | 0.047549 |
| training | shop | leave | 9180 | 0.380561 | 0.473079 | 0.092518 |
| training | shop | remove_card | 4677 | 0.100135 | 0.242580 | 0.142445 |
| initial_canary | card_reward | bowl | 3 | 0.249954 | 0.497270 | 0.247316 |
| initial_canary | card_reward | skip | 964 | 0.249641 | 0.496053 | 0.246413 |
| initial_canary | card_reward | take | 967 | 0.750358 | 0.503943 | -0.246416 |
| initial_canary | event | event_option | 250 | 1.000000 | 1.000000 | 0.000000 |
| initial_canary | route | map_node | 1699 | 1.000000 | 1.000000 | 0.000000 |
| initial_canary | shop | buy_card | 168 | 0.536566 | 0.280143 | -0.256422 |
| initial_canary | shop | buy_potion | 114 | 0.278636 | 0.243957 | -0.034679 |
| initial_canary | shop | buy_relic | 58 | 0.168111 | 0.221581 | 0.053470 |
| initial_canary | shop | leave | 203 | 0.286091 | 0.403779 | 0.117688 |
| initial_canary | shop | remove_card | 138 | 0.096128 | 0.241349 | 0.145221 |
| trained_canary | card_reward | bowl | 21 | 0.151818 | 0.291948 | 0.140129 |
| trained_canary | card_reward | skip | 1437 | 0.121985 | 0.243825 | 0.121840 |
| trained_canary | card_reward | take | 1458 | 0.877585 | 0.755482 | -0.122103 |
| trained_canary | event | event_option | 564 | 1.000000 | 1.000000 | 0.000000 |
| trained_canary | route | map_node | 3000 | 1.000000 | 1.000000 | 0.000000 |
| trained_canary | shop | buy_card | 453 | 0.617776 | 0.407347 | -0.210429 |
| trained_canary | shop | buy_potion | 149 | 0.261057 | 0.227992 | -0.033065 |
| trained_canary | shop | buy_relic | 164 | 0.178210 | 0.208244 | 0.030034 |
| trained_canary | shop | leave | 663 | 0.419276 | 0.493406 | 0.074131 |
| trained_canary | shop | remove_card | 339 | 0.109273 | 0.245489 | 0.136215 |

## Bounded Conclusions

- Joint candidate probability is not a neutral deterministic projection
  of max-pooled family scores; score and joint argmax are reported separately.
- Event and route rows have one family, so family entropy alone provides no
  regularization there; conditional entropy remains a distinct quantity.
- The measured mass reallocations do not select a training objective, entropy
  coefficient, deterministic policy, or successor experiment.

## Authority

- deterministic_selection_authority: false
- experiment_execution_authority: false
- formal_rl_authority: false
- gameplay_authority: false
- holdout_access_authority: false
- model_loading_authority: false
- native_loading_authority: false
- policy_promotion_authority: false
- qualification_authority: false
- seed_access_authority: false
- training_authority: false
- training_objective_authority: false
