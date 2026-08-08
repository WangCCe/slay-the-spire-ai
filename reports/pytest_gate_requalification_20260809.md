# Pytest Gate Requalification - 2026-08-09

## Decision

The inclusive `commit` profile is requalified on the designated Windows
interpreter. It passed in 284.75 seconds, 15.25 seconds below the unchanged
300-second ceiling. The unchanged `full` profile subsequently passed with no
test exclusions.

This is a test-selection and feedback-latency result. It changes no production,
gameplay, simulator, RL, pytest, or test-body behavior.

## Frozen Attribution

| Measurement | Result | Pytest time | Gate or wall time | Use |
|---|---:|---:|---:|---|
| Pre-change `commit` | 4,638 passed, 18 skipped | 1,270.15s | 1,273.82s | Invalidated the old five-minute qualification |
| Baseline audit plus cross-fitted verifier | 157 passed, 1 skipped | 423.81s | 423.81s | Isolated verifier-heavy boundary |
| Baseline audit alone | 34 passed | 1.01s | 1.01s | Attributes about 422.8s to the paired verifier |
| Cross-fitted runtime file | 22 passed | 19.17s | 19.17s | Retained in `commit`; not materially heavy enough |
| Seven lifecycle/control files | 759 passed, 1 skipped | 320.32s | 320.32s | Measured lifecycle candidate group |
| Remaining set after first exclusions | 3,756 passed, 16 skipped | 502.59s | 502.59s | Located the remaining material slow files |

The lifecycle group included a 72.95-second real-registration node. The
remaining set was led by a 138.28-second historical baseline-study overlap
rejection, followed by material replay, fresh-process isolation, publication,
and deterministic-rendering nodes.

## Final Full-Only Boundary

The two pre-existing entries remain:

- `tests/test_noncombat_outcome_evidence_runner.py`
- `tests/test_noncombat_outcome_evidence_verifier.py`

The requalification adds these 13 measured whole-file entries:

- `tests/test_adaptive_route_opportunity_audit.py`
- `tests/test_noncombat_cross_fitted_empirical_successor_readiness.py`
- `tests/test_noncombat_cross_fitted_hierarchical_learning_control.py`
- `tests/test_noncombat_cross_fitted_hierarchical_learning_verifier.py`
- `tests/test_noncombat_current_baseline_evidence_study.py`
- `tests/test_noncombat_current_policy_simulator_bridge.py`
- `tests/test_noncombat_hierarchical_advantage_attribution.py`
- `tests/test_noncombat_hierarchical_policy_objective.py`
- `tests/test_noncombat_hierarchical_simulator_learning_experiment.py`
- `tests/test_noncombat_route_card_residual_ranker_poc.py`
- `tests/test_noncombat_simulator_baseline_warm_start.py`
- `tests/test_noncombat_simulator_rl_experiment.py`
- `tests/test_noncombat_state_conditioned_simulator_learning_experiment.py`

The manifest stores a nonblank measured rationale for every entry. New and
ordinary tests remain included by default. Changing an excluded test or source
it specifically owns requires that file or a stricter focused set directly;
the `commit` profile is not evidence for a file it excludes.

## Qualification Evidence

- RED: the exact repository-membership regression failed before the 13 entries
  were added.
- GREEN: `tests/test_run_test_gate.py` passed 39 tests in 1.88 seconds.
- Command construction: `commit --dry-run` emitted exactly 15 whole-file
  ignores; `full --dry-run` emitted none.
- OpenSpec: strict validation passed 78 items with zero failures before the
  final gates.
- Patch hygiene: `git diff --check` passed.
- Final `commit`: 3,593 passed, 16 skipped in 281.23 seconds of pytest and
  284.75 seconds including orchestration; exit code 0.
- Final `full`: 5,353 passed, 18 skipped in 2,283.45 seconds of pytest and
  2,287.43 seconds including orchestration; exit code 0.

Both final profiles were invoked exactly once. Neither was retried for
duration, and the manifest was not tuned after either run.

## Validity And Rollback

The five-minute claim remains valid only until a later conforming `commit`
invocation exceeds 300 seconds. Such an observation preserves its correctness
result but invalidates bounded-feedback qualification until another measured
requalification succeeds.

Rollback removes the 13 new manifest entries and this qualification record.
Direct pytest and the unchanged `full` profile remain available throughout.
Fresh gameplay validation is not applicable because live behavior did not
change.
