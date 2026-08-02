# Bounded Non-Combat Simulator Training Smoke

- Verdict: `pipeline_demonstrated_with_holdout_signal`
- Quality: `holdout_signal`
- Registration SHA-256: `9e8ab44f5777a0624fb5c12d8c56830623839654480e423868a853f598ce079a`
- Candidate legality: `true`
- Paired holdout seeds: 64
- Mean terminal-floor difference: 2.921875
- 95% paired-bootstrap interval: [1.703125, 4.171875]

## Checks

- candidate_legality: `true`
- four_category_coverage: `true`
- replay_identity: `true`
- seed_disjoint: `true`
- terminal_outcomes: `true`
- within_bounds: `true`

## Blockers

- None

## Authority

- formal_noncombat_rl: `false`
- live_gameplay: `false`
- live_policy_loading: `false`
- live_study_launch: `false`
- ope_reinterpretation: `false`
- policy_promotion: `false`
- qualification: `false`
- simulator_training_smoke: `false`

## Limitations

- Rewards and outcomes are simulator-only evidence.
- Combat and unsupported non-combat screens use the declared baseline.
- This smoke does not authorize formal RL, live loading, OPE, qualification, gameplay, or promotion.
- No hyperparameter, reward, seed, or cohort retry is permitted under this change.
