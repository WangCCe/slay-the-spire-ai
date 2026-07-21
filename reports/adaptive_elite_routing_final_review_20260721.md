# Adaptive Elite Routing Final Review - 2026-07-21

## Review Scope

- Reviewed range: `e1a559f37..8540a39de` (`21` commits).
- Method: read-only strongest-model whole-change review.
- Attempt 1 (`reports/adaptive_elite_routing_automated_qualification_20260721.md`)
  and attempt 2
  (`reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`)
  are preserved unchanged.

## Verdict

**FAIL.**

Critical findings: none.

### Important Product Findings

1. **Malformed-map fallback can revalidate and escape instead of producing one
   conservative fallback.**
   - References: `spirecomm/ai/agent.py` around line 2854;
     `openspec/changes/add-adaptive-elite-routing-baseline/specs/adaptive-elite-routing/spec.md`
     around line 79; `tests/test_map_routing_safety.py` around line 1786.
   - Impact: malformed routing input can leave the intended single conservative
     fallback contract and permit an escaping path rather than a bounded safe
     decision.

2. **The full-RL `create_agent` path ignores an explicit adaptive mode.**
   - References: `main.py` around line 565; `spirecomm/ai/rl/agent.py` factory
     around line 863; `tests/test_main_runtime_errors.py` around line 435.
   - Impact: a caller can explicitly select adaptive routing but receive a
     non-adaptive full-RL agent, making runtime mode selection inconsistent with
     the feature contract.

3. **The structured decision record omits required routing context and fallback
   evidence.**
   - References: `spirecomm/ai/agent.py` around lines 2967 and 3027;
     `openspec/changes/add-adaptive-elite-routing-baseline/specs/adaptive-elite-routing/spec.md`
     around line 99; `tests/test_map_routing_safety.py` around line 2241.
   - Impact: the record omits normalized `hp_pct`, `elite_seen`, and
     `last_rest_floor`; minimum and added elite counts; and the fallback
     candidate summary. This prevents the required decision-level audit trail.

### Important Procedural Finding

The corrected host-permission attempt 2 did not preserve final-head static
validation evidence. The current-final-head checks below close only that
procedural evidence omission. They do not resolve any product finding and do
not complete task 4.4.

## Minor Findings (Non-Blocking)

- Constructor docstrings need clearer coverage of the adaptive-routing state and
  dependencies.
- The qualification harness does not enforce clean-provenance conditions.

These are non-blocking relative to the findings above.

## Current-Final-Head Static Evidence

Executed after the read-only review at final head `8540a39de`; no tests or test
gates were run.

```text
> openspec validate add-adaptive-elite-routing-baseline
Change 'add-adaptive-elite-routing-baseline' is valid
exit code: 0
```

```text
> git diff --check e1a559f37..HEAD
(no output)
exit code: 0
```

```text
> git diff --stat e1a559f37..HEAD
 .../benchmark_adaptive_route_candidates.py         |  533 ++++++
 .../2026-07-21-adaptive-elite-routing-baseline.md  |  595 +++++++
 main.py                                            |    7 +-
 .../add-adaptive-elite-routing-baseline/design.md  |   29 +-
 .../proposal.md                                    |    3 +
 .../specs/adaptive-elite-routing/spec.md           |   50 +
 .../add-adaptive-elite-routing-baseline/tasks.md   |   41 +-
 ...ite_routing_automated_qualification_20260721.md |  219 +++
 ...omated_qualification_20260721_attempt-2-host.md |   76 +
 reports/adaptive_route_candidate_poc_20260721.json |  341 ++++
 reports/adaptive_route_candidate_poc_20260721.md   |   59 +
 ...oute_candidate_poc_20260721_attempt-1_fail.json |  341 ++++
 ..._route_candidate_poc_20260721_attempt-1_fail.md |   59 +
 ...ute_candidate_poc_20260721_attempt-2_clean.json | 1757 ++++++++++++++++++++
 ...route_candidate_poc_20260721_attempt-2_clean.md |   74 +
 spirecomm/ai/agent.py                              |  577 ++++++-
 spirecomm/ai/heuristics/map_routing.py             |  459 +++++
 .../adaptive_route_maps/full_height_dense.json     |   51 +
 .../adaptive_route_maps/full_height_sparse.json    |   51 +
 .../adaptive_route_maps/full_height_typical.json   |   51 +
 tests/test_adaptive_route_candidate_benchmark.py   |  303 ++++
 tests/test_main_runtime_errors.py                  |   15 +
 tests/test_map_routing_safety.py                   | 1583 +++++++++++++++++-
 23 files changed, 7201 insertions(+), 73 deletions(-)
exit code: 0
```

```text
> git status --porcelain=v1 --untracked-files=no
(no output; tracked worktree clean)
exit code: 0
```

Unrelated untracked artifacts were present and preserved. No tracked product,
training, or live-configuration file was changed for this evidence record.

## Required Disposition

- Task 4.4 remains unchecked.
- Live qualification is forbidden.
- The three Important product findings require a follow-up OpenSpec change and
  fresh qualification evidence. They must not be fixed within this attempt.
- The preserved static evidence closes only the procedural omission; it does not
  change this review verdict.
