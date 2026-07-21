# Adaptive Route Audit Task 3 Transition Report

## Scope

Implemented only Task 3 Step 6 / OpenSpec task 3.3: canonical post-boss
`null` transition slots in `.run` evidence.

The change:

- preserves `B, null, M` as `("B", None, "M")` in `RunEvidence`;
- accepts `null` only when the immediately preceding entry is exactly `B`;
- preserves `None` through the deterministic JSON result as `null`;
- marks integrity invalid when a joined `ChooseMapNodeAction` targets a
  canonical transition slot, with game, run source, act, and floor provenance.

Completed Steps 1-5 were not reimplemented or altered. The failed frozen POC
artifact was not modified or rerun.

## RED

Command:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_adaptive_route_opportunity_audit.py -k transition_slot -p no:cacheprovider --basetemp .pytest_adaptive_route_audit_transition_red -q
```

Result: exit 1, `3 failed, 156 deselected in 2.53s`.

The failures were expected and specific to the missing behavior:

- canonical `B, null, M` ingestion returned invalid evidence;
- misplaced `null` produced only the old generic room-symbol error;
- action-targeted canonical `null` failed during ingestion instead of producing
  an integrity diagnostic with run/floor provenance.

## GREEN

Focused command:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_adaptive_route_opportunity_audit.py -k transition_slot -p no:cacheprovider --basetemp .pytest_adaptive_route_audit_transition_final_focused -q
```

Result: exit 0, `3 passed, 156 deselected in 0.66s`.

Complete audit test command:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_adaptive_route_opportunity_audit.py -p no:cacheprovider --basetemp .pytest_adaptive_route_audit_transition_final_full -q
```

Result: exit 0, `159 passed in 3.68s`.

No full repository profile, commit gate, or POC rerun was performed, as required
by the task brief.

## Files Changed

- `analysis_scripts/adaptive_route_opportunity_audit.py`
- `tests/test_adaptive_route_opportunity_audit.py`
- `openspec/changes/add-adaptive-route-opportunity-audit/tasks.md` (checkbox 3.3 only)
- `.superpowers/sdd/adaptive-route-audit-task-3-transition-report.md`

## Review

An independent ephemeral read-only Codex review inspected only the Step 6 brief
and the three owned implementation/task files. It reported no Critical or
Important findings, independently ran the complete audit test file with
`159 passed in 1.85s`, and found task 3.3 ready to mark complete.

Self-review confirmed:

- `None` is accepted only after exact symbol `B`; no other symbol validation was
  loosened;
- malformed placement identifies the offending `path_per_floor` index;
- action-targeted `None` produces invalid integrity and identifies the ordered
  run source plus global floor;
- deterministic serialization uses the existing sorted ASCII JSON path and
  retains the transition entry as JSON `null`;
- no gameplay, policy, training, configuration, source evidence, or failed POC
  report file changed;
- scoped `git diff --check` completed with exit 0.

## Commit

Cohesive commit subject: `fix: preserve canonical run transition slots`.
The final commit hash is reported in the task response because a commit cannot
contain its own final hash without changing that hash.

## Concerns

No implementation concerns or unresolved review findings. The independent
review process printed non-fatal local model-cache warnings, but exited 0 and
returned complete findings and test evidence.
