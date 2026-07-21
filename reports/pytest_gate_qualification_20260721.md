# Tiered Pytest Gate Qualification - 2026-07-21

## Status

The `commit`, `protocol`, `gameplay`, and `noncombat-evidence` profiles were
qualified with `D:\anaconda\envs\stsai\python.exe`. The unchanged `full`
profile was also run once. It preserved one known timing-sensitive
stream-silence failure; the permitted one-node diagnosis then passed.

No gameplay run was required. No test is removed from `full`: `full` invokes
the configured pytest suite without `full_only` exclusions.

## Baseline

The pre-qualification full baseline was 3,456 tests in `33:34`, with one
timing-sensitive evidence-runner failure. That failing node passed alone in
3.08s. The focused coordinator/startup baseline was 32 tests in 0.70s.

The current full run collected 3,491 tests, reflecting tests added after that
baseline. Its result is recorded below rather than rewritten as a pass.

## Final Manifest Membership

`tests/test_gate_manifest.json` remains unchanged. Its `full_only` entries are
whole files and remain the minimal exclusion set:

| Path | Rationale | Measured evidence |
|---|---|---|
| `tests/test_noncombat_outcome_evidence_runner.py` | Subprocess, crash-recovery, and temporary Git replay matrix. | The fresh full-versus-commit difference for the two existing whole-file entries was 1,369.54s (22:49.54), material relative to the five-minute commit budget. |
| `tests/test_noncombat_outcome_evidence_verifier.py` | Independent verifier subprocess and historical Git replay matrix. | The same fresh combined measurement supports retaining this existing whole-file exclusion; no node-level exclusion is used. |

The `commit` profile completed in 226.02s, so it was below the five-minute
threshold by 73.98s. No additional `full_only` file was added: the threshold
was already met, and no separate candidate had material evidence requiring a
new whole-file rationale.

## Profile Results

All qualification commands used the production Windows interpreter from the
repository root.

| Profile | Command | Result | Pytest duration | Runner duration |
|---|---|---:|---:|---:|
| `protocol` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py protocol` | 74 passed | 7.77s | 10.39s |
| `gameplay` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay` | 271 passed | 7.59s | 9.34s |
| `noncombat-evidence` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py noncombat-evidence` | 329 passed | 72.03s | 75.27s |
| `commit` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit` | 2,781 passed | 221.71s | 226.02s |

## Unchanged Full Result

Command:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Result: `3490 passed, 1 failed in 1591.20s (0:26:31)`; runner duration
`1595.56s`. The runner result is retained unchanged.

The failure was the known timing-sensitive node:

```text
tests/test_noncombat_outcome_evidence_runner.py::test_stream_silence_post_handoff_child_owns_unchanged_binary_streams
```

The allowed one-time diagnosis used:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_stream_silence_diagnosis tests/test_noncombat_outcome_evidence_runner.py::test_stream_silence_post_handoff_child_owns_unchanged_binary_streams
```

It passed: `1 passed in 1.90s`. This diagnostic did not retry or alter the
failed `full` result.

## Execution Note

The first sandboxed profile attempts failed because pytest could not create or
enumerate the runner's repository-local `.pytest_gates/<profile>` base-temp
directory (`WinError 3` followed by `WinError 5`). The required production
profile commands were then executed outside the Codex filesystem sandbox with
the same interpreter. This is an execution-environment concern, not a
manifest, test, or gameplay failure.

## Focused Verification

The runner-focused regression command was run after the artifact edits:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_test_gate_final tests/test_run_test_gate.py
```

Result: recorded in the Task 3 completion report.

`openspec validate add-tiered-pytest-gates` and `git diff --check` were also
run after the artifact edits. The runner-focused suite passed: `35 passed in
1.75s`; OpenSpec reported `Change 'add-tiered-pytest-gates' is valid`; and the
whitespace check reported no errors.

## Scope

Changed deliverables are this report, `docs/testing.md`, and the OpenSpec task
checklist. The manifest was reviewed but intentionally not changed. No
gameplay code, Communication Mod configuration, runner implementation, or
unrelated reports were modified.
