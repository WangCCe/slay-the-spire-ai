# Qualification Isolation Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every new pre-lock qualification bind and independently replay exact CommunicationMod, marker, run, checkpoint, log, and owned-child cleanup evidence before it can pass.

**Architecture:** Request v2 carries one compact canonical baseline. The runner validates it before launch, restores CommunicationMod, and seals post-observations in result v2; the standalone verifier uses an independent collector to replay the restored state and PID liveness. Historical v1 evidence remains replayable but never satisfies the strengthened launch gate.

**Tech Stack:** Python 3, stdlib `hashlib`/`base64`/`ctypes`, pytest, OpenSpec, Windows CommunicationMod.

## Global Constraints

- Use `D:\anaconda\envs\stsai\python.exe` for production-compatible tests.
- Add each regression before its production change and observe the intended failure.
- Do not launch Slay the Spire, consume r4, create a run lock, collect games, train, tune, or change gameplay policy.
- Reject symlinks, Windows reparse points, non-regular entries, traversal ambiguity, and incomplete observations.
- Keep every authority field false; terminal and verifier output are evidence only.
- Preserve immutable r1/r2/r3 v1 replay while refusing v1 for a new live qualification.

---

### Task 1: Red Request And CLI Regressions

**Files:**
- Modify: `tests/test_noncombat_outcome_evidence_runner.py`
- Modify: `openspec/changes/bind-qualification-isolation-evidence/tasks.md`

**Interfaces:**
- Consumes: `_qualification_request_fixture()` and `build_qualification_request()`.
- Produces: fixture resources for every later lifecycle test and red expectations for request v2.

- [x] **Step 1: Extend the request fixture with bounded live resources**

Create `config.properties`, `runs/IRONCLAD/100.run`, one registered checkpoint,
`ai_debug.log`, and `communication_mod_errors.log` beneath `tmp_path`; keep
their bytes small and deterministic.

```python
communication_path = tmp_path / "config.properties"
communication_path.write_bytes(
    b"verbose=false\ncommand=normal-agent\nrunAtGameStart=true\n"
)
(tmp_path / "runs" / "IRONCLAD").mkdir(parents=True)
(tmp_path / "runs" / "IRONCLAD" / "100.run").write_bytes(b"{}\n")
(tmp_path / "checkpoints").mkdir()
(tmp_path / "checkpoints" / "rl_model_ep1.pth").write_bytes(b"checkpoint")
(tmp_path / "ai_debug.log").write_bytes(b"debug baseline\n")
(tmp_path / "communication_mod_errors.log").write_bytes(b"")
```

- [x] **Step 2: Add red request assertions**

```python
def test_qualification_request_binds_complete_isolation_baseline(tmp_path, monkeypatch):
    _module_value, _registration_path, _source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    assert request["schema_version"].endswith("request-v2")
    assert set(request["isolation"]) == {
        "baseline_hash", "checkpoints", "communication_mod",
        "global_logs", "marker", "runs", "schema_version",
    }
    assert base64.b64decode(
        request["isolation"]["communication_mod"]["original_bytes_b64"]
    ) == (tmp_path / "config.properties").read_bytes()
```

- [x] **Step 3: Add red CLI silence assertion**

Change `test_qualification_cli_keeps_result_off_communication_stdout` to require
both `captured.out == ""` and `captured.err == ""` on success. The completion
file is the only success result channel.

- [x] **Step 4: Run the red tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "binds_complete_isolation_baseline or keeps_result_off_communication_stdout" -p no:cacheprovider --basetemp .pytest_tmp/isolation-red-request -q
```

Expected: the baseline assertion fails because `isolation` is absent, and the
CLI test fails because success JSON is still written to stderr.

### Task 2: Runner Snapshot And Request V2

**Files:**
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_runner.py`

**Interfaces:**
- Produces: `_qualification_build_isolation_baseline(registration, marker_path) -> dict[str, Any]`.
- Produces: `_qualification_observe_isolation(baseline, *, include_original_bytes=False) -> dict[str, Any]`.
- Produces: `_qualification_isolation_mismatches(expected, observed) -> list[str]`.

- [x] **Step 1: Add canonical collector tests before implementation**

