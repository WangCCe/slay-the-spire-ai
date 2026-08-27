# Pytest Gate Drift Audit - 2026-08-27

## Decision

The 2026-08-09 r2 `commit` qualification is invalid. A fresh invocation of the unchanged 17-file boundary failed correctness and exceeded the fixed five-minute limit. Routine coherent changes must not cite the old 262.89-second qualification until a frozen replacement boundary passes once within 300 seconds.

This report is testing workflow evidence only. It grants no training, evaluation, OPE, model or native loading, gameplay, CommunicationMod, qualification, promotion, policy-quality, causal, or formal-RL authority.

## Observed Gates

| Profile | Selection | Result | Pytest time | Runner time | Status |
|---|---|---:|---:|---:|---|
| Raw full | All configured tests, no exclusions | 6,423 passed, 28 skipped, 230 failed | 2,868.18s | Not runner-mediated | Complete-boundary baseline failed |
| Commit profiling | Existing 17-file `full_only` boundary | 4,800 passed, 26 skipped, 20 failed | 1,174.83s | 1,177.80s | Correctness and timing qualification invalid |

Neither invocation was retried. The full invocation used an isolated Windows system-temp basetemp. The commit invocation used the registered runner's unique `.pytest_gates` basetemp and added only `--durations=50 --tb=short` through `PYTEST_ADDOPTS` for diagnostics.

## Commit Failure Clusters

The 20 commit failures reduce to three independent roots:

1. `tests/test_damage_fallback_guards.py`: one Reaper fixture constructs a `SimpleNamespace` without current `SimulationState.has_magic_flower`; production healing reads that field.
2. `tests/test_noncombat_current_baseline_replication.py`: three tests stop at `predecessor_source_identity_mismatch` before reaching the historical evidence branch they intend to exercise.
3. `tests/test_noncombat_reachable_event_option_semantics.py`: sixteen tests stop at `event_option_semantics_current_ast_mismatch`; actual Current-policy AST SHA-256 is `0b5c8dad7359c6a2fefba1a0315e699892a86bbec341179301e2529a8345083b`, while the bound identity expects `15fb21a410b5cc7a430b76d46171a2510651e78537aac21fc0e7dc28978bdbd9`.

No failing file will be added to `full_only` solely because it fails. Each root must be repaired or remain an explicit correctness blocker before timing candidates are frozen.

## Correctness Repairs

The three roots were repaired without changing gameplay or simulator behavior:

1. The Reaper regression fixture now supplies `has_magic_flower=False`, matching the complete current simulation state. Its exact node passed: `1 passed in 0.89s`.
2. The final Current-baseline replication now hashes its registered source files from planning commit `9c80b2c1bfeb0c017b43b07f5d5eb2a9c9cbd384`. Recomputing the historical aggregate produced the registered `83c86cee723e0b5421311daf35e73ad6a8dcf86fe4fae9d7c49cd0b70d0e26fc`; using today's worktree would incorrectly mix later behavior into historical evidence. The complete focused file passed: `33 passed in 9.73s`.
3. The reachable event contract remains the immutable 2026-08-03 identity. Current policy later added only the 2026-08-15 Scrap Ooze lethal-cost guard: its branch AST is `e3a9aeef20797c0b2cbaa56819c437e624ec0095e92fb38772da30d612a2dc99`, while every pre-existing branch retained its registered AST hash. Scrap Ooze observation semantics remain candidate-derived. The resolver now binds the exact compatible Current AST `0b5c8dad7359c6a2fefba1a0315e699892a86bbec341179301e2529a8345083b` without rewriting the historical contract identity. Focused validation passed: `21 passed in 4.14s`, plus `214 passed in 5.22s` across the current-policy bridge, diagnostic smoke, and reachable native-compatibility owner files.

The first non-elevated replication run ended with a Windows pytest basetemp cleanup `PermissionError` and is recorded only as infrastructure failure. Its single permitted fresh-scope elevated rerun produced the passing result above.

## Slow-Test Evidence

The commit invocation's slowest observed test calls included:

| Seconds | Test file | Node summary |
|---:|---|---|
| 32.36 | `test_noncombat_family_preserving_conditional_card_ranking.py` | deterministic checkpoint training |
| 31.39 | `test_noncombat_card_only_baseline_clipping_ablation.py` | dual-entry failure restoration |
| 30.66 | `test_noncombat_large_corpus_state_conditioned_card_ranking.py` | fixed-epoch no-improvement stop |
| 23.27 | `test_noncombat_card_only_baseline_clipping_ablation.py` | shared ablation branch advancement |
| 23.06 | `test_noncombat_card_only_native_baseline_rl_pilot.py` | residual concentration checkpoint stop |
| 22.97 | `test_noncombat_card_scorer_optimizer_replay_ablation.py` | decoded full-update replay |
| 22.12 | `test_noncombat_large_corpus_state_conditioned_card_ranking.py` | deterministic checkpoint training |
| 21.05 | `test_noncombat_card_only_behavior_sensitivity_training.py` | candidate-only blocker restoration |
| 20.21 | `test_noncombat_card_only_behavior_sensitivity_training.py` | censored chunk access accounting |
| 19.88 | `test_noncombat_card_only_native_baseline_rl_pilot.py` | rollout bootstrap ownership |

