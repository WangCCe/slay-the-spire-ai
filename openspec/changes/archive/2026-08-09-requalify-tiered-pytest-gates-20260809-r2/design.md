## Context

The 2026-08-09 requalification established a 284.75-second `commit`
baseline with 15 `full_only` files. The next conforming run included the new
card-acceptance audit tests and ended after 303.60 seconds with one failure in
`test_rollout_sampling_is_replayable_and_rejects_source_mutation`. The runtime
computed a default deadline as `now + 14400.0`, then rejected that same value
when `(deadline - now)` rounded to `14400.000000000002`.

The observed run is simultaneously correctness evidence and timing drift. It
cannot be retried under the old qualification. The prior qualification report
records the old 15-file boundary and its 3,593-pass result; the new invocation
adds exactly 46 tests from the pending audit file, yielding 3,638 passes plus
the one runtime failure. The pending audit source has passed those 46 tests
directly in 7.39 seconds. The prior report measured the unchanged 22-test
runtime file at 19.17 seconds but retained it because that cost alone was not
material against the old 284.75-second result.

## Goals / Non-Goals

**Goals:**

- Restore a green `commit` result at or below 300 seconds with measured whole-
  file exclusions only.
- Preserve inclusive collection for every other ordinary test and preserve
  the exact complete suite in `full`.
- Close the pending audit source boundary only after direct audit/runtime
  tests, one final `commit`, and one unchanged `full` are green.

**Non-Goals:**

- Change the 300-second ceiling, test assertions, pytest behavior, runner,
  dependencies, parallelism, or complete-suite membership.
- Change training objectives, candidate scoring, seeds, model state, gameplay,
  CommunicationMod, or the sealed r2 audit result.
- Retry a failed or slow qualification, or choose exclusions after seeing the
  final qualification result.
- Specify, archive, or roll back the separate runtime deadline behavior fix.

## Decisions

### Keep the deadline repair outside the gate capability

The failing runtime behavior is corrected and committed first as an ordinary
RED-to-GREEN bug fix. This change records its focused result only as a
qualification prerequisite. It neither defines runtime semantics nor combines
the behavior fix with test-selection publication.

### Freeze two measured whole-file exclusions before qualification

Add exactly:

- `tests/test_audit_card_acceptance_conditional_choice.py`, measured at 46
  passes in 7.39 seconds, containing source-only import isolation and isolated
  deterministic publication checks;
- `tests/test_noncombat_cross_fitted_hierarchical_learning_runtime.py`,
  measured at 22 passes in 19.17 seconds, containing Torch runtime rollout,
  update, checkpoint, and source-mutation coverage.

The complete post-failure candidate inventory is intentionally limited to the
only test delta since qualification and the only failed file:

1. Excluding the mandatory new audit file predicts `303.60 - 7.39 = 296.21`
   seconds, only 3.79 seconds below the ceiling and less than the previous
   qualification's 15.25-second margin.
2. Adding the already measured runtime file predicts `296.21 - 19.17 = 277.04`
   seconds, 22.96 seconds below the ceiling and above that prior margin.

The reproducible rule is therefore: include the new test delta, then include
the failed owning file only when the delta alone does not restore at least the
previous qualified margin. No other file was added, changed, or failed in the
observed gate, so no other candidate is eligible.

After the separate deadline fix, the runtime file passed 24 tests in 16.14
seconds. Substituting that fresher measurement predicts `296.21 - 16.14 =
280.07` seconds, leaving 19.93 seconds below the ceiling. The selected boundary
therefore remains unchanged and still exceeds the frozen 15.25-second margin
rule. Git comparison from the prior qualification commit confirms that the
runtime file and untracked pending audit file are the only test-tree changes.

Both selected files remain in `full`. Any change to either file or its owned
source requires direct focused execution before `commit`; therefore the
exclusion does not become a substitute for relevant correctness evidence.

Alternative: exclude only the new audit file. Rejected because subtracting
7.39 seconds from the observed 303.60-second run leaves too little normal-load
margin. Alternative: raise the ceiling. Rejected because the user explicitly
identified long feedback as an iteration bottleneck and the complete suite is
already retained separately.

### Qualify once after the boundary is final

The qualification environment is the current Windows machine, repository root
and working directory, `D:\anaconda\envs\stsai\python.exe`, the exact
`scripts/run_test_gate.py` command, and no deliberately concurrent CPU-heavy
task. With two new deadline regressions in the separately fixed runtime file,
the expected final `commit` collection is 3,571 passes and 16 skips; the
expected unchanged `full` collection is 5,401 passes and 18 skips.

First run the separately owned deadline nodes, both direct files,
runner/manifest regressions, strict OpenSpec, compilation, and diff checks.
Then run `commit` once and require exit zero at or below 300 seconds. Because
the manifest boundary changes, run unchanged `full` once. Any failure or over-
ceiling result is recorded without retry or post-result manifest tuning.

## Risks / Trade-offs

- [Risk] Two more exclusions reduce routine coverage. -> Require exact direct
  ownership validation and keep unchanged `full` as the phase-close boundary.
- [Risk] The predicted gate still exceeds five minutes or collection differs.
  -> Preserve the result as a failed requalification and stop; do not add
  another candidate afterward.
- [Risk] Full validation takes roughly 38 minutes. -> Invoke it once after all
  focused evidence is green and monitor the existing process to completion.

## Migration Plan

1. Commit and push a proposal-only commit containing exactly this complete
   OpenSpec planning directory, without pending audit or behavior source.
2. Complete and commit the deadline repair separately with direct focused
   evidence; do not include it in this capability's final commit.
3. Add the two frozen manifest entries, exact-membership regressions, testing
   docs, qualification report, and direction record.
4. Run focused runtime, audit, runner, OpenSpec, compile, and diff gates.
5. Run final `commit` once, then unchanged `full` once.
6. Sync and archive this change, commit the final manifest/docs/report/spec
   publication, then commit and push the pending audit source boundary.

Rollback removes the two manifest entries, their exact-membership regression,
testing/direction/report records, and synced specification delta. It does not
revert the separate deadline fix or alter direct pytest and the complete-suite
universe.

## Open Questions

None.
