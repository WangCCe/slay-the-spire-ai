# Adaptive Route Audit Pause Handoff

## Pause State

- Paused: 2026-07-22, at the user's request to conserve GPT plan budget and
  switch to `gpt-5.6-terra`.
- Repository: `D:\PycharmProjects\slay-the-spire-ai`
- Branch: `master`, direct development approved by the user.
- Upstream baseline: `origin/master` at
  `d333a26003dc5e09eb2fe15a4c5655a5316b066c`.
- Current implementation HEAD before this handoff commit:
  `637048183e194335ca23028d82b90bc66eaef4f8`.
- Local branch state at pause: 18 commits ahead of `origin/master`; nothing from
  this change has been pushed.
- OpenSpec change: `add-adaptive-route-opportunity-audit`.
- The working tree contains many intentional historical untracked reports and
  pytest basetemp directories. Do not clean, reset, or stage them broadly.

## Scope And Safety Boundary

This is a read-only adaptive-route opportunity audit. Keep the remaining work
inside these tracked paths:

- `analysis_scripts/adaptive_route_opportunity_audit.py`
- `tests/test_adaptive_route_opportunity_audit.py`
- `reports/adaptive_route_opportunity_audit_20260722.json`
- `reports/adaptive_route_opportunity_audit_20260722.md`
- `openspec/changes/add-adaptive-route-opportunity-audit/**`
- `docs/superpowers/plans/2026-07-22-adaptive-route-opportunity-audit.md`
- this handoff document

Do not launch Slay the Spire, alter frozen logs/traces/runs, tune route policy,
change gameplay code, train a model, touch checkpoints, or modify protocol/live
configuration. Use `D:\anaconda\envs\stsai\python.exe`.

## Completed Work

The audit change was implemented and produced a frozen artifact before final
whole-change review. Its last published artifact state was:

- JSON SHA-256:
  `252e57b7830d7d10027ae223a023b6d30aea02470cdb89263d08511ff8f65955`
- 13 frozen sources
- 346 occurrences to 173 callback-independent records
- multiplicity `{2: 173}`
- 58 zero-versus-one opportunities, 54 in Act 1
- one aggressive selection, revoked before divergence
- zero divergences taken and zero realized optional elites
- four separately auditable fallback records
- stop decision: keep conservative; no tuning, training, cohort rerun, or policy
  promotion

Commits through `b92f413c6` implemented Tasks 1-4 and recorded verification.
That verification was 161 focused tests and 3101 commit-gate tests, but it is
now explicitly superseded because later code changed.

Final review of `d333a2600..b92f413c6` found four Important issues and one Minor
issue. Commit `637048183` completed the first three with focused TDD:

1. Added a deterministic ledger for all callback-independent records and stable
   ordinal references from opportunities and fallbacks. Focused result: 2
   passed.
2. Made overlapping/interleaved treatment chronology fail closed. Focused
   result: 2 passed.
3. Rejected non-finite numeric CLI values and enforced strict JSON
   serialization with `allow_nan=False`. Focused result: 9 passed.

The full audit test file was not rerun after `637048183`.

Detailed ignored scratch reports remain available locally:

- `.superpowers/sdd/adaptive-route-audit-final-review.md`
- `.superpowers/sdd/adaptive-route-audit-final-fix-report.md`

## Publication Blockers

Two review findings remain untouched:

1. **Important: source physical identity and partial snapshots.** Prevalidate
   physical identity across AI logs, decision traces, and runs so path aliases,
   symlinks, and hard links cannot double count or cross categories. Invalid
   artifacts must retain deterministic snapshots and parse status for sources
   read before a later malformed source fails.
2. **Minor: exact virtual MAP root.** Accept only the canonical frozen sentinel
   `{"symbol":"","x":0,"y":-1}`. Existing task-3 fixtures using
   `(-1, -1), "?"` must be corrected before enforcing it.

OpenSpec Tasks 5.1-5.5 are intentionally unchecked. The plan and Markdown
report also mark the old verification as superseded. Those three controller
edits were preserved with this pause handoff.

## Exact Resume Sequence

1. Read this file and both `.superpowers/sdd` reports. Run `git status --short
   --branch`, `git log -5 --oneline`, and inspect commit `637048183`. Do not pull,
   reset, or clean the working tree.
2. Add focused RED tests for finding 4: normalized/symlink/hard-link AI-log
   aliases, cross-type aliases, and retained snapshots/parse status when a later
   AI log or run is malformed. Implement the smallest production fix, then run
   only that focused selection.
3. Add focused RED tests for finding 5, update only canonical-root fixtures,
   enforce the exact sentinel, and run that focused selection.
4. Run the complete audit test file:

   ```powershell
   D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_adaptive_route_audit_final tests/test_adaptive_route_opportunity_audit.py
   ```

5. Independently review the final-fix code before regenerating evidence. Resolve
   every Critical and Important finding.
6. Regenerate the frozen JSON and derivative Markdown exactly once from the
   unchanged registered sources. Update execution lineage and the JSON hash;
   verify the expected 346-to-173 cohort and funnel values. This is artifact
   regeneration, not a new live cohort.
7. Run the registered commit gate only after focused tests and artifact checks
   pass:

   ```powershell
   D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
   ```

8. Run strict OpenSpec validation, `git diff --check`, and a path-boundary check
   against `d333a2600`. Record fresh verification in the report.
9. Run a final independent whole-change review. Mark Tasks 5.1-5.5 only when no
   Critical or Important finding remains, then make cohesive bookkeeping
   commits without broad staging.
10. Push `master`, sync the OpenSpec delta to the main spec, and archive the
    completed change. Do not archive before publication verification is fresh.

## Budget-Conscious Operating Mode

Start the next task with `gpt-5.6-terra` at medium reasoning. Keep work local and
sequential; do not spawn agents for routine implementation. Raise reasoning to
high only for the source-loader identity design or the final independent review.
Use focused tests while editing and run the four-minute commit gate once, near
publication. Pause and update this handoff at the next coherent commit boundary
if budget pressure returns.

## Pasteable Prompt For The Next Task

```text
Continue the OpenSpec change add-adaptive-route-opportunity-audit in
D:\PycharmProjects\slay-the-spire-ai. Use gpt-5.6-terra at medium reasoning and
first read docs/superpowers/handoffs/2026-07-22-adaptive-route-audit-pause.md,
.superpowers/sdd/adaptive-route-audit-final-review.md, and
.superpowers/sdd/adaptive-route-audit-final-fix-report.md. Verify HEAD and git
status before editing. Do not pull, reset, clean, launch the game, train, tune
policy, modify frozen sources, or stage unrelated untracked files. Resume at
final-review finding 4, then finding 5, using focused RED/GREEN tests. After both
are fixed, follow the handoff's exact verification, artifact regeneration,
independent review, push, OpenSpec sync, and archive sequence. Use
D:\anaconda\envs\stsai\python.exe and do not run the full repository suite; the
registered commit gate is the final broad verification. Conserve budget by
staying sequential and pausing only at coherent commit boundaries.
```
