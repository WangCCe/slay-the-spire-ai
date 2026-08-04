# Final Current Baseline Replication: Source-Only Implementation Verification

Date: 2026-08-05 (Asia/Shanghai)

## Decision

The versioned final-replication runner and its regressions are ready for one
source-only implementation commit. This verification does not preregister or
execute the empirical replication. Tasks 5 and 6 remain pending.

## Bound Scope

- OpenSpec change: `add-post-final-repair-current-baseline-replication`
- Planning parent and pushed `origin/master` before implementation:
  `9c80b2c1bfeb0c017b43b07f5d5eb2a9c9cbd384`
- Canonical preimplementation bytes: 12,106 bytes, SHA-256
  `c8ba9f4d0c496c3698e036d01cc222b8286522475bd0d1133c104f8161eb5675`
- Bound predecessor source aggregate: 24 files, SHA-256
  `83c86cee723e0b5421311daf35e73ad6a8dcf86fe4fae9d7c49cd0b70d0e26fc`
- The consumed study runner, Current policy, first-candidate control, bridge,
  gates, limits, registration, journal, rows, and terminal artifacts were not
  edited.

## Implementation

- Added `analysis_scripts/noncombat_current_baseline_replication.py` as a
  locked, versioned wrapper around the immutable predecessor runner.
- Added fixed first-ascending-unexcluded selection from `60000`, with exact
  16-seed canary and 64-seed holdout partitions.
- Added successor-specific schemas, verdicts, paths, lineage checks,
  all-false authority checks, repeatable preflight, exact separate execution
  authorization, durable lifecycle reuse, and `prepare`, `preflight`,
  `execute`, and `verify` commands.
- Added an explicit readiness-delta classifier. Only the historical incomplete
  `study_blocked / card_metadata_cost_invalid / Injury / 18 rows / no holdout`
  identity permits this proposal. Complete results, other blockers, and every
  final-successor result are terminal.

## Verification

- Successor regressions: `33 passed in 7.42s`.
- Focused task-4.1 selection covering successor, predecessor, Current bridge,
  adapter, event, shop, metadata, seed inventory, and readiness:
  `461 passed, 5 skipped in 121.52s`.
- `py_compile` passed with its cache outside the repository.
- `git diff --check` passed.
- Fresh-process predecessor recomputation verified all 7 canonical artifacts
  byte-for-byte, retained `study_blocked` and 18 partial rows, matched the old
  runner to the planning commit, and did not import the native module.
- Strict OpenSpec validation passed for this change (`1/1`) and globally
  (`66/66`).
- Registered partitioned `commit` gate passed:
  `3882 passed, 11 skipped in 329.71s`; gate elapsed time was 333.03 seconds.
  The gate exceeded the five-minute performance target but did not fail and
  was not retried.

## Authority And Isolation

- No native module was loaded and no real simulator environment was built.
- No game, CommunicationMod process, gameplay run, training, fitting, reward
  evaluation, OPE, checkpoint, qualification, loading, or promotion occurred.
- No successor seed inventory, exact cohort, registration, preflight,
  execution authorization, started journal, or output directory exists.
- All execution and downstream authority remains false.

## Next Gate

After this exact implementation commit is pushed, task 5 may regenerate the
tracked seed inventory and deterministically materialize the 80-seed cohort in
a separate source-only preregistration commit. Execution must still stop until
the user approves the exact pushed registration hash, command, limits, cohort,
and final-attempt semantics in a tracked authorization.
