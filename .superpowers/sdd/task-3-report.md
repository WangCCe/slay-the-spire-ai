# Task 3 Report: Pre-Request Qualification Stages

## Status

Implemented Task 3 only. The trusted v3 qualification path now records the
ordered pre-request prefix through `isolation_verified`, records at most one
sanitized controlled failure before active request, and stops before Task 4's
active request/handoff ownership.

OpenSpec items 2.3 and 2.4 are checked. Item 1.3 remains unchecked for Task 7.

## RED Evidence

Initial focused stage slice:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "bootstrap_stage or bootstrap_controlled_failure or pre_request_stage_boundary" -p no:cacheprovider --basetemp "...\stages-red-task3-20260718" -q
7 failed, 301 deselected in 13.08s
```

All seven failures were caused by absent Task 3 interfaces, stage files, or
failure files. There were no fixture/setup errors.

Two additional TDD boundaries were observed RED during self-review:

```text
pre_request_stage_boundary_success: 1 failed, 309 deselected in 5.40s
```

The existing path reached `process_starter` after stage 5 instead of stopping
at Task 4 ownership.

```text
pre_request_stage_boundary_success single-observation check:
1 failed, 309 deselected in 4.67s
```

Registration loading and S-to-R review each ran twice instead of reusing the
production request loader's validated context.

## GREEN Evidence

Final stage/failure gate:

```text
9 passed, 301 deselected in 12.95s
```

Final brief-prescribed source/request/isolation/stream gate:

```text
36 passed, 274 deselected in 44.08s
```

Task 2 launcher compatibility gate:

```text
16 passed, 294 deselected in 13.77s
```

The successful single-observation regression also passed independently:

```text
1 passed, 309 deselected in 2.46s
```

Static verification also passed:

```text
git diff --check
openspec validate add-pre-request-qualification-observability --strict
Change 'add-pre-request-qualification-observability' is valid
```

All commands used Windows production Python, `-p no:cacheprovider`, and a
unique repository-local basetemp child. The whole repository suite was not run,
per the Task 3 brief's test-economics instruction.

## Last-Stage / Failure Matrix

| Boundary | Last valid stage | Controlled failure |
|---|---|---|
| Trusted launcher runner path/hash/vector rejection | `claim` | none; Task 2 claim-only behavior preserved |
| Isolated/no-site/original-argv/environment/current-runner entry rejection | `launcher_verified` | `runner_entry_validation_failed` |
| HEAD/reviewed bytes/tracked inventory/executable paths/Git metadata or config rejection | `runner_entered` | `source_validation_failed` |
| Request anchors/S-to-R review/registration/implementation/command/static inventory rejection | `source_verified` | `request_validation_failed` |
| CommunicationMod or marker/run/checkpoint/global-log prelaunch drift | `request_reviewed` | `prelaunch_isolation_failed` |
| Unexpected pre-request exception with a valid prefix | current last valid stage | `unexpected_pre_request_failure` |
| Successful Task 3 qualification | `isolation_verified` | none; silent exit 2 before active request |

The claim-only first row follows the binding Task 3 instruction to preserve
Task 2 launcher failures, despite the older table in the brief listing a
`runner_validation_failed` record.

## Isolation And Ownership Proof

Boundary tests assert no active request, bootstrap handoff, attempt, ready,
release, completion, lifecycle failure, forbidden study output, or child start.
They snapshot and compare CommunicationMod config, AI marker, run bytes,
checkpoint bytes, global logs, registration, and qualification config. Captured
stdout/stderr remain empty.

The successful stage-5 test asserts the same absent artifacts and stops before
`process_starter`. It also instruments the production path and proves exactly
one request-root inventory, registration load, S-to-R review, and isolation
observation. Stage rendering performs none of those checks again.

Failure publication is best effort and exclusive. Tests prove fixed public
detail, exception type plus integer errno/winerror only, no exception text or
secret/gameplay data, no overwrite of an existing valid failure, and no repair
or overwrite of a malformed partial failure entry.

## Files

- `scripts/run_noncombat_outcome_evidence_expansion.py`
- `tests/test_noncombat_outcome_evidence_runner.py`
- `openspec/changes/add-pre-request-qualification-observability/tasks.md`
- `.superpowers/sdd/task-3-report.md`

## Self-Review

- Bootstrap state has one exact field set and every transition returns a new
  dictionary without mutating its input.
- Stages 2-5 use exact names/indexes, identical static anchors, and the previous
  valid record hash.
- Claim and launcher stage replay uses canonical ASCII/LF bytes and no-follow
  reads before runner entry publication.
- Runner entry and source failures remain pre-import and stream-silent.
- Request review reuses the production loader's validated bytes, registration,
  and review binding. Isolation uses the existing single observation result.
- The non-CLI/direct lifecycle path is unchanged; Task 3's trusted v3 CLI path
  stops before active request. V1/v2 schema dispatch and terminal authority are
  untouched.
- Existing Task 2 post-claim launcher-vector failures remain claim-only and
  second invocation remains blocked by the consumed claim path.
- No game, CommunicationMod edit, Java, timeout, retry, collection, OPE,
  training, tuning, or policy behavior was invoked or changed.

## Concerns

- The trusted v3 CLI intentionally exits with code 2 after
  `isolation_verified` and no failure record. Task 4 must replace this ownership
  stop with exact active-request publication plus handoff before attempt/child.
- Independent replay/classification and the full crash matrix remain Task 7 and
  later OpenSpec work; item 1.3 is intentionally still unchecked.
- Verification is the brief's focused suite only, not the greater-than-15-minute
  whole repository suite.

## Review Fix Addendum - 2026-07-19

### Status

Implemented every item in `task-3-review-findings.md`. This addendum supersedes
the earlier claim-only launcher row: after a valid claim, reviewed runner
path/hash/vector/shape rejection now publishes one best-effort canonical
`runner_validation_failed` record linked to the claim. Pre-claim envelope
rejection and malformed/existing claim collisions remain unmodified and do not
publish a stage or failure.

Runner-entry state is reconstructed from the original argv envelope and token,
then mutable environment anchors, isolated/no-site flags, argv, launcher code,
runner path, and current runner bytes are validated. A mismatch after canonical
`launcher_verified` publishes `runner_entry_validation_failed` and never
publishes `runner_entered`.

`_qualify_command()` no longer reads registration/checkpoint inputs before
request-failure ownership. The real `main()`/`_qualify_command()` path now lets
the production request loader classify registration drift as
`request_validation_failed` after `source_verified`; checkpoint cwd resolution
is deferred to the existing child-start lifecycle.

### Review RED Evidence

The first behavioral review run selected 17 cases. Fourteen launcher/CLI cases
reached the expected missing-failure assertion; the three new runner subprocess
cases exposed a bytes/text mismatch in their test helper. After correcting only
that test harness, with production still unchanged, the runner boundary was
cleanly RED:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "review_fix_runner_entry_subprocess" -p no:cacheprovider --basetemp "...\review-runner-red-fix-20260719-01" -q
3 failed, 312 deselected in 6.29s
```

