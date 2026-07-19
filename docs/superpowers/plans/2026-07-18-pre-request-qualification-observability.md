# Pre-Request Qualification Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every future qualification identity durably consumed and independently diagnosable from trusted-launcher entry through active-request handoff, while preserving stream silence, one-shot behavior, evidence-bounded historical compatibility, and uniformly closed study/training/policy authority.

**Architecture:** Request, result, and review-binding v3 bind one bootstrap-evidence v1 contract. A pure-stdlib publish-once primitive creates a claim before runner execution, then five immutable hash-linked stage files and one request-bound handoff. The independent verifier reconstructs the token, guarded paths, canonical bytes, chain, and lifecycle without importing producer builders; historical v1/v2 evidence stays on an unchanged read-only branch.

**Tech Stack:** Python 3 standard library, pytest, Git object replay, OpenSpec, Windows production Python, CommunicationMod-compatible command tokenization.

## Global Constraints

- Use `D:\anaconda\envs\stsai\python.exe` for every production-compatible test and subprocess smoke.
- Add each regression first and observe the intended failure before changing production behavior.
- Keep each task green before its commit; do not knowingly commit a failing focused slice.
- Use `-p no:cacheprovider` and a unique ignored repository-local `--basetemp` for every pytest command.
- Do not launch Slay the Spire, edit live CommunicationMod configuration, modify CommunicationMod Java, increase a timeout, retry or relabel r6, prepare r7, invoke `start`, create a run lock, collect trajectories, run OPE, train, tune, or change gameplay policy.
- Keep qualification stdout and stderr empty on every success and failure path before child stream ownership transfers.
- Treat every entry at the claim path, including partial or malformed bytes, as permanent identity consumption. Never delete, truncate, replace, repair, complete, downgrade, or retry it.
- Publish bootstrap files only as fixed direct children of the guarded qualification root. Reject traversal, alternate data streams, Win32 alias components, symlinks, reparse points, non-regular entries, identity changes, and unexpected files.
- Preserve every available r1-r6 request/result/review/audit/report/root byte and every recorded absence. Keep evidence-derived classification separate from externally reviewed governance disposition; require complete public v1/v2 replay only for bundles retaining every required request, review, and Git anchor. Never synthesize missing history. New launch execution accepts v3 only.
- Claim, stages, failure, handoff, terminal, and verifier output are evidence only. Every live, study, collection, causal, policy, training, and promotion authority field remains false.
- Never use current worktree bytes as substitutes for externally anchored S, R, request, runner, result, or historical evidence.
- Stage publication records checks that have already completed; it must not repeat Git, source, inventory, isolation, restoration, or child-liveness work.
- Keep unrelated untracked reports and `.superpowers/` out of every stage and commit.

## File Map

**Production files**

- Modify `scripts/run_noncombat_outcome_evidence_expansion.py`: v3 constants, canonical bootstrap library, launcher envelope/token, request construction/loading, five stage transitions, handoff, result/review binding, and terminal validation.
- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`: independent v3 token/path/record replay, prefix classification, handoff/terminal requirements, audit v3, and isolated historical dispatch.

**Test files**

- Modify `tests/test_noncombat_outcome_evidence_runner.py`: exact byte fixtures, publisher/path tests, trusted-launcher and stage regressions, handoff ordering, failure/crash matrix, stream silence, isolation preservation, ordinary-start invariants, and production-Python smoke.
- Modify `tests/test_noncombat_outcome_evidence_verifier.py`: independent prefix vectors, corrupt-root matrix, terminal binding, all-false authority, and r1-r6 replay.

**Planning and closeout files**

- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md` incrementally as verified task groups complete.
- Modify `openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md` only in Task 8, checking item 7.7 after source-only closeout passes.
- Modify `openspec/changes/run-v2-known-propensity-outcome-evidence-study/tasks.md` only in Task 8, checking item 3.12 after source-only closeout passes.
- Add `reports/pre_request_qualification_observability_20260718_closeout.md` in Task 8.

## Frozen V3 Contract

Use explicit historical names instead of moving the meaning of a legacy alias:

```python
QUALIFICATION_REQUEST_V1_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v1"
)
QUALIFICATION_REQUEST_V2_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v2"
)
QUALIFICATION_REQUEST_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v3"
)
QUALIFICATION_RESULT_V1_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v1"
)
QUALIFICATION_RESULT_V2_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v2"
)
QUALIFICATION_RESULT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v3"
)
QUALIFICATION_REVIEW_BINDING_V1_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-review-binding-v1"
)
QUALIFICATION_REVIEW_BINDING_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-review-binding-v3"
)
QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-bootstrap-evidence-v1"
)
QUALIFICATION_BOOTSTRAP_TOKEN_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-bootstrap-token-v1"
)
QUALIFICATION_BOOTSTRAP_STAGE_NAMES = (
    "launcher_verified",
    "runner_entered",
    "source_verified",
    "request_reviewed",
    "isolation_verified",
)
```

Keep compatibility aliases only where existing imports require them, and make every schema dispatch compare against an explicit version constant.

The request v3 `bootstrap` field is exactly:

