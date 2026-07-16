# Outcome-Evidence Study Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently verify registered blocked closeouts and require an attempt/ready/release CommunicationMod handshake before any future outcome-evidence slot is claimed.

**Architecture:** Split verifier replay into normal and blocked branches selected only from the validated ledger and claim. Add a small shared handshake module used by the actual `main.py` child and the registered runner; publish a durable attempt before `Popen`, claim the slot only after a bound ready record and unchanged marker/output checks, then release the child. Version future registrations as v2 while keeping v1 read-only verification.

**Tech Stack:** Python 3.10, standard-library JSON/hash/path/process/threading APIs, existing CommunicationMod `Coordinator`, OpenSpec 1.6.0, Windows production Python `D:\anaconda\envs\stsai\python.exe`, `pytest`.

## Global Constraints

- Keep `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260715` byte-for-byte immutable and permanently blocked.
- Do not create a fresh registration, resume a slot, collect gameplay evidence, run OPE, train, tune, alter rewards/RL spaces/gameplay policy, or authorize promotion.
- Every production behavior change follows RED -> minimal GREEN -> focused pytest before the next behavior.
- Future handshake deadlines are exactly 30 seconds for readiness and 10 seconds for release.
- Future launchable registrations use v2; v1 remains read-only and `start`/`run-next` reject it.
- Ordinary gameplay with no explicit study-handshake environment remains behaviorally inert.
- Use Windows Python with `-p no:cacheprovider --basetemp .pytest-study-recovery-*` for focused and full tests.
- Stage only files named by the current task; do not add historical untracked test/report artifacts.

---

### Task 1: Freeze A Reproducible Blocked Baseline

**Files:**
- Create: `reports/outcome_evidence_study_recovery_baseline_20260716.md`
- Modify: `tests/test_noncombat_outcome_evidence_verifier.py`

**Interfaces:**
- Consumes: existing `_build_study()`, `runner.StudyLedger`, `expansion.finalize_registered_integrity_stop()`, and the immutable external v1 artifacts.
- Produces: `_build_blocked_study(tmp_path, monkeypatch) -> dict[str, Path | OutcomeEvidenceRegistration]` for all blocked verifier tests.

- [ ] **Step 1: Record the immutable external baseline**

Create the report with the known hashes, `terminal_slot_structure_invalid_14`, 305 marker trajectories, the current verifier error, and explicit absence of pool/target/readiness/estimate artifacts. Recompute every listed hash with `Get-FileHash`; do not write under the external artifact root.

- [ ] **Step 2: Add a synthetic v1 blocked fixture builder**

Add this interface beside `_build_study` and reuse its repo/run-lock setup helpers:

```python
def _build_blocked_study(tmp_path, monkeypatch):
    artifacts = _build_study_scaffold(tmp_path, monkeypatch)
    ledger = artifacts["ledger"]
    for slot_number, count in ((1, 25), (2, 22)):
        slot = artifacts["registration"].slots[slot_number - 1]
        ledger.start_slot(slot_number, slot.session_id, started_unix_ns=slot_number * 2)
        ledger.finish_slot(
            slot_number,
            process_exit_code=0 if count == 25 else 1,
            complete_trajectories=count,
            marker_start_count=25 * (slot_number - 1),
            marker_end_count=25 * (slot_number - 1) + count,
            ended_unix_ns=slot_number * 2 + 1,
        )
    ledger.global_stop(reason="terminal_slot_structure_invalid_03", created_unix_ns=10)
    result = expansion.finalize_registered_integrity_stop(
        artifacts["registration"],
        run_lock_hash=artifacts["run_lock"]["run_lock_hash"],
        ledger_snapshot=ledger.snapshot(),
    )
    artifacts.update(
        closeout_path=Path(result["paths"]["closeout_json"]),
        closeout_markdown_path=Path(result["paths"]["closeout_markdown"]),
    )
    return artifacts
```

- [ ] **Step 3: Add the observed red regression and normal control**

