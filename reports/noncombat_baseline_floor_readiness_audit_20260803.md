# Non-Combat Baseline-Floor Readiness Audit

**Verdict:** `diagnostic_smoke_required`

Planning only. This audit grants no native, cohort, gameplay, reward, OPE, formal-RL, training, loading, qualification, or promotion authority.

## Candidate Roles

| Policy | Role | Eligible | Status |
| --- | --- | --- | --- |
| `current` | `eligible_non_teacher` | `true` | `structural_closure_required` |
| `native_simple_agent` | `auxiliary_deterministic_control` | `false` | `teacher_quality_gate_rejected` |
| `bottled` | `auxiliary_oracle` | `false` | `reference_only` |
| `seeded_initial` | `weak_control` | `false` | `not_credible_baseline_floor` |
| `smoke_trained` | `negative_policy_evidence` | `false` | `baseline_signal_not_demonstrated` |
| `simpleagent_warm_start` | `negative_policy_evidence` | `false` | `baseline_floor_not_demonstrated` |
| `structured_ranker` | `negative_policy_evidence` | `false` | `candidate_not_selected` |
| `route_card_residual` | `negative_policy_evidence` | `false` | `candidate_not_selected` |

## Structural Evidence

- Frozen Current bridge rows passed: `4`
- Completed Current own-trajectory rows: `0`
- Subsequent repairs close known code boundaries but do not reinterpret consumed failures.

## Unsupported Episodes

Every selected episode remains in the denominator. A declared support blocker counts as a non-victory at the last supported floor; it cannot be dropped, replaced, or retried. A future registration must fix an unsupported-rate ceiling.

## Blockers

- `current_own_trajectory_complete_row_absent`
- `baseline_floor_contract_missing:comparison_controls_fixed`
- `baseline_floor_contract_missing:absolute_quality_gate_fixed`
- `baseline_floor_contract_missing:paired_quality_gate_fixed`
- `baseline_floor_contract_missing:unsupported_rate_ceiling_fixed`
- `baseline_floor_contract_missing:replay_contract_fixed`
- `baseline_floor_contract_missing:bootstrap_contract_fixed`
- `baseline_floor_contract_missing:stop_rules_fixed`
- `baseline_floor_contract_missing:untouched_holdout_fixed`

## Next Prerequisite

`reused_development_seed_current_bridge_smoke`

The independent target-supported-outcome blocker remains unchanged.
