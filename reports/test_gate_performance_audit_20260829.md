# Commit gate performance audit

## Scope

This is a read-only audit of
`test_gate_timing_action_relative_successor_delta_ablation_20260829.json`.
It changes no test selection, assertion, runner behavior, gameplay behavior,
simulator behavior, model, or training recipe.

## Current boundary

- Profile: `commit`
- Result: 4,442 passed, 26 skipped, 21 deselected, exit code 0
- Collected outcomes: 4,468
- Runner wall time: 209.529 seconds
- JUnit-attributed test time: 189.568 seconds
- Collection, import, and runner remainder: 19.961 seconds
- Existing hard feedback ceiling: 300 seconds
- Previous node-exclusion qualification target: 240 seconds

The current boundary is qualified, but its margin below the 240-second target
has narrowed to 30.471 seconds. Across the twelve recorded commit timing runs
on 2026-08-29, test count grew from 4,330 to 4,468 and runner time grew from
158.192 to 209.529 seconds. The series contains material machine-load variance,
so the endpoint difference is evidence of pressure, not a per-test cost model.

## Concentration

- Slowest test: 8.080 seconds, or 3.9% of runner time.
- Slowest 10 tests: 38.201 seconds, or 18.2%.
- Slowest 25 tests: 63.879 seconds, or 30.5%.
- Slowest 100 tests: 114.309 seconds, or 54.6%.
- Slowest file: 11.959 seconds, or 5.7%.
- Slowest 10 files: 70.810 seconds, or 33.8%.

No single node dominates. Parallel pytest remains out of scope because this
suite exercises temporary Git repositories, child processes, environment
isolation, and shared runtime surfaces whose concurrency safety has not been
qualified.

## Narrow follow-up candidate

Propose a separate OpenSpec change named
`reduce-commit-gate-artifact-replay-cost`. Freeze these measured candidates
before implementation:

| Candidate | Seconds | Proposed treatment |
| --- | ---: | --- |
| Bound real-context parity/support replay | 8.080 | Node-level commit deselection |
| Bound event-ranker training artifact restore | 4.815 | Node-level commit deselection |
| Checkpoint interpolation publication roundtrip | 4.012 | Node-level commit deselection |
| Noncombat OPE estimate artifact file | 11.959 | Assess whole-file `full_only`; retain it in the `noncombat-evidence` profile |

The measured upper-bound saving is 28.866 seconds. It is not additive proof;
the replacement boundary must retain the containing files' ordinary tests,
require direct focused coverage for owned source changes, keep `full`
inclusive, and pass one frozen timing-enabled `commit` qualification at no
more than 190 seconds. If ownership cannot be stated narrowly or the frozen
qualification exceeds 190 seconds, retain the current boundary and close the
proposal without adding further exclusions.

The 4.546-second static event-semantics test is intentionally not a candidate:
it is ordinary behavioral coverage rather than historical artifact replay.

## Decision

Do not alter the gate inside the successor-delta ablation. Close that change on
its successful 209.529-second gate, then handle the candidate boundary as a
separate maintenance change before another long experimental phase. Do not run
the current successor-delta gate a second time for this audit.