```python
def test_verifier_replays_registered_blocked_closeout(tmp_path, monkeypatch):
    artifacts = _build_blocked_study(tmp_path, monkeypatch)
    result = _verifier().verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )
    assert result["passed"] is True
    assert result["closeout_mode"] == "integrity_stop"


def test_normal_verifier_control_still_passes(tmp_path, monkeypatch):
    artifacts = _build_study(tmp_path, monkeypatch)
    assert _verifier().verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )["passed"] is True
```

- [ ] **Step 4: Run RED and control tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_verifier.py::test_verifier_replays_registered_blocked_closeout tests/test_noncombat_outcome_evidence_verifier.py::test_normal_verifier_control_still_passes -q -p no:cacheprovider --basetemp .pytest-study-recovery-red
```

Expected: blocked test fails with `normal closeout has a global stop`; normal control passes.

---

### Task 2: Add An Independent Blocked Verifier Branch

**Files:**
- Modify: `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_verifier.py`
- Modify: `openspec/changes/harden-outcome-evidence-study-recovery/tasks.md`

**Interfaces:**
- Consumes: `_verify_ledger(...) -> dict[str, Any]`, `_verify_claim(...)`, `_artifact_paths(...)`, `_Checks`.
- Produces: `_verify_blocked_closeout(...) -> dict[str, Any]`; `_verify_claim(...) -> Mapping[str, Any]`; branch-aware audit with `closeout_mode`.

- [ ] **Step 1: Make ledger and claim replay branch-neutral**

Remove only the normal-only assertions from `_verify_ledger`; keep `active is None`, chain, order, marker arithmetic, and duplicate-stop checks. Return `global_stop`. Change `_verify_claim` to validate `mode in {"complete", "integrity_stop"}`, exact binding, and return the claim.

At the top level:

```python
ledger = _verify_ledger(...)
claim = _verify_claim(...)
blocked = ledger["global_stop"] is not None
checks.require(
    claim["mode"] == ("integrity_stop" if blocked else "complete"),
    "ledger and finalization claim mode mismatch",
)
if not blocked:
    checks.require(len(ledger["terminal_slots"]) == SLOT_COUNT, "not every registered slot is terminal")
```

- [ ] **Step 2: Add blocked artifact paths and exact reconstruction helpers**

Extend `_artifact_paths` with `closeout_markdown`, `estimate_markdown`, and `readiness_markdown`. Implement independent helpers:

```python
def _blocked_gate(registration): ...
def _blocked_slots(registration, ledger): ...
def _blocked_closeout(registration, run_lock, ledger): ...
def _render_blocked_closeout_markdown(closeout): ...
def _verify_blocked_closeout(*, registration, run_lock, ledger, paths, checks): ...
```

`_blocked_gate` uses zero observed evidence, `all_registered_slots_accounted=False`, and `global_integrity_stop=True`; `_blocked_closeout` reproduces the v1 closeout fields and self-hash without importing `noncombat_outcome_evidence_expansion`.

- [ ] **Step 3: Branch before loading normal artifacts**

Immediately after claim verification:

```python
if blocked:
    blocked_result = _verify_blocked_closeout(...)
    return {
        "check_count": checks.count,
        "closeout_hash": blocked_result["closeout_hash"],
        "closeout_mode": "integrity_stop",
        "ledger_final_record_hash": ledger["final_record_hash"],
        "passed": True,
        "registration_hash": registration["registration_hash"],
        "run_lock_hash": run_lock["run_lock_hash"],
        "schema_version": AUDIT_SCHEMA_VERSION,
        "study_id": registration["study_id"],
        "verifier_implementation_sha256": _file_sha256(Path(__file__)),
    }
