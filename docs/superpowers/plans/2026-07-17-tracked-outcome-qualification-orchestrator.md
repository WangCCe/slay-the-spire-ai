# Tracked Outcome Qualification Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the failure-prone external pre-lock monitor with one tracked, one-shot CommunicationMod qualifier that proves release consumption and exits before exploration or agent construction.

**Architecture:** CommunicationMod starts a fixed stdlib-only `python -I -S -c` trust-root launcher encoded as one whitespace-free token with an externally preserved runner SHA-256. The launcher rejects runner path links/reparse points, hashes the runner, and executes only the validated in-memory bytes; the runner rejects direct file startup, rechecks the original command/environment anchor, and later binds it to the reviewed implementation map. The request records implementation snapshot S and is tracked byte-for-byte in direct-child review commit R. External request self-hash/file-SHA/size/R anchors, lexical no-follow path checks before parsing/resolution/reads, a pinned no-follow absolute Git executable bound to a guarded local `.git` and worktree with sterile configuration/environment and no lazy fetch, exact diff allowlisting, a pure-stdlib pre-project-import bootstrap that extracts exactly one external R, proves clean `HEAD == R`, hashes tracked non-inert worktree bytes against R tree blobs without trusting index stat data, and rejects nonordinary index flags, Git attributes/filters, partial-clone/promisor remotes, and extension protocols, fail-closed tracked/untracked/ignored source inventory with reparse-aware no-follow traversal, parent/child bytecode write suppression plus null-device cache lookup redirection and repository no-follow source-only loading, and unchanged registered bytes establish the live binding. The runner exclusively publishes the active request, publishes attempt before starting the registered command with fixed `-I -S` isolation added and ambient `PYTHON*`/`GIT_*` removed, accepts immediate ready, performs one deadline-bounded live validation including Git metadata/process work and chunked root hashing through the instant before release publication, publishes release, and requires an attempt-hash-bound zero exit before publishing terminal evidence carrying a canonical review binding. The standalone qualification verifier also requires `-I -S`, rejects abbreviated qualification options, uses null-device cache lookup redirection and repository no-follow source-only loading, and skips ordinary audit-helper imports before replaying S/R Git blobs independently of current HEAD or current request-parent existence; optional audit output is no-follow/exclusive and outside the qualification root. It requires independently preserved result-hash/file-SHA/size anchors for terminal replay, enforces launch-count/PID/handshake consistency, and classifies prepared, valid partial, invalid consumed, or terminal evidence. Ordinary registration audit startup is unchanged; r4 and study `start` remain separate gates.

**Tech Stack:** Python 3.10, stdlib JSON/hash/process APIs, pytest, CommunicationMod condition files, OpenSpec.

## Global Constraints

- Use `D:\anaconda\envs\stsai\python.exe` for Windows tests and real CommunicationMod children.
- Keep `study_handshake.py`, protocol v1, readiness 120, and release 10 unchanged.
- Do not create r4, a run lock, a ledger, training, or gameplay-policy changes in the source-fix commit.
- Preserve r1/r2/r3 byte-for-byte; describe r3 only as an independently verified release-side orchestration failure.
- Keep qualifier diagnostics off CommunicationMod stdout and do not read live logs while the child runs.

---

### Task 1: Canonical Request And Result Contracts

**Files:**
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Test: `tests/test_noncombat_outcome_evidence_runner.py`

**Interfaces:**
- `build_qualification_request(..., request_source_path) -> dict[str, Any]`
- `load_qualification_request_source(path, registration_path, expected_request_hash, expected_review_commit, expected_request_file_sha256, expected_request_size) -> dict[str, Any]`
- `load_qualification_request(path, registration_path) -> dict[str, Any]`
- `build_qualification_result(..., status: str) -> dict[str, Any]`
- `publish_qualification_result_once(path, result) -> None`

- [ ] **Step 1: Write failing request tests**

Add a canonical fixture matching the exact field set in `design.md`. Parameterize duplicate keys, non-canonical bytes, self-hash, source, registration, implementation map, command, config, marker, 120/10, stale control files, preexisting inventory, and forbidden paths.

```python
with pytest.raises(module.OutcomeEvidenceRunnerError, match="source commit"):
    module.load_qualification_request(request_path, registration_path)
assert process_starts == []
```