```python
{
    "claim_path": str(qualification_root / "qualification-bootstrap-claim.json"),
    "failure_path": str(qualification_root / "qualification-bootstrap-failure.json"),
    "handoff_path": str(qualification_root / "qualification-bootstrap-handoff.json"),
    "schema_version": QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION,
    "stage_paths": [
        {
            "index": 1,
            "name": "launcher_verified",
            "path": str(
                qualification_root
                / "qualification-bootstrap-stage-01-launcher-verified.json"
            ),
        },
        {
            "index": 2,
            "name": "runner_entered",
            "path": str(
                qualification_root
                / "qualification-bootstrap-stage-02-runner-entered.json"
            ),
        },
        {
            "index": 3,
            "name": "source_verified",
            "path": str(
                qualification_root
                / "qualification-bootstrap-stage-03-source-verified.json"
            ),
        },
        {
            "index": 4,
            "name": "request_reviewed",
            "path": str(
                qualification_root
                / "qualification-bootstrap-stage-04-request-reviewed.json"
            ),
        },
        {
            "index": 5,
            "name": "isolation_verified",
            "path": str(
                qualification_root
                / "qualification-bootstrap-stage-05-isolation-verified.json"
            ),
        },
    ],
    "token_schema_version": QUALIFICATION_BOOTSTRAP_TOKEN_SCHEMA_VERSION,
}
```

The reviewed request does not contain a runtime token. The fixed launcher receives one canonical base64 envelope and one lowercase token derived after request bytes and external R are fixed:

```python
def _qualification_bootstrap_envelope(
    *,
    request: Mapping[str, Any],
    expected_request_file_sha256: str,
    expected_request_size: int,
    review_commit: str,
    runner_sha256: str,
) -> dict[str, Any]:
    return {
        "bootstrap": request["bootstrap"],
        "qualification_id": request["qualification_id"],
        "qualification_root": request["qualification_root"],
        "request_file_sha256": expected_request_file_sha256,
        "request_hash": request["request_hash"],
        "request_size": expected_request_size,
        "review_commit": review_commit,
        "runner_sha256": runner_sha256,
        "schema_version": QUALIFICATION_BOOTSTRAP_TOKEN_SCHEMA_VERSION,
        "source_commit": request["source_commit"],
    }


def _qualification_bootstrap_token(envelope: Mapping[str, Any]) -> str:
    canonical = _canonical_json(envelope).encode("ascii")
    domain = b"noncombat-outcome-evidence-qualification-bootstrap-token-v1\x00"
    return hashlib.sha256(domain + canonical).hexdigest()
```

`_qualification_bootstrap_encode_envelope()` emits canonical ASCII JSON as strict base64 without whitespace. `_qualification_bootstrap_decode_envelope()` rejects non-canonical JSON/base64, duplicate keys, JSON constants, extra fields, wrong types, unsafe paths, and a re-encode mismatch.

The launcher vector is fixed as:

```text
python -I -S -c TRUSTED_CODE RUNNER_PATH RUNNER_SHA256 ENVELOPE_B64 LAUNCH_TOKEN qualify QUALIFIER_ARGUMENTS
```

The launcher exports only these reviewed anchors to the in-memory runner:

```python
QUALIFICATION_RUNNER_SHA256_ENV = "STS_OUTCOME_EVIDENCE_QUALIFICATION_RUNNER_SHA256"
QUALIFICATION_BOOTSTRAP_ENVELOPE_ENV = (
    "STS_OUTCOME_EVIDENCE_QUALIFICATION_BOOTSTRAP_ENVELOPE_B64"
)
QUALIFICATION_BOOTSTRAP_LAUNCH_TOKEN_ENV = (
    "STS_OUTCOME_EVIDENCE_QUALIFICATION_BOOTSTRAP_LAUNCH_TOKEN"
)
```

Every bootstrap record uses one exact top-level field set:

```python
SHA256_VECTOR = "0" * 64
COMMIT_VECTOR = "1" * 40

{
    "anchors": {
        "envelope_sha256": SHA256_VECTOR,
        "launch_token": SHA256_VECTOR,
        "qualification_id": "fixture-qualification",
        "request_file_sha256": SHA256_VECTOR,
        "request_hash": SHA256_VECTOR,
        "request_size": 1,
        "review_commit": COMMIT_VECTOR,
        "runner_sha256": SHA256_VECTOR,
        "source_commit": COMMIT_VECTOR,
    },
    "created_unix_ns": 1,
    "payload": {},
    "pid": 1,
    "previous_hash": None,
    "record_hash": SHA256_VECTOR,
    "record_type": "claim",
    "schema_version": QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION,
    "stage_index": 0,
    "stage_name": "claim",
}
```

Stage records change `record_type`, `stage_index`, `stage_name`, and `previous_hash`; their payload remains `{}`. A failure record retains the last completed index/name and uses exactly:

```python
{
    "code": "source_validation_failed",
    "detail": "reviewed source validation failed",
    "errno": None,
    "exception_type": "OutcomeEvidenceRunnerError",
    "winerror": None,
}
```

Allowed failure codes are:

```python
QUALIFICATION_BOOTSTRAP_FAILURE_CODES = frozenset(
    {
        "bootstrap_envelope_invalid",
        "bootstrap_claim_publish_failed",
        "runner_validation_failed",
        "runner_entry_validation_failed",
        "source_validation_failed",
        "request_validation_failed",
        "prelaunch_isolation_failed",
        "unexpected_pre_request_failure",
    }
)
```

Failure details come from a fixed public code-to-message mapping, not raw environment values, arbitrary output, file contents, or unrestricted exception strings. `errno` and `winerror` are integers or `None`.

The handoff record is stage index 6, stage name `active_request_handoff`, previous hash equal to the `isolation_verified` record hash, and payload exactly:

```python
{
    "active_request_file_sha256": SHA256_VECTOR,
    "active_request_size": 1,
    "claim_hash": SHA256_VECTOR,
    "final_stage_hash": SHA256_VECTOR,
    "request_hash": SHA256_VECTOR,
}
```

All records serialize as `_canonical_json(record).encode("ascii") + b"\n"`. `record_hash` is the SHA-256 of the same canonical object with `record_hash=None` and no trailing newline.

---

### Task 1: Lock V3 Schema, Path, Token, And Byte Fixtures

**Files:**

- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:877-1450`
- Modify `tests/test_noncombat_outcome_evidence_runner.py:1418-1700`
- Modify `tests/test_noncombat_outcome_evidence_verifier.py:55-230`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Add `_qualification_bootstrap_paths(qualification_root: Path) -> dict[str, Any]`.
- Add `_qualification_bootstrap_envelope(*, request: Mapping[str, Any], expected_request_file_sha256: str, expected_request_size: int, review_commit: str, runner_sha256: str) -> dict[str, Any]`.
- Add `_qualification_bootstrap_token(envelope: Mapping[str, Any]) -> str`.
- Add `_qualification_bootstrap_encode_envelope(envelope: Mapping[str, Any]) -> str`.
- Add `_qualification_bootstrap_decode_envelope(encoded: str) -> dict[str, Any]`.
- Advance producer request creation/loading to v3 while retaining named v1/v2 constants.

- [ ] **Step 1: Add exact red schema and byte fixtures**

Extend `_qualification_request_fixture()` with fixed `created_unix_ns`, fixed root names, fixed S/R/request/runner hashes, and expected bootstrap paths. Assert the exact request field set gains only `bootstrap`, request schema is v3, all bootstrap paths are fixed direct children, and rendered request bytes are canonical ASCII plus one LF.

Add a frozen token vector with literal expected envelope base64 and token SHA-256. Assert key reordering cannot change the token, while changing qualification ID, root, any path, request hash/file hash/size, S, R, runner hash, evidence schema, or token schema changes it.

Keep fixed v1 and v2 request/result/review fixtures and assert their input bytes are unchanged.

- [ ] **Step 2: Run the red contract slice**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  tests/test_noncombat_outcome_evidence_verifier.py `
  -k "bootstrap_schema or bootstrap_paths or bootstrap_token or historical_schema_bytes" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\contract-red" `
  -q
```

Expected: selected tests fail because v3 constants, the `bootstrap` request field, and token helpers do not exist.

- [ ] **Step 3: Implement deterministic paths, envelope, and token**

Build all paths from the already guarded lexical qualification root. Require exact filenames, `path.parent == qualification_root`, no collision with request/attempt/ready/release/completion/failure/config/forbidden paths, and sorted unique stage indexes/names.

Validate the envelope independently of ambient argv. The decoder must round-trip exact base64 and exact canonical JSON bytes; do not accept padding variants, whitespace, duplicate keys, floats, booleans in integer fields, or extra fields.

- [ ] **Step 4: Advance request build/load to v3**

Add `bootstrap` before computing `request_hash`. During request construction require every declared bootstrap path absent and exclude those declared paths from `preexisting_files`. During source-mode loading allow only the exact contiguous bootstrap prefix later tasks validate; during ordinary active-request loading require the exact handoff contract.

Keep historical parsing constants available, but make the producer's launch path reject v1/v2 with `qualification request schema mismatch`.

- [ ] **Step 5: Run the contract slice green**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  tests/test_noncombat_outcome_evidence_verifier.py `
  -k "qualification_request or bootstrap_schema or bootstrap_paths or bootstrap_token or historical_schema_bytes" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\contract-green" `
  -q
```

Expected: zero selected failures; fixture writes remain under `tmp_path`.

- [ ] **Step 6: Check OpenSpec items 1.1 and 2.2 and commit**

Stage only the producer, two focused test files, and the current change task file. Inspect `git diff --cached --name-only`, then commit:

```powershell
git commit -m "test: define qualification bootstrap v3 contract"
```

---

### Task 2: Add The Pure-Stdlib Publisher And Trusted-Launcher Claim

**Files:**

- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:1-167`
- Modify `tests/test_noncombat_outcome_evidence_runner.py:1-180`
- Modify `tests/test_noncombat_outcome_evidence_runner.py:2800-3300`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Add one `_QUALIFICATION_BOOTSTRAP_LIBRARY_SOURCE` used by both trusted-launcher code and runner code.
- Add pure-stdlib `_qualification_bootstrap_publish_bytes_once(path_text: str, raw: bytes) -> None`.
- Add `_qualification_bootstrap_record(*, record_type: str, anchors: Mapping[str, Any], created_unix_ns: int, pid: int, previous_hash: str | None, stage_index: int, stage_name: str, payload: Mapping[str, Any]) -> dict[str, Any]`.
- Add `_qualification_bootstrap_record_bytes(record: Mapping[str, Any]) -> bytes`.
- Add `_qualification_bootstrap_publish_record_once(path: Path, record: Mapping[str, Any]) -> None`.
- Change trusted launcher argv to include envelope base64 and launch token before `qualify`.

- [ ] **Step 1: Add red publisher and claim tests**

Execute `_QUALIFICATION_BOOTSTRAP_LIBRARY_SOURCE` in an empty namespace with only standard builtins. Cover:

- exact ASCII/LF bytes and self-hash replay;
- `os.O_CREAT | os.O_EXCL | os.O_RDWR` creation, complete write, `os.fsync`, same-descriptor reread, final identity equality, and no temporary file;
- missing parent, linked/reparse parent or final path, non-regular entry, alternate data stream, Win32 alias, UNC, relative path, parent identity drift, short write, fsync error, and reread mismatch;
- collision with empty, partial, malformed, or valid existing claim bytes, proving the original bytes remain unchanged;
- no parent creation and no delete/truncate/replace behavior.

Add a trusted-launcher subprocess fixture that supplies valid v3 anchors and a tiny reviewed runner. Assert claim exists before runner code writes its entry marker. Assert a second invocation exits 2, keeps the first claim bytes unchanged, creates no later control file, and emits `stdout == b""` and `stderr == b""`.

