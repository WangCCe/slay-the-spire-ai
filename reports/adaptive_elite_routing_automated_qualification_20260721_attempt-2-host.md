# Adaptive Elite Routing Automated Qualification Attempt 2 Host - 2026-07-21

## Result

**PASS.** The sole corrected host-permission sequence completed once, in order,
after reviewed commit `8facb9fea`. All three gate commands exited `0`.

- Execution surface: Codex shell with `sandbox_permissions=require_escalated`.
- Focused verification: not rerun; attempt 1 already recorded `183 passed`.
- Stream-silence diagnosis: not needed.
- Attempt 1: unchanged immutable sandbox FAIL evidence at
  `reports/adaptive_elite_routing_automated_qualification_20260721.md`.

## Gameplay Gate

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
```

Printed profile: `gameplay`.

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\gameplay-8587883b9da5405ca93f5d49021d2075 tests/test_map_routing_safety.py tests/test_shop_screen_guards.py tests/test_event_choice_guard.py tests/test_ironclad_card_reward_guards.py tests/test_rest_guard.py tests/test_decision_context_guards.py tests/test_offline_decision_comparator.py
```

- Unique basetemp:
  `D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\gameplay-8587883b9da5405ca93f5d49021d2075`.
- Count and pytest duration: `371 passed in 11.73s`.
- Gate duration: `14.36s`.
- Exit code: `0`.

## Commit Gate

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
```

Printed profile: `commit`.

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\commit-ca67a428694a4a4eb84ec471dc837f12 --ignore=tests/test_noncombat_outcome_evidence_runner.py --ignore=tests/test_noncombat_outcome_evidence_verifier.py
```

- Unique basetemp:
  `D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\commit-ca67a428694a4a4eb84ec471dc837f12`.
- Manifest full-only ignores:
  `tests/test_noncombat_outcome_evidence_runner.py` and
  `tests/test_noncombat_outcome_evidence_verifier.py`.
- Count and pytest duration: `2917 passed in 284.64s (0:04:44)`.
- Gate duration: `290.35s`.
- Exit code: `0`.

## Full Gate

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Printed profile: `full`.

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\full-0b40e7683b3f469796e7e1f35fcdbbad
```

- Unique basetemp:
  `D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\full-0b40e7683b3f469796e7e1f35fcdbbad`.
- Count and pytest duration: `3627 passed in 2026.51s (0:33:46)`.
- Gate duration: `2031.66s`.
- Exit code: `0`.

## Protocol Status

The sequence reached all three commands because each preceding gate exited `0`.
No retry or diagnostic was used. Task `4.3b` is supported by this evidence.
Task `4.4` remains unchecked pending the required independent read-only final
review. Live qualification remains outside this report's scope.
