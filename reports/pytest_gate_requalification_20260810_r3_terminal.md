# Pytest Commit Gate Requalification R3 Terminal Report

## Verdict

`terminal_unqualified`

The one preregistered attribution invocation passed and produced trustworthy
machine-readable evidence, but the deterministically eligible files aggregate
to 258.760 seconds. This is 6.940 seconds below the preregistered 265.700-second
minimum. The r3 plan therefore prohibits a manifest edit and prohibits final
`commit` or `full` qualification runs.

No test, runner, manifest, pytest configuration, production source, simulator,
RL, model, checkpoint, gameplay, or CommunicationMod behavior was changed.

## Frozen Identity

- Planning commit: `150a845f8737c08787244b86f4e0141260ccaac3`
- Execution HEAD: `bba7dedb6f0365524bde6cddacf4efbbbc5157e0`
- Interpreter: `D:\anaconda\envs\stsai\python.exe`
- Repository and working directory: `D:\PycharmProjects\slay-the-spire-ai`
- Temp child: `C:\Users\20571\AppData\Local\Temp\codex-pytest-stsai\pytest-gate-r3-attribution-20260810-bba7dedb6`
- JUnit XML: `reports/pytest_gate_requalification_20260810_r3_attribution.xml`
- JUnit XML SHA-256: `27d48b7d0a2526316fa5867f469073380b31519c5d28d278f5f2504cb2d120bd`
- JUnit XML bytes: 93,480

