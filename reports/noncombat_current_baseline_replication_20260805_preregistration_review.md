# Final Current Baseline Replication: Preregistration Review

Date: 2026-08-05 (Asia/Shanghai)

## Decision

The final Current baseline replication is source-only preregistered and ready
to be committed and pushed. Empirical execution remains unauthorized. No
execution authorization, started journal, native import, environment, seed
access, or output artifact exists.

## Implementation And Registration

- Pushed implementation commit:
  `6d86f7a693cf71c7db656bc23c2f5ebd14fd31ba`
- Registration:
  `reports/noncombat_current_baseline_replication_20260805_input.json`
- Registration size: 10,362 bytes
- Registration SHA-256:
  `8a2a3948eb3e604b0aebb2296fa15c40dac7efb4005d2245e5f4d5c6c6043a46`
- Exact future command:
  `D:\anaconda\envs\stsai\python.exe analysis_scripts/noncombat_current_baseline_replication.py execute`

## Fixed Cohort

- Selection algorithm: first 80 ascending unexcluded integers at or above
  `60000`
- Tracked seed sources: 225
- Excluded historical, selected, reserved, compatibility, diagnostic,
  training, evaluation, and qualification seeds: 2,111
- Canary: `60000..60015` inclusive, 16 seeds
- Conditional holdout: `60016..60079` inclusive, 64 seeds
- The 80 selected seeds are unique, ordered, and disjoint from the complete
  tracked exclusion inventory.
- Seed inventory:
  `reports/noncombat_current_baseline_replication_20260805_seed_inventory.json`
- Seed inventory size: 5,459,044 bytes
- Seed inventory SHA-256:
  `c6b30ff50a7f28b73fc213c72362096ac3b756843cc860fa01aa38996944b222`

## Frozen Policies And Gates

- Current:
  `current_optimized_ironclad_a0_conservative_snapshot_v1`
- Control:
  `deterministic_first_candidate_control_v1`
- Canary requires 16 complete pairs, all four Current categories, zero
  unexpected failures, at most one Courier support row per policy, Current
  mean floor at least 15, and paired mean floor at least 0.
- Holdout requires 64 complete pairs, all four Current categories, zero
  unexpected failures, at most three Courier support rows per policy, Current
  mean floor at least 18, absolute bootstrap lower bound at least 15, paired
  mean floor at least 3, and paired bootstrap lower bound greater than 0.
- Bootstrap is fixed at 10,000 percentile resamples, confidence 0.95, seed
  `20260803`.
- Only exact `unsupported_shop_courier_restock_semantics` may become a
  conservative non-victory support row. Every other failure is terminal.

## Resource And Lifecycle Limits

- Two deterministic replays per policy and seed
- At most 500 target decisions per episode
- At most 64 canary policy executions and 600 canary seconds
- At most 256 conditional holdout policy executions
- At most 320 total policy executions and 1,800 total seconds
- The runner must write the durable started journal before native loading.
- A failed canary never accesses holdout.
- Any success, quality failure, blocker, interruption, timeout, or publication
  failure after the journal consumes this final identity. There is no retry,
  resume, seed replacement, threshold change, repair rerun, or successor.

## External Identity

- Windows runtime: `D:\anaconda\envs\stsai\python.exe`, Python 3.10.18,
  SHA-256
  `1528904a43037efee64b4d91fa73db1d5fac79c2be75aebc5d8b210b496e7e6c`
- Native module size: 4,225,024 bytes
- Native module SHA-256:
  `7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88`
- Simulator commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- Simulator physical source: 79 files, SHA-256
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`

## Source-Only Preflight

- Preflight:
  `reports/noncombat_current_baseline_replication_20260805_preflight.json`
- Preflight size: 1,724 bytes
- Preflight SHA-256:
  `6679ff7dac3056324bc56bb448d9bf0b4d45632be81891161f9362f281adfeed`
- Two independent calls returned byte-equivalent results.
- The preflight records registration canonical, seed inventory recomputed,
  external bytes hashed, output root absent, and tracked-clean preparation.
- It records environment constructed, native module imported, seed environment
  accessed, and execution authorization present as false.
- Registration and preflight keep every gameplay, reward, OPE, model fitting,
  formal RL, training, qualification, loading, promotion, target outcome,
  native, environment, seed, fresh-evidence, and execution authority false.

## Required Stop

Commit and push these exact preregistration bytes, then stop. A later tracked
execution authorization must bind the pushed preregistration commit, exact
registration SHA-256, exact command, cohort, limits, and final-attempt
semantics after explicit user approval. Preregistration itself cannot start the
replication.
