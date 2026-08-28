# Commit Gate Duration Audit

## Decision

Do not change `commit` selection or install parallel-test tooling now. Keep
focused RED/GREEN validation during iteration and run exactly one `commit` gate
at each cohesive behavior-class boundary. Reserve `full` for explicit complete
boundaries. This addresses the observed iteration cost without weakening the
current fail-closed profile.

## Evidence

| Source boundary | Runner seconds | Tests | Passed | Skipped |
|---|---:|---:|---:|---:|
| action-relative CPU shadow | 158.19 | 4,330 | 4,304 | 26 |
| action-relative candidate | 165.12 | 4,353 | 4,327 | 26 |
| target-lethal guard fix | 206.55 | 4,356 | 4,330 | 26 |

The latest run was broadly slower rather than dominated by the new tests:

- Median latest/prior per-file duration ratio: `1.214` across 130 comparable
  files.
- 94 files slowed by at least 10%; 59 slowed by at least 25%; only 11 improved
  by at least 10%.
- Aggregate attributed test duration grew by 25.5%, while runner duration grew
  by 25.1%.
- `tests/test_action_relative_live_candidate.py` took 0.84 seconds in the
  latest run.

The stable median leaders were distributed across OPE artifact tests,
cross-fitted learning, event semantics, process-script tests, and large combat
guard files. No single new or domain-local test explains the variation.

## Boundary

The current profile remains conforming to the registered five-minute ceiling.
Adding more `full_only` exclusions now would trade broad default coverage and
ownership complexity for roughly tens of seconds, while the primary project
bottleneck is candidate quality and live information gain rather than this one
boundary run.

Reopen selection optimization only if one of these triggers occurs:

- a conforming `commit` run exceeds 300 seconds;
- the median of three conforming runs exceeds 180 seconds under comparable host
  load; or
- commit-gate waiting again consumes more project time than training,
  simulation, and candidate analysis combined.

If reopened, first measure and freeze domain-specific whole-file candidates,
retain direct focused owner validation, and perform one final qualification.
Do not install `pytest-xdist` until parallel safety and shared artifact isolation
have focused tests; it is not installed in the designated Windows environment.