## Exact Invocation

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\20571\AppData\Local\Temp\codex-pytest-stsai\pytest-gate-r3-attribution-20260810-bba7dedb6 --durations=50 -o junit_family=xunit1 -o junit_duration_report=total --junitxml reports\pytest_gate_requalification_20260810_r3_attribution.xml tests\test_audit_card_acceptance_objective_interventions.py tests\test_noncombat_card_acceptance_empirical_successor_control.py tests\test_noncombat_card_acceptance_empirical_successor_runtime.py tests\test_noncombat_card_acceptance_empirical_successor_seed_inventory.py tests\test_noncombat_card_acceptance_empirical_successor_verifier.py tests\test_noncombat_card_acceptance_objective.py tests\test_noncombat_card_acceptance_policy.py
```

The command was invoked exactly once after confirming that the temp child and
XML output did not exist. It exited zero with `347 passed in 265.82s`.

## Trust Checks

| Check | Observed | Required | Result |
|---|---:|---:|---|
| Process exit | 0 | 0 | pass |
| XML suite tests | 347 | 347 terminal tests | pass |
| XML testcase elements | 347 | 347 suite tests | pass |
| XML errors | 0 | 0 | pass |
| XML failures | 0 | 0 | pass |
| XML skipped | 0 | 0 terminal skips | pass |
| Explicit files in frozen set | 347/347 | 347/347 | pass |
| Frozen files represented | 7/7 | 7/7 | pass |
| Finite nonnegative times | 347/347 | 347/347 | pass |
| XML testcase time sum | 258.874s | recorded | pass |
| Pytest terminal wall | 265.820s | recorded | pass |
| Absolute residual | 6.946s | at most 30.000s | pass |

The XML suite-level time was 265.809 seconds. The selection calculation uses
the sum of every testcase `time`, not the suite-level time or orchestration
overhead.

## Frozen Per-File Attribution

| File | Tests | Testcase seconds | At least 5.00s |
|---|---:|---:|---|
| `tests/test_audit_card_acceptance_objective_interventions.py` | 38 | 7.292 | yes |
| `tests/test_noncombat_card_acceptance_empirical_successor_control.py` | 134 | 37.186 | yes |
| `tests/test_noncombat_card_acceptance_empirical_successor_runtime.py` | 56 | 110.474 | yes |
| `tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py` | 27 | 31.216 | yes |
| `tests/test_noncombat_card_acceptance_empirical_successor_verifier.py` | 50 | 62.201 | yes |
| `tests/test_noncombat_card_acceptance_objective.py` | 21 | 0.114 | no |
| `tests/test_noncombat_card_acceptance_policy.py` | 21 | 10.391 | yes |
| **All files** | **347** | **258.874** | n/a |
| **Eligible files** | **326** | **258.760** | **no aggregate qualification** |

The six individually eligible files explain 258.760 seconds. The fixed
aggregate requirement is 265.700 seconds, so the result fails closed. The
0.114-second objective file is ineligible and cannot be added. Residual session
overhead cannot be assigned to a file after measurement.

## Preserved Slow-Duration Table

```text
21.47s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_paired_chunk_update_applies_one_named_step_per_arm_and_preserves_frozen_state
16.32s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_verifier_reconstructs_training_checkpoint_and_frozen_bytes
12.21s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_checkpoint_verifier_rejects_frozen_state_drift
9.19s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_untouched_holdout_runs_each_arm_once_and_classifies_complete_evidence
9.05s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_training_collection_uses_write_ahead_candidate_then_control_hooks
8.62s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_verifier_reconstructs_holdout_bootstrap_and_outcome
8.25s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_holdout_bootstrap_uses_exact_seed_zero_draw_order_and_linear_quantiles
8.24s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_paired_frozen_evaluation_is_greedy_repeatable_and_state_immutable
6.79s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_family_only_shadow_adam_changes_only_clone_family_state
6.67s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_paired_bootstrap_checkpoint_is_canonical_and_restores_every_ranker_and_rng
6.38s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_paired_chunk_validates_both_arms_before_the_candidate_step
5.33s call     tests/test_noncombat_card_acceptance_policy.py::test_legacy_imports_do_not_load_the_new_capability
5.29s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_bootstrap_verifier_rejects_mapping_or_state_drift
5.09s call     tests/test_audit_card_acceptance_objective_interventions.py::test_existing_modules_do_not_load_objective_intervention_audit
5.02s call     tests/test_noncombat_card_acceptance_policy.py::test_fresh_import_avoids_every_prohibited_transitive_module
4.43s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_verifier_reconstructs_matched_bootstrap_without_torch
4.39s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_paired_cross_fitted_baselines_are_arm_local_and_advantages_are_unscaled
4.38s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_verifier_reconstructs_canary_outputs_chain_and_replays
4.19s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_holdout_verifier_rejects_pair_or_outcome_drift
3.78s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_only_one_complete_checkpoint_training_continuation_is_authorized
3.75s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_untouched_holdout_separates_concentration_failure_from_outcome
3.37s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_checkpoint_republication_rejects_ambiguous_staging
2.99s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_each_arm_has_one_exact_adam_group_and_replayable_moments
2.83s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_structural_canary_concentration_failure_skips_shadow
2.76s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_structural_canary_commits_first_outputs_before_exact_replay
2.33s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[reordered-closed source]
2.30s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_paired_training_rollout_uses_same_seed_fixed_arm_order_and_frozen_routing
2.28s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[successor_nested_dynamic_import-imports successor]
2.27s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[successor_import-imports successor]
2.24s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[successor_getattr_alias_dynamic_import-imports successor]
2.20s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[successor_dynamic_import-imports successor]
2.19s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[successor_importlib_module_alias-imports successor]
2.18s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[successor_getattr_dynamic_import-imports successor]
2.03s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_inventory_is_write_once_and_rejects_mutated_materialized_bytes
2.00s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_accepts_exact_synthetic_fixture
1.90s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[missing-missing]
1.89s setup    tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_verifier_reconstructs_training_checkpoint_and_frozen_bytes
1.82s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_historical_exclusion_roles_include_failed_and_untouched_reservations
1.81s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_build_inventory_accepts_pushed_publication_descendant
1.76s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_verify_inventory_reconstructs_without_selector_or_materializer
1.76s call     tests/test_noncombat_card_acceptance_empirical_successor_verifier.py::test_independent_canary_verifier_rejects_replay_or_artifact_drift
1.74s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_family_saturation_keeps_canary_and_holdout_zero_and_blocks_more_training
1.72s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_reviewed_consumed_evidence_manifest_reobserves_current_repository
1.70s call     tests/test_noncombat_card_acceptance_empirical_successor_runtime.py::test_exact_eight_chunk_coordinates_are_required_for_no_saturation_completion
1.70s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[extra-artifact root.*mismatch]
1.68s call     tests/test_noncombat_card_acceptance_empirical_successor_control.py::test_consumed_evidence_preservation_rejects_closed_mutation_matrix[changed-source.*mismatch]
1.66s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_verify_inventory_rejects_rehashed_build_launch_substitution
1.65s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_partial_started_receipt_blocks_before_source_discovery[truncated]
1.65s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_started_receipt_persists_and_blocks_retry_after_source_failure
1.65s call     tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py::test_build_inventory_rejects_source_drift_in_pushed_descendant
```

## Closeout Decision

- Do not add any of the seven files to `full_only` in r3.
- Do not edit `tests/test_gate_manifest.json`, `tests/test_run_test_gate.py`, or
  `docs/testing.md`.
- Do not run r3 final `commit` or `full` gates.
- Preserve this report and the JUnit XML, independently review the terminal
  interpretation, and archive the OpenSpec change without syncing its failed
  replacement-boundary delta into the main spec.
- Fresh gameplay validation is not applicable.

This result leaves the existing correctness evidence green and the five-minute
`commit` timing claim unqualified. A future change must use a newly justified,
pre-registered approach rather than reinterpret or retune r3.

## Independent Review

An independent read-only review recomputed the XML hash, byte count, suite and
testcase counts, every per-file aggregate, the 6.946-second residual, and the
6.940-second selection shortfall. It found no actionable issues and confirmed
that no manifest, runner-test, testing-doc, runner, or pytest-configuration
change exists and that no r3 final `commit` or `full` gate was invoked.