- [ ] **Step 2: Prove the tests are red**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-qualification-request-red-20260717 tests\test_noncombat_outcome_evidence_runner.py -k "qualification_request or qualification_result" -q
```

Expected: missing qualification APIs cause failure.

- [ ] **Step 3: Implement strict canonical loading**

Use duplicate-key and non-finite JSON rejection; require raw bytes equal sorted compact ASCII JSON plus LF; replay `request_hash`; bind an absolute reviewed-source path distinct from the active path; reject UNC/device namespaces, every symlink/reparse component, every colon outside the drive component (including NTFS alternate data streams), and every component ending in a dot or space lexically before normal registration parsing, filesystem probes, resolution, reads, traversal, or hashing; inspect every raw absolute registration path and derived registered implementation path before the normal validator; run a pure-stdlib source bootstrap before project imports; stream non-inert worktree bytes through guarded `git -c core.autocrlf=true hash-object --path --stdin` so Windows newline conversion is accepted while binary drift is rejected, and allow only R-tracked raw-byte-identical inert text/eol attributes; invoke only the pinned absolute Git executable with guarded `GIT_DIR`/`GIT_WORK_TREE`, sterile config/attributes and command controls, no nonordinary index flags, filters, replacement/grafts/alternates/commondir/reparse metadata, and stderr fail-closed; enforce implementation snapshot S, later clean review commit R, S ancestry, unchanged registration and registered implementation bytes across S/R/launch HEAD, explicit expected hash, the registered child command with fixed `-I -S`, config hash, marker count, zero run-lock hash, slot 1, and absent control/forbidden paths.

```python
QUALIFICATION_REQUEST_SCHEMA_VERSION = "noncombat-outcome-evidence-qualification-request-v1"
QUALIFICATION_RESULT_SCHEMA_VERSION = "noncombat-outcome-evidence-qualification-result-v1"
QUALIFICATION_ATTEMPT_HASH_ENV = "STS_OUTCOME_EVIDENCE_QUALIFICATION_ATTEMPT_HASH"
```

- [ ] **Step 4: Implement passed/failed result builders**

Enforce the exact result fields and branch invariants from `design.md`, compute `result_hash` with that field null, publish once with `_publish_text_once`, and require every authority field false.

- [ ] **Step 5: Run the selected tests green**

Repeat Step 2. Expected: all selected tests PASS.

### Task 2: Post-Release Qualification Exit

**Files:**
- Modify: `main.py`
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Test: `tests/test_main_runtime_errors.py`
- Test: `tests/test_noncombat_outcome_evidence_runner.py`

**Interfaces:**
- `QualificationChildComplete`
- `qualification_exit_requested(environ=None) -> bool`
- Existing non-qualification `initialize_pre_agent_runtime` tuple remains unchanged.

- [ ] **Step 1: Write failing boundary tests**

Require handshake completion first, then a token exactly equal to the loaded attempt hash; make exploration initialization fail the test if called. Cover missing handshake, malformed/mismatched token, absent-token ordinary startup, and ambient token in `run-next`.

```python
with pytest.raises(main_module.QualificationChildComplete):
    main_module.initialize_pre_agent_runtime(
        agent_type="optimized",
        environ=environ,
        handshake_initializer=lambda *_args, **_kwargs: True,
        exploration_initializer=lambda **_kwargs: pytest.fail("exploration initialized"),
        coordinator_factory=lambda *_args, **_kwargs: (object(), True),
    )
```

- [ ] **Step 2: Prove the boundary tests are red**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-qualification-child-red-20260717 tests\test_main_runtime_errors.py tests\test_noncombat_outcome_evidence_runner.py -k "qualification_child or ambient_qualification" -q
```

- [ ] **Step 3: Implement token validation and zero exit**

Require `qualify` to be invoked through the exact stdlib-only Python `-I -S -c` launcher with an externally preserved runner SHA-256 before argument parsing or project imports; execute only the no-follow validated in-memory runner bytes, reject direct runner-file startup, and bind the launcher anchor to the request implementation map. Launch the child from the registered executable/main/arguments with fixed `-I -S`, remove all inherited `PYTHON*` and `GIT_*` entries, and set only the bound qualification additions. When the qualification token is present, load `HANDSHAKE_ATTEMPT_ENV`, lexically inspect every existing component and require a regular final file before coordinator construction or the shared handshake initializer. After the unchanged handshake returns true, repeat that guard before the shared attempt loader, require lowercase 64-hex equality with `attempt_hash`, and raise `QualificationChildComplete` before exploration. Catch it before generic startup errors, log through the existing channel, and exit zero.

- [ ] **Step 4: Guard `run-next` before attempt publication**

