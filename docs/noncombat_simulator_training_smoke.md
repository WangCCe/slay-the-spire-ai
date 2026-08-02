# Bounded Non-Combat Simulator Training Smoke

## Scope

This is one pre-registered, offline-only CandidateRanker REINFORCE smoke over
route, shop, event, and card-reward decisions. It uses `sts_lightspeed` for the
environment and its declared baseline for combat and unsupported screens. It is
not a general trainer and is not imported by the live runtime.

The checked-in registration is
`reports/noncombat_simulator_training_smoke_20260802_input.json`. It binds:

- adapter and implementation commit `68369db646a074fa712fccddc6a650015197332d`;
- repaired fit input/report and native module physical identity;
- train seeds `1000..1031`, holdout seeds `2000..2063`, and model seed `0`;
- four full-batch Adam updates at learning rate `0.001`;
- floor-progress plus terminal-victory simulator reward; and
- 500 decisions per episode, 128 train episodes, and 600 seconds per execution.

The CLI was invoked once. It ran one primary execution and one identical replay
without a parameter, reward, seed, or cohort retry.

## Result

The canonical report is
`reports/noncombat_simulator_training_smoke_20260802/report.md`.

| Measure | Result |
| --- | ---: |
| Structural verdict | `pipeline_demonstrated_with_holdout_signal` |
| Replay identity | exact |
| Train episodes | 128 |
| Paired holdout seeds | 64 |
| Initial mean terminal floor | 11.156250 |
| Trained mean terminal floor | 14.078125 |
| Mean paired difference | +2.921875 |
| 95% paired-bootstrap interval | [1.703125, 4.171875] |
| Improved / unchanged / declined | 29 / 30 / 5 |
| Initial / trained victories | 0 / 0 |
| Primary / replay wall time | 281.39s / 273.43s |

All target categories were covered, every reported selection remained legal,
all episodes terminated, train and holdout seeds were disjoint, and both
executions stayed within the registered bounds. The model changed from its
seeded initialization. Canonical artifact hashes close through
`artifact_manifest.json`; measured timing remains noncanonical.

## Interpretation

The smoke demonstrates that the bounded simulator-policy pipeline can learn a
reproducible terminal-floor signal from the registered progress reward. It does
not demonstrate victory improvement, superiority to the current gameplay
policy, or simulator/live mechanics equivalence. The comparison is against the
same randomly initialized CandidateRanker, not a strong gameplay baseline.

Formal non-combat RL, another training pass, live policy loading, gameplay,
OPE reinterpretation, qualification, and promotion remain unauthorized.

## Next Gate

Any continuation requires a separate reviewed OpenSpec change. The next useful
step is an offline policy-validity study that freezes this model, pre-registers
new disjoint simulator seeds, compares against meaningful fixed baselines, and
reports category-level action shifts and failure concentration. The observed
holdout must not be reused for selection, tuning, or promotion.