```

Normal loading and audit remain below this branch and add `closeout_mode="complete"`.

- [ ] **Step 4: Add blocked tamper cases**

Parametrize `stop_reason`, `claim_mode`, `terminal_slot`, `source`, `blocker`, `gate`, `limitation`, `closeout_hash`, `markdown`, and `forbidden_pool`. Each mutation must recompute outer self-hashes where needed so the test reaches the intended independent mismatch.

- [ ] **Step 5: Run focused GREEN tests**

Run the full verifier test module. Expected: all tests pass, including the unchanged normal replay and static import-independence test.

- [ ] **Step 6: Verify the external artifact read-only and commit**

Run the CLI against `reports/noncombat_outcome_evidence_expansion_20260715_registration.json`; confirm `closeout_mode=integrity_stop`, then re-hash the external root and update the baseline report. Mark OpenSpec tasks 1.1-2.5 complete and commit:

```powershell
git commit -m "fix: verify blocked outcome study closeouts"
```

---

### Task 3: Implement Strict Handshake Records And Child Gate

**Files:**
- Create: `spirecomm/communication/study_handshake.py`
- Create: `tests/test_study_handshake.py`
- Modify: `main.py`
- Modify: `tests/test_main_runtime_errors.py`
- Modify: `openspec/changes/harden-outcome-evidence-study-recovery/tasks.md`

**Interfaces:**
- Produces: `HANDSHAKE_ATTEMPT_ENV`, `HANDSHAKE_SCHEMA_VERSION`, `StudyHandshakeError`, `HandshakePaths`, `derive_slot_token`, `build_attempt_record`, `publish_record_once`, `validate_ready_record`, `build_release_record`, `perform_child_handshake_if_configured`.
- Consumes: coordinator `start_input_thread()` and `receive_game_state_update(block=False, perform_callbacks=False)`.

- [ ] **Step 1: Write red schema/publication tests**

Tests cover absent environment returns `False`, exact field sets, bool/float/string integer rejection, self-hash mismatch, non-absolute paths, duplicate exclusive publication, token determinism, PID mismatch, and release binding.

Use this stable API:

```python
paths = HandshakePaths(attempt=..., ready=..., release=...)
attempt = build_attempt_record(
    study_id="study-1",
    registration_hash="1" * 64,
    run_lock_hash="2" * 64,
    slot_number=1,
    session_id="study-1-s01",
    config_path=config_path,
    config_sha256="3" * 64,
    marker_start_count=10,
    paths=paths,
    readiness_timeout_seconds=30,
    release_timeout_seconds=10,
    created_unix_ns=1,
)
```

- [ ] **Step 2: Run RED**

Expected: import failure for `spirecomm.communication.study_handshake`.

- [ ] **Step 3: Implement strict records and atomic publication**

Use canonical ASCII JSON, exact field validation, SHA-256 self-hashes, `os.open(..., os.O_CREAT | os.O_EXCL | os.O_WRONLY)`, `fsync`, and cleanup only when creation itself failed before publication. Never overwrite an existing attempt/ready/release.

- [ ] **Step 4: Write red child-gate tests**

Use a fake coordinator whose first nonblocking receive returns `True`, records `perform_callbacks=False`, and retains `last_game_state`. Assert ready publication precedes release polling; assert timeout and CommunicationMod error raise `StudyHandshakeError`; assert no-environment path never touches the coordinator.

- [ ] **Step 5: Implement child gate and integrate explicit startup ordering**

Add:

```python
def create_ready_coordinator(agent_type, *, force_input_thread=False):
    defer_input_thread = agent_type in {"rl", "combat_rl"} and not force_input_thread
    ...


def initialize_study_handshake_if_configured(coordinator, *, environ=None):
    from spirecomm.communication.study_handshake import (
        perform_child_handshake_if_configured,
    )
    return perform_child_handshake_if_configured(
        coordinator,
        environ=os.environ if environ is None else environ,
    )