Cover deterministic file ordering, content drift, added/deleted run files,
checkpoint-pattern filtering, explicit absent logs, marker bytes/count, and
reparse/non-regular rejection. Each test calls the wished-for collector API and
must initially fail because the function does not exist.

- [x] **Step 2: Implement compact file and inventory observations**

Use this stable shape:

```python
def _qualification_file_observation(path: Path, *, allow_missing: bool) -> dict[str, Any]:
    guarded = _qualification_require_no_follow_path(
        path, "isolation file", expected_kind="file", allow_missing=allow_missing
    )
    if not _qualification_path_entry_exists(guarded):
        return {"exists": False, "path": str(guarded), "sha256": None, "size": None}
    raw = guarded.read_bytes()
    return {
        "exists": True,
        "path": str(guarded),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }

def _qualification_inventory_observation(
    root: Path,
    *,
    patterns: Sequence[str] | None = None,
) -> dict[str, Any]:
    guarded_root = _qualification_require_no_follow_path(
        root, "isolation inventory root", expected_kind="directory"
    )
    rows = []
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(guarded_root):
        if is_link_or_reparse:
            raise OutcomeEvidenceRunnerError("isolation inventory contains a link or reparse point")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise OutcomeEvidenceRunnerError("isolation inventory contains a non-regular entry")
        relative = path.relative_to(guarded_root).as_posix()
        if patterns is not None and not any(path.match(pattern) for pattern in patterns):
            continue
        raw = path.read_bytes()
        rows.append({
            "kind": "file",
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        })
    rows.sort(key=lambda row: row["path"])
    return _qualification_compact_inventory(guarded_root, patterns, rows)
```

The persisted inventory is exactly:

```python
{
    "entry_count": len(rows),
    "inventory_sha256": hashlib.sha256(
        _canonical_json(rows).encode("utf-8")
    ).hexdigest(),
    "patterns": normalized_patterns_or_none,
    "root": str(root),
    "total_bytes": sum(row["size"] for row in rows),
}
```

- [x] **Step 3: Build and validate isolation baseline v1**

Derive the game root from `registration.checkpoint_root.parent`, require marker
at `game_root/runs/ai_games.txt`, bind both global logs, and store original
CommunicationMod bytes as canonical base64 plus parsed Java-properties
semantics. Self-hash the isolation object through `baseline_hash`.

- [x] **Step 4: Advance request creation/loading to v2**

Add `isolation` to the exact field set, emit
`noncombat-outcome-evidence-qualification-request-v2`, and validate every nested
field, hash, root, pattern, path relation, and base64 byte/hash/size equality.
Keep named v1 constants for historical verifier dispatch only.

- [x] **Step 5: Make qualification success CLI silent**

```python
if args.subcommand not in {"qualify"}:
    output_stream = sys.stderr if args.subcommand == "run-next" else sys.stdout
    print(_canonical_json(result), file=output_stream)
```

- [x] **Step 6: Run request-focused tests green**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "qualification_request or qualification_cli" -p no:cacheprovider --basetemp .pytest_tmp/isolation-request-green -q
```

Expected: all selected tests pass.

### Task 3: Owned Restoration And Result V2

**Files:**
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_runner.py`

**Interfaces:**
- Consumes: request `isolation` baseline from Task 2.
- Produces: `_qualification_restore_communication_config(baseline) -> dict[str, Any]`.
- Produces: result-v2 `isolation` evidence and strict validation.

- [x] **Step 1: Add red lifecycle tests**

Parameterize mutation of marker bytes, run inventory, checkpoint content, and
both global logs. Assert pre-launch mutations reject before `process_starter`;
post-exit mutations reject completion. Add tests that success and ordinary
failure restore exact original config bytes.

- [x] **Step 2: Validate live CommunicationMod semantics**

In real CLI mode, parse current Java properties and require every property
except `command` to equal the baseline. Require
`properties["command"].strip().split()` to equal `list(sys.orig_argv)`. Direct
unit execution may use the original baseline command, but the CLI path must not.

- [x] **Step 3: Restore exact bytes on controlled exits**

Write the decoded baseline bytes to a guarded same-directory temporary file,
flush/fsync it, atomically replace `config.properties`, reread and hash the
result, then remove any uncommitted temporary path on error. Never follow a
link/reparse component.

