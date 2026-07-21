# Adaptive Elite Routing Automated Qualification Attempt 1 Sandbox FAIL - 2026-07-21

## Result

**BLOCKED.** The focused production-interpreter regression passed, but the
required gameplay, commit, and unchanged full gates each failed during pytest
session cleanup with `PermissionError: [WinError 5]` on their generated
repository-local basetemp directories. These are not the documented
timing-sensitive stream-silence node, so no node diagnosis was run and no
qualification commit was created.

## Record Status

This is the canonical immutable attempt-1 managed-sandbox FAIL record. The original focused, gameplay, commit, and full gate evidence below is retained unchanged, including exact basetemps, durations, and exit codes. A corrected host-permission result, if authorized and executed, MUST be written only to `reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`.

## Gate Evidence

### Focused production-interpreter verification

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_adaptive_route_final tests/test_map_routing_safety.py tests/test_adaptive_route_candidate_benchmark.py tests/test_main_runtime_errors.py
```

- Printed profile: not applicable (direct pytest command).
- Resolved command: the command above.
- Basetemp: `.pytest_tmp_adaptive_route_final`.
- Count: `183 passed`.
- Duration: `14.09s`.
- Exit code: `0`.

### Gameplay gate

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
```

- Printed profile: `gameplay`.
- Resolved command:
  `D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\gameplay-64b234dee8aa45f0813a26cff7e22e97 tests/test_map_routing_safety.py tests/test_shop_screen_guards.py tests/test_event_choice_guard.py tests/test_ironclad_card_reward_guards.py tests/test_rest_guard.py tests/test_decision_context_guards.py tests/test_offline_decision_comparator.py`
- Unique basetemp: `D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\gameplay-64b234dee8aa45f0813a26cff7e22e97`.
- Count: no aggregate pytest count was printed; progress reached `97%` before
  session cleanup raised `PermissionError`.
- Duration: `16.07s`.
- Exit code: `1`.
- Failure: `PermissionError: [WinError 5] Access is denied` while pytest
  executed `cleanup_dead_symlinks()` for the generated basetemp.

### Commit gate

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
```

- Printed profile: `commit`.
- Resolved command:
  `D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\commit-7502bce838be469c9e2135ee55a013bf --ignore=tests/test_noncombat_outcome_evidence_runner.py --ignore=tests/test_noncombat_outcome_evidence_verifier.py`
- Unique basetemp: `D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\commit-7502bce838be469c9e2135ee55a013bf`.
- Count: no aggregate pytest count was printed; progress reached `100%` before
  session cleanup raised `PermissionError`.
- Duration: `707.37s`.
- Gate exit code: `1`.
- Harness collection exit code: `124` after `709.9s`; the gate had already
  printed its pytest result before the harness timeout.
- Failure: the same `PermissionError: [WinError 5] Access is denied` in
  pytest `cleanup_dead_symlinks()` for the generated basetemp.

### Unchanged full gate

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

- Printed profile: `full`.
- Resolved command:
  `D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\full-686867af39844b94aad17af9d16ab0a7`
- Unique basetemp: `D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\full-686867af39844b94aad17af9d16ab0a7`.
- Count: no aggregate pytest count was printed; progress reached `100%` before
  session cleanup raised `PermissionError`.
- Duration: `1237.76s`.
- Exit code: `1`.
- Failure: the same `PermissionError: [WinError 5] Access is denied` in
  pytest `cleanup_dead_symlinks()` for the generated basetemp.
- Stream-silence diagnosis: not run. The full-gate failure was not solely the
  documented timing-sensitive stream-silence node.

## Artifact And Scope Validation

```powershell
openspec validate add-adaptive-elite-routing-baseline
git diff --check e1a559f37..HEAD
git diff --stat e1a559f37..HEAD
```

- `openspec validate`: `Change 'add-adaptive-elite-routing-baseline' is valid`
  (exit `0`).
- `git diff --check`: clean (exit `0`).
- `git diff --stat`: `21 files changed, 6851 insertions(+), 68 deletions(-)`
  (exit `0`).
- Scope review of `git diff --name-only e1a559f37..HEAD`: implementation is
  confined to adaptive route logic, CLI initialization, route fixtures/tests,
  benchmark POC, reports, plan, and OpenSpec artifacts. No combat, shop,
  event, card-reward, campfire, checkpoint, training, or Communication Mod
  protocol files are present. Live game/config/training files were not touched.

## OpenSpec Status

- Marked from observed evidence: `3.7`, `4.1`, `4.2`, and `4.3`.
- Left unchecked: `4.4`; the independent final review has not occurred.

## Concern

The three tiered gate failures share a pytest temporary-directory cleanup
failure after test execution. This evidence does not qualify the implementation
for bounded live use. No production code, tests, scripts, live configuration,
or training artifacts were modified, and no commit was created.

## Post-Attempt Root-Cause Evidence

The failure is an execution-environment ACL failure, not an adaptive-route or test-assertion failure. pytest `9.0.2` reached `cleanup_dead_symlinks(basetemp)`, then `root.iterdir()` on the generated basetemp root before inspecting or unlinking a child. The direct single `tmp_path` node passed. The same node executed through parent-Python to a pytest-child failed. A minimal nested Python `mkdir(mode=0o700)` followed immediately by `iterdir()` failed in the managed sandbox, while the identical minimal nested mkdir/iterdir operation passed under host permission.

This evidence authorizes one corrected host-permission attempt of the unchanged `gameplay`, `commit`, and `full` gate commands, one attempt per profile with generated unique basetemps and unchanged manifest/thresholds. Focused verification is not rerun because it already passed `183` tests. The attempt-1 failures remain failures. Only the already-known stream-silence node retains its existing one diagnostic-run allowance when it is the sole full-gate failure; any other corrected-run failure stops qualification without another retry.