Each failure was an absent bootstrap failure file after an existing canonical
claim and `launcher_verified` stage.

After the launcher and runner fixes, the real CLI registration-drift regression
remained independently RED:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "review_fix_main_registration_drift" -p no:cacheprovider --basetemp "...\review-main-red-fix-20260719-01" -q
1 failed, 314 deselected in 2.90s
```

The failure was the absent `request_validation_failed` file because the old
wrapper parsed registration before entering the executor's request boundary.

### Review GREEN Evidence

```text
launcher post-claim/collision/retry slice: 21 passed, 294 deselected in 17.18s
runner-entry focused slice:               4 passed, 311 deselected in 5.41s
real main registration-drift slice:       1 passed, 314 deselected in 2.47s
combined review regressions:             17 passed, 298 deselected in 16.92s
brief stage/failure gate:                 9 passed, 306 deselected in 12.27s
brief source/request/isolation gate:     36 passed, 279 deselected in 45.09s
real qualify-command compatibility:      2 passed, 313 deselected in 3.86s
Task 2 publisher/launcher/request gate:  75 passed, 240 deselected in 60.86s
final runner no-marker slice:             3 passed, 312 deselected in 5.31s
```

Static verification:

```text
git diff --check
openspec validate add-pre-request-qualification-observability --strict
Change 'add-pre-request-qualification-observability' is valid
```

All pytest commands used `D:\anaconda\envs\stsai\python.exe`, disabled the
cacheprovider, and used a unique child under the repository's prescribed
basetemp parent.

### Corrected Last-Stage / Failure Matrix

| Failure input | Last successful record | Controlled failure | Forbidden later evidence |
|---|---|---|---|
| Invalid envelope before a safe claim target | none | none | claim, stage, failure |
| Existing, partial, or malformed claim collision | existing claim bytes are only consumed identity | none | overwrite, stage, failure |
| Runner path/hash/qualifier shape or exact launcher vector rejection after a valid claim, including missing `-I` or `-S` | `claim` | `runner_validation_failed` | `launcher_verified` and later stages |
| Runner-side isolated/no-site, argv, environment-anchor, launcher-code, runner-path, or current-byte mismatch | `launcher_verified` | `runner_entry_validation_failed` | `runner_entered` and later stages |
| Git/HEAD/reviewed source/tracked inventory/importable-source rejection | `runner_entered` | `source_validation_failed` | `source_verified` and later stages |
| Request/review/registration/implementation/command rejection | `source_verified` | `request_validation_failed` | `request_reviewed` and later stages |
| CommunicationMod or marker/run/checkpoint/log isolation drift | `request_reviewed` | `prelaunch_isolation_failed` | `isolation_verified` and later evidence |
| Unexpected exception before active request with a valid prefix | current last valid record | `unexpected_pre_request_failure` | later stage and active lifecycle evidence |
| Successful Task 3 qualification | `isolation_verified` | none | active request, handoff, attempt, child |

Every controlled failure reuses the previous record's exact anchors and
`record_hash`. Publication rereads the valid claim where required, uses the
exclusive canonical publisher, catches publication errors as best effort, and
never overwrites an existing or partial failure entry. Public payloads contain
only fixed code/detail, sanitized exception type, and integer errno/winerror or
`null`; no raw exception text, environment, output, secret, or gameplay value is
rendered.

### No-Later-Ownership Proof

The review regressions assert empty stdout/stderr, immutable claim/stage/failure
bytes on retry, no runner marker, no later bootstrap stage, and no handoff.
The real CLI and existing boundary gates additionally assert no active request,
attempt, ready, release, completion, lifecycle failure, forbidden output, or
child start. Existing protected-state snapshots prove CommunicationMod config,
AI marker, run bytes, checkpoint bytes, global logs, registration, and
qualification config are unchanged except for the deliberately corrupted input
under test. No Git/source/request/inventory/isolation check is repeated to
render evidence.

### Review Files And Self-Review

- `scripts/run_noncombat_outcome_evidence_expansion.py`
- `tests/test_noncombat_outcome_evidence_runner.py`
- `.superpowers/sdd/task-3-report.md`

OpenSpec task items were not changed during this review fix. Items 2.3 and 2.4
remain checked, and 1.3 remains unchecked for Task 7.

The trusted launcher still creates the claim before exact runner/vector checks;
only validated post-claim rejections can attempt the new failure. Runner
reconstruction does not trust mutable environment values. Source-only,
isolated/no-site startup and stream ownership remain intact. The non-bootstrap
v1/v2 lifecycle path still owns active request, attempt, child, completion, and
lifecycle failures. No Task 4 publication or handoff behavior was added.

### Review Concerns

- The trusted v3 CLI still intentionally stops after `isolation_verified`.
  Task 4 owns active-request publication and handoff.
- The whole repository suite was not run, per the explicit test-economics
  instruction; verification is the focused review, Task 3, Task 2 compatibility,
  and CLI-wrapper gates above.

## Replacement Implementer Audit - 2026-07-19

The replacement audit reread the Task 3 brief, frozen contract, review findings,
and inherited diff. No additional production defect was found. In particular,
the bootstrap state begins at `launcher_verified` index 1, every stage transition
increments the index once and uses the prior state's `last_record_hash`, and a
failure retains the last completed stage index/name with `previous_hash` equal
to that same last record hash. The immutable contiguous-chain regression checks
all five stage files against those returned states.

The real `main()` regression proves malformed registration bytes are classified
by `load_qualification_request_source()` as `request_validation_failed` linked
to `source_verified`. The real `_qualify_command()` junction regression proves
the same ownership for no-follow registration rejection. Neither path publishes
`request_reviewed`, active request, handoff, attempt, or child evidence.

Fresh focused review selector:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "trusted_qualification_launcher_post_claim_rejection_consumes_identity or v3_launcher_missing_isolation_vector_records_runner_failure or modified_trusted_launcher_code_records_runner_validation_failure or review_fix_runner_entry_subprocess_records_failure_after_launcher_stage or review_fix_main_registration_drift_records_request_failure or qualify_command_routes_registration_junction_to_request_failure" -p no:cacheprovider --basetemp "...\replacement-focused-20260719" -q
18 passed, 297 deselected in 17.04s
```

Fresh compatibility gates:

```text
bootstrap_stage or bootstrap_controlled_failure or pre_request_stage_boundary:
9 passed, 306 deselected in 13.04s

bootstrap_stage or bootstrap_controlled_failure or qualification_source or qualification_request or prelaunch_isolation or stream_silence:
36 passed, 279 deselected in 46.78s

bootstrap_publisher or trusted_launcher or claim or qualification_request:
75 passed, 240 deselected in 56.26s
```

All fresh pytest commands used Windows production Python, disabled the cache
provider, and used distinct repository-local basetemp children. OpenSpec items
2.3 and 2.4 remain supported and checked; item 1.3 remains deferred to Task 7.

Fresh static verification:

```text
git diff --check: exit 0
openspec validate add-pre-request-qualification-observability --strict:
Change 'add-pre-request-qualification-observability' is valid
```
