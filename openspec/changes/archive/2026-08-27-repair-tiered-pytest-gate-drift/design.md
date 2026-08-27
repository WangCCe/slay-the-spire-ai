## Context

The tiered gate was qualified on 2026-08-09 with 17 `full_only` files: `commit` passed in 262.89 seconds and `full` passed in 2,252.15 seconds. Since then, the suite grew materially. On 2026-08-27, raw full pytest reported 6,423 passes, 28 skips, 230 failures in 2,868.18 seconds. A fresh commit profiling run using the unchanged 17-file boundary reported 4,800 passes, 26 skips, 20 failures in 1,174.83 seconds of pytest and 1,177.80 seconds including orchestration.

The commit failures reduce to three independent drift clusters: one Reaper simulator fixture lacks the newly required `has_magic_flower` state; current-baseline replication rejects a stale predecessor source identity; and reachable event semantics reject a stale Current-policy AST identity. The slowest commit tests are concentrated in newer noncombat fitting/runtime files, but the current runner records only total wall time, so whole-file selection cannot be derived rigorously from the completed run.

## Goals / Non-Goals

**Goals:**

- Restore a green commit correctness baseline through three narrow, independently tested repairs.
- Produce deterministic machine-readable per-test and per-file timing evidence from one gate invocation.
- Freeze a measured replacement `full_only` boundary before one final commit qualification.
- Keep the default gate command and the inclusive full profile unchanged.
- Make focused plus commit the normal coherent-change boundary and reserve full for explicit complete boundaries.

**Non-Goals:**

- Delete, skip, mark, or weaken test bodies to obtain a timing result.
- Automatically infer or mutate `full_only` entries from one result.
- Retry, shard, parallelize, or tune a failed qualification.
- Repair every historical failure in the current full-only files.
- Change gameplay, simulator policy, reward, training, native-module, checkpoint, or CommunicationMod behavior.

## Decisions

### Repair correctness before changing selection

Each of the three commit failure clusters will receive a focused regression or binding audit and a separate minimal repair. No failing file becomes `full_only` merely because it fails. The profiler boundary is measured only after these focused repairs pass.

Treating failures as exclusions was rejected because it would convert a latency mechanism into a correctness bypass and make the final commit result untrustworthy.

### Reuse pytest JUnit for opt-in timing capture

The runner will accept an explicit timing-report path. Only for that invocation it will request pytest's built-in legacy JUnit output at a run-scoped temporary path, parse testcase duration and file identity after pytest exits, and publish a deterministic JSON summary containing profile, exit code, elapsed wall time, outcome counts, per-file totals, and slow tests. The requested final path must not pre-exist. The report is published for passing or failing pytest results and does not alter the returned exit code.

The default command receives no additional pytest arguments. A custom pytest plugin, JSON-report dependency, and output scraping were rejected: the plugin broadens collection behavior, the dependency is not installed, and text scraping is fragile.

### Prove selection equivalence directly

Runner regressions will compare the pytest argv before and after telemetry is enabled after removing only the JUnit output options. Commit ignores, profile targets, cache settings, basetemp, interpreter, and ordering must remain identical. This permits timing-only implementation work to use runner-focused tests plus commit without repeating full solely for output instrumentation.

Manifest selection changes still require exact command-construction tests and the one final commit qualification. The inclusive full command remains unchanged and is retained for release, phase close, broad cross-domain changes, and owned full-only source changes.

### Freeze candidates from file-level evidence

One post-repair profiling invocation will aggregate whole-file wall time. Candidate files must have material measured cost, a nonblank rationale, and explicit source ownership. The candidate set is frozen before the final commit invocation and cannot be expanded in response to a slow or failed result.

No fixed exclusion count is preregistered because the file-level evidence does not yet exist. The five-minute limit and unchanged complete boundary remain fixed.

## Risks / Trade-offs

- [JUnit time can differ slightly from runner wall time] -> Use file totals only for candidate attribution and use runner wall time for qualification.
- [Legacy JUnit file attributes can be absent for unusual collectors] -> Fail timing summarization for unattributable executed tests instead of guessing a file.
- [Historical source bindings may represent real semantic drift] -> Recompute and compare the bound semantic surface before rehashing; stop if behavior changed beyond the recorded contract.
- [Many moderate files may be required to recover five minutes] -> Preserve inclusive full coverage and require direct owner tests; do not weaken the ceiling or tune after qualification.
- [The final commit may still fail or exceed five minutes] -> Record the exact result once and leave the qualification invalid.

## Migration Plan

1. Add RED runner tests for timing-report validation, result preservation, deterministic aggregation, and selection equivalence.
2. Audit and repair the three correctness clusters independently with focused tests.
3. Implement opt-in JUnit capture and JSON summary without changing default profile argv.
4. Run runner-focused and repaired-cluster tests, then one profiling commit invocation.
5. Freeze and document the measured whole-file candidate boundary.
6. Run the final commit qualification exactly once; record pass/fail and duration without retry.
7. Roll back by removing telemetry, manifest additions, docs/report updates, and correctness repair commits. Existing profiles and full selection remain usable.

## Open Questions

The exact replacement `full_only` set remains evidence-dependent and will be resolved from the single post-repair file-level profiling report before final qualification.