```python
if QUALIFICATION_ATTEMPT_HASH_ENV in os.environ:
    raise OutcomeEvidenceRunnerError("run-next refuses ambient qualification environment")
```

- [ ] **Step 5: Run startup and handshake tests green**

Run all of `tests/test_main_runtime_errors.py` and `tests/test_study_handshake.py`. Expected: PASS, including ordinary startup and exact 120/10 boundaries.

### Task 3: Owner-Controlled `qualify`

**Files:**
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Test: `tests/test_noncombat_outcome_evidence_runner.py`

**Interfaces:**
- `execute_prelock_qualification(*, registration_path, request_path, expected_request_hash, expected_review_commit, expected_request_file_sha256, expected_request_size, process_starter, monotonic, sleep, time_ns) -> dict[str, Any]`
- Reuse `_wait_for_child_readiness`, handshake builders/validators, and `_terminate_child_process`.

- [ ] **Step 1: Write failing event-order tests**

The fake starter asserts attempt already exists, publishes valid ready before returning, and exposes release during `wait()`. Assert `attempt -> start -> ready -> release -> zero exit -> completion`, one start, and no live-log reader.

- [ ] **Step 2: Prove the orchestration tests are red**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-qualification-runner-red-20260717 tests\test_noncombat_outcome_evidence_runner.py -k "qualification_orchestrator or qualification_accepts_ready" -q
```

- [ ] **Step 3: Implement the success path**

Load the committed reviewed request source, require its expected hash, reject every untracked or ignored executable/importable path and untracked symlink while failing closed on Git/traversal diagnostics, exclusively publish those canonical bytes as the active request, then publish attempt, set config/handshake/attempt-hash environments, route only the child file logger to `os.devnull`, start the exact command once with inherited stdio, accept ready on the first poll only after a qualification-specific lexical guard runs before the shared ready loader, derive one conservative remaining-release deadline from the ready timestamp, validate PID/config/marker/output/current review-bound files/Git metadata and subprocesses/chunked root inventory under that deadline without repeating S/R blob replay, publish release, require an exact integer exit 0 within the registered release timeout, revalidate isolation, and publish completion. Post-exit-validation and completion-publication failures after release/zero exit remain immutable partial prefixes; neither may be relabelled as a failed terminal.

- [ ] **Step 4: Implement failure and cleanup paths**

Cover timeout, early exit, malformed/PID-mismatched ready, boundary drift, release failure, wait failure, nonzero/non-integer exit, cleanup failure, and result collision. Never retry or publish a late release; publish at most one failure record.

- [ ] **Step 5: Add CLI routing**

Add the trusted launcher plus `qualify --registration ... --request ... --request-hash ... --request-file-sha256 ... --request-size ... --review-commit ...`; `--request` is the tracked reviewed source, direct file startup is rejected, and the default child starter uses exact command, game-directory cwd, and inherited stdin/stdout/stderr. Print qualifier success and errors to stderr.

- [ ] **Step 6: Run all runner tests green**

Run `tests/test_noncombat_outcome_evidence_runner.py`. Expected: PASS with no real process.

### Task 4: Independent Qualification Replay

**Files:**
- Modify: `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`
- Test: `tests/test_noncombat_outcome_evidence_verifier.py`

**Interfaces:**
- `verify_prelock_qualification(request_source_path, result_path=None, *, expected_review_commit, expected_request_hash, expected_request_file_sha256, expected_request_size, expected_result_hash=None, expected_result_file_sha256=None, expected_result_size=None) -> dict[str, Any]`
- Audit schema `noncombat-outcome-evidence-qualification-verification-audit-v1`.

- [ ] **Step 1: Write failing replay/tamper tests**

Cover the S-to-R request review chain, request/result canonical bytes and self-hashes, mandatory external terminal anchors, source/registration/implementation/config, exact JSON types, lifecycle ordering, attempt/ready/release, PID, launch count, mutually exclusive branch, forbidden paths, and true authority. Add request-only and each contiguous handshake-prefix case; the verifier test may use fixture bytes but the verifier module must not import runner result builders.

- [ ] **Step 2: Prove verifier tests are red**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-qualification-verifier-red-20260717 tests\test_noncombat_outcome_evidence_verifier.py -k "qualification" -q
```

- [ ] **Step 3: Implement independent replay**