```

Keep the existing no-handshake ordering. Only when `HANDSHAKE_ATTEMPT_ENV` is present: create the coordinator with `force_input_thread=True`, complete the gate, then initialize exploration runtime and create the agent.

- [ ] **Step 6: Run focused GREEN tests and mark tasks 3.1-3.4**

Run `tests/test_study_handshake.py` plus `tests/test_main_runtime_errors.py`. Expected: all pass; normal combat-RL stdin remains deferred and explicit handshake starts it early.

---

### Task 4: Version Future Registrations As V2

**Files:**
- Modify: `analysis_scripts/noncombat_outcome_evidence_expansion.py`
- Modify: `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_verifier.py`
- Modify: `tests/test_noncombat_outcome_evidence_runner.py`

**Interfaces:**
- Produces: `LEGACY_REGISTRATION_SCHEMA_VERSION`, v2 `REGISTRATION_SCHEMA_VERSION`, `build_registration(..., schema_version=...)`, `registration_handshake_rules(registration)`, and `require_launchable_registration(registration)`.
- Consumes: handshake protocol constants and `RUN_LOCK_IMPLEMENTATION_PATHS`.

- [ ] **Step 1: Add red v1/v2 contract tests**

Assert default builder emits v2 with exact handshake fields; explicit legacy builder reproduces the committed v1 JSON shape; both validate/render; runner launch guard rejects v1 and accepts v2; verifier independently reconstructs both.

- [ ] **Step 2: Run RED**

Expected: missing `LEGACY_REGISTRATION_SCHEMA_VERSION` and no v2 handshake rules.

- [ ] **Step 3: Implement versioned registration generation**

Add `schema_version` to `OutcomeEvidenceRegistration`. `_registration_body` includes the v1 body unchanged or the v2 `integrity_rules.communication_handshake` object:

```python
{
    "attempt_suffix": "-communication-attempt.json",
    "orphaned_attempt_global_stop": True,
    "protocol_version": "noncombat-outcome-evidence-handshake-v1",
    "ready_suffix": "-communication-ready.json",
    "readiness_timeout_seconds": 30,
    "release_suffix": "-communication-release.json",
    "release_timeout_seconds": 10,
    "required_before_slot_claim": True,
}
```

Add `spirecomm/communication/study_handshake.py` to v2 implementation paths only. `validate_registration` accepts exactly v1 or v2 and rebuilds the matching canonical body.

- [ ] **Step 4: Add launch guard and independent verifier support**

`start` and `run-next` call `require_launchable_registration`; dry-run and verifier may load v1. The verifier's `_expected_registration` selects the exact v1 or v2 implementation list/rules by `schema_version` without importing production registration code.

- [ ] **Step 5: Run focused GREEN tests**

Run expansion, runner registration, and verifier modules. Expected: v1 fixture remains byte-identical and blocked verification still passes; all default synthetic studies now use v2.

---

### Task 5: Claim A Slot Only After The Real Child Is Ready

**Files:**
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_runner.py`
- Modify: `openspec/changes/harden-outcome-evidence-study-recovery/tasks.md`

**Interfaces:**
- Produces: `execute_handshaken_registered_slot(...) -> dict[str, Any]` and a `HandshakeChildProcess` protocol with `pid`, `poll()`, `wait()`, `terminate()`, `kill()`.
- Consumes: v2 handshake rules, `build_attempt_record`, `validate_ready_record`, `build_release_record`, `publish_record_once`, `StudyLedger`.

- [ ] **Step 1: Add red successful-ordering test**

Use a fake process starter that asserts the attempt already exists while `ledger.snapshot()["active_slot"] is None`, writes a valid ready record, and returns a live fake process. Capture events and require:

```python
assert events == [
    "marker-baseline",
    "attempt-published",
    "process-started",
    "ready-verified",
    "slot-started",
    "release-published",
    "process-waited",
    "slot-finished",
]
```

- [ ] **Step 2: Add red fail-closed matrix**

Parametrize process-start failure, orphaned attempt, readiness timeout, early exit, malformed ready, PID/token/config mismatch, marker growth, premature manifest, premature trace, release publication failure, and wait exception. Before claim failures leave no active/terminal slot and exactly one global stop. After claim failures recover one interrupted terminal and globally stop. No case calls the process starter twice.

- [ ] **Step 3: Implement bounded lifecycle**

Capture marker count before attempt. Publish attempt once. Start with `Popen`; poll ready/process using monotonic deadlines. Re-check marker count and manifest/trace absence before `ledger.start_slot`. Publish release only after start. On failure, terminate then wait, escalate to kill after a bounded grace period, and record the appropriate ledger state exactly once.