- [ ] **Step 2: Run the red launcher slice**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "bootstrap_publisher or trusted_launcher_claim or claim_collision or claim_stream_silence" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\claim-red" `
  -q
```

Expected: selected tests fail before any real qualification child is started.

- [ ] **Step 3: Implement one reusable pure-stdlib library source**

The library source may import only `hashlib`, `json`, `os`, `stat`, and `time`. Compile that exact source into the trusted launcher and execute the same source in the runner namespace. Keep all inputs explicit so the library never imports repository modules or reads environment variables itself.

The exclusive writer must:

1. Lexically validate a local absolute direct-child path.
2. lstat every existing component without following links/reparse points.
3. snapshot parent `(st_dev, st_ino, file attributes)` before open.
4. open the final path once with exclusive creation, read/write access, and binary mode where available.
5. write all bytes in a loop, fsync, fstat, seek, and reread exact bytes through the same descriptor.
6. close once, lstat parent and final path again, and require unchanged parent identity plus final identity equality with the regular non-link fstat result.
7. leave any created bytes in place on every later error.

- [ ] **Step 4: Claim before runner validation**

In trusted-launcher code, first suppress stderr, decode and validate only the minimum canonical envelope/token/root/claim path needed for safe publication, and exclusively publish the claim. Only after a durable valid claim may it validate runner lexical identity, runner bytes/SHA, the exact qualifier option order, request hash/file-hash/size/R equality with the envelope, argv shape, and remaining static anchors. On success publish `launcher_verified`, export the three anchor environment variables, strip envelope/token from runner `sys.argv`, and execute the already-hashed in-memory runner bytes.

An invalid envelope that cannot safely identify the reviewed claim path exits silently without writing elsewhere. An existing claim exits silently and never attempts a failure/stage write. A post-claim controlled launcher failure may publish one failure record only if the valid claim can be reread and linked.

- [ ] **Step 5: Update runner trusted-shape validation**

Require `sys.orig_argv[1:5] == ("-I", "-S", "-c", QUALIFICATION_TRUSTED_LAUNCHER_CODE)`, runner at index 5, runner SHA at 6, envelope at 7, token at 8, and qualifier arguments from index 9 onward. Require all three exported environment anchors equal those argv values before clearing them from the child environment assembled later.

- [ ] **Step 6: Run launcher and request tests green**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "bootstrap_publisher or trusted_launcher or claim or qualification_request" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\claim-green" `
  -q
```

Expected: zero selected failures and empty subprocess streams.

- [ ] **Step 7: Check OpenSpec items 1.2 and 2.1; record progress on 2.3 without checking it; commit**

```powershell
git commit -m "feat: add pre-request qualification claim"
```

---

### Task 3: Record Runner, Source, Request, And Isolation Stages

**Files:**

- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:122-819`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:1070-1302`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:2325-2415`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:3785-3910`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:7410-7465`
- Modify `tests/test_noncombat_outcome_evidence_runner.py:2800-3900`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Use one exact bootstrap-state dictionary containing envelope, anchors, paths, claim hash, last record hash/index/name, and consumed flag; each transition returns a new dictionary instead of mutating its input.
- Add `_qualification_bootstrap_state_from_environment() -> dict[str, object]`.
- Add `_qualification_bootstrap_publish_stage(state: Mapping[str, object], stage_name: str, *, created_unix_ns: int | None = None) -> dict[str, object]`.
- Add `_qualification_bootstrap_publish_failure(state, code, exc) -> str | None`.
- Add `_qualification_bootstrap_validate_prefix_for_request(state, request) -> None`.

- [ ] **Step 1: Add red integration tests at every validation boundary**

Use the exact trusted launcher and production request loader. For each case, assert the exact final contiguous stage, optional fixed failure code, no active request, no attempt, no child marker, unchanged protected state, and empty stdout/stderr:

| Failure input | Last successful stage | Failure code |
|---|---|---|
| runner path/hash/shape rejection after claim | `claim` | `runner_validation_failed` |
| isolated/no-site/orig-argv/environment mismatch | `launcher_verified` | `runner_entry_validation_failed` |
| wrong HEAD, tracked bytes, executable/importable drift, unsafe Git metadata/config | `runner_entered` | `source_validation_failed` |
| malformed request anchors, invalid S-to-R review, registration/implementation drift | `source_verified` | `request_validation_failed` |
| CommunicationMod semantics or marker/run/checkpoint/log inventory drift | `request_reviewed` | `prelaunch_isolation_failed` |

Also assert that failure publication itself cannot overwrite an existing failure entry and that an unexpected exception maps to `unexpected_pre_request_failure` with fixed public detail.

- [ ] **Step 2: Run the red stage slice**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "bootstrap_stage or bootstrap_controlled_failure or pre_request_stage_boundary" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\stages-red" `
  -q
```

Expected: tests fail because runner/source/request/isolation stage files are absent.

- [ ] **Step 3: Publish `runner_entered` only after the current entry checks**

Have `_qualification_require_trusted_launcher()` return validated bootstrap state. Publish `runner_entered` only after isolated/no-site, exact original argv, environment anchors, current runner bytes, and launcher-code identity all pass. Do not parse project arguments or import project modules first.

- [ ] **Step 4: Publish `source_verified` after the current pre-import bootstrap**

Remove the broad silent `SystemExit` conversion that loses stage context. Preserve silent exit behavior, but route source validation exceptions through one fixed `source_validation_failed` publication attempt. Publish `source_verified` only after Git executable/environment, metadata, HEAD/R, reviewed executable/importable bytes, tracked inventory, untracked executable checks, and source-only import setup all pass.

- [ ] **Step 5: Publish `request_reviewed` and `isolation_verified`**

Publish `request_reviewed` after argument parsing, external request/file/size/R anchors, canonical request source, S-to-R review chain, registration, implementation map, command, static bootstrap declaration, and current valid prefix all pass.

Publish `isolation_verified` after the existing request-bound CommunicationMod semantics and marker/run/checkpoint/global-log prelaunch comparison returns zero mismatches. Pass the already-computed observation result through; do not recollect isolation merely to render the stage.

- [ ] **Step 6: Centralize pre-request controlled failure handling**

Track whether active-request publication has started. Before that boundary, map known checks to fixed failure codes and fixed public details, publish at most one failure record linked to the last valid prefix, remain stream-silent, and return exit code 2. After active-request publication, retain the existing lifecycle failure ownership; never relabel it as a bootstrap failure.

- [ ] **Step 7: Run stage and isolation tests green**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "bootstrap_stage or bootstrap_controlled_failure or qualification_source or qualification_request or prelaunch_isolation or stream_silence" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\stages-green" `
  -q
