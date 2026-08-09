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

`protocol`, `gameplay`, and `noncombat-evidence` are focused domain profiles.
`commit` runs the configured suite except for the explicit whole-file
`full_only` entries in `tests/test_gate_manifest.json`. `full` runs the
unchanged configured pytest suite, including every `full_only` file.
Each `full_only` entry has measured runtime evidence and a repository-owned
rationale. Exclusion applies only to routine `commit`: changing an excluded
file or source that it specifically owns requires running that file (or a
stricter focused set) directly before the complete boundary.
For this rule, a `full_only` file owns each source module it directly imports
or references as an executable path. Shared source may have multiple owning
files; run every affected owner, or a documented stricter focused set that
covers the same changed behavior.

| Change class | Required validation |
|---|---|
| Red-green iteration | Narrow node or relevant domain profile |
| Coherent code/test commit | Relevant focused tests, then `commit` |
| Pytest config, shared fixture, gate runner, or manifest | Runner-focused tests, then `full` |
| `full_only` test or source it specifically owns | Direct file or stricter focused set, then `commit` and `full` |
| Broad cross-domain refactor, merge, release, or phase close | `full` |
| Documentation only | No pytest unless executable examples or manifest change |

The runner never retries a failure and returns pytest's result unchanged.
The current 17-file `commit` boundary qualified with 3,571 passes and 16 skips
in 262.89 seconds including orchestration, 37.11 seconds below the five-minute
ceiling. Its unchanged `full` boundary passed 5,401 tests with 18 skips and no
exclusions. A later conforming `commit` invocation above five minutes
invalidates this timing claim until a measured requalification passes. The
runner does not retry a slow or failed result.
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