The top-50 text summary is insufficient to derive complete whole-file totals. A post-repair machine-readable profiling run is required before changing the manifest.

## Post-Repair Profiling And Frozen Boundary

The one permitted post-repair `commit` profiling invocation used the unchanged 17-file boundary and completed without retry:

- Result: `4,825 passed, 26 skipped` from 4,851 attributed testcases.
- Pytest time: 1,156.19 seconds.
- Runner time: 1,159.269308 seconds.
- JUnit whole-file sum: 1,141.726 seconds across 203 files.
- Machine-readable evidence: `reports/pytest_gate_commit_profile_20260828.json`.

The replacement candidate rule is frozen at every newly measured file with at least 10 seconds of whole-file testcase time. The exact 20 additions are:

| Seconds | Tests | File |
|---:|---:|---|
| 143.227 | 26 | `tests/test_noncombat_card_only_native_baseline_rl_pilot.py` |
| 117.800 | 70 | `tests/test_noncombat_card_acceptance_empirical_successor_runtime.py` |
| 87.089 | 83 | `tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py` |
| 83.010 | 5 | `tests/test_noncombat_card_only_behavior_sensitivity_training.py` |
| 69.575 | 7 | `tests/test_noncombat_large_corpus_state_conditioned_card_ranking.py` |
| 60.528 | 68 | `tests/test_noncombat_card_acceptance_empirical_successor_training_runner_verifier.py` |
| 57.955 | 7 | `tests/test_noncombat_family_preserving_conditional_card_ranking.py` |
| 53.333 | 5 | `tests/test_noncombat_card_only_baseline_clipping_ablation.py` |
| 53.070 | 71 | `tests/test_noncombat_card_acceptance_empirical_successor_verifier.py` |
| 29.781 | 143 | `tests/test_noncombat_card_acceptance_empirical_successor_control.py` |
| 25.200 | 13 | `tests/test_noncombat_card_counterfactual_ranking_training.py` |
| 23.364 | 2 | `tests/test_noncombat_card_scorer_optimizer_replay_ablation.py` |
| 22.085 | 11 | `tests/test_noncombat_ope_estimate_verifier.py` |
| 18.891 | 160 | `tests/test_noncombat_card_acceptance_empirical_successor_training_runner.py` |
| 15.700 | 35 | `tests/test_noncombat_hierarchical_simulator_learning_runtime.py` |
| 14.719 | 37 | `tests/test_noncombat_outcome_evidence_expansion.py` |
| 13.597 | 28 | `tests/test_audit_hierarchical_card_reward_credit_assignment.py` |
| 11.643 | 33 | `tests/test_noncombat_current_baseline_replication.py` |
| 11.512 | 31 | `tests/test_noncombat_cross_fitted_hierarchical_learning_seed_inventory.py` |
| 11.143 | 3 | `tests/test_noncombat_expanded_shop_ensemble_retraining.py` |

The additions total 923.222 measured seconds. Subtracting that observed work from the profiling runner time predicts 236.047 seconds for the frozen 37-file `commit` boundary, leaving about 64 seconds below the fixed ceiling. Each manifest rationale names the directly owned runner, verifier, fitting, subprocess, or publication lifecycle. These files remain included in `full` and require direct owner validation when their owned source changes.

Runner-focused validation passed `44 passed in 1.39s`. The generated frozen `commit` command contains exactly 37 ignores; the generated inclusive `full` command contains none. This set is frozen before final qualification and will not be changed in response to that result.

## Final Qualification

The frozen boundary was committed and pushed as `8d25635e4ab040eac728310e2fe1df96ca230b6e` before qualification. Its one permitted final `commit` invocation completed without retry or boundary changes:

- Result: `3,987 passed, 26 skipped`, zero failures and zero errors.
- Attributed testcases: 4,013 across 183 files.
- Pytest time: 226.45 seconds.
- Runner time: 229.334943 seconds.
- Fixed ceiling margin: 70.665057 seconds.
- Machine-readable evidence: `reports/pytest_gate_commit_qualification_20260828.json`.

The 37-file `commit` boundary is qualified for routine focused-plus-commit validation. The 2026-08-27 raw-full result remains the current complete-boundary baseline; raw full was not rerun solely for selection-equivalent telemetry, and generated `full` still contains zero exclusions.

## Boundaries

- Fixed success metric: one final frozen `commit` invocation exits zero and completes in at most 300 seconds including orchestration.
- `full` remains inclusive and unchanged; the 2026-08-27 failed run is retained as the current complete-boundary baseline and is not repeated solely for timing instrumentation.
- No automatic retry, parallel pytest, test deletion, skip markers, gameplay, CommunicationMod, native module, simulator fitting, or RL training is authorized.