- [x] **Step 4: Seal post-isolation before completion**

After child `wait()` returns zero, require `poll()` is not `None`, restore the
config, recollect the compact observation, and require zero mismatches. Result
v2 includes:

```python
"isolation": {
    "baseline_hash": request["isolation"]["baseline_hash"],
    "child_alive": False,
    "communication_restored": True,
    "matched": not mismatches,
    "mismatches": mismatches,
    "post_observation": observed,
    "post_observation_hash": _self_hash(observed, "observation_hash"),
}
```

Ordinary failure attempts cleanup/restoration and binds observed mismatches;
completion remains forbidden unless every success predicate is exact.

- [x] **Step 5: Run lifecycle tests green**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py -k "qualification_orchestrator or qualification_result or isolation" -p no:cacheprovider --basetemp .pytest_tmp/isolation-lifecycle-green -q
```

Expected: all selected tests pass and no fixture writes outside `tmp_path`.

### Task 4: Independent Verifier Replay

**Files:**
- Modify: `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_verifier.py`

**Interfaces:**
- Consumes: request/result v2 bytes and existing external anchors.
- Produces: independent `_qualification_collect_isolation(request) -> dict[str, Any]` and `_qualification_pid_is_alive(pid) -> bool`.

- [x] **Step 1: Add red verifier drift tests**

Build valid completion evidence, then mutate each restored resource after the
terminal is anchored. Assert verification raises for config, marker, run,
checkpoint, and log drift. Monkeypatch `_qualification_pid_is_alive` to return
`True` and assert rejection.

- [x] **Step 2: Add independent collector**

Implement the same canonical row contract in the verifier without importing
the runner collector. Add cross-implementation fixture-vector tests asserting
equal observations for the same small tree.

- [x] **Step 3: Add strict v2 replay and audit binding**

Dispatch request/result schemas explicitly. For v2, verify request baseline,
terminal post-observation, current recollection, restoration flags, mismatch
list, and dead child PID before emitting a v2 audit. Include the verified
baseline/post hashes in the audit and keep every authority false.

- [x] **Step 4: Preserve v1 historical replay**

Add a fixed v1 request/result fixture and require the audit to label
`isolation_bound=false` and `launch_qualified=false`. Do not route v1 through
the live v2 qualifier.

- [x] **Step 5: Run verifier tests green**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_verifier.py -k "qualification" -p no:cacheprovider --basetemp .pytest_tmp/isolation-verifier-green -q
```

Expected: all selected tests pass.

### Task 5: Exact Bindings, Full Verification, And Source Commit

**Files:**
- Modify: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json`
- Modify: exact registration tests selected by `qualification_request`
- Modify: `openspec/changes/bind-qualification-isolation-evidence/tasks.md`
- Preserve but supersede: current uncommitted r4 request/review artifacts

**Interfaces:**
- Consumes: verified runner/verifier implementations.
- Produces: one cohesive source-fix commit S; no live authority.

- [x] **Step 1: Replay exact registration only after code is stable**

Re-render through the repository's canonical registration builder. The
registration binds implementation paths rather than file hashes, so the replay
must remain byte-for-byte equal even though a later request binds new runner and
verifier hashes. Preserve the old request externally and do not hand edit
canonical JSON.

- [x] **Step 2: Run focused verification**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py tests/test_noncombat_outcome_evidence_verifier.py -k "qualification" -p no:cacheprovider --basetemp .pytest_tmp/isolation-focused -q
```

- [x] **Step 3: Run full verification**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp/isolation-full -q
openspec validate --all --strict
git diff --check
```

Expected: pytest and all OpenSpec changes pass; no whitespace errors.

- [x] **Step 4: Obtain independent review**

Require explicit `Ready: Yes` for schema compatibility, restoration safety,
independent replay, source hygiene, and the no-live boundary. Resolve every
Important finding and rerun focused/full verification.

- [x] **Step 5: Commit one cohesive source snapshot**

Stage only the OpenSpec repair, plan, runner/verifier, focused tests, canonical
registration/fixtures, and necessary supersession notes. Verify the staged path
set and commit:

```powershell
git commit -m "fix: bind qualification isolation evidence"
```

Do not include a live request R, terminal evidence, run lock, collection,
training, or gameplay-policy artifact in this commit.
