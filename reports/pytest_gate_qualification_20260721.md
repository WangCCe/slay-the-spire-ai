# Tiered Pytest Gate Qualification - 2026-07-21

## Status

The `commit`, `protocol`, `gameplay`, and `noncombat-evidence` profiles were
qualified with `D:\anaconda\envs\stsai\python.exe`. The unchanged `full`
profile was also run once during the original qualification and once after the
final-review runner fix. Both full runs preserved the same known
timing-sensitive stream-silence failure; the original permitted one-node
diagnosis passed, and no diagnosis or retry was run after the fresh final-review
full result.

No gameplay run was required. No test is removed from `full`: `full` invokes
the configured pytest suite without `full_only` exclusions.

## Baseline

The pre-qualification full baseline was 3,456 tests in `33:34`, with one
timing-sensitive evidence-runner failure. That failing node passed alone in
3.08s. The focused coordinator/startup baseline was 32 tests in 0.70s.

The original qualification full run collected 3,491 tests. The fresh
final-review full run collected 3,495 tests after four runner regressions were
added. Both original results are recorded below rather than rewritten as
passes.

## Final Manifest Membership

`tests/test_gate_manifest.json` remains unchanged. Its two `full_only` entries
are whole files and remain the minimal exclusion set. Each file was measured
alone with the production Windows interpreter, `-p no:cacheprovider`, and a
different repository-local basetemp:

| Path | Exact result | Pytest duration | Wall duration | Decision |
|---|---:|---:|---:|---|
| `tests/test_noncombat_outcome_evidence_runner.py` | 393 passed | 536.15s (08:56) | 537.44s | Retain. Its subprocess, crash-recovery, and temporary Git replay matrix exceeds the entire five-minute commit budget by itself. |
| `tests/test_noncombat_outcome_evidence_verifier.py` | 317 passed | 992.45s (16:32) | 995.04s | Retain. Its independent verifier subprocess and historical Git replay matrix exceeds the entire five-minute commit budget by itself. |

Commands and unique leaves:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\qualification-runner-1c5e96d7fefd47d5a430af9151d07c27 tests/test_noncombat_outcome_evidence_runner.py
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\qualification-verifier-e78fc35b68714ecaafdb20d8f61f1ae5 tests/test_noncombat_outcome_evidence_verifier.py
```

## Combined Commit Qualification

The earlier combined qualification remains separate from the per-file
measurements. The `commit` profile completed with `2,781 passed in 221.71s` and
runner duration `226.02s`, below the five-minute threshold by 73.98s. The fresh
full-versus-commit difference for the two existing whole-file entries was
1,369.54s (22:49.54). No additional `full_only` file was added.

## Profile Results

All qualification commands used the production Windows interpreter from the
repository root.

| Profile | Command | Result | Pytest duration | Runner duration |
|---|---|---:|---:|---:|
| `protocol` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py protocol` | 74 passed | 7.77s | 10.39s |
| `gameplay` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay` | 271 passed | 7.59s | 9.34s |
| `noncombat-evidence` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py noncombat-evidence` | 329 passed | 72.03s | 75.27s |
| `commit` | `D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit` | 2,781 passed | 221.71s | 226.02s |

## Original Unchanged Full Result

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

## Fresh Final-Review Full Result

Exactly one fresh full gate was run after the runner and test-infrastructure
changes:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

The runner printed the unique basetemp
`D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\full-5608b2bbb0374bb89a371d943c411d0e`
before invoking pytest. The original result was
`1 failed, 3494 passed in 1715.75s (0:28:35)`; runner duration `1720.47s` and
exit code 1. The same stream-silence PID-liveness node failed. No retry or
direct diagnosis was run, and this result is not rewritten as a pass.

## ACL And Cleanup History

During the original qualification, fixed `.pytest_gates/<profile>` leaves
became inaccessible under the Codex filesystem sandbox. Attempts first
reported `WinError 3` and then `WinError 5`; the fixed leaf meant that residue
could poison later invocations. The controller subsequently removed the
ACL-locked `.pytest_gates` residue outside the sandbox. At head `055bfef5d`,
the directory was absent.

The final-review qualification preserved two additional infrastructure-invalid
sandbox attempts rather than treating them as test measurements. With the
shared parent absent, the first direct runner-file command reported `28 passed,
365 errors in 44.39s` and `46.76s` wall before `WinError 3`. After creating only
the shared parent, a second unique leaf still received sandbox ACLs; progress
showed 28 passed and 365 setup errors, pytest session cleanup raised `WinError
5`, and wall duration was `192.57s`. No locked leaf was cleaned or reused.
Valid standalone measurements and the fresh full gate therefore ran outside
the filesystem sandbox with new unique sibling leaves.

The final runner now creates only the ignored `.pytest_gates/` parent and gives
every invocation a unique `<profile>-<UUID>` leaf. It performs no retry and no
cleanup that can rewrite the result.

## Focused Verification

The runner-focused regressions were run after the code and ignore-policy edits:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_tiered_final_verify tests/test_run_test_gate.py
```

Result: `39 passed in 2.68s`. The RED evidence was three intended failures for
missing pre-executor output, fixed basetemp reuse, and missing Git ignore
coverage, followed by one intended failure for the missing shared-parent
creation behavior.

`openspec validate add-tiered-pytest-gates` reported `Change
'add-tiered-pytest-gates' is valid`. `git diff --check` exited 0 with no
whitespace errors.

## Scope

Final-review changes are limited to `scripts/run_test_gate.py`,
`tests/test_run_test_gate.py`, `.gitignore`, this report, `docs/testing.md`, and
the OpenSpec task checklist, plus the requested ignored SDD report. The test
gate manifest was reviewed but intentionally not changed. No gameplay code,
Communication Mod configuration, or unrelated tracked/untracked content was
modified.
