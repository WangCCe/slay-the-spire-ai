# Non-Combat Simulator Baseline Warm Start

- Verdict: `study_valid_without_baseline_floor`
- Quality: `baseline_floor_not_demonstrated`
- Registration SHA-256: `2815274e61c7d4ad8e553190ca234d6303457d9543cd63def541637729340a7a`
- Replay identity: `true`
- Final test untouched: `true`

## Cohorts

- final_test: 32 seeds
- train: 32 seeds
- validation: 16 seeds

## Gates

- Validation: not demonstrated
- Final test: untouched

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
- simulator_rl_training: `false`
- simulator_training: `false`

## Limitations

- Demonstrations and rollout outcomes are simulator-only evidence.
- SimpleAgent is auxiliary supervision, not reward or permanent ground truth.
- This result does not authorize formal RL, live loading, gameplay, OPE, qualification, or promotion.
- Current and Bottled remain excluded until a simulator feature/action bridge is validated.