Duplicate schema constants and exact checks, independently load canonical records, locate Git from the nearest existing ancestor when the current reviewed-source parent is gone, guard the qualification root, purely bind active/attempt/ready/release/completion/failure declarations to its fixed direct children and recheck their parents before any classification/inventory/probe/read, inspect reviewed registration absolute and derived implementation paths before normal validation/resolution, classify dangling/non-regular control paths before inventory, inventory links with no-follow metadata, use lstat existence for forbidden paths, enforce launch/PID/cleanup/attempt/ready/release consistency, reject success-looking failure relabels including claimed post-exit-validation failures, require all-false study/run-lock/collection/policy/causal/training authority, and return a self-hashed audit with check count and no promotion claim.

- [ ] **Step 4: Add backward-compatible CLI mode**

Keep `--registration` unchanged. Disable long-option abbreviation. Add mutually exclusive exact `--qualification-request-source` (with the prior name as an alias), optional `--qualification-result`, required external request-hash/file-SHA/size/review-commit arguments, and result-hash/file-SHA/size arguments required exactly when a terminal is supplied. Qualification `--output` requires a lexical absolute missing path with no alternate-data-stream syntax or Win32 trailing-dot/space alias whose canonical no-follow parent stays outside the qualification root and which matches no request-bound path or forbidden subtree, plus exclusive publication; ordinary registration output semantics remain unchanged. Omitting the result classifies reviewed-prepared, valid partial, or consumed-invalid evidence; it must reject result anchors, must not verify either terminal branch, and keeps all authority false.

- [ ] **Step 5: Run all verifier tests green**

Run `tests/test_noncombat_outcome_evidence_verifier.py`. Expected: PASS.

### Task 5: Verification, Review, And Source Commit

**Files:**
- Update if required: `tests/test_noncombat_outcome_evidence_expansion.py`
- Preserve: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json`
- Preserve r3 as historical: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration_review.md`
- Update: `openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md`

- [ ] **Step 1: Run focused pytest**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-qualification-focused-20260717 tests\test_study_handshake.py tests\test_main_runtime_errors.py tests\test_noncombat_outcome_evidence_expansion.py tests\test_noncombat_outcome_evidence_runner.py tests\test_noncombat_outcome_evidence_verifier.py -q
```

If the failed r3 candidate's current-byte guard fires, preserve its historical rows and add an explicit historical-versus-current binding distinction; do not rewrite r3 as successful or weaken digest validation.

- [ ] **Step 2: Run full pytest**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-qualification-full-20260717 -q
```

Expected: all tests PASS.

- [ ] **Step 3: Run structural verification**

Run `py_compile` for main/runner/verifier/handshake, `openspec validate --all --strict`, `git diff --check`, canonical registration comparison, and a diff scan proving no deadline/schema/rate/seed/schedule/estimator/threshold/policy/checkpoint/training/Java/gameplay drift.

- [ ] **Step 4: Obtain independent review**

Require explicit Critical/Important/Minor counts and `Ready to commit: Yes`. Fix every Critical/Important with a red regression and rerun Steps 1-3.

- [ ] **Step 5: Commit and push the source fix**

Stage only named source, tests, OpenSpec, and this plan; exclude unrelated reports and `.pytest-*`. Commit `feat: add tracked outcome qualification orchestrator` and push `codex/noncombat-ope-readiness`.

### Task 6: Separate r4 Binding Handoff

**Files:**
- Later update: `openspec/changes/run-v2-known-propensity-outcome-evidence-study/`
- Later update: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration_review.md`

- [ ] **Step 1: Re-render registration after the source commit**

Compare exact bytes/hash with canonical hash `7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace`; preserve current bytes if identical, otherwise archive them as superseded. This source-fix commit is implementation snapshot S; always refresh its implementation bindings.

- [ ] **Step 2: Amend the study before live launch**

Preserve r1/r2/r3, record the r3 evidence limitation, generate a request that binds S and its reviewed source path, commit those exact bytes and expected hash in later review commit R, prove no registered implementation or registration drift across S/R, name a previously absent r4 root, and keep `start`, run-lock, collection, training, and policy authority false.

- [ ] **Step 3: Independently review and commit the r4 candidate**

Run focused/full pytest and strict OpenSpec validation, obtain a ready-to-commit verdict, and verify tracked-clean source plus absent r4/study roots.

- [ ] **Step 4: Run r4 exactly once**

Use real Windows Python and CommunicationMod. Require attempt/ready/release/completion replay, restored config bytes, unchanged markers/runs/checkpoints/global logs, no study/gameplay artifact, no surviving process, and independent attestation before reconsidering `start`.
