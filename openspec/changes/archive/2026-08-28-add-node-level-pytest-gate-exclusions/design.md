## Context

The gate currently has one granularity for reducing routine cost: a complete
test file can be listed in `full_only`. The current profile contains 4,221
testcases across 198 files. Its fresh runner time was 274.77 seconds, while an
earlier conforming run at the same source boundary took about 318.74 seconds.
The fresh timing report attributes 103.65 seconds to 21 isolated-process import
checks, each at least 4.5 seconds, embedded in files whose remaining tests are
fast and useful during routine commits.

## Goals / Non-Goals

**Goals:**

- Preserve ordinary tests from each affected file in `commit`.
- Remove only the 21 measured isolated-process nodes from routine execution.
- Keep direct pytest and `full` inclusive.
- Restore at least 60 seconds of margin below the five-minute feedback ceiling.

**Non-Goals:**

- Parallel pytest, persistent worker processes, caching, or automatic manifest
  mutation.
- Changing any test assertion, production module, gameplay, simulator, model,
  or training behavior.
- Making raw `full` a routine per-commit gate.

## Decisions

The manifest schema advances to version 2 and adds `commit_deselect`, a list of
objects with `node_id` and `reason`. The runner validates that each entry is a
unique nonblank pytest node ID under a configured test file. The `commit`
profile emits one `--deselect=<node_id>` argument per entry after its existing
whole-file ignores. `full` and positive domain profiles emit no deselections.

The initial list is frozen to 21 fresh-process import-isolation nodes measured
at 103.65 aggregate seconds in
`reports/pytest_gate_commit_profile_20260828_r2.json`. Ordinary semantic,
training-smoke, and publication tests remain included even when individually
slow. A stale deselection can only restore coverage and consume time; the
recorded qualification and exact-manifest regression expose that drift.

Runner regressions assert that `full` receives neither `--ignore` nor
`--deselect`, and a repository-manifest dry-run records the same invariant.
Because this change alters only commit selection, those checks plus the frozen
commit qualification replace an otherwise redundant raw-full invocation. The
latest raw-full boundary already took 2,868.18 seconds and reported 230 known
failures; repeating it cannot add selection evidence when its argv is proven
unchanged. Raw `full` remains required for phase close or any change that can
alter its configured test universe.

Whole-file `full_only` remains available for files whose complete lifecycle is
materially expensive. Node-level deselection is used here because moving the
affected files wholesale would remove hundreds of fast behavior regressions.
`pytest-xdist` was rejected because this suite uses Git repositories, process
environment, and shared runtime resources whose concurrency safety has not
been established. Shared subprocess pooling was rejected because it would
weaken the fresh-interpreter property these tests intentionally assert.

## Risks / Trade-offs

- [Risk] Routine commits no longer execute selected import-isolation checks. ->
  Require direct focused execution when an excluded node or the source it owns
  changes; retain every node in `full`.
- [Risk] The list grows without discipline. -> Require fresh per-node timing,
  a nonblank rationale, default inclusion for new tests, and a frozen boundary
  before qualification.
- [Risk] A renamed node becomes a no-op deselection. -> Treat this as safe
  coverage restoration; exact manifest tests and the bounded timing gate expose
  the stale entry without hiding a test.

## Migration Plan

1. Add RED parser and command-construction regressions for schema version 2.
2. Add the frozen 21-node manifest list and update documentation.
3. Run runner-focused tests and strict OpenSpec validation.
4. Prove `full` argv equivalence, then run one final frozen `commit`
   qualification and record its exact result.
5. Roll back by removing `commit_deselect`, reverting schema version 1, and
   restoring the current runner behavior.

## Open Questions

None. Additional exclusions require a separate fresh timing decision rather
than extension during this qualification.
