# Testing

Use the Windows production interpreter for gate profiles from the repository
root:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py protocol
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py noncombat-evidence
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

To capture machine-readable timings for one invocation, supply a new path
inside the repository:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit `
  --timing-report reports/pytest_gate_commit_timing.json
```

The report path must not already exist. Timing mode adds only pytest's built-in
legacy JUnit output, aggregates complete testcase evidence by file, publishes
the JSON report for passing or failing pytest results, and preserves pytest's
exit code. The runner does not retry. Without `--timing-report`, the pytest
command is unchanged.

`protocol`, `gameplay`, and `noncombat-evidence` are focused domain profiles.
`commit` runs the configured suite except for the explicit whole-file
`full_only` entries and node-level `commit_deselect` entries in
`tests/test_gate_manifest.json`. `full` runs the unchanged configured pytest
suite, including every excluded file and node.
Each `full_only` entry has measured runtime evidence and a repository-owned
rationale. Exclusion applies only to routine `commit`: changing an excluded
file or source that it specifically owns requires running that file (or a
stricter focused set) directly before the complete boundary.
For this rule, a `full_only` file owns each source module it directly imports
or references as an executable path. Shared source may have multiple owning
files; run every affected owner, or a documented stricter focused set that
covers the same changed behavior.

Each `commit_deselect` entry is a measured fresh-process import-isolation node
inside an otherwise useful routine test file. Only that node is removed from
`commit`; the rest of its file remains collected. Changing a deselected test or
the source entrypoint it imports or executes requires running the node, its
whole file, or a documented stricter focused set directly before `commit`.
Direct pytest and every positive domain profile ignore `commit_deselect`, and
`full` never emits `--ignore` or `--deselect`. New tests remain included by
default. Node exclusions are not skip markers and do not change test code.

| Change class | Required validation |
|---|---|
| Red-green iteration | Narrow node or relevant domain profile |
| Coherent code/test commit | Relevant focused tests, then `commit` |
| Pytest config, shared fixture, or complete-profile selection | Runner-focused tests, then `full` |
| Commit-only runner/manifest selection with exact inclusive-full argv regression | Runner-focused tests, then `commit`; retain `full` for the configured complete boundary |
| Selection-equivalent opt-in timing telemetry | Runner-focused tests, then `commit` |
| Excluded test or source it specifically owns | Direct node/file or stricter focused set, then `commit`; run `full` at the configured complete boundary |
| Broad cross-domain refactor, merge, release, or phase close | `full` |
| Documentation only | No pytest unless executable examples or manifest change |

The runner never retries a failure and returns pytest's result unchanged. The
measured 37-file `commit` boundary qualified on 2026-08-28 with 3,987 passes
and 26 skips in 229.33 seconds including orchestration, 70.67 seconds below the
five-minute ceiling. It replaced the invalidated 17-file boundary, which took
1,177.80 seconds and failed 20 tests on 2026-08-27. `full` remains the unchanged
inclusive complete boundary; the commit qualification is not evidence that the
latest raw-full baseline passed.

Later combat-RL test growth produced one conforming run at 318.74 seconds and
invalidated that timing qualification. The 2026-08-28 r2 profiling run passed
4,195 tests with 26 skips in 274.77 runner seconds and measured 21 fresh-process
import-isolation nodes at 103.649 aggregate testcase seconds. The frozen
schema-v2 boundary then qualified with 4,182 passes, 26 skips, and 21 deselected
nodes in 171.75 runner seconds. Runner regressions and a repository-manifest
dry-run proved `full` retains the ordinary inclusive argv; the known
2,868.18-second failing raw-full baseline was not repeated solely for equivalent
selection telemetry. Rollback removes the node entries and restores manifest
schema version 1; it does not alter test or production code.
Before launching pytest, an ordinary run prints and flushes the selected profile
and the fully assembled Windows command. `--dry-run` prints the same information
with an explicit dry-run label but does not create test state or launch pytest.

Each non-dry-run invocation uses a new repository-local basetemp named
`.pytest_gates/<profile>-<UUID>`. The shared `.pytest_gates/` directory is
ignored by Git. The runner creates that shared parent when needed but neither
reuses nor cleans invocation leaves, so an inaccessible sibling cannot affect a
later gate and no cleanup can rewrite a pytest result.

Direct pytest remains the rollback path when a gate command must be bypassed:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_manual
```
