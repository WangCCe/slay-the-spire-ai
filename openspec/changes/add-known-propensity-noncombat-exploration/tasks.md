## 1. Configuration And Exact Sampling Core

- [x] 1.1 Add failing tests for exploration-off behavior, configuration schema validation, hard rate/budget/category limits, path collisions, and invalid provenance.
- [x] 1.2 Implement immutable exploration configuration, proposal, candidate, distribution, and selection types in an isolated module with no Bottled, PyTorch, or checkpoint dependency.
- [x] 1.3 Add failing tests for unique candidate IDs, exact basis-point distributions, canonical state hashes, deterministic SHA-256 draws, selected-action probabilities, and byte-stable replay.
- [x] 1.4 Implement the exact fail-closed sampler and distribution replay validator, preserving integer numerator/denominator evidence alongside the compatible float field.

## 2. Shadow Proposal Adapters

- [ ] 2.1 Add card-reward regression fixtures proving the Current action is unchanged and `card_reward:skip` is proposed only when the selected card maps uniquely and skip is immediately legal.
- [ ] 2.2 Implement the side-effect-free card-reward proposal adapter and keep all non-abstention alternatives shadow-only.
- [ ] 2.3 Add shop regression fixtures covering purchase, purge, leave, duplicate offers, post-purchase waits, and immediate exit commands; assert proposal construction does not mutate shop state.
- [ ] 2.4 Implement the shop proposal adapter with `shop:leave` as the only executable alternative and explicit ineligibility reasons for transitional or ambiguous states.
- [ ] 2.5 Add event and route shadow records and tests proving they never replace the Current action under this change.

## 3. Persistence And Action Confirmation

- [ ] 3.1 Add failing tests for Current-arm and alternative-arm proposal writes, write failure, partial records, duplicate decision IDs, per-run alternative-attempt budgets, unresolved terminal decisions, and rejected or superseded transitions.
- [ ] 3.2 Implement append-only proposed/resolution records, stable session/trajectory/decision IDs, and atomic session-manifest creation with configuration and source hashes.
- [ ] 3.3 Implement category-specific confirmation for card take/skip and shop purchase/purge/leave, exporting only uniquely confirmed transitions as executed evidence.
- [ ] 3.4 Integrate persistence-before-return for both mixture arms and fail-closed fallback so an unwritable or ambiguous record always returns the unmodified Current action without a known-propensity claim.

## 4. Explicit Runtime Wiring

- [ ] 4.1 Add failing integration tests for absent, valid, invalid, and tracked-dirty `STS_NONCOMBAT_EXPLORATION_CONFIG` startup, including per-game controller reset and no session artifact on the default path.
- [ ] 4.2 Wire the explicit configuration into `main.py` and the bounded batch runner without editing CommunicationMod configuration or changing normal `optimized`/`combat_rl` defaults.
- [ ] 4.3 Add exploration-off and zero-rate equivalence tests over representative shop/card-reward fixtures, plus guards proving no pilot model or combat checkpoint is loaded or written.
- [ ] 4.4 Run a dry-run process smoke with the Windows production Python and verify startup, manifest provenance, default behavior, and clean shutdown before any nonzero exploration batch.

## 5. Canonical Export And Qualification Report

- [ ] 5.1 Add failing exporter tests for additive v3 exploration blocks, v1/v2 backward compatibility, exact probabilities, shadow/rejected/unresolved exclusions, and conservative run joins.
- [ ] 5.2 Implement confirmed exploration export with behavior policy ID, exact candidate distribution, selected probability, decision/session provenance, replay status, and source hashes.
- [ ] 5.3 Add failing validator/report tests for replay mismatches, candidate illegality, confirmation gaps, unique-trajectory counts, baseline/alternative support, outcome coverage, victories, and isolation failures.
- [ ] 5.4 Implement the offline replay validator and qualification report with separate `known_propensity_exploration_data_ready`, `ope_ready`, `causal_uplift_ready`, `formal_noncombat_rl_training_ready`, and `live_policy_promotion_ready` fields.

## 6. Fresh Gameplay Evidence And Verification

- [ ] 6.1 Run focused exploration/export tests, the full pytest suite with a writable basetemp, strict OpenSpec validation, and `git diff --check`; fix only failures attributable to this change, then commit the implementation so live evidence starts from a tracked-clean source commit.
- [ ] 6.2 Capture pre-session CommunicationMod and combat-checkpoint hashes, then run a small nonzero shop/card-reward smoke with Windows Python and no training; inspect fresh `.run` files, `ai_debug.log`, `communication_mod_errors.log`, proposal records, and confirmations before continuing.
- [ ] 6.3 If the smoke is clean, run a bounded fresh eval until the configured limit or the qualification minimum is reached; do not exceed the 10 percent category ceiling or two-attempt per-run budget to force support.
- [ ] 6.4 Freeze the exact input allowlist, at least 25 uniquely joined trajectories when available, replay/support/outcome report, artifact hashes, source commit, isolation comparison, and all blocking limitations.
- [ ] 6.5 Obtain independent raw-evidence and code review, resolve accepted findings with regressions, rerun focused/full verification, and leave OPE, causal uplift, formal RL, and live promotion blocked.
