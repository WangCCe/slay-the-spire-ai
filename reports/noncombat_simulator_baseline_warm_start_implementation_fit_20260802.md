# Non-Combat Simulator Baseline Warm-Start Implementation Fit

- Verdict: `implementation_fit_ready`
- Quality claim: `none`
- Reused seeds: `0..19`
- Demonstration rows: 770
- Episodes: 20
- Dataset SHA-256: `723cc6502920e4d7d5979764b2d08b7d4c4e0ddb200a5d57343c98391e3c25cf`
- Final model SHA-256: `c37124d76c12daba62c0dd56af6250b0d9cde0fd93980a20ad3773ca6369a593`

## Category Rows

- card_reward: 195
- event: 91
- route: 407
- shop: 77

## Checks

- candidate_mapping: `pass`
- collection_replay_identity: `pass`
- four_category_coverage: `pass`
- model_updated: `pass`
- provenance_identity: `pass`
- teacher_policy_identity: `pass`
- terminal_outcomes: `pass`
- training_replay_identity: `pass`
- within_bounds: `pass`

## Runtime

- Collection seconds: 60.995650, 58.330638
- Training seconds: 55.358325, 52.196647
- Total seconds: 250.188227

## Blockers

- None.

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

- Only already-observed adapter fit seeds 0 through 19 were reused.
- The report evaluates implementation behavior, not policy quality.
- SimpleAgent labels are auxiliary demonstrations, not reward or permanent truth.
- No validation, final-test, live, OPE, qualification, or promotion authority is granted.
- Measured runtime is machine-specific and excluded from later canonical study identity.
