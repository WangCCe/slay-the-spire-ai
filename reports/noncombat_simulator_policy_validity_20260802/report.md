# Non-Combat Simulator Policy Validity Study

- Verdict: `study_valid_without_baseline_signal`
- Quality: `baseline_signal_not_demonstrated`
- Registration SHA-256: `149a0ed451f52804561de34b213fb4602f6825740705b6c1cf98ab87e0748d10`
- Fresh paired seeds: 64
- Primary trained-minus-SimpleAgent floor interval: [-7.875000, -2.921875]
- Secondary trained-minus-initial floor interval: [1.375000, 4.250000]

## Policies

- smoke_trained: mean floor 14.562500, victories 0/64, categories card_reward, event, route, shop
- seeded_initial: mean floor 11.796875, victories 0/64, categories card_reward, event, route, shop
- native_simple_agent: mean floor 19.968750, victories 0/64, categories card_reward, event, route, shop

## Checks

- candidate_legality: `true`
- episode_count: `true`
- finite_metrics: `true`
- four_category_coverage: `true`
- model_immutability: `true`
- no_gradients: `true`
- replay_identity: `true`
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
- simulator_policy_validity: `false`
- simulator_training: `false`

## Limitations

- Floors and victories are simulator-only evidence.
- Combat and unsupported non-combat screens use the declared adapter baseline.
- Current and Bottled pilot models are excluded because no simulator feature/action bridge is validated.
- A floor signal does not authorize training, live loading, OPE, qualification, gameplay, or promotion.
- No alternate model, metric, seed cohort, or parameter retry is permitted under this change.
- The trained policy recorded zero simulator victories in this cohort.
