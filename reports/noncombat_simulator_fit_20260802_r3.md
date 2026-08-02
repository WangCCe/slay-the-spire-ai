# Non-Combat Simulator Fit Audit

- Verdict: `adapter_poc_ready`
- Simulator commit: `7476a81954020087da31d41d16fddf475746ec2d`
- Adapter source commit: `a810d6d0ce92c1ebab8483fb8819163fc76d54fe`
- Seeds: 20
- Clone candidates checked: 46
- Native baseline decisions checked: 770
- Historical reward candidates: 12/12

## Checks

- candidate_legality: `pass`
- clone_isolation: `pass`
- four_category_coverage: `pass`
- historical_prefix_agreement: `pass`
- historical_source_identity: `pass`
- native_baseline_candidate_mapping: `pass`
- native_baseline_four_category_coverage: `pass`
- native_baseline_non_mutation: `pass`
- native_baseline_repeated_seed_determinism: `pass`
- native_baseline_terminal_outcomes: `pass`
- provenance_identity: `pass`
- repeated_seed_determinism: `pass`
- terminal_outcomes: `pass`
- throughput_budget: `pass`

## Blockers

- None for the adapter POC fit gate.

## Authority

- formal_noncombat_rl: `false`
- live_gameplay: `false`
- live_policy_loading: `false`
- live_study_launch: `false`
- ope_reinterpretation: `false`
- policy_promotion: `false`
- simulator_policy_validity: `false`
- simulator_training_smoke: `false`

## Limitations

- Simulator outcomes are not live outcomes and do not enter live OPE or supported-victory counts.
- Combat uses the declared SimpleAgent baseline with battle potion use disabled.
- Neow, boss relics, campfires, treasure, and follow-up card selections are baseline-controlled.
- Historical agreement covers twelve early reward candidate sets, not full-run mechanics equivalence.
- The upstream save loader cannot import arbitrary non-combat live states.
- The native target query is valid only while target actions follow that baseline.
- Adapter fit and policy validity do not authorize formal simulator training.
