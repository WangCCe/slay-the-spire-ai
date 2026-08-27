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

## Boundaries

- Fixed success metric: one final frozen `commit` invocation exits zero and completes in at most 300 seconds including orchestration.
- `full` remains inclusive and unchanged; the 2026-08-27 failed run is retained as the current complete-boundary baseline and is not repeated solely for timing instrumentation.
- No automatic retry, parallel pytest, test deletion, skip markers, gameplay, CommunicationMod, native module, simulator fitting, or RL training is authorized.
