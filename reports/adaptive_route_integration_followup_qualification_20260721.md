# Adaptive Route Integration Follow-up Qualification - 2026-07-21

## Result

**PASS (automated gates).** The reviewed source at
`40bb9d8f9904f6764fc7160b46bafe0a8d7022f4` completed the one-shot
`gameplay`, `commit`, and `full` gate sequence in order. Every reached command
exited `0`; no gate was retried. Final whole-range review remains a separate
required gate.

- Branch: `codex/noncombat-ope-readiness`
- Production interpreter: `D:\anaconda\envs\stsai\python.exe`
- Tracked worktree before the sequence: clean
- Source pushed before the sequence: yes
- Training enabled: no
- Game/live cohort launched: no
- Persistent Communication Mod or live configuration changed: no

## Focused Preflight

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_map_routing_safety.py -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_final_routing_20260721 -q
```

- Result: `136 passed in 2.82s`
- Exit code: `0`

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_main_runtime_errors.py -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_final_main_20260721 -q
```

- Result: `39 passed in 9.50s`
- Exit code: `0`

Both active OpenSpec changes passed strict validation, and
`git diff --check e1a559f37..HEAD` exited `0` with no output. Task-scoped and
combined implementation reviews reported no Critical or Important findings.
The follow-up product-code delta changes only `main.py` and
`spirecomm/ai/agent.py`; it does not change adaptive thresholds, learned MAP
behavior, training, checkpoint handling, protocol code, defaults, or live
configuration.

## Gameplay Gate

Invocation:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
```

Printed command:

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\gameplay-062e741416724fd48c72d822843f700c tests/test_map_routing_safety.py tests/test_shop_screen_guards.py tests/test_event_choice_guard.py tests/test_ironclad_card_reward_guards.py tests/test_rest_guard.py tests/test_decision_context_guards.py tests/test_offline_decision_comparator.py
```

- Result: `386 passed in 10.86s`
- Gate duration: `14.04s`
- Exit code: `0`
- Transcript: `reports/adaptive_route_integration_followup_gameplay_20260721.txt`
- Transcript bytes: `1017`
- Transcript SHA-256:
  `6BC4A99823C65A8252B423BC65FE3ECDA963BF0E932B3894F63B8CF23C090D6C`

## Commit Gate

Invocation:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
```

Printed command:

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\commit-54ac2ef941094fa7b761baedd358a15b --ignore=tests/test_noncombat_outcome_evidence_runner.py --ignore=tests/test_noncombat_outcome_evidence_verifier.py
```

- Result: `2940 passed in 271.11s (0:04:31)`
- Gate duration: `277.90s`
- Exit code: `0`
- Transcript: `reports/adaptive_route_integration_followup_commit_20260721.txt`
- Transcript bytes: `3729`
- Transcript SHA-256:
  `E684C98380409281EC136BFF866D0550D7C43FE811B25F5C643550056A9D5E52`

## Reboot Boundary

The host rebooted after the commit gate passed and before the full gate was
started. The user reported restart completion at `2026-07-21 23:15:43 +08:00`.
Before resuming, the following were rechecked:

- `HEAD` still equaled `40bb9d8f9904f6764fc7160b46bafe0a8d7022f4`.
- The tracked worktree was clean.
- Gameplay and commit transcripts still ended with exit code `0` and retained
  the hashes above.
- The full transcript did not exist, proving the full gate had not started.

## Full Gate

Invocation:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Printed command:

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_gates\full-64605c7580724712b365294d10c3f9a1
```

- Result: `3650 passed in 1589.76s (0:26:29)`
- Gate duration: `1595.32s`
- Exit code: `0`
- Transcript: `reports/adaptive_route_integration_followup_full_20260721.txt`
- Transcript bytes: `4419`
- Transcript SHA-256:
  `3F62A3A0EABD0553CF44F01AAB958C55D40E7E7CFCBE01DCC9B1ED361AB1DA3D`

## Protocol Disposition

The sequence reached all three commands because every preceding command exited
`0`. The reboot was an idle boundary between completed commands and did not
interrupt or repeat a gate. Automated qualification is complete, but live
qualification remains forbidden until final static checks and the independent
whole-range review also pass.