- [ ] **Step 4: Route `run-next` through the new lifecycle**

Replace `subprocess.call` with a `Popen` starter using inherited stdin/stdout/stderr and the attempt environment. Keep the existing low-level `execute_registered_slot` only for non-handshake unit compatibility; no launchable CLI path may call it.

- [ ] **Step 5: Run focused GREEN tests and commit**

Run runner, handshake, main startup, registration, and verifier tests. Mark tasks 4.1-4.4 complete and commit:

```powershell
git commit -m "fix: gate registered slots on CommunicationMod readiness"
```

---

### Task 6: Expose Safe Handshake Structure In Dry-Run And Monitor

**Files:**
- Modify: `scripts/run_noncombat_outcome_evidence_expansion.py`
- Modify: `tests/test_noncombat_outcome_evidence_runner.py`
- Modify: `openspec/changes/harden-outcome-evidence-study-recovery/tasks.md`

**Interfaces:**
- Consumes: registration v2 handshake rules and deterministic per-slot paths.
- Produces: dry-run `handshake` objects and blinded monitor `handshake` status with existence/SHA-256 only.

- [ ] **Step 1: Add red dry-run and monitor tests**

Require every launch plan to include attempt/ready/release paths plus fixed deadlines. Monitor rows may include `attempt_exists`, `attempt_sha256`, `ready_exists`, `ready_sha256`, `release_exists`, `release_sha256`, and lifecycle status; recursively assert all existing forbidden outcome/evaluation keys remain absent.

- [ ] **Step 2: Implement deterministic rendering**

Build paths from artifact root, session ID, and registered suffixes. Hash only existing regular files. Treat ready/release without attempt, release without ledger claim, or any handshake artifact on a later unattempted slot as a structural blocker.

- [ ] **Step 3: Run focused GREEN tests and commit**

Run all runner/monitor tests. Mark tasks 4.5-4.6 complete and commit the monitor changes with the handshake cluster if not already committed.

---

### Task 7: Complete Verification And No-Action Live Smoke

**Files:**
- Create: `reports/outcome_evidence_study_recovery_20260716.md`
- Modify: `openspec/changes/harden-outcome-evidence-study-recovery/tasks.md`

**Interfaces:**
- Consumes: all implementation and immutable baseline hashes.
- Produces: final no-study closeout report and completed OpenSpec checklist.

- [ ] **Step 1: Run focused Windows tests**

Run verifier, finalizer, expansion, runner, handshake, main startup, exploration runtime, and monitor tests with a fresh writable basetemp. Record exact pass count/time.

- [ ] **Step 2: Run full Windows pytest**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest-study-recovery-full
```

Record exact pass/fail count and duration.

- [ ] **Step 3: Run static and contract checks**

Run `openspec validate --all --strict`, `git diff --check`, `python -m py_compile` on changed Python files, direct import smoke, ASCII/LF/trailing-whitespace checks, and re-hash the immutable external artifacts.

- [ ] **Step 4: Run one no-action CommunicationMod smoke**

Snapshot config/checkpoints/AI marker count. Use a dedicated non-registration smoke attempt root and the real Windows Python child; require attempt -> ready -> release while callbacks/exploration remain disabled, then exit before gameplay. Restore config byte-for-byte, assert marker and checkpoints unchanged, inspect both logs, and stop all launched processes. Do not write a study ledger or reuse the blocked root.

- [ ] **Step 5: Obtain independent review**

Review verifier independence, mixed branch rejection, attempt crash windows, after-claim recovery, child state retention, normal-runtime inertness, forbidden monitor fields, tests, and authority boundary. Accept only findings supported by a red regression.

- [ ] **Step 6: Write closeout, mark tasks, commit, and push**

State that no fresh registration or evidence collection occurred and all RL/OPE/promotion gates remain unauthorized. Mark tasks 5.1-5.6 complete, run final OpenSpec/diff checks, commit:

```powershell
git commit -m "docs: close outcome study recovery hardening"
```

Push `codex/noncombat-ope-readiness`. The change is then ready for sync/archive review; a separate approved change is required before any new registered collection.