```

Expected: zero selected failures; each fixture shows one exact prefix and no repeated protected-state observations.

- [ ] **Step 8: Check OpenSpec items 2.3 and 2.4; leave 1.3 unchecked until Task 7; commit**

```powershell
git commit -m "feat: record pre-request qualification stages"
```

---

### Task 4: Bind Active Request, Handoff, Review, And Terminal V3

**Files:**

- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:1381-1455`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:2624-2667`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:3500-3660`
- Modify `scripts/run_noncombat_outcome_evidence_expansion.py:3785-4555`
- Modify `tests/test_noncombat_outcome_evidence_runner.py:3400-4700`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Add `_qualification_bootstrap_publish_handoff(state: Mapping[str, object], active_request_bytes: bytes) -> dict[str, object]`.
- Add `_qualification_bootstrap_inventory(state, *, include_handoff: bool) -> dict[str, Any]`.
- Add request/result/review-binding v3 `bootstrap` validation.
- Keep result v1/v2 and review-binding v1 parsers available only to historical replay.

- [ ] **Step 1: Add red ordering and binding tests**

Cover these exact boundaries:

- active request cannot publish before a valid five-stage prefix;
- handoff cannot publish before exact active-request bytes exist;
- attempt publication and `process_starter` are unreachable until handoff rereads and validates;
- a crash after active-request publication but before handoff leaves immutable active-request partial evidence;
- a copied, changed, malformed, linked, non-regular, or preexisting handoff fails closed;
- result/review v3 reject missing or changed claim hash, final-stage hash, handoff hash, launch token, inventory path/hash/size, and active-request byte hash;
- failure result remains owned by the existing post-handoff lifecycle and cannot create a bootstrap failure record.

- [ ] **Step 2: Run the red handoff slice**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "bootstrap_handoff or active_request_partial or qualification_result or qualification_review_binding" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\handoff-red" `
  -q
```

Expected: selected tests fail because active request is not yet gated by a handoff and result/review schemas remain old.

- [ ] **Step 3: Publish active request and handoff in fixed order**

In `execute_prelock_qualification()`:

1. Require `isolation_verified` as the final valid prefix record.
2. Read exact reviewed source-request bytes already validated against external file hash/size.
3. Publish those exact bytes at `request_path` with the existing exclusive operation.
4. Reread active request no-follow and require byte equality.
5. Publish handoff with claim hash, final-stage hash, active-request SHA/size, request self-hash, and launch token.
6. Reread and validate the complete chain.
7. Only then publish attempt and call `process_starter`.

Do not catch a handoff interruption as a pre-request failure. Once active request exists, the immutable state is `active_request_partial` unless the existing terminal lifecycle later completes.

- [ ] **Step 4: Bind bootstrap evidence into review and result v3**

Use one canonical `bootstrap` summary in both records:

```python
{
    "claim_hash": state["claim_hash"],
    "failure_hash": None,
    "final_stage_hash": state["final_stage_hash"],
    "handoff_hash": state["handoff_hash"],
    "inventory": [
        {
            "path": path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }
        for path, raw in ordered_bootstrap_files
    ],
    "launch_token": state["launch_token"],
    "schema_version": QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION,
}
```

Require exact sorted inventory order: claim, stages 1-5, handoff. Completion/failure result v3 validates every record and hash before publication. Review-binding v3 binds the same summary plus existing request/allowed-path/implementation/registration/S/R fields.

- [ ] **Step 5: Preserve child stream and restoration behavior**

Do not change child stdin/stdout/stderr forwarding, handshake deadlines, at-most-one child behavior, release handling, CommunicationMod restoration, post-isolation recollection, child-death checks, or terminal publish-once semantics. Add only the handoff prerequisite and v3 evidence fields.

- [ ] **Step 6: Run lifecycle tests green**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "qualification_orchestrator or bootstrap_handoff or active_request_partial or qualification_result or qualification_review_binding or isolation" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\handoff-green" `
  -q
