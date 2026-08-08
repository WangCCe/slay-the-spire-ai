## Context

The original gate qualified on 2026-07-21 with two `full_only` files. The
repository has since added 56 test files, primarily source-only RL evidence,
full lifecycle, Git replay, and independent-verifier suites. On 2026-08-09 the
unchanged `commit` semantics passed 4,638 tests with 18 skips in 1,273.82
seconds.

Three fresh measurements partition the drift without changing test code:

- the new baseline audit plus cross-fitted verifier passed 157 tests with one
  skip in 423.81 seconds; the audit file alone passes in 1.01 seconds;
- seven lifecycle/control-plane candidates passed 759 tests with one skip in
  320.32 seconds, with individual nodes up to 72.95 seconds;
- the remaining commit set after those exclusions passed 3,756 tests with 16
  skips in 502.59 seconds, led by a 138.28-second historical baseline-study
  overlap check.

The existing runner already provides the correct mechanism. The drift is in
the manifest classification and in treating a historical qualification as a
permanent timing fact.

## Goals / Non-Goals

**Goals:**

- Restore the measured `commit` wall time to at most 300 seconds.
- Keep all ordinary and newly added tests inclusive by default.
- Move only measured whole-file evidence/lifecycle boundaries to `full_only`.
- Preserve direct focused validation for code that owns an excluded file and
  preserve every test in `full`.
- Record enough evidence to detect and respond to later timing drift.

**Non-Goals:**

- Change a test body, assertion, fixture, pytest configuration, or runner.
- Add parallel execution, retries, markers, dependencies, or Git hooks.
- Claim that `full` is fast or run it as part of every ordinary commit.
- Change production, gameplay, CommunicationMod, simulator, or RL behavior.

## Decisions

### Extend the existing whole-file boundary

Keep manifest schema v1 and add these 13 measured files to `full_only`:

- `tests/test_noncombat_cross_fitted_hierarchical_learning_verifier.py`;
- `tests/test_noncombat_cross_fitted_hierarchical_learning_control.py`;
- `tests/test_noncombat_hierarchical_simulator_learning_experiment.py`;
- `tests/test_noncombat_state_conditioned_simulator_learning_experiment.py`;
- `tests/test_noncombat_cross_fitted_empirical_successor_readiness.py`;
- `tests/test_noncombat_simulator_rl_experiment.py`;
- `tests/test_noncombat_current_policy_simulator_bridge.py`;
- `tests/test_adaptive_route_opportunity_audit.py`;
- `tests/test_noncombat_current_baseline_evidence_study.py`;
- `tests/test_noncombat_route_card_residual_ranker_poc.py`;
- `tests/test_noncombat_hierarchical_policy_objective.py`;
- `tests/test_noncombat_simulator_baseline_warm_start.py`;
- `tests/test_noncombat_hierarchical_advantage_attribution.py`.

The first seven form the measured 320.32-second lifecycle group apart from the
separately measured verifier. The last five contain the material slow nodes
from the 502.59-second remainder. This leaves an observed remainder near 263
seconds before orchestration, providing margin under the five-minute ceiling.

Alternative: switch `commit` to an explicit allow-list. Rejected because new
ordinary tests could silently miss routine validation. Alternative: add
markers or xdist. Rejected because both require broader test or dependency
changes and introduce a larger correctness surface than reclassification.

### Require direct focused coverage for excluded ownership

Documentation will state that changing a `full_only` file or its owned source
requires that exact file (or a stricter focused set) before `full`. The ordinary
`commit` gate is not evidence for an excluded file. This keeps fast routine
feedback from becoming a substitute for relevant source-only lifecycle tests.

### Treat timing qualification as expiring evidence

The main specification will retain the 300-second ceiling and add an explicit
drift scenario. A later observed run above the ceiling invalidates the previous
bounded-feedback claim until a measured requalification closes it. The runner
does not enforce a timeout because an artificial cutoff would discard useful
correctness evidence and could leave pytest children alive.

### Qualify once at each final boundary

Use the measurements already collected to choose the manifest once. Run the
focused runner regressions, then one final `commit` qualification. Because the
manifest and `full_only` boundary change, run `full` once afterward and record
its actual result and duration without retrying merely for slowness.

## Risks / Trade-offs

- [Risk] Fifteen total `full_only` files weaken routine coverage. -> Require
  direct focused execution for owned changes, retain inclusive semantics for
  every unlisted test, and keep `full` unchanged.
- [Risk] The predicted remainder still exceeds five minutes. -> Record the run
  as failed requalification and do not claim bounded feedback or silently tune
  the list from the failed run.
- [Risk] `full` takes substantially longer than the previous 33-minute
  baseline. -> Invoke it once with process liveness monitoring and preserve the
  result without retrying solely for duration.
- [Risk] Future source-only files recreate the drift. -> Make observed
  over-ceiling timing an explicit qualification invalidator.

## Migration Plan

1. Push this plan and the archived original change before implementation.
2. Add manifest-contract regressions for exact validated membership and update
   the 13 whole-file entries plus documentation.
3. Publish a qualification report containing all three attribution runs.
4. Run runner-focused tests and one final `commit` profile.
5. Run the unchanged `full` profile once because test infrastructure changed.
6. Record both gates, update project direction, sync the delta, archive, commit,
   and push.

Rollback removes only the 13 manifest entries and requalification records. It
does not alter tests or the full-suite universe.

## Open Questions

None.
