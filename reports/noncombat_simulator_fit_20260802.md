# Non-Combat Simulator Fit Audit

- Verdict: `adapter_poc_ready`
- Simulator commit: `7476a81954020087da31d41d16fddf475746ec2d`
- Adapter source commit: `dbf67c01cd30c16d4eb2a6d9b45a1d9816898cbe`
- Seeds: 20
- Clone candidates checked: 46
- Historical reward candidates: 12/12

## Checks

- candidate_legality: `pass`
- clone_isolation: `pass`
- four_category_coverage: `pass`
- historical_prefix_agreement: `pass`
- historical_source_identity: `pass`
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
- simulator_training_smoke: `false`

## Limitations

- Simulator outcomes are not live outcomes and do not enter live OPE or supported-victory counts.
- Combat uses the declared SimpleAgent baseline with battle potion use disabled.
- Neow, boss relics, campfires, treasure, and follow-up card selections are baseline-controlled.
- Historical agreement covers twelve early reward candidate sets, not full-run mechanics equivalence.
- The upstream save loader cannot import arbitrary non-combat live states.
- A separate reviewed change is required before any simulator training smoke.