```

Expected: zero selected failures; `process_starter` call count remains zero in every incomplete-handoff case.

- [ ] **Step 7: Check OpenSpec item 2.5 and commit**

```powershell
git commit -m "feat: bind qualification bootstrap handoff"
```

---

### Task 5: Independently Verify V3 Prefixes And Classifications

**Files:**

- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py:150-180`
- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py:517-680`
- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py:1477-1930`
- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py:2411-2700`
- Modify `tests/test_noncombat_outcome_evidence_verifier.py:860-1900`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Add `_qualification_bootstrap_declared_paths(request, qualification_root) -> dict[str, Path]`.
- Add `_qualification_bootstrap_expected_envelope(*, request: Mapping[str, Any], expected_request_file_sha256: str, expected_request_size: int, review_commit: str, runner_sha256: str) -> dict[str, Any]`.
- Add `_qualification_verify_bootstrap_prefix(request, review, *, active_request_bytes, checks) -> dict[str, Any]`.
- Advance current audit output to `noncombat-outcome-evidence-qualification-verification-audit-v3`; retain an explicit audit-v2 historical constant.

- [ ] **Step 1: Add red independent replay vectors**

Construct verifier fixtures from literal canonical bytes rather than producer record builders. Cover:

- absent root artifacts -> `reviewed_prepared`, `consumed=false`;
- valid claim only -> `pre_request_partial`, `partial_stage=abrupt_after_claim`;
- each valid contiguous stage prefix -> `abrupt_after_${stage_name}`;
- each fixed valid failure -> `partial_stage` equal to its fixed code;
- malformed/torn claim, bad canonical bytes, bad self-hash, changed anchors, gap, reorder, duplicate, extra stage, linked/non-regular entry, or unexpected root entry -> `sealed_invalid`;
- valid five-stage prefix plus active request but absent/invalid handoff -> `active_request_partial`;
- every prefix/audit authority field false, `retry_allowed=false`, and `consumed=true` whenever any bootstrap/control entry exists.

- [ ] **Step 2: Run the red verifier-prefix slice**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_verifier.py `
  -k "bootstrap_prefix or reviewed_prepared or pre_request_partial or sealed_invalid or active_request_partial" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\verifier-prefix-red" `
  -q
```

Expected: tests fail because current verifier only understands request/control lifecycle evidence.

- [ ] **Step 3: Reconstruct paths and token independently**

Repeat the schema rules in verifier code; do not import producer constants or helpers. Use externally supplied S/R/request file anchors and independently read reviewed Git blobs. Validate every lexical path before resolution/read/hash, require exact direct-child names, and derive the token with the frozen domain-separated canonical algorithm.

- [ ] **Step 4: Replay canonical records and root inventory**

Read each candidate once no-follow, preserve raw bytes, reject duplicates/constants/non-ASCII/non-canonical LF, recompute each self-hash, compare static anchors, and enforce exact previous-hash links. Inventory the guarded root and distinguish reviewed `preexisting_files` from the complete declared bootstrap/control set; any undeclared new entry is invalid.

Return this internal result shape:

```python
{
    "bootstrap_inventory": {
        "entries": ordered_rows,
        "entry_count": len(ordered_rows),
        "inventory_sha256": inventory_sha256,
    },
    "claim_hash": claim_hash,
    "consumed": consumed,
    "evidence_error": evidence_error,
    "evidence_valid": evidence_valid,
    "final_stage_hash": final_stage_hash,
    "handoff_hash": handoff_hash,
    "partial_stage": partial_stage,
    "qualification_status": qualification_status,
}
```

- [ ] **Step 5: Implement deterministic prefix classification**

Classification precedence is:

1. no claim/bootstrap/control entry -> `reviewed_prepared`;
2. malformed claim or any malformed/gapped/extra prefix evidence -> `sealed_invalid`;
3. valid claim/stage prefix and no active request -> `pre_request_partial`;
4. active request present without a complete valid prefix and handoff -> `active_request_partial` or `sealed_invalid` according to existing bytes, never repaired;
5. complete valid handoff -> continue through existing attempt/ready/release/terminal verification.

No timestamp threshold, elapsed-time guess, current process observation, or later-looking file may fill a missing stage.

- [ ] **Step 6: Run prefix tests green**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_verifier.py `
  -k "bootstrap_prefix or reviewed_prepared or pre_request_partial or sealed_invalid or active_request_partial or authority" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\verifier-prefix-green" `
  -q
```

Expected: zero selected failures; no fixture artifact is deleted or rewritten.

- [ ] **Step 7: Check OpenSpec items 3.1 and 3.2; leave 1.4 unchecked until Task 7; commit**

```powershell
git commit -m "feat: verify qualification bootstrap prefixes"
```

---

### Task 6: Verify Complete V3 Terminals And Preserve R1-R6 Replay

**Files:**

- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py:1477-1930`
- Modify `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py:2411-3275`
- Modify `tests/test_noncombat_outcome_evidence_verifier.py:1900-3000`
- Modify `tests/test_noncombat_outcome_evidence_runner.py:1418-1700`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Add strict v3 bootstrap comparison to `_qualification_expected_review_binding()`.
- Add strict v3 bootstrap comparison to `_verify_qualification_result()`.
- Keep request/result v1/v2, review-binding v1, and audit v2 dispatch byte-stable.

- [ ] **Step 1: Add red complete-terminal tamper tests**

Start from one literal valid v3 claim/stages/active-request/handoff/attempt/ready/release/result chain. Mutate each bootstrap path, byte, size, hash, anchor, stage link, handoff payload, result summary, review summary, external terminal anchor, restored-isolation field, or child-liveness outcome. Each mutation must prevent verified terminal output and keep all authority false.

Assert the verifier does not call producer record, request, result, review-binding, inventory, or token builders. A test should fail if the producer module appears in `sys.modules` during source-only verifier replay.

- [ ] **Step 2: Add immutable historical byte-and-absence fixture tests**

Use every actually preserved r1-r6 request/result/review/audit/report/root byte from reviewed Git commits or literal tracked fixtures. For every fixture, pin the complete available-artifact inventory by relative path, byte size, and SHA-256 and pin every expected absence. Record evidence-derived classification separately from the immutable governance disposition, including consumed/retry semantics, hashes, launchability, and authority output. Invoke complete public v1/v2 replay only when the preserved bundle retains every request, review, and Git anchor required by that path. Assert v3 implementation does not change a byte, collapse evidence and governance classifications, or synthesize a request, result, review commit, audit byte, Git anchor, bootstrap field, or root artifact for incomplete history.

