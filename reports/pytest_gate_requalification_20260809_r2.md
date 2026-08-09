# Pytest Gate Requalification R2 - 2026-08-09

## Decision

The prior 284.75-second `commit` qualification was invalidated. Its next conforming
invocation reported one failure after 3,638 passes and 16 skips, and completed
in 303.60 seconds. The frozen 17-file replacement boundary is now qualified:
its one-shot `commit` passed in 262.89 seconds, and unchanged `full` passed all
configured tests without exclusions.

This is test correctness, selection, and feedback-latency evidence. It grants
no training, evaluation, OPE, model/native loading, gameplay, CommunicationMod,
qualification, promotion, policy-quality, causal, or formal-RL authority.

## Baseline Reconciliation

| Boundary | Result | Pytest time | Gate time | Status |
|---|---:|---:|---:|---|
| Prior 15-file qualification | 3,593 passed, 16 skipped | 281.23s | 284.75s | Invalidated by the next conforming invocation |
| Invalidating invocation | 3,638 passed, 16 skipped, 1 failed | 300.24s | 303.60s | Correctness failed and timing exceeded 300s; not retried |

The count difference is exact: the pending card-acceptance audit contributes
46 new ordinary tests, so `3,593 + 46 = 3,639` non-skipped tests. The
invalidating invocation passed 3,638 of them and failed the existing runtime
source-mutation node when default deadline subtraction rounded to
`14400.000000000002`.

## Separate Correctness Repair

Commit `35b4249c0` replaced subtraction-based deadline validation with one
representable upper bound for episode and chunk entry. The two new boundary
regressions and original failed node passed three tests in 8.57 seconds. The
complete runtime file then passed 24 tests in 16.14 seconds. This direct bug
fix is separate from the gate capability and is not part of its rollback.

## Frozen Candidate Rule

The candidate inventory contains only the test delta since the prior
qualification and the sole failed owning file:

| Candidate | Fresh direct evidence | Selection calculation |
|---|---:|---:|
| `tests/test_audit_card_acceptance_conditional_choice.py` | 46 passed in 7.39s | Mandatory new delta; predicts 296.21s and only 3.79s margin |
| `tests/test_noncombat_cross_fitted_hierarchical_learning_runtime.py` | 24 passed in 16.14s | Failed owner; predicts 280.07s and 19.93s margin |

The fixed rule requires at least the prior qualification's 15.25-second
margin. The audit file alone is insufficient; adding the failed runtime owner
exceeds that margin. Git comparison from qualification commit `32fbdb263` to
the repaired source found only the runtime test change, while the untracked
pending audit is the only other test-tree delta. No third candidate is
eligible, and the boundary will not be tuned after the final run.

## Final Full-Only Boundary

The 15 prior entries remain. The frozen candidate adds exactly:

- `tests/test_audit_card_acceptance_conditional_choice.py`;
- `tests/test_noncombat_cross_fitted_hierarchical_learning_runtime.py`.

Changing either excluded file or source it specifically owns requires that
file or a stricter focused set directly. Ownership means a source module the
test directly imports or references as an executable path; shared source may
have multiple owners, all of which must run unless a documented stricter set
covers the changed behavior. `full` still applies no exclusions.

## Prequalification Evidence

- Deadline RED: two deterministic boundary regressions failed under the old
  subtraction guard.
- Deadline GREEN: original failure plus two boundary nodes passed 3 tests in
  8.57 seconds; the complete runtime file passed 24 tests in 16.14 seconds.
- Audit direct boundary: 46 tests passed in 7.39 seconds.
- Runner/manifest boundary: 39 tests passed in 1.53 seconds.
- Command construction: `commit --dry-run` emitted exactly 17 whole-file
  ignores; `full --dry-run` emitted none.
- Final focused boundary: 109 tests passed in 25.95 seconds.
- Python compilation, 79-item strict OpenSpec, `git diff --check`, and
  independent review passed with no remaining findings.

## One-Shot Qualification

- Final `commit`: 3,571 passed and 16 skipped in 259.47 seconds of pytest,
  262.89 seconds including orchestration; exit code 0 and exact expected count.
- Unchanged `full`: 5,401 passed and 18 skipped in 2,248.44 seconds of pytest,
  2,252.15 seconds including orchestration; exit code 0 and exact expected count.

Each final profile was invoked exactly once. Neither was retried, and the
exclusion set was not changed after either result. The qualified `commit`
margin is 37.11 seconds below the fixed 300-second ceiling.

## Rollback And Applicability

Rollback removes the two manifest entries, exact-membership updates,
testing/direction/report records, and synced specification delta. Direct pytest
and unchanged `full` remain available. Fresh gameplay validation is not
applicable because no live policy behavior changes.