- [ ] **Step 3: Run the red terminal/history slice**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_verifier.py `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "bootstrap_terminal or historical_r1 or historical_r2 or historical_r3 or historical_r4 or historical_r5 or historical_r6" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\terminal-history-red" `
  -q
```

Expected: v3 terminal tests fail; historical fixtures continue to expose any byte, absence, schema-dispatch, evidence-classification, or governance-disposition drift.

- [ ] **Step 4: Require full bootstrap replay before terminal success**

For request v3, require valid claim, all five stages, exact active request, valid handoff, attempt, ready, release, zero child exit, restored isolation, dead child, terminal anchors, result v3, and review-binding v3. Compare independently reconstructed bootstrap inventory/claim/final-stage/handoff hashes to both result and review before building audit v3.

Keep existing verified terminal status names. Observability is an additional prerequisite, not a new positive authority.

- [ ] **Step 5: Isolate historical dispatch**

Dispatch on explicit request schema before applying any v3 field-set checks. A historically complete request v1/v2 bundle must use its existing result/review/audit rules and remain unlaunchable by the current producer. An incomplete historical bundle must remain an exact byte/absence inventory with separately pinned evidence and governance classifications; do not make it replayable by rendering substitute bytes or reinterpret an absent bootstrap field as an empty valid prefix.

- [ ] **Step 6: Run terminal/history tests green**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_verifier.py `
  tests/test_noncombat_outcome_evidence_runner.py `
  -k "qualification or bootstrap_terminal or historical" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\terminal-history-green" `
  -q
```

Expected: zero selected failures; fixed historical SHA-256 values remain unchanged.

- [ ] **Step 7: Check OpenSpec items 3.3 and 3.4; commit**

```powershell
git commit -m "test: preserve historical qualification replay"
```

---

### Task 7: Prove Crash, Isolation, Tokenization, And Startup Matrices

**Files:**

- Modify `tests/test_noncombat_outcome_evidence_runner.py:2800-4700`
- Modify `tests/test_noncombat_outcome_evidence_verifier.py:860-3000`
- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`

**Interfaces:**

- Add a test-only subprocess worker that invokes the exact production bootstrap publisher and exits with `os._exit(97)` immediately after a selected durable record.
- Do not add a production CLI flag, environment pause, sleep, timeout, or retry hook.

- [ ] **Step 1: Add the durable crash matrix**

For claim, each stage, active request, and handoff, run a fresh subprocess rooted under `tmp_path`. The worker must use production canonical/publish functions, reread the target bytes, then call `os._exit(97)` without cleanup. Verify the root in a separate process and assert exact last-stage classification, consumption, retry refusal, no synthetic failure, and all-false authority.

For the active-request boundary, publish exact reviewed bytes and stop before handoff. Assert `active_request_partial`. For handoff, stop before attempt and assert the complete handoff is replayable but still non-terminal and non-authorizing.

- [ ] **Step 2: Prove retry refusal for every consumed prefix**

Run the exact trusted launcher a second time against every crash fixture. Require exit 2, unchanged recursive file inventory and bytes, no attempt/ready/release/terminal, no child marker, and empty stdout/stderr.

- [ ] **Step 3: Prove protected-state isolation**

Snapshot config, marker, runs, checkpoints, global logs, registered study root, run lock, ledger, manifest, trace, model, and policy fixtures before each pre-request case. Compare canonical inventory and bytes afterward. Monkeypatch or sentinel-wrap `_start_command`, ledger constructors, registered slot launch, and training entrypoints; every call count must stay zero.

- [ ] **Step 4: Prove CommunicationMod-equivalent tokenization and silence**

Build the exact command string stored in fixture `config.properties`, parse its `command` with the same whitespace split semantics used by CommunicationMod, and require exact equality with the reviewed vector. Assert trusted launcher code, envelope, token, and every remaining argument are each one token with no whitespace.

Run success, each controlled failure, each collision, malformed envelope, and post-handoff child smoke with binary capture. Require qualifier diagnostics never reach stdout/stderr; after handoff the fake child receives unchanged stdin/stdout/stderr ownership.

- [ ] **Step 5: Prove ordinary startup is unchanged**

Exercise `start`, `dry-run`, `run-next`, `monitor`, `finalize`, ordinary gameplay startup, registered slot startup, and training argument parsing without the exact qualification launcher/environment. Require their existing return/stream behavior and zero bootstrap artifacts. Ambient partial bootstrap environment must fail before ordinary attempt or child creation.

- [ ] **Step 6: Run production-Windows-Python launcher-to-handoff smoke**

Use only reviewed temporary fixtures and a no-action fake child; do not use Java or the game. Invoke:

```powershell
D:\anaconda\envs\stsai\python.exe -I -S -c TRUSTED_CODE RUNNER_PATH RUNNER_SHA256 ENVELOPE_B64 LAUNCH_TOKEN qualify FIXTURE_ARGUMENTS
```

The test itself constructs the vector; do not hand-enter secrets or live paths. Assert exact claim/stages/active-request/handoff/attempt/ready/release/terminal fixture artifacts as applicable, zero streams, zero protected-state drift, and no surviving child. Record artifact hashes in test output only on assertion failure; do not create a live qualification root.

- [ ] **Step 7: Run the focused subprocess matrix**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  tests/test_noncombat_outcome_evidence_verifier.py `
  -k "bootstrap_crash or bootstrap_retry or bootstrap_isolation or communication_tokenization or stream_silence or ordinary_startup or production_python_smoke" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\subprocess-matrix" `
  -q
```

Expected: zero selected failures, zero surviving fixture processes, and no file outside pytest basetemp changes.

- [ ] **Step 8: Check OpenSpec items 4.1 through 4.4 and remaining red-matrix portions of 1.3/1.4; commit**

```powershell
git commit -m "test: prove qualification bootstrap failure matrix"
```

---

### Task 8: Full Verification, Independent Review, And Offline Closeout

**Files:**

- Modify `openspec/changes/add-pre-request-qualification-observability/tasks.md`
- Modify `openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md`
- Modify `openspec/changes/run-v2-known-propensity-outcome-evidence-study/tasks.md`
- Add `reports/pre_request_qualification_observability_20260718_closeout.md`
- Review all implementation and focused test files from Tasks 1-7

**Interfaces:**

- Produce one source-only closeout with exact commands, counts, hashes, compatibility evidence, limits, and authority boundary.
- Do not produce a v3 request for a live candidate, a qualification root, CommunicationMod edit, game launch, or `start` decision.

- [ ] **Step 1: Run focused qualification verification**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  tests/test_noncombat_outcome_evidence_runner.py `
  tests/test_noncombat_outcome_evidence_verifier.py `
  tests/test_main_runtime_errors.py `
  tests/test_study_handshake.py `
  -k "qualification or bootstrap or handshake or runtime_error" `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\focused-final" `
  -q
```

Expected: zero failures. Record the collected/passed/skipped counts from this exact run.

- [ ] **Step 2: Run the complete Windows suite**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest `
  -p no:cacheprovider `
  --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\full-final" `
  -q
```

Expected: zero failures. Resolve any regression within this change's scope and rerun both focused and full commands.

- [ ] **Step 3: Run structural validation**

```powershell
openspec validate --all --strict
git diff --check
```

Render the fixed request/result/review/bootstrap/token/history vectors twice in fresh subprocesses and compare exact bytes and SHA-256 values. Search edited files for stale placeholder markers using split string literals so the plan itself does not become a match. Confirm no generated bytecode, pytest cache, temporary file, live report, request, root, or unrelated untracked artifact is staged.

- [ ] **Step 4: Obtain independent source-only review**

Use `superpowers:requesting-code-review` against the exact implementation diff. Require explicit review of:

- claim-before-runner ordering and permanent consumption;
- no-follow/O_EXCL/fsync/identity behavior;
- canonical byte and token determinism;
- stage/failure/handoff ordering and failure ownership;
- independent verifier implementation and classification precedence;
- historical v1/v2 replay isolation;
- stream silence, child ownership, and protected-state isolation;
- all-false authority and absence of live/start/training behavior.

Resolve every Important or higher finding, add a regression for behavioral corrections, and rerun focused/full/OpenSpec/diff checks.

- [ ] **Step 5: Write the offline closeout**

`reports/pre_request_qualification_observability_20260718_closeout.md` must contain:

1. source commit range and exact modified paths;
2. request/result/review-binding v3 and bootstrap/token v1 names;
3. fixed artifact names and byte/hash fixture values;
4. focused/full pytest commands and observed counts;
5. crash and controlled-failure matrix outcomes;
6. CommunicationMod-equivalent tokenization and stream-silence evidence;
7. protected-state isolation and no-surviving-child evidence;
8. r1-r6 byte/hash/absence inventory, evidence/governance classification, and eligible public-replay results;
9. strict OpenSpec, diff, deterministic-render, placeholder, and review results;
10. non-goals and rollback boundary;
11. explicit statement that r7, game launch, `start`, collection, OPE, policy, causal, training, and promotion authority remain false and require a separate amendment.

- [ ] **Step 6: Complete only source-observability task boxes**

After all evidence and review are green:

- check all remaining items 1.1-5.5 in `add-pre-request-qualification-observability`;
- check item 7.7 in `add-tracked-outcome-qualification-orchestrator`;
- check item 3.12 in `run-v2-known-propensity-outcome-evidence-study`;
- leave every r7 preparation, live qualification, game launch, and study `start` item unchecked.

- [ ] **Step 7: Re-run final validation after documentation edits**

```powershell
openspec validate --all --strict
git diff --check
git status --short
```

Expected: all OpenSpec changes valid; only intended implementation, test, plan/task, and closeout paths differ from the task base. Existing unrelated untracked files remain untouched and unstaged.

- [ ] **Step 8: Commit the cohesive closeout**

Inspect staged paths and staged diff before committing:

```powershell
git commit -m "docs: close pre-request qualification observability"
```

This commit must not contain a live request, runtime root, CommunicationMod configuration, game output, run lock, ledger, trajectory, model, policy, or training artifact.

## OpenSpec Coverage Matrix

| OpenSpec item | Plan task |
|---|---|
| 1.1 | Task 1 |
| 1.2 | Task 2 |
| 1.3 | Tasks 3 and 7 |
| 1.4 | Tasks 5 and 7 |
| 2.1 | Task 2 |
| 2.2 | Task 1 |
| 2.3 | Tasks 2 and 3 |
| 2.4 | Task 3 |
| 2.5 | Task 4 |
| 3.1 | Task 5 |
| 3.2 | Task 5 |
| 3.3 | Task 6 |
| 3.4 | Task 6 |
| 4.1 | Task 7 |
| 4.2 | Task 7 |
| 4.3 | Task 7 |
| 4.4 | Task 7 |
| 5.1 | Task 8 |
| 5.2 | Task 8 |
| 5.3 | Task 8 |
| 5.4 | Task 8 |
| 5.5 | Task 8 |

## Completion Gate

Implementation is complete only when all eight tasks are committed, every OpenSpec item maps to passing evidence, focused and full Windows pytest have zero failures, strict OpenSpec and diff checks pass, independent review is clear, historical bytes remain unchanged, and the closeout explicitly leaves all live/study/training authority false. Completion does not authorize a replacement identity; that remains a separate reviewed amendment.
