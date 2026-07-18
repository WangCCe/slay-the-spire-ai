import ast
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from analysis_scripts import noncombat_outcome_evidence_expansion as expansion
from scripts import run_noncombat_outcome_evidence_expansion as runner
from spirecomm.ai.noncombat_exploration import (
    create_exploration_session_manifest,
    parse_exploration_config,
)
from spirecomm.communication.study_handshake import (
    HandshakePaths,
    build_attempt_record,
    build_ready_record,
    build_release_record,
    publish_record_once,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
SEED_BASE = 2_026_071_500
QUALIFICATION_SOURCE_COMMIT = "c" * 40
QUALIFICATION_REVIEW_COMMIT = "d" * 40


def _verifier():
    try:
        return importlib.import_module(
            "analysis_scripts.verify_noncombat_outcome_evidence_expansion"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"outcome evidence verifier is missing: {exc}")


def _create_directory_junction(link_path, target_path):
    completed = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link_path), str(target_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _qualification_review_kwargs(request):
    source_bytes = Path(request["request_source_path"]).read_bytes()
    return {
        "expected_request_file_sha256": hashlib.sha256(
            source_bytes
        ).hexdigest(),
        "expected_request_size": len(source_bytes),
        "expected_review_commit": QUALIFICATION_REVIEW_COMMIT,
    }


def test_historical_schema_bytes_remain_explicit_and_unchanged():
    expected = {
        "request_v1": "noncombat-outcome-evidence-qualification-request-v1",
        "request_v2": "noncombat-outcome-evidence-qualification-request-v2",
        "result_v1": "noncombat-outcome-evidence-qualification-result-v1",
        "result_v2": "noncombat-outcome-evidence-qualification-result-v2",
        "review_v1": "noncombat-outcome-evidence-qualification-review-binding-v1",
    }

    observed = {
        "request_v1": runner.QUALIFICATION_REQUEST_V1_SCHEMA_VERSION,
        "request_v2": runner.QUALIFICATION_REQUEST_V2_SCHEMA_VERSION,
        "result_v1": runner.QUALIFICATION_RESULT_V1_SCHEMA_VERSION,
        "result_v2": runner.QUALIFICATION_RESULT_V2_SCHEMA_VERSION,
        "review_v1": runner.QUALIFICATION_REVIEW_BINDING_V1_SCHEMA_VERSION,
    }

    assert observed == expected
    assert _canonical_json(observed).encode("ascii") == (
        b'{"request_v1":"noncombat-outcome-evidence-qualification-request-v1",'
        b'"request_v2":"noncombat-outcome-evidence-qualification-request-v2",'
        b'"result_v1":"noncombat-outcome-evidence-qualification-result-v1",'
        b'"result_v2":"noncombat-outcome-evidence-qualification-result-v2",'
        b'"review_v1":"noncombat-outcome-evidence-qualification-review-binding-v1"}'
    )


def test_qualification_file_reader_rejects_path_identity_change(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    evidence_path = tmp_path / "evidence.log"
    evidence_path.write_bytes(b"stable evidence\n")
    monkeypatch.setattr(verifier.os.path, "samestat", lambda *_args: False)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="changed while being read",
    ):
        verifier._qualification_read_file_bytes(
            evidence_path,
            "isolation evidence",
        )


def test_qualification_collector_reads_communication_bytes_once(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, _result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    communication_path = Path(
        request["isolation"]["communication_mod"]["path"]
    )
    original_reader = verifier._qualification_read_file_bytes
    read_count = 0

    def read_once(path, label):
        nonlocal read_count
        if Path(path) == communication_path:
            read_count += 1
            if read_count > 1:
                pytest.fail("CommunicationMod was reread for derived fields")
        return original_reader(path, label)

    monkeypatch.setattr(verifier, "_qualification_read_file_bytes", read_once)

    verifier._qualification_collect_isolation(request)

    assert read_count == 1


def test_qualification_collector_derives_marker_count_from_hashed_bytes(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, _result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    monkeypatch.setattr(
        verifier,
        "_qualification_marker_count",
        lambda _path: pytest.fail("marker was reread for line_count"),
    )

    observation = verifier._qualification_collect_isolation(request)

    assert observation["marker"]["line_count"] == 2


def _qualification_result_kwargs(result_path):
    try:
        result_bytes = Path(result_path).read_bytes()
    except OSError:
        return {
            "expected_result_file_sha256": "0" * 64,
            "expected_result_hash": "0" * 64,
            "expected_result_size": 1,
        }
    try:
        result = json.loads(result_bytes.decode("utf-8"))
        result_hash = result.get("result_hash")
    except (UnicodeError, json.JSONDecodeError, AttributeError):
        result_hash = None
    if not isinstance(result_hash, str) or len(result_hash) != 64:
        result_hash = "0" * 64
    return {
        "expected_result_file_sha256": hashlib.sha256(
            result_bytes
        ).hexdigest(),
        "expected_result_hash": result_hash,
        "expected_result_size": len(result_bytes),
    }


def _verify_qualification(
    verifier,
    request,
    result_path=None,
    **result_anchor_overrides,
):
    source_path = Path(request["request_source_path"])
    reviewed_request = json.loads(source_path.read_text(encoding="utf-8"))
    result_kwargs = (
        _qualification_result_kwargs(result_path)
        if result_path is not None
        else {}
    )
    result_kwargs.update(result_anchor_overrides)
    return verifier.verify_prelock_qualification(
        source_path,
        result_path,
        expected_request_hash=reviewed_request["request_hash"],
        **result_kwargs,
        **_qualification_review_kwargs(request),
    )


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_json(path, value):
    Path(path).write_text(
        _canonical_json(value) + "\n",
        encoding="utf-8",
        newline="",
    )


def _write_jsonl(path, rows):
    Path(path).write_text(
        "".join(_canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
        newline="",
    )


def _self_hash(value, field):
    payload = deepcopy(value)
    payload[field] = None
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _manifest_hash(value):
    payload = deepcopy(value)
    payload.pop("manifest_hash", None)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _rehash_closeout(path):
    closeout = json.loads(Path(path).read_text(encoding="utf-8"))
    closeout["closeout_hash"] = _self_hash(closeout, "closeout_hash")
    _write_json(path, closeout)
    return closeout


def _update_closeout_source(artifacts, field, value):
    closeout_path = artifacts["closeout_path"]
    closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
    closeout["source"][field] = value
    closeout["closeout_hash"] = _self_hash(closeout, "closeout_hash")
    _write_json(closeout_path, closeout)


def _update_pool_manifest(artifacts, mutate):
    path = artifacts["pool_manifest_path"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest["pool_manifest_hash"] = _self_hash(
        manifest,
        "pool_manifest_hash",
    )
    _write_json(path, manifest)
    _update_closeout_source(
        artifacts,
        "pool_manifest_hash",
        manifest["pool_manifest_hash"],
    )


def _sample(
    *,
    session_id,
    run_id,
    category,
    arm,
    source_commit,
    victory=False,
):
    if category == "card_reward":
        baseline_action = f"card_reward:take:{run_id}"
        alternative_action = "card_reward:skip"
        alternative_numerator = 300
        denominator = 10_000
        candidate_kind = "take"
    else:
        baseline_action = f"shop:buy:{run_id}"
        alternative_action = "shop:leave"
        alternative_numerator = 1_000
        denominator = 10_000
        candidate_kind = "buy"
    selected_action = (
        baseline_action if arm == "baseline" else alternative_action
    )
    selected_numerator = (
        denominator - alternative_numerator
        if arm == "baseline"
        else alternative_numerator
    )
    trajectory_session_id = f"{session_id}:trajectory:{run_id}"
    candidates = [
        {
            "action_id": baseline_action,
            "available": True,
            "executable": True,
            "kind": candidate_kind,
            "label": baseline_action,
            "raw": {},
        },
        {
            "action_id": alternative_action,
            "available": True,
            "executable": True,
            "kind": "skip" if category == "card_reward" else "leave",
            "label": alternative_action,
            "raw": {},
        },
    ]
    state = {"floor": 3}
    state_hash = hashlib.sha256(
        _canonical_json(
            {
                "candidates": candidates,
                "category": category,
                "state": state,
            }
        ).encode("utf-8")
    ).hexdigest()
    decision_payload = {
        "decision_index": 0,
        "namespace": "noncombat-exploration-decision-v1",
        "session_id": session_id,
        "state_hash": state_hash,
        "trajectory_session_id": trajectory_session_id,
    }
    sample_id = "decision-" + hashlib.sha256(
        _canonical_json(decision_payload).encode("utf-8")
    ).hexdigest()[:32]
    distribution = [
        {
            "action_id": baseline_action,
            "denominator": denominator,
            "numerator": denominator - alternative_numerator,
            "value": (denominator - alternative_numerator) / denominator,
        },
        {
            "action_id": alternative_action,
            "denominator": denominator,
            "numerator": alternative_numerator,
            "value": alternative_numerator / denominator,
        },
    ]
    distribution_hash = hashlib.sha256(
        _canonical_json(distribution).encode("utf-8")
    ).hexdigest()
    return {
        "behavior_action_probability": selected_numerator / denominator,
        "behavior_policy_commit": source_commit,
        "behavior_policy_id": f"known-propensity-epsilon-v1:{session_id}",
        "behavior_probability_status": "verified_known_propensity",
        "candidate_actions": candidates,
        "category": category,
        "current_policy_label": {
            "action_id": baseline_action,
            "label": baseline_action,
        },
        "exploration": {
            "alternative_action_id": alternative_action,
            "baseline_action_id": baseline_action,
            "candidate_distribution": distribution,
            "candidate_legality": "valid",
            "confirmation_status": "confirmed",
            "decision_id": sample_id,
            "decision_index": 0,
            "distribution_hash": distribution_hash,
            "replay_status": "valid",
            "selected_arm": arm,
            "selected_probability": {
                "denominator": denominator,
                "numerator": selected_numerator,
                "value": selected_numerator / denominator,
            },
            "session_id": session_id,
            "source_commit": source_commit,
            "state_hash": state_hash,
            "trajectory_session_id": trajectory_session_id,
        },
        "floor": state["floor"],
        "outcome": {
            "floor_reached": 16,
            "included_in_gate": True,
            "join_status": "matched",
            "killed_by": "" if victory else "Slime Boss",
            "playtime": 90,
            "run_file": f"{run_id}.run",
            "victory": victory,
        },
        "sample_id": sample_id,
        "schema_version": "noncombat-rl-decision-v3",
        "selected_action_id": selected_action,
        "trajectory_group_id": f"run:{run_id}",
        "trajectory_session_id": trajectory_session_id,
    }


def _trace_rows(sample, *, seed):
    exploration = sample["exploration"]
    completed_unix = int(Path(sample["outcome"]["run_file"]).stem)
    trajectory_started_unix = max(
        0,
        completed_unix - sample["outcome"]["playtime"],
    )
    proposal = {
        "alternative_action_id": exploration["alternative_action_id"],
        "baseline_action_id": exploration["baseline_action_id"],
        "candidates": sample["candidate_actions"],
        "category": sample["category"],
        "execution_eligible": True,
        "ineligibility_reason": "",
        "rollout_mode": "executable",
        "state": {"floor": sample["floor"]},
        "state_hash": exploration["state_hash"],
    }
    draw_input = {
        "alternative_action_id": exploration["alternative_action_id"],
        "baseline_action_id": exploration["baseline_action_id"],
        "candidate_action_ids": [
            candidate["action_id"] for candidate in sample["candidate_actions"]
        ],
        "category": sample["category"],
        "decision_index": exploration["decision_index"],
        "epsilon_bps": (
            300 if sample["category"] == "card_reward" else 1_000
        ),
        "schema_version": "noncombat-exploration-selection-v1",
        "seed": seed,
        "session_id": exploration["session_id"],
        "state_hash": exploration["state_hash"],
        "trajectory_session_id": sample["trajectory_session_id"],
    }
    draw_input_json = _canonical_json(draw_input).encode("utf-8")
    acceptance_limit = (1 << 64) - ((1 << 64) % 10_000)
    for draw_counter in range(1_000_000):
        digest = hashlib.sha256(
            draw_input_json + b"\x00" + str(draw_counter).encode("ascii")
        ).digest()
        draw_u64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
        if draw_u64 < acceptance_limit:
            break
    else:
        raise AssertionError("fixture could not derive an exploration draw")
    draw_bucket = draw_u64 % 10_000
    selected_action_id = (
        exploration["alternative_action_id"]
        if draw_bucket < draw_input["epsilon_bps"]
        else exploration["baseline_action_id"]
    )
    selected_probability = next(
        row
        for row in exploration["candidate_distribution"]
        if row["action_id"] == selected_action_id
    )
    selection = {
        "category": sample["category"],
        "decision_index": exploration["decision_index"],
        "distribution": exploration["candidate_distribution"],
        "distribution_hash": exploration["distribution_hash"],
        "draw_bucket": draw_bucket,
        "draw_counter": draw_counter,
        "draw_input_hash": hashlib.sha256(draw_input_json).hexdigest(),
        "draw_u64": draw_u64,
        "schema_version": "noncombat-exploration-selection-v1",
        "selected_action_id": selected_action_id,
        "selected_action_probability": selected_probability["value"],
        "selected_probability_denominator": selected_probability[
            "denominator"
        ],
        "selected_probability_numerator": selected_probability["numerator"],
        "session_id": exploration["session_id"],
        "state_hash": exploration["state_hash"],
        "trajectory_session_id": sample["trajectory_session_id"],
    }
    proposed = {
        "behavior_policy_id": sample["behavior_policy_id"],
        "category": sample["category"],
        "decision_id": sample["sample_id"],
        "decision_index": exploration["decision_index"],
        "proposal": proposal,
        "proposed_unix": trajectory_started_unix + 1,
        "record_type": "proposed",
        "schema_version": "noncombat-exploration-record-v1",
        "selected_candidate": next(
            row
            for row in sample["candidate_actions"]
            if row["action_id"] == selected_action_id
        ),
        "selection": selection,
        "session_id": exploration["session_id"],
        "trajectory_session_id": sample["trajectory_session_id"],
        "trajectory_started_unix": trajectory_started_unix,
        "alternative_attempt_budget": {
            "limit": 2,
            "selected_alternative": (
                selected_action_id == exploration["alternative_action_id"]
            ),
            "used_before": 0,
        },
    }
    resolved = {
        "category": sample["category"],
        "decision_id": sample["sample_id"],
        "executed_known_propensity": True,
        "reason": "confirmed",
        "record_type": "resolution",
        "resolved_unix": trajectory_started_unix + 2,
        "schema_version": "noncombat-exploration-record-v1",
        "selected_action_id": selected_action_id,
        "session_id": exploration["session_id"],
        "status": "confirmed",
        "trajectory_session_id": sample["trajectory_session_id"],
    }
    return proposed, resolved


def _copy_registered_sources(repo_root):
    for relative_path in expansion.RUN_LOCK_IMPLEMENTATION_PATHS:
        source = REPO_ROOT / relative_path
        assert source.is_file(), relative_path
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _git(repo_root, *arguments):
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _pre_session_isolation(run_lock):
    communication = run_lock["communication_mod"]
    isolation = {
        communication["path"]: {
            "semantic_sha256": communication["semantic_sha256"],
        }
    }
    for row in run_lock["checkpoints"]["files"]:
        isolation[row["path"]] = {
            "sha256": row["sha256"],
            "size": row["size"],
        }
    return isolation


def _publish_preclaim_handshake(registration, run_lock, slot, launch, marker_start):
    rules = registration.to_record()["integrity_rules"]["communication_handshake"]
    config_path = Path(launch.config_path).resolve()
    parent = config_path.parent
    paths = HandshakePaths(
        attempt=parent / f"{slot.session_id}{rules['attempt_suffix']}",
        ready=parent / f"{slot.session_id}{rules['ready_suffix']}",
        release=parent / f"{slot.session_id}{rules['release_suffix']}",
    )
    attempt = build_attempt_record(
        study_id=registration.study_id,
        registration_hash=registration.registration_hash,
        run_lock_hash=run_lock["run_lock_hash"],
        slot_number=slot.slot_number,
        session_id=slot.session_id,
        config_path=config_path,
        config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        marker_start_count=marker_start,
        paths=paths,
        readiness_timeout_seconds=rules["readiness_timeout_seconds"],
        release_timeout_seconds=rules["release_timeout_seconds"],
        created_unix_ns=slot.slot_number * 10 + 1,
    )
    publish_record_once(paths.attempt, attempt)
    ready = build_ready_record(
        attempt,
        child_pid=10_000 + slot.slot_number,
        created_unix_ns=slot.slot_number * 10 + 2,
    )
    publish_record_once(paths.ready, ready)
    return paths, attempt, ready


def _build_qualification_evidence(tmp_path, monkeypatch, *, status="passed"):
    communication_path = tmp_path / "config.properties"
    communication_path.write_bytes(
        b"verbose=false\ncommand=normal-agent\nrunAtGameStart=true\n"
    )
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    (checkpoint_root / "rl_model_ep1.pth").write_bytes(b"checkpoint-v1\n")
    run_root = tmp_path / "runs"
    (run_root / "IRONCLAD").mkdir(parents=True)
    (run_root / "IRONCLAD" / "100.run").write_bytes(b'{"victory":false}\n')
    (tmp_path / "ai_debug.log").write_bytes(b"existing debug log\n")
    (tmp_path / "communication_mod_errors.log").write_bytes(
        b"existing communication log\n"
    )
    registration = expansion.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=REPO_ROOT,
        seed_base=SEED_BASE,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=communication_path,
        checkpoint_root=checkpoint_root,
    )
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        expansion.render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    qualification_root = tmp_path / "qualification-r4"
    qualification_root.mkdir()
    qualification_id = f"{STUDY_ID}-qualification-r4"
    config_path = qualification_root / "qualification-config.json"
    config_path.write_text(
        _canonical_json(
            {
                "category_rates_bps": {"card_reward": 300, "shop": 1000},
                "enabled_categories": ["card_reward", "shop"],
                "manifest_path": str(
                    (qualification_root / "qualification-manifest.json").resolve()
                ),
                "per_run_alternative_budget": 2,
                "schema_version": "noncombat-exploration-config-v1",
                "seed": SEED_BASE + 1,
                "session_id": f"{qualification_id}-s01",
                "source_commit": QUALIFICATION_SOURCE_COMMIT,
                "study_id": qualification_id,
                "study_registration_hash": registration.registration_hash,
                "study_run_lock_hash": "0" * 64,
                "study_slot_number": 1,
                "trace_path": str(
                    (qualification_root / "qualification-trace.jsonl").resolve()
                ),
            }
        )
        + "\n",
        encoding="utf-8",
        newline="",
    )
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir(exist_ok=True)
    marker_path.write_text("10\n11\n", encoding="utf-8", newline="")
    current_commit = [QUALIFICATION_SOURCE_COMMIT]
    monkeypatch.setattr(
        runner,
        "_tracked_source_commit",
        lambda _repo_root, **_kwargs: current_commit[0],
    )
    monkeypatch.setattr(
        runner,
        "_require_committed_qualification_registration",
        lambda _registration_path, _repo_root, _source_commit: None,
        raising=False,
    )
    monkeypatch.setattr(
        runner,
        "_require_committed_qualification_request_source",
        lambda *_args, **_kwargs: QUALIFICATION_REVIEW_COMMIT,
        raising=False,
    )
    def validate_runner_review_chain(**kwargs):
        request_record = kwargs["request"]
        if request_record["source_commit"] != QUALIFICATION_SOURCE_COMMIT:
            raise runner.OutcomeEvidenceRunnerError(
                "qualification source commit mismatch"
            )
        source_path = Path(request_record["request_source_path"])
        source_bytes = source_path.read_bytes()
        return runner._build_qualification_review_binding(
            request=request_record,
            review_commit=QUALIFICATION_REVIEW_COMMIT,
            request_source_path=source_path,
            request_source_relative=source_path.relative_to(REPO_ROOT).as_posix(),
            request_bytes=source_bytes,
        )

    monkeypatch.setattr(
        runner,
        "_validate_qualification_review_chain",
        validate_runner_review_chain,
        raising=False,
    )
    request_source_path = (tmp_path / "reviewed-qualification-request.json").resolve()
    request = runner.build_qualification_request(
        registration_path=registration_path,
        qualification_id=qualification_id,
        qualification_root=qualification_root,
        config_path=config_path,
        marker_path=marker_path,
        request_source_path=request_source_path,
        created_unix_ns=100,
    )
    current_commit[0] = QUALIFICATION_REVIEW_COMMIT
    request_path = Path(request["request_path"])
    _write_json(request_source_path, request)
    reviewed_request = deepcopy(request)

    def load_historical_review(source_path, **kwargs):
        assert Path(source_path) == request_source_path
        assert kwargs["expected_review_commit"] == QUALIFICATION_REVIEW_COMMIT
        assert kwargs["expected_request_hash"] == reviewed_request["request_hash"]
        source_bytes = request_source_path.read_bytes()
        assert kwargs["expected_request_file_sha256"] == hashlib.sha256(
            source_bytes
        ).hexdigest()
        assert kwargs["expected_request_size"] == len(source_bytes)
        review_binding = runner._build_qualification_review_binding(
            request=reviewed_request,
            review_commit=QUALIFICATION_REVIEW_COMMIT,
            request_source_path=request_source_path,
            request_source_relative=request_source_path.relative_to(
                REPO_ROOT
            ).as_posix(),
            request_bytes=source_bytes,
        )
        return {
            "registration": registration.to_record(),
            "registration_bytes": registration_path.read_bytes(),
            "repo_root": REPO_ROOT,
            "request": reviewed_request,
            "request_bytes": source_bytes,
            "review_binding": review_binding,
        }

    monkeypatch.setattr(
        _verifier(),
        "_load_historical_qualification_review",
        load_historical_review,
        raising=False,
    )
    monkeypatch.setattr(
        _verifier(),
        "_qualification_pid_is_alive",
        lambda _pid: False,
        raising=False,
    )

    class QualificationChild:
        pid = 4321

        def __init__(self):
            self.returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.returncode = 0
            return self.returncode

        def terminate(self):
            self.returncode = -15

        def kill(self):
            self.returncode = -9

    child = QualificationChild()

    def process_starter(_command, environment):
        if status == "passed":
            attempt = runner.load_attempt_record(
                Path(environment[runner.HANDSHAKE_ATTEMPT_ENV])
            )
            ready = build_ready_record(
                attempt,
                child_pid=child.pid,
                created_unix_ns=201,
            )
            publish_record_once(Path(attempt["ready_path"]), ready)
        return child

    timestamps = iter(range(200, 220))
    if status == "passed":
        result = runner.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )
        result_path = Path(request["completion_path"])
    else:
        clock = [0.0]

        def advance_clock(_seconds):
            clock[0] = 121.0

        with pytest.raises(runner.OutcomeEvidenceRunnerError, match="readiness"):
            runner.execute_prelock_qualification(
                registration_path=registration_path,
                request_path=request_source_path,
                expected_request_hash=request["request_hash"],
                **_qualification_review_kwargs(request),
                process_starter=process_starter,
                monotonic=lambda: clock[0],
                sleep=advance_clock,
                time_ns=lambda: next(timestamps),
            )
        result_path = Path(request["failure_path"])
        result = json.loads(result_path.read_text(encoding="utf-8"))
    return request_path, result_path, request, result


def _downgrade_qualification_evidence_to_v1(
    verifier,
    request,
    result_path,
    monkeypatch,
):
    legacy_request = deepcopy(request)
    legacy_request.pop("isolation")
    legacy_request["schema_version"] = (
        runner.LEGACY_QUALIFICATION_REQUEST_SCHEMA_VERSION
    )
    legacy_request["request_hash"] = _self_hash(
        legacy_request,
        "request_hash",
    )
    request_source_path = Path(legacy_request["request_source_path"])
    active_request_path = Path(legacy_request["request_path"])
    _write_json(request_source_path, legacy_request)
    _write_json(active_request_path, legacy_request)
    request_bytes = request_source_path.read_bytes()
    review_binding = runner._build_qualification_review_binding(
        request=legacy_request,
        review_commit=QUALIFICATION_REVIEW_COMMIT,
        request_source_path=request_source_path,
        request_source_relative=request_source_path.relative_to(REPO_ROOT).as_posix(),
        request_bytes=request_bytes,
    )

    legacy_result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    legacy_result.pop("isolation")
    legacy_result["schema_version"] = (
        runner.LEGACY_QUALIFICATION_RESULT_SCHEMA_VERSION
    )
    legacy_result["request"]["hash"] = legacy_request["request_hash"]
    legacy_result["review_binding"] = review_binding
    legacy_result["result_hash"] = _self_hash(legacy_result, "result_hash")
    _write_json(result_path, legacy_result)

    registration_path = Path(legacy_request["registration"]["path"])
    registration_bytes = registration_path.read_bytes()
    registration = json.loads(registration_bytes.decode("utf-8"))

    def load_historical_review(source_path, **kwargs):
        assert Path(source_path) == request_source_path
        assert kwargs["expected_request_hash"] == legacy_request["request_hash"]
        assert kwargs["expected_request_file_sha256"] == hashlib.sha256(
            request_bytes
        ).hexdigest()
        assert kwargs["expected_request_size"] == len(request_bytes)
        return {
            "registration": registration,
            "registration_bytes": registration_bytes,
            "repo_root": REPO_ROOT,
            "request": legacy_request,
            "request_bytes": request_bytes,
            "review_binding": review_binding,
        }

    monkeypatch.setattr(
        verifier,
        "_load_historical_qualification_review",
        load_historical_review,
    )
    return legacy_request, legacy_result


def test_qualification_verifier_rejects_unanchored_terminal_evidence(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    source_path = Path(request["request_source_path"])
    reviewed_request = json.loads(source_path.read_text(encoding="utf-8"))

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="result anchors",
    ):
        verifier.verify_prelock_qualification(
            source_path,
            result_path,
            expected_request_hash=reviewed_request["request_hash"],
            **_qualification_review_kwargs(request),
        )


def test_qualification_verifier_rejects_reviewed_source_junction_alias(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    source_path = Path(request["request_source_path"])
    source_alias = tmp_path / "reviewed-source-alias"
    _create_directory_junction(source_alias, tmp_path)
    reviewed_request = json.loads(source_path.read_text(encoding="utf-8"))

    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="symbolic link|reparse",
        ):
            verifier.verify_prelock_qualification(
                source_alias / source_path.name,
                result_path,
                expected_request_hash=reviewed_request["request_hash"],
                **_qualification_result_kwargs(result_path),
                **_qualification_review_kwargs(request),
            )
    finally:
        os.rmdir(source_alias)


def test_qualification_verifier_guards_root_before_control_classification(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, _result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    qualification_root = Path(request["qualification_root"])
    qualification_target = tmp_path / "qualification-target"
    qualification_root.rename(qualification_target)
    _create_directory_junction(qualification_root, qualification_target)
    monkeypatch.setattr(
        verifier,
        "_qualification_irregular_path_reason",
        lambda _path: pytest.fail(
            "control path classified before qualification root guard"
        ),
    )

    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="symbolic link|reparse",
        ):
            _verify_qualification(verifier, request)
    finally:
        os.rmdir(qualification_root)


@pytest.mark.parametrize(
    "declared_path",
    ("request", "attempt", "completion"),
)
def test_qualification_verifier_binds_declared_paths_before_probe(
    tmp_path,
    monkeypatch,
    declared_path,
):
    verifier = _verifier()
    _request_path, _result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    outside_target = tmp_path / "outside-target"
    outside_target.mkdir()
    outside_alias = tmp_path / "outside-alias"
    _create_directory_junction(outside_alias, outside_target)
    outside_path = outside_alias / f"{declared_path}.json"
    original_review_loader = verifier._load_historical_qualification_review

    def load_review(*args, **kwargs):
        review = deepcopy(original_review_loader(*args, **kwargs))
        if declared_path == "request":
            review["request"]["request_path"] = str(outside_path)
        elif declared_path == "attempt":
            review["request"]["handshake"]["attempt_path"] = str(
                outside_path
            )
        else:
            review["request"]["completion_path"] = str(outside_path)
        return review

    original_entry_exists = verifier._qualification_path_entry_exists

    def reject_probe(path):
        if Path(path) == outside_path:
            pytest.fail("verifier probed a path before root binding")
        return original_entry_exists(path)

    monkeypatch.setattr(
        verifier,
        "_load_historical_qualification_review",
        load_review,
    )
    monkeypatch.setattr(
        verifier,
        "_qualification_path_entry_exists",
        reject_probe,
    )

    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="declared path binding",
        ):
            _verify_qualification(verifier, request)
    finally:
        os.rmdir(outside_alias)


def test_qualification_verifier_rejects_reviewed_registration_junction(
    tmp_path,
):
    verifier = _verifier()
    repo_target = tmp_path / "repo-target"
    repo_target.mkdir()
    repo_alias = tmp_path / "repo-alias"
    _create_directory_junction(repo_alias, repo_target)
    registration = {
        "artifact_root": str(tmp_path / "artifacts"),
        "integrity_rules": {"implementation_paths": []},
        "repo_root": str(repo_alias),
    }

    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="symbolic link|reparse",
        ):
            verifier._verify_qualification_registration_paths(
                registration,
                repo_root=repo_target,
            )
    finally:
        os.rmdir(repo_alias)


def test_qualification_marker_count_rejects_ancestor_junction(tmp_path):
    verifier = _verifier()
    marker_target = tmp_path / "marker-target"
    marker_target.mkdir()
    (marker_target / "ai_games.txt").write_text(
        "10\n11\n",
        encoding="utf-8",
        newline="",
    )
    marker_alias = tmp_path / "marker-alias"
    _create_directory_junction(marker_alias, marker_target)

    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="symbolic link|reparse",
        ):
            verifier._qualification_marker_count(
                marker_alias / "ai_games.txt"
            )
    finally:
        os.rmdir(marker_alias)


def test_qualification_verifier_rejects_unc_before_filesystem_probe(
    monkeypatch,
):
    verifier = _verifier()
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted a UNC probe"),
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="UNC|local drive",
    ):
        verifier._qualification_require_no_follow_path(
            r"\\qualification.invalid\share\result.json",
            "result",
            expected_kind="file",
        )


def test_qualification_verifier_rejects_ads_before_filesystem_probe(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    source_path = tmp_path / "result.json"
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted an ADS probe"),
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="alternate data stream",
    ):
        verifier._qualification_require_no_follow_path(
            f"{source_path}:qualification-result",
            "result",
            expected_kind="file",
            allow_missing=True,
        )


def test_qualification_verifier_rejects_ads_lexically(tmp_path):
    verifier = _verifier()
    output_path = tmp_path / "verification-audit.json"

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="alternate data stream",
    ):
        verifier._qualification_lexical_absolute_path(
            f"{output_path}:qualification-audit",
            "qualification audit output path",
        )


def test_qualification_verifier_git_uses_pinned_absolute_executable(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    (tmp_path / ".git").mkdir()
    observed = {}

    def run(command, **_kwargs):
        observed["command"] = list(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(verifier.subprocess, "run", run)

    assert verifier._qualification_git_text(tmp_path, "status") == "ok"
    executable = Path(observed["command"][0])
    assert executable.is_absolute()
    assert executable == verifier.QUALIFICATION_GIT_EXECUTABLE


def test_qualification_verifier_rejects_successful_git_warning(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="warning: graft file is deprecated\n",
        ),
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="graft file is deprecated",
    ):
        verifier._qualification_git_text(tmp_path, "status")


def test_qualification_verifier_git_uses_sterile_environment(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    (tmp_path / ".git").mkdir()
    observed = {}
    monkeypatch.setenv("GIT_DIR", r"C:\untrusted-git")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", r"C:\untrusted.gitconfig")

    def run(command, **kwargs):
        observed["command"] = list(command)
        observed["environment"] = dict(kwargs["env"])
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(verifier.subprocess, "run", run)

    assert verifier._qualification_git_text(tmp_path, "status") == "ok"
    assert "--no-replace-objects" in observed["command"]
    assert "--no-lazy-fetch" in observed["command"]
    assert "core.fsmonitor=false" in observed["command"]
    assert observed["environment"]["GIT_DIR"] == str(tmp_path / ".git")
    assert observed["environment"]["GIT_WORK_TREE"] == str(tmp_path)
    assert observed["environment"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert observed["environment"]["GIT_NO_LAZY_FETCH"] == "1"


def test_qualification_verifier_rejects_promisor_helper_before_lazy_fetch(
    tmp_path,
):
    verifier = _verifier()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tracked_path = repo_root / "tracked.py"
    tracked_path.write_text("VALUE = 'reviewed'\n", encoding="utf-8", newline="")
    _git(repo_root, "init", "--object-format=sha1")
    _git(repo_root, "config", "user.email", "verifier@example.invalid")
    _git(repo_root, "config", "user.name", "Verifier Fixture")
    _git(repo_root, "add", "tracked.py")
    _git(repo_root, "commit", "-m", "source")
    blob_oid = _git(repo_root, "rev-parse", "HEAD:tracked.py")
    object_path = repo_root / ".git" / "objects" / blob_oid[:2] / blob_oid[2:]
    assert object_path.is_file()
    os.chmod(object_path, 0o666)
    object_path.unlink()
    marker_path = tmp_path / "verifier-promisor-helper-executed.txt"
    helper_path = tmp_path / "verifier-promisor-helper.cmd"
    helper_path.write_text(
        f'@echo executed>"{marker_path}"\r\n@exit /b 1\r\n',
        encoding="utf-8",
        newline="",
    )
    for key, value in (
        ("extensions.partialClone", "origin"),
        ("remote.origin.promisor", "true"),
        ("remote.origin.partialCloneFilter", "blob:none"),
        ("protocol.ext.allow", "always"),
        ("remote.origin.url", f"ext::{helper_path}"),
    ):
        _git(repo_root, "config", key, value)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="unsafe.*directive",
    ):
        verifier._qualification_git_text(
            repo_root,
            "show",
            "HEAD:tracked.py",
        )

    assert not marker_path.exists()


def test_qualification_verifier_rejects_git_metadata_junction_before_run(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    metadata_target = tmp_path / "metadata-target"
    metadata_target.mkdir()
    metadata_path = repo_root / ".git"
    _create_directory_junction(metadata_path, metadata_target)
    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran before metadata validation"
        ),
    )

    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="symbolic link|reparse",
        ):
            verifier._qualification_git_text(repo_root, "status")
    finally:
        os.rmdir(metadata_path)


@pytest.mark.parametrize("config_name", ("config", "config.worktree"))
def test_qualification_verifier_rejects_spaced_external_config_before_run(
    tmp_path,
    monkeypatch,
    config_name,
):
    verifier = _verifier()
    config_path = tmp_path / ".git" / config_name
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[diff]\n\texternal    = untrusted-command\n",
        encoding="utf-8",
        newline="",
    )
    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran with unsafe repository config"
        ),
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="unsafe",
    ):
        verifier._qualification_git_text(tmp_path, "status")


@pytest.mark.parametrize(
    "config_text",
    (
        "[extensions]\n\tpartialClone = origin\n",
        '[remote "origin"]\n\tpromisor = true\n',
        '[protocol "ext"]\n\tallow = always\n',
    ),
)
def test_qualification_verifier_rejects_lazy_fetch_config_before_run(
    tmp_path,
    monkeypatch,
    config_text,
):
    verifier = _verifier()
    config_path = tmp_path / ".git" / "config"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config_text, encoding="utf-8", newline="")
    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran with lazy-fetch repository config"
        ),
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="unsafe",
    ):
        verifier._qualification_git_text(tmp_path, "status")


@pytest.mark.parametrize(
    "executable_path",
    (
        "ops/qualification-launch.ps1",
        "ops/qualification-launch.cmd",
        "ops/qualification-launch.pyz",
        "ops/qualification-launch.whl",
        "ops/qualification-launch.scr",
        "ops/qualification-launch",
    ),
)
def test_qualification_verifier_review_allowlist_rejects_all_executable_suffixes(
    executable_path,
):
    verifier = _verifier()
    request_source = "reports/qualification-request.json"

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="executable path",
    ):
        verifier._verify_qualification_review_allowed_paths(
            sorted((executable_path, request_source)),
            request_source_relative=request_source,
            protected_paths=set(),
            checks=verifier._Checks(),
        )


def test_qualification_inert_suffix_contract_matches_producer():
    verifier = _verifier()

    assert (
        verifier.QUALIFICATION_INERT_SUFFIXES
        == runner._QUALIFICATION_INERT_SUFFIXES
    )


def test_qualification_verifier_output_cannot_mutate_qualification_root(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    request_bytes = request_path.read_bytes()
    output_path = Path(request["qualification_root"]) / "verification-audit.json"

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="outside qualification root",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            audit_output_path=output_path,
        )

    assert request_path.read_bytes() == request_bytes
    assert not output_path.exists()


def test_qualification_verifier_output_is_exclusive(tmp_path, monkeypatch):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    output_path = (tmp_path / "audit-output" / "verification.json").resolve()
    output_path.parent.mkdir()

    audit = _verify_qualification(
        verifier,
        request,
        result_path,
        audit_output_path=output_path,
    )

    assert output_path.read_text(encoding="utf-8") == (
        verifier.render_verification_audit(audit)
    )
    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="already exists",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            audit_output_path=output_path,
        )


def test_qualification_verifier_output_rejects_forbidden_path(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    output_path = next(
        Path(path)
        for path in request["forbidden_paths"]
        if Path(path).name == "study"
    )
    assert output_path.parent.is_dir()
    assert not output_path.exists()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="request-bound or forbidden",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            audit_output_path=output_path,
        )

    assert not output_path.exists()


@pytest.mark.parametrize("suffix", [".", " "])
def test_qualification_verifier_output_rejects_final_win32_alias(
    tmp_path,
    monkeypatch,
    suffix,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    forbidden_path = next(
        Path(path)
        for path in request["forbidden_paths"]
        if Path(path).name == "study"
    )
    output_path = Path(f"{forbidden_path}{suffix}")
    assert not forbidden_path.exists()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="Win32 alias",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            audit_output_path=output_path,
        )

    assert not forbidden_path.exists()


def test_qualification_verifier_output_rejects_trailing_dot_root_alias(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    qualification_root = Path(request["qualification_root"])
    output_path = Path(str(qualification_root) + ".") / "alias-audit.json"

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="lexical absolute|Win32 alias|qualification root",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            audit_output_path=output_path,
        )

    assert not (qualification_root / "alias-audit.json").exists()


def test_qualification_verifier_output_rejects_canonical_parent_alias(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    qualification_root = Path(request["qualification_root"])
    alias_parent = (tmp_path / "canonical-alias").resolve()
    alias_parent.mkdir()
    output_path = alias_parent / "alias-audit.json"
    original_realpath = verifier.os.path.realpath

    def canonicalize(path):
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            str(alias_parent)
        ):
            return str(qualification_root)
        return original_realpath(path)

    monkeypatch.setattr(verifier.os.path, "realpath", canonicalize)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="qualification root",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            audit_output_path=output_path,
        )

    assert not output_path.exists()


def test_qualification_verifier_replays_passed_terminal_evidence(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    audit = _verify_qualification(verifier, request, result_path)

    assert audit["status"] == "verified"
    assert audit["qualification_status"] == "passed"
    assert audit["request_hash"] == request["request_hash"]
    assert audit["result_hash"] == result["result_hash"]
    assert audit["result_file_sha256"] == hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()
    assert audit["result_size"] == result_path.stat().st_size
    assert audit["review_binding"]["review_commit"] == QUALIFICATION_REVIEW_COMMIT
    assert audit["review_binding"]["request_source"]["path"] == (
        request["request_source_path"]
    )
    assert audit["study_start_authorized"] is False
    assert audit["collection_authorized"] is False
    assert audit["gameplay_policy_change_authorized"] is False
    assert audit["causal_claim_authorized"] is False
    assert audit["isolation_bound"] is True
    assert audit["launch_qualified"] is True
    assert audit["isolation_baseline_hash"] == request["isolation"][
        "baseline_hash"
    ]
    assert audit["isolation_post_observation_hash"] == result["isolation"][
        "post_observation_hash"
    ]
    assert audit["check_count"] > 0


def test_qualification_verifier_replays_v1_as_historical_unqualified_evidence(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    legacy_request, legacy_result = _downgrade_qualification_evidence_to_v1(
        verifier,
        request,
        result_path,
        monkeypatch,
    )

    audit = _verify_qualification(verifier, legacy_request, result_path)

    assert audit["status"] == "verified"
    assert audit["qualification_status"] == "passed"
    assert audit["result_hash"] == legacy_result["result_hash"]
    assert audit["isolation_bound"] is False
    assert audit["launch_qualified"] is False
    assert audit["isolation_baseline_hash"] is None
    assert audit["isolation_post_observation_hash"] is None


def test_qualification_verifier_rejects_v1_result_for_v2_request(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    mixed_result = json.loads(result_path.read_text(encoding="utf-8"))
    mixed_result.pop("isolation")
    mixed_result["schema_version"] = (
        runner.LEGACY_QUALIFICATION_RESULT_SCHEMA_VERSION
    )
    mixed_result["result_hash"] = _self_hash(mixed_result, "result_hash")
    _write_json(result_path, mixed_result)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="schema",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_verifier_rejects_v2_result_for_v1_request(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    legacy_request, legacy_result = _downgrade_qualification_evidence_to_v1(
        verifier,
        request,
        result_path,
        monkeypatch,
    )
    mixed_result = deepcopy(legacy_result)
    mixed_result["schema_version"] = runner.QUALIFICATION_RESULT_SCHEMA_VERSION
    mixed_result["isolation"] = result["isolation"]
    mixed_result["result_hash"] = _self_hash(mixed_result, "result_hash")
    _write_json(result_path, mixed_result)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="schema",
    ):
        _verify_qualification(verifier, legacy_request, result_path)


def test_qualification_verifier_collector_matches_runner_fixture_vector(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, _result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )

    assert verifier._qualification_collect_isolation(request) == (
        runner._qualification_observe_isolation(request["isolation"])
    )


@pytest.mark.parametrize(
    "resource",
    (
        "communication_mod",
        "marker",
        "runs",
        "checkpoints",
        "ai_debug_log",
        "communication_error_log",
    ),
)
def test_qualification_verifier_rejects_restored_resource_drift(
    tmp_path,
    monkeypatch,
    resource,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    baseline = request["isolation"]
    if resource == "communication_mod":
        Path(baseline["communication_mod"]["path"]).write_bytes(
            b"command=changed-agent\n"
        )
    elif resource == "marker":
        Path(baseline["marker"]["path"]).write_text(
            "10\n11\n12\n",
            encoding="utf-8",
            newline="",
        )
    elif resource == "runs":
        (Path(baseline["runs"]["root"]) / "IRONCLAD" / "100.run").write_bytes(
            b'{"drift":true}\n'
        )
    elif resource == "checkpoints":
        (
            Path(baseline["checkpoints"]["root"]) / "rl_model_ep1.pth"
        ).write_bytes(b"checkpoint-drift\n")
    elif resource == "ai_debug_log":
        Path(next(iter(baseline["global_logs"]))).write_bytes(b"debug drift\n")
    else:
        Path(list(baseline["global_logs"])[1]).write_bytes(
            b"communication drift\n"
        )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="isolation|restored|resource|marker",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_verifier_rejects_live_owned_child_pid(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    monkeypatch.setattr(
        verifier,
        "_qualification_pid_is_alive",
        lambda pid: pid == result["process"]["pid"],
        raising=False,
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="PID|pid|live|alive",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_pid_probe_distinguishes_current_and_missing_process():
    verifier = _verifier()

    assert verifier._qualification_pid_is_alive(os.getpid()) is True
    assert verifier._qualification_pid_is_alive(2_147_483_647) is False


def test_qualification_verifier_replays_failed_terminal_without_authority(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
        status="failed",
    )
    audit = _verify_qualification(verifier, request, result_path)

    assert audit["status"] == "verified"
    assert audit["qualification_status"] == "failed"
    assert audit["request_hash"] == request["request_hash"]
    assert audit["result_hash"] == result["result_hash"]
    assert audit["study_start_authorized"] is False
    assert audit["run_lock_authorized"] is False


def test_qualification_verifier_rejects_mismatched_terminal_file_anchor(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="file-SHA anchor mismatch",
    ):
        _verify_qualification(
            verifier,
            request,
            result_path,
            expected_result_file_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("partial_stage", "retained_handshake"),
    (
        ("request_only", ()),
        ("attempt_only", ("attempt",)),
        ("ready_without_release", ("attempt", "ready")),
        ("release_without_result", ("attempt", "ready", "release")),
    ),
)
def test_qualification_verifier_seals_valid_partial_prefix_without_authority(
    tmp_path,
    monkeypatch,
    partial_stage,
    retained_handshake,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    result_path.unlink()
    for name in ("attempt", "ready", "release"):
        if name not in retained_handshake:
            Path(request["handshake"][f"{name}_path"]).unlink()

    audit = _verify_qualification(verifier, request)

    assert request_path.is_file()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()
    assert audit["status"] == "sealed_partial"
    assert audit["qualification_status"] == "partial"
    assert audit["partial_stage"] == partial_stage
    assert audit["request_hash"] == request["request_hash"]
    assert audit["result_hash"] is None
    assert audit["review_binding"]["review_commit"] == QUALIFICATION_REVIEW_COMMIT
    assert audit["passed"] is True
    assert audit["study_start_authorized"] is False
    assert audit["run_lock_authorized"] is False
    assert audit["training_authorized"] is False


@pytest.mark.parametrize(
    ("case", "expected_status", "consumed", "partial_stage"),
    (
        ("prepared", "reviewed_prepared", False, "source_only"),
        ("orphan_attempt", "sealed_invalid", True, "orphan_control_artifacts"),
        ("malformed_active", "sealed_invalid", True, "malformed_active_request"),
        ("active_directory", "sealed_invalid", True, "malformed_active_request"),
    ),
)
def test_qualification_verifier_seals_prepared_or_invalid_consumption_state(
    tmp_path,
    monkeypatch,
    case,
    expected_status,
    consumed,
    partial_stage,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    result_path.unlink()
    for name in ("ready", "release"):
        Path(request["handshake"][f"{name}_path"]).unlink()
    if case != "orphan_attempt":
        Path(request["handshake"]["attempt_path"]).unlink()
    if case in {"prepared", "orphan_attempt"}:
        request_path.unlink()
    elif case == "active_directory":
        request_path.unlink()
        request_path.mkdir()
    else:
        request_path.write_text(
            "{\"malformed\":true}\n",
            encoding="utf-8",
            newline="",
        )

    audit = _verify_qualification(verifier, request)

    assert audit["status"] == expected_status
    assert audit["consumed"] is consumed
    assert audit["partial_stage"] == partial_stage
    assert audit["qualification_status"] == (
        "not_attempted" if case == "prepared" else "invalid_partial"
    )
    assert audit["evidence_valid"] is (case == "prepared")
    assert audit["isolation_bound"] is False
    assert audit["launch_qualified"] is False
    assert audit["isolation_baseline_hash"] is None
    assert audit["isolation_post_observation_hash"] is None
    assert audit["study_start_authorized"] is False
    assert audit["run_lock_authorized"] is False


def test_qualification_verifier_seals_dangling_control_symlink_as_consumed(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    result_path.unlink()
    request_path.unlink()
    for name in ("attempt", "ready", "release"):
        Path(request["handshake"][f"{name}_path"]).unlink()
    dangling_path = Path(request["handshake"]["attempt_path"])
    original_exists = verifier._qualification_path_entry_exists
    original_is_regular = verifier._qualification_path_is_regular_file
    classification_seen = {"value": False}

    def entry_exists(path):
        if path == dangling_path:
            return True
        return original_exists(path)

    def classify_regular_file(path):
        if path == dangling_path:
            classification_seen["value"] = True
            return False
        return original_is_regular(path)

    original_inventory = verifier._qualification_audit_inventory

    def inventory_after_classification(value):
        assert classification_seen["value"] is True
        return original_inventory(value)

    monkeypatch.setattr(
        verifier,
        "_qualification_path_entry_exists",
        entry_exists,
    )
    monkeypatch.setattr(
        verifier,
        "_qualification_path_is_regular_file",
        classify_regular_file,
    )
    monkeypatch.setattr(
        verifier,
        "_qualification_audit_inventory",
        inventory_after_classification,
    )

    audit = _verify_qualification(verifier, request)

    assert audit["status"] == "sealed_invalid"
    assert audit["qualification_status"] == "invalid_partial"
    assert audit["partial_stage"] == "invalid_control_path"
    assert audit["consumed"] is True
    assert audit["evidence_valid"] is False
    assert audit["isolation_bound"] is False
    assert audit["launch_qualified"] is False
    assert "regular file" in audit["evidence_error"]


def test_qualification_verifier_seals_real_dangling_control_junction(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    result_path.unlink()
    request_path.unlink()
    for name in ("attempt", "ready", "release"):
        Path(request["handshake"][f"{name}_path"]).unlink()
    target_path = tmp_path / "junction-target"
    target_path.mkdir()
    junction_path = Path(request["handshake"]["attempt_path"])
    _create_directory_junction(junction_path, target_path)
    target_path.rmdir()
    try:
        audit = _verify_qualification(verifier, request)
    finally:
        os.rmdir(junction_path)

    assert audit["status"] == "sealed_invalid"
    assert audit["qualification_status"] == "invalid_partial"
    assert audit["partial_stage"] == "invalid_control_path"
    assert audit["consumed"] is True
    assert audit["evidence_valid"] is False
    assert "reparse" in audit["evidence_error"]


def test_qualification_verifier_rejects_control_directory_in_terminal_replay(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch, status="failed")
    )
    ready_path = Path(request["handshake"]["ready_path"])
    assert not ready_path.exists()
    ready_path.mkdir()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="control path.*regular|regular.*control path",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_verifier_rejects_dangling_forbidden_junction(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, _result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    qualification_root = Path(request["qualification_root"])
    forbidden_path = next(
        Path(path)
        for path in request["forbidden_paths"]
        if (
            not Path(path).is_relative_to(qualification_root)
            and Path(path).parent.exists()
        )
    )
    target_path = tmp_path / "dangling-forbidden-target"
    target_path.mkdir()
    _create_directory_junction(forbidden_path, target_path)
    target_path.rmdir()
    try:
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match="forbidden",
        ):
            _verify_qualification(verifier, request, result_path)
    finally:
        os.rmdir(forbidden_path)


def test_qualification_verifier_rejects_terminal_without_active_request(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    request_path.unlink()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="active qualification request is missing",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_verifier_requires_prepared_source_preflight(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    result_path.unlink()
    request_path.unlink()
    for name in ("attempt", "ready", "release"):
        Path(request["handshake"][f"{name}_path"]).unlink()
    Path(request["config"]["path"]).write_text(
        "{}\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="configuration|config",
    ):
        _verify_qualification(verifier, request)


@pytest.mark.parametrize("case", ("terminal_exists", "ready_gap", "attempt_tamper"))
def test_qualification_verifier_rejects_invalid_partial_prefix(
    tmp_path,
    monkeypatch,
    case,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    if case != "terminal_exists":
        result_path.unlink()
    if case == "ready_gap":
        Path(request["handshake"]["attempt_path"]).unlink()
        Path(request["handshake"]["release_path"]).unlink()
    elif case == "attempt_tamper":
        attempt_path = Path(request["handshake"]["attempt_path"])
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        attempt["marker_start_count"] += 1
        attempt["attempt_hash"] = _self_hash(attempt, "attempt_hash")
        _write_json(attempt_path, attempt)
        Path(request["handshake"]["ready_path"]).unlink()
        Path(request["handshake"]["release_path"]).unlink()

    audit = _verify_qualification(verifier, request)

    assert audit["status"] == "sealed_invalid"
    assert audit["qualification_status"] == "invalid_partial"
    assert audit["consumed"] is True
    assert audit["evidence_valid"] is False
    assert audit["evidence_error"]
    assert audit["study_start_authorized"] is False


def test_qualification_verifier_rejects_failed_terminal_relabelled_passed(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
        status="failed",
    )
    completion_path = result_path.with_name("qualification-completion.json")
    result["status"] = "passed"
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(completion_path, result)
    result_path.unlink()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="release|passed result",
    ):
        _verify_qualification(verifier, request, completion_path)


def test_qualification_verifier_rejects_passed_terminal_relabelled_failed(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, completion_path, request, result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    failure_path = Path(request["failure_path"])
    result["status"] = "failed"
    result["failure"] = {
        "exception_type": "RuntimeError",
        "message": "invented failure",
        "stage": "wait_for_qualification_exit",
    }
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(failure_path, result)
    completion_path.unlink()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="failed result does not contradict success evidence",
    ):
        _verify_qualification(verifier, request, failure_path)


def test_qualification_verifier_rejects_relabel_with_forged_launch_count(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, completion_path, request, result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    failure_path = Path(request["failure_path"])
    result["status"] = "failed"
    result["failure"] = {
        "exception_type": "RuntimeError",
        "message": "invented failure",
        "stage": "wait_for_qualification_exit",
    }
    result["process"]["launch_count"] = 0
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(failure_path, result)
    completion_path.unlink()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="launch|process",
    ):
        _verify_qualification(verifier, request, failure_path)


def test_qualification_verifier_rejects_launch_without_attempt_evidence(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, result_path, request, result = (
        _build_qualification_evidence(tmp_path, monkeypatch, status="failed")
    )
    attempt_path = Path(request["handshake"]["attempt_path"])
    attempt_path.unlink()
    result["handshake"]["attempt"]["sha256"] = None
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(result_path, result)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="attempt|launch",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_verifier_rejects_unproven_post_exit_validation_failure(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    _request_path, completion_path, request, result = (
        _build_qualification_evidence(tmp_path, monkeypatch)
    )
    failure_path = Path(request["failure_path"])
    result["status"] = "failed"
    result["failure"] = {
        "exception_type": "OutcomeEvidenceRunnerError",
        "message": "qualification config changed",
        "stage": "post_exit_validation",
    }
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(failure_path, result)
    completion_path.unlink()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="failed result does not contradict success evidence",
    ):
        _verify_qualification(verifier, request, failure_path)


def test_qualification_verifier_rejects_dual_terminal_branches(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    Path(request["failure_path"]).write_text(
        "{\"external\":true}\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="terminal branches are not exclusive",
    ):
        _verify_qualification(verifier, request, result_path)


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("implementation", "active request differs"),
        ("pid", "PID"),
        ("launch_count", "launch count|passed result"),
        ("marker", "marker"),
        ("marker_path", "active request differs"),
        ("attempt", "attempt"),
        ("authority_zero", "authority"),
        ("forbidden_zero", "forbidden"),
        ("ready_boolean_alias", "ready"),
        ("timestamp_order", "active request differs"),
        ("cleanup_type", "cleanup flag"),
        ("noncanonical_result", "canonical"),
    ),
)
def test_qualification_verifier_rejects_cross_artifact_laundering(
    tmp_path,
    monkeypatch,
    case,
    message,
):
    verifier = _verifier()
    request_path, result_path, request, result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    if case == "implementation":
        request["implementation_sha256"]["main.py"] = "f" * 64
        request["request_hash"] = _self_hash(request, "request_hash")
        _write_json(request_path, request)
        result["implementation_sha256"]["main.py"] = "f" * 64
        result["request"]["hash"] = request["request_hash"]
    elif case == "pid":
        result["process"]["pid"] += 1
    elif case == "launch_count":
        result["process"]["launch_count"] = 0
    elif case == "marker":
        result["marker"]["end_count"] += 1
    elif case == "marker_path":
        decoy_marker = (tmp_path / "decoy" / "ai_games.txt").resolve()
        decoy_marker.parent.mkdir()
        decoy_marker.write_text("10\n11\n", encoding="utf-8", newline="")
        request["marker"]["path"] = str(decoy_marker)
        request["request_hash"] = _self_hash(request, "request_hash")
        _write_json(request_path, request)
        result["marker"]["path"] = str(decoy_marker)
        result["request"]["hash"] = request["request_hash"]
    elif case == "attempt":
        attempt_path = Path(request["handshake"]["attempt_path"])
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        attempt["config_sha256"] = "f" * 64
        attempt["attempt_hash"] = _self_hash(attempt, "attempt_hash")
        _write_json(attempt_path, attempt)
        result["handshake"]["attempt"]["sha256"] = hashlib.sha256(
            attempt_path.read_bytes()
        ).hexdigest()
    elif case == "authority_zero":
        result["authority"]["study_start"] = 0
    elif case == "forbidden_zero":
        forbidden_path = next(iter(result["forbidden_paths"]))
        result["forbidden_paths"][forbidden_path] = 0
    elif case == "ready_boolean_alias":
        ready_path = Path(request["handshake"]["ready_path"])
        ready = json.loads(ready_path.read_text(encoding="utf-8"))
        ready["communication_state_received"] = 1
        _write_json(ready_path, ready)
        result["handshake"]["ready"]["sha256"] = hashlib.sha256(
            ready_path.read_bytes()
        ).hexdigest()
    elif case == "timestamp_order":
        request["created_unix_ns"] = result["ended_unix_ns"] + 1
        request["request_hash"] = _self_hash(request, "request_hash")
        _write_json(request_path, request)
        result["request"]["hash"] = request["request_hash"]
    elif case == "cleanup_type":
        result["process"]["cleanup_attempted"] = "false"
    else:
        result["result_hash"] = _self_hash(result, "result_hash")
        result_path.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
            newline="",
        )
        with pytest.raises(
            verifier.OutcomeEvidenceVerificationError,
            match=message,
        ):
            _verify_qualification(verifier, request, result_path)
        return
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(result_path, result)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match=message,
    ):
        _verify_qualification(verifier, request, result_path)


@pytest.mark.parametrize("case", ("authority", "release_hash"))
def test_qualification_verifier_rejects_rehashed_semantic_tamper(
    tmp_path,
    monkeypatch,
    case,
):
    verifier = _verifier()
    request_path, result_path, request, _result = _build_qualification_evidence(
        tmp_path,
        monkeypatch,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if case == "authority":
        result["authority"]["study_start"] = True
    else:
        result["handshake"]["release"]["sha256"] = "f" * 64
    result["result_hash"] = _self_hash(result, "result_hash")
    _write_json(result_path, result)

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="authority|release",
    ):
        _verify_qualification(verifier, request, result_path)


def test_qualification_verifier_cli_selects_request_and_result(
    tmp_path,
    monkeypatch,
    capsys,
):
    verifier = _verifier()
    request_path = tmp_path / "qualification-request.json"
    result_path = tmp_path / "qualification-completion.json"
    audit = {
        "passed": True,
        "schema_version": "qualification-audit-sentinel",
        "status": "verified",
    }
    def verify(observed_request, observed_result, **kwargs):
        assert observed_request == request_path
        assert observed_result == result_path
        assert kwargs == {
            "expected_request_file_sha256": "b" * 64,
            "expected_request_hash": "a" * 64,
            "expected_request_size": 123,
            "expected_review_commit": QUALIFICATION_REVIEW_COMMIT,
            "expected_result_file_sha256": "e" * 64,
            "expected_result_hash": "f" * 64,
            "expected_result_size": 456,
        }
        return audit

    monkeypatch.setattr(verifier, "verify_prelock_qualification", verify)

    exit_code = verifier.main(
        [
            "--qualification-request-source",
            str(request_path),
            "--qualification-result",
            str(result_path),
            "--qualification-request-hash",
            "a" * 64,
            "--qualification-request-file-sha256",
            "b" * 64,
            "--qualification-request-size",
            "123",
            "--qualification-review-commit",
            QUALIFICATION_REVIEW_COMMIT,
            "--qualification-result-hash",
            "f" * 64,
            "--qualification-result-file-sha256",
            "e" * 64,
            "--qualification-result-size",
            "456",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == audit
    assert captured.err == ""


def test_qualification_verifier_cli_selects_request_only_partial_replay(
    tmp_path,
    monkeypatch,
    capsys,
):
    verifier = _verifier()
    request_path = tmp_path / "qualification-request.json"
    audit = {
        "passed": True,
        "schema_version": "qualification-audit-sentinel",
        "status": "sealed_partial",
    }
    def verify(observed_request, observed_result=None, **kwargs):
        assert observed_request == request_path
        assert observed_result is None
        assert kwargs == {
            "expected_request_file_sha256": "b" * 64,
            "expected_request_hash": "a" * 64,
            "expected_request_size": 123,
            "expected_review_commit": QUALIFICATION_REVIEW_COMMIT,
            "expected_result_file_sha256": None,
            "expected_result_hash": None,
            "expected_result_size": None,
        }
        return audit

    monkeypatch.setattr(verifier, "verify_prelock_qualification", verify)

    exit_code = verifier.main(
        [
            "--qualification-request-source",
            str(request_path),
            "--qualification-request-hash",
            "a" * 64,
            "--qualification-request-file-sha256",
            "b" * 64,
            "--qualification-request-size",
            "123",
            "--qualification-review-commit",
            QUALIFICATION_REVIEW_COMMIT,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == audit
    assert captured.err == ""


def test_qualification_verifier_cli_rejects_abbreviated_request_option(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    monkeypatch.setattr(
        verifier,
        "verify_prelock_qualification",
        lambda *_args, **_kwargs: pytest.fail(
            "abbreviated option entered qualification replay"
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        verifier.main(
            [
                "--qualification-request-so",
                str(tmp_path / "request.json"),
                "--qualification-request-hash",
                "a" * 64,
                "--qualification-request-file-sha256",
                "b" * 64,
                "--qualification-request-size",
                "123",
                "--qualification-review-commit",
                QUALIFICATION_REVIEW_COMMIT,
            ]
        )

    assert exc_info.value.code == 2


def _build_historical_qualification_review_fixture(
    tmp_path,
    monkeypatch,
    *,
    review_case="clean",
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_registered_sources(repo_root)
    communication_path = (tmp_path / "config.properties").resolve()
    communication_path.write_text(
        "command=python main.py\nclientTimeout=30\n",
        encoding="iso-8859-1",
    )
    checkpoint_root = (tmp_path / "game" / "checkpoints").resolve()
    checkpoint_root.mkdir(parents=True)
    marker_path = checkpoint_root.parent / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8", newline="")
    registration = expansion.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=repo_root,
        seed_base=SEED_BASE,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=communication_path,
        checkpoint_root=checkpoint_root,
    )
    registration_path = (repo_root / "reports" / "registration.json").resolve()
    registration_path.parent.mkdir()
    registration_path.write_text(
        expansion.render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    monkeypatch.setattr(runner, "REPO_ROOT", repo_root.resolve())
    _git(repo_root, "init", "--object-format=sha1")
    _git(repo_root, "config", "core.autocrlf", "false")
    _git(repo_root, "config", "user.email", "verifier@example.invalid")
    _git(repo_root, "config", "user.name", "Verifier Fixture")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "implementation snapshot")
    source_commit = _git(repo_root, "rev-parse", "HEAD")

    qualification_root = (tmp_path / "qualification-r4").resolve()
    qualification_root.mkdir()
    qualification_id = f"{STUDY_ID}-qualification-r4"
    config_path = qualification_root / "qualification-config.json"
    _write_json(
        config_path,
        {
            "category_rates_bps": {"card_reward": 300, "shop": 1000},
            "enabled_categories": ["card_reward", "shop"],
            "manifest_path": str(
                (qualification_root / "qualification-manifest.json").resolve()
            ),
            "per_run_alternative_budget": 2,
            "schema_version": "noncombat-exploration-config-v1",
            "seed": SEED_BASE + 1,
            "session_id": f"{qualification_id}-s01",
            "source_commit": source_commit,
            "study_id": qualification_id,
            "study_registration_hash": registration.registration_hash,
            "study_run_lock_hash": "0" * 64,
            "study_slot_number": 1,
            "trace_path": str(
                (qualification_root / "qualification-trace.jsonl").resolve()
            ),
        },
    )
    request_source_path = (
        repo_root / "reports" / "reviewed-qualification-request.json"
    ).resolve()
    request = runner.build_qualification_request(
        registration_path=registration_path,
        qualification_id=qualification_id,
        qualification_root=qualification_root,
        config_path=config_path,
        marker_path=marker_path,
        request_source_path=request_source_path,
        created_unix_ns=100,
    )
    assert request["source_commit"] == source_commit
    if review_case == "non_direct":
        (repo_root / "review-note.txt").write_text(
            "intermediate review note\n",
            encoding="utf-8",
            newline="",
        )
        _git(repo_root, "add", ".")
        _git(repo_root, "commit", "-m", "intermediate review commit")
    _write_json(request_source_path, request)
    if review_case == "extra_diff":
        (repo_root / "review-note.txt").write_text(
            "unregistered review note\n",
            encoding="utf-8",
            newline="",
        )
    elif review_case == "implementation_drift":
        (repo_root / "main.py").write_text(
            "# implementation drift during review\n",
            encoding="utf-8",
            newline="",
        )
    elif review_case not in {"clean", "non_direct"}:
        raise AssertionError(f"unsupported review case: {review_case}")
    request_bytes = request_source_path.read_bytes()
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "review qualification request")
    review_commit = _git(repo_root, "rev-parse", "HEAD")
    return {
        "repo_root": repo_root,
        "request": request,
        "request_bytes": request_bytes,
        "request_source_path": request_source_path,
        "review_commit": review_commit,
        "source_commit": source_commit,
    }


def _load_historical_review(verifier, fixture, **overrides):
    kwargs = {
        "expected_review_commit": fixture["review_commit"],
        "expected_request_hash": fixture["request"]["request_hash"],
        "expected_request_file_sha256": hashlib.sha256(
            fixture["request_bytes"]
        ).hexdigest(),
        "expected_request_size": len(fixture["request_bytes"]),
    }
    kwargs.update(overrides)
    return verifier._load_historical_qualification_review(
        fixture["request_source_path"],
        checks=verifier._Checks(),
        **kwargs,
    )


def test_qualification_verifier_replays_historical_two_commit_review_chain(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    fixture = _build_historical_qualification_review_fixture(
        tmp_path,
        monkeypatch,
    )
    repo_root = fixture["repo_root"]
    request = fixture["request"]
    request_source_path = fixture["request_source_path"]
    review_commit = fixture["review_commit"]
    source_commit = fixture["source_commit"]

    review = _load_historical_review(verifier, fixture)
    assert review["request"] == request
    assert review["review_binding"]["source_commit"] == source_commit
    assert review["review_binding"]["review_commit"] == review_commit

    (repo_root / "main.py").write_text(
        "# later implementation drift\n",
        encoding="utf-8",
        newline="",
    )
    request_source_path.write_text(
        "{\"later\":\"request drift\"}\n",
        encoding="utf-8",
        newline="",
    )
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "advance current head")
    assert _git(repo_root, "rev-parse", "HEAD") != review_commit

    replayed = _load_historical_review(verifier, fixture)
    assert replayed == review


def test_qualification_verifier_replays_when_current_request_parent_is_removed(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    fixture = _build_historical_qualification_review_fixture(
        tmp_path,
        monkeypatch,
    )

    shutil.rmtree(fixture["request_source_path"].parent)

    review = _load_historical_review(verifier, fixture)
    assert review["request"] == fixture["request"]
    assert (
        review["review_binding"]["review_commit"]
        == fixture["review_commit"]
    )


@pytest.mark.parametrize(
    ("override", "message"),
    (
        ({"expected_request_hash": "f" * 64}, "source anchor mismatch"),
        (
            {"expected_request_file_sha256": "f" * 64},
            "source file binding mismatch",
        ),
        ({"expected_request_size": 1}, "source file binding mismatch"),
    ),
)
def test_qualification_verifier_rejects_wrong_external_review_anchors(
    tmp_path,
    monkeypatch,
    override,
    message,
):
    verifier = _verifier()
    fixture = _build_historical_qualification_review_fixture(
        tmp_path,
        monkeypatch,
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match=message,
    ):
        _load_historical_review(verifier, fixture, **override)


@pytest.mark.parametrize(
    ("review_case", "message"),
    (
        ("non_direct", "not a direct child"),
        ("extra_diff", "allowed path set"),
        ("implementation_drift", "implementation changed"),
    ),
)
def test_qualification_verifier_rejects_invalid_historical_review_chain(
    tmp_path,
    monkeypatch,
    review_case,
    message,
):
    verifier = _verifier()
    fixture = _build_historical_qualification_review_fixture(
        tmp_path,
        monkeypatch,
        review_case=review_case,
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match=message,
    ):
        _load_historical_review(verifier, fixture)


def test_verifier_requires_independent_120_second_handshake_contract(tmp_path):
    verifier = _verifier()
    registration = expansion.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "repo",
        seed_base=SEED_BASE,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
    )
    record = registration.to_record()

    verifier._verify_registration(record, verifier._Checks())
    expected = verifier._expected_registration(record)
    assert expected["integrity_rules"]["communication_handshake"][
        "readiness_timeout_seconds"
    ] == 120

    historical = deepcopy(record)
    historical["integrity_rules"]["communication_handshake"][
        "readiness_timeout_seconds"
    ] = 30
    historical["registration_hash"] = _self_hash(
        historical,
        "registration_hash",
    )
    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="registered study contract mismatch",
    ):
        verifier._verify_registration(historical, verifier._Checks())


def _build_study(
    tmp_path,
    monkeypatch,
    *,
    history_exclusion_reason=None,
    launder_confirmed=False,
    launder_unattributed=False,
    omit_joinable_run=False,
):
    repo_root = tmp_path / "repo"
    artifact_root = tmp_path / "study"
    game_root = tmp_path / "game"
    checkpoint_root = game_root / "checkpoints"
    runs_root = game_root / "runs" / "IRONCLAD"
    communication_path = tmp_path / "config.properties"
    checkpoint_root.mkdir(parents=True)
    runs_root.mkdir(parents=True)
    communication_path.write_text(
        "command=python main.py\nclientTimeout=30\n",
        encoding="iso-8859-1",
    )
    (checkpoint_root / "rl_combat_model_ep1.pth").write_bytes(b"checkpoint-v1")
    _copy_registered_sources(repo_root)
    calibration_source = (
        REPO_ROOT / "reports" / "noncombat_ope_estimator_calibration_20260714.json"
    )
    calibration_target = (
        repo_root / "reports" / "noncombat_ope_estimator_calibration_20260714.json"
    )
    calibration_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(calibration_source, calibration_target)

    registration = expansion.build_registration(
        study_id=STUDY_ID,
        artifact_root=artifact_root,
        repo_root=repo_root,
        seed_base=SEED_BASE,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=communication_path,
        checkpoint_root=checkpoint_root,
    )
    registration_path = repo_root / "reports" / "registration.json"
    registration_path.write_text(
        expansion.render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    _git(repo_root, "init", "--object-format=sha1")
    _git(repo_root, "config", "core.autocrlf", "false")
    _git(repo_root, "config", "user.email", "verifier-fixture@example.invalid")
    _git(repo_root, "config", "user.name", "Verifier Fixture")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "build verifier fixture")
    source_commit = _git(repo_root, "rev-parse", "HEAD")
    command_record = registration.to_record()["command"]
    child_command = [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    run_lock_path = artifact_root / "run-lock.json"
    run_lock = expansion.create_run_lock(
        registration_path=registration_path,
        lock_path=run_lock_path,
        repo_root=repo_root,
        child_command=child_command,
        created_unix_ns=1_750_000_000_000_000_000,
    )

    ledger_path = artifact_root / "study-ledger.jsonl"
    ledger = runner.StudyLedger(
        path=ledger_path,
        registration=registration,
        run_lock_hash=run_lock["run_lock_hash"],
    )
    ledger.initialize(created_unix_ns=1)
    sessions = []
    run_counter = 1_780_000_090
    victory_count = 0
    isolation = _pre_session_isolation(run_lock)
    marker_timestamps = []
    for slot in registration.slots:
        marker_start = (slot.slot_number - 1) * 25
        launch = runner.build_slot_launch(
            registration,
            run_lock,
            slot.slot_number,
        )
        Path(slot.config_path).write_text(
            runner.render_slot_config(launch),
            encoding="utf-8",
            newline="",
        )
        handshake_paths, attempt, ready = _publish_preclaim_handshake(
            registration,
            run_lock,
            slot,
            launch,
            marker_start,
        )
        ledger.start_slot(
            slot.slot_number,
            slot.session_id,
            marker_start_count=marker_start,
            started_unix_ns=slot.slot_number * 2,
        )
        release = build_release_record(
            attempt,
            ready,
            created_unix_ns=slot.slot_number * 10 + 3,
        )
        publish_record_once(handshake_paths.release, release)
        ledger.finish_slot(
            slot.slot_number,
            process_exit_code=0,
            complete_trajectories=25,
            marker_start_count=marker_start,
            marker_end_count=slot.slot_number * 25,
            ended_unix_ns=slot.slot_number * 2 + 1,
        )
        config = parse_exploration_config(
            launch.config_record,
            config_path=Path(slot.config_path),
        )
        manifest = create_exploration_session_manifest(
            config,
            source_clean=True,
            python_executable=registration.python_executable,
            command=list(launch.command),
            isolation_hashes=isolation,
        )

        samples = []
        trace_rows = []
        joined_run_files = []
        for category in ("card_reward", "shop"):
            for arm in ("baseline", "alternative"):
                victory = arm == "baseline" and victory_count < 3
                while True:
                    run_counter += 1
                    sample = _sample(
                        session_id=slot.session_id,
                        run_id=str(run_counter),
                        category=category,
                        arm=arm,
                        source_commit=source_commit,
                        victory=victory,
                    )
                    proposed, resolved = _trace_rows(
                        sample,
                        seed=slot.seed,
                    )
                    if proposed["selection"]["selected_action_id"] == sample[
                        "selected_action_id"
                    ]:
                        break
                if victory:
                    victory_count += 1
                selection = proposed["selection"]
                sample["exploration"].update(
                    {
                        "config_file_sha256": manifest[
                            "config_file_sha256"
                        ],
                        "confirmation_reason": resolved["reason"],
                        "effective_config_hash": manifest[
                            "effective_config_hash"
                        ],
                        "draw_bucket": selection["draw_bucket"],
                        "draw_counter": selection["draw_counter"],
                        "draw_input_hash": selection["draw_input_hash"],
                        "draw_u64": selection["draw_u64"],
                        "manifest_hash": manifest["manifest_hash"],
                        "proposal_record_hash": hashlib.sha256(
                            _canonical_json(proposed).encode("utf-8")
                        ).hexdigest(),
                        "proposed_unix": proposed["proposed_unix"],
                        "resolution_record_hash": hashlib.sha256(
                            _canonical_json(resolved).encode("utf-8")
                        ).hexdigest(),
                        "resolved_unix": resolved["resolved_unix"],
                        "trajectory_started_unix": proposed[
                            "trajectory_started_unix"
                        ],
                    }
                )
                samples.append(sample)
                trace_rows.extend((proposed, resolved))
                joined_run_files.append(sample["outcome"]["run_file"])
                _write_json(
                    runs_root / sample["outcome"]["run_file"],
                    {
                        "floor_reached": sample["outcome"]["floor_reached"],
                        "killed_by": sample["outcome"]["killed_by"],
                        "playtime": sample["outcome"]["playtime"],
                        "victory": sample["outcome"]["victory"],
                    },
                )
                run_counter += 1_000
        slot_run_markers = [
            int(Path(run_file).stem) for run_file in joined_run_files
        ]
        last_run_marker = slot_run_markers[-1]
        marker_timestamps.extend(slot_run_markers)
        marker_timestamps.extend(
            last_run_marker + 20 * index
            for index in range(1, 25 - len(slot_run_markers) + 1)
        )
        exported_samples = samples
        export_exclusions = ()
        registered_joined_run_files = joined_run_files
        confirmed_count = len(samples)
        replay_valid_count = len(samples)
        if launder_confirmed and slot.slot_number == 1:
            laundered = samples[-1]
            exported_samples = samples[:-1]
            export_exclusions = (
                {
                    "category": laundered["category"],
                    "decision_id": laundered["sample_id"],
                    "reason": "selected_candidate_illegal",
                },
            )
        elif history_exclusion_reason is not None and slot.slot_number == 1:
            laundered = samples[-1]
            proposal = next(
                row
                for row in trace_rows
                if row["record_type"] == "proposed"
                and row["decision_id"] == laundered["sample_id"]
            )
            proposal["alternative_attempt_budget"]["used_before"] = 1
            exported_samples = samples[:-1]
            export_exclusions = (
                {
                    "category": laundered["category"],
                    "decision_id": laundered["sample_id"],
                    "reason": history_exclusion_reason,
                },
            )
            confirmed_count = len(exported_samples)
            replay_valid_count = len(exported_samples)
        elif launder_unattributed and slot.slot_number == 1:
            laundered = samples[-1]
            laundered["trajectory_group_id"] = None
            laundered["outcome"] = {
                "included_in_gate": False,
                "join_status": "missing",
            }
        elif omit_joinable_run and slot.slot_number == 1:
            laundered = samples[-1]
            laundered["trajectory_group_id"] = None
            laundered["outcome"] = {
                "included_in_gate": False,
                "join_status": "missing",
            }
            registered_joined_run_files = joined_run_files[:-1]
        _write_jsonl(slot.trace_path, trace_rows)
        sessions.append(
            expansion.RegisteredSessionEvidence(
                slot_number=slot.slot_number,
                session_id=slot.session_id,
                run_lock_hash=run_lock["run_lock_hash"],
                config_sha256=hashlib.sha256(
                    Path(slot.config_path).read_bytes()
                ).hexdigest(),
                manifest_sha256=hashlib.sha256(
                    Path(slot.manifest_path).read_bytes()
                ).hexdigest(),
                manifest_hash=manifest["manifest_hash"],
                trace_sha256=hashlib.sha256(
                    Path(slot.trace_path).read_bytes()
                ).hexdigest(),
                marker_trajectory_count=25,
                joined_run_files=tuple(registered_joined_run_files),
                samples=tuple(exported_samples),
                exclusions=export_exclusions,
                validation_summary={
                    "candidate_legal": len(exported_samples),
                    "confirmed": confirmed_count,
                    "exported": len(exported_samples),
                    "replay_valid": replay_valid_count,
                },
                provenance_verified=True,
                isolation_verified=True,
            )
        )

    marker_path = runs_root.parent / "ai_games.txt"
    marker_path.write_text(
        "".join(f"{timestamp}\n" for timestamp in marker_timestamps),
        encoding="utf-8",
        newline="",
    )
    ledger_snapshot = ledger.snapshot()
    pool = expansion.build_registered_pool(
        registration,
        run_lock_hash=run_lock["run_lock_hash"],
        ledger_snapshot=ledger_snapshot,
        sessions=tuple(sessions),
    )
    finalization = expansion.finalize_registered_outcome_evidence(
        registration,
        run_lock_hash=run_lock["run_lock_hash"],
        ledger_snapshot=ledger_snapshot,
        pool=pool,
    )
    paths = {name: Path(path) for name, path in finalization["paths"].items()}
    return {
        "artifact_root": artifact_root,
        "closeout_path": paths["closeout_json"],
        "estimate_path": paths["estimate_json"],
        "ledger_path": ledger_path,
        "marker_path": marker_path,
        "pool_manifest_path": paths["pool_manifest"],
        "pool_samples_path": paths["pool_samples"],
        "readiness_path": paths["readiness_json"],
        "registration": registration,
        "registration_path": registration_path,
        "repo_root": repo_root,
        "run_lock_path": run_lock_path,
        "runs_root": runs_root,
        "target_path": paths["target_manifest"],
    }


def _build_blocked_study(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    artifact_root = tmp_path / "study"
    checkpoint_root = tmp_path / "game" / "checkpoints"
    communication_path = tmp_path / "config.properties"
    checkpoint_root.mkdir(parents=True)
    communication_path.write_text(
        "command=python main.py\nclientTimeout=30\n",
        encoding="iso-8859-1",
    )
    (checkpoint_root / "rl_combat_model_ep1.pth").write_bytes(b"checkpoint-v1")
    _copy_registered_sources(repo_root)

    registration = expansion.build_registration(
        study_id=STUDY_ID,
        artifact_root=artifact_root,
        repo_root=repo_root,
        seed_base=SEED_BASE,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=communication_path,
        checkpoint_root=checkpoint_root,
        schema_version=expansion.LEGACY_REGISTRATION_SCHEMA_VERSION,
    )
    registration_path = repo_root / "reports" / "registration.json"
    registration_path.parent.mkdir(parents=True, exist_ok=True)
    registration_path.write_text(
        expansion.render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    _git(repo_root, "init", "--object-format=sha1")
    _git(repo_root, "config", "core.autocrlf", "false")
    _git(repo_root, "config", "user.email", "verifier-fixture@example.invalid")
    _git(repo_root, "config", "user.name", "Verifier Fixture")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "build blocked verifier fixture")

    command_record = registration.to_record()["command"]
    child_command = [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    run_lock_path = artifact_root / "run-lock.json"
    run_lock = expansion.create_run_lock(
        registration_path=registration_path,
        lock_path=run_lock_path,
        repo_root=repo_root,
        child_command=child_command,
        created_unix_ns=1_750_000_000_000_000_000,
    )
    ledger_path = artifact_root / "study-ledger.jsonl"
    ledger = runner.StudyLedger(
        path=ledger_path,
        registration=registration,
        run_lock_hash=run_lock["run_lock_hash"],
    )
    ledger.initialize(created_unix_ns=1)
    for slot_number, complete_trajectories in ((1, 25), (2, 22)):
        slot = registration.slots[slot_number - 1]
        marker_start = 25 * (slot_number - 1)
        ledger.start_slot(
            slot_number,
            slot.session_id,
            started_unix_ns=slot_number * 2,
        )
        ledger.finish_slot(
            slot_number,
            process_exit_code=0,
            complete_trajectories=complete_trajectories,
            marker_start_count=marker_start,
            marker_end_count=marker_start + complete_trajectories,
            ended_unix_ns=slot_number * 2 + 1,
        )
    ledger.global_stop(
        reason="terminal_slot_structure_invalid_03",
        created_unix_ns=10,
    )
    finalization = expansion.finalize_registered_integrity_stop(
        registration,
        run_lock_hash=run_lock["run_lock_hash"],
        ledger_snapshot=ledger.snapshot(),
    )
    paths = {name: Path(path) for name, path in finalization["paths"].items()}
    return {
        "artifact_root": artifact_root,
        "claim_path": artifact_root / "finalization-claim.json",
        "closeout_markdown_path": paths["closeout_markdown"],
        "closeout_path": paths["closeout_json"],
        "ledger_path": ledger_path,
        "registration": registration,
        "registration_path": registration_path,
        "repo_root": repo_root,
        "run_lock_path": run_lock_path,
    }


def _rehash_ledger(path):
    records = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for index, record in enumerate(records, start=1):
        record["sequence"] = index
        record["previous_record_hash"] = previous_hash
        record["record_hash"] = _self_hash(record, "record_hash")
        previous_hash = record["record_hash"]
    _write_jsonl(path, records)


def _tamper_blocked(artifacts, case):
    if case in {"stop_reason", "ledger_without_stop"}:
        path = artifacts["ledger_path"]
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        if case == "stop_reason":
            records[-1]["payload"]["reason"] = "tampered_stop_reason"
        else:
            records.pop()
        _write_jsonl(path, records)
        _rehash_ledger(path)
        return
    if case == "claim_mode":
        path = artifacts["claim_path"]
        claim = json.loads(path.read_text(encoding="utf-8"))
        claim["mode"] = "complete"
        claim["claim_hash"] = _self_hash(claim, "claim_hash")
        _write_json(path, claim)
        return
    if case == "markdown":
        path = artifacts["closeout_markdown_path"]
        path.write_text(
            path.read_text(encoding="utf-8") + "tampered\n",
            encoding="utf-8",
            newline="",
        )
        return

    path = artifacts["closeout_path"]
    closeout = json.loads(path.read_text(encoding="utf-8"))
    if case == "terminal_slot":
        closeout["slots"][0]["terminal_status"] = "interrupted"
    elif case == "source":
        closeout["source"]["pool_manifest_hash"] = "a" * 64
    elif case == "blocker":
        closeout["blockers"].pop()
    elif case == "gate":
        closeout["gates"]["reward_design_ready"] = True
    elif case == "limitation":
        closeout["limitations"].append("tampered")
    elif case == "closeout_hash":
        closeout["closeout_hash"] = "0" * 64
        _write_json(path, closeout)
        return
    else:
        raise AssertionError(case)
    closeout["closeout_hash"] = _self_hash(closeout, "closeout_hash")
    _write_json(path, closeout)


def _tamper(artifacts, case):
    if case == "registration":
        path = artifacts["registration_path"]
        record = json.loads(path.read_text(encoding="utf-8"))
        record["analysis_rules"]["bootstrap_replicates"] = 9_999
        record["registration_hash"] = _self_hash(record, "registration_hash")
        _write_json(path, record)
        return
    if case == "run_lock":
        path = artifacts["run_lock_path"]
        record = json.loads(path.read_text(encoding="utf-8"))
        record["source"]["commit"] = "c" * 40
        record["run_lock_hash"] = _self_hash(record, "run_lock_hash")
        _write_json(path, record)
        return
    if case == "ledger":
        path = artifacts["ledger_path"]
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        terminal = next(row for row in records if row["event"] == "slot_terminal")
        terminal["payload"]["complete_trajectories"] = 24
        _write_jsonl(path, records)
        _rehash_ledger(path)
        return
    if case == "ledger_marker_gap":
        path = artifacts["ledger_path"]
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        terminals = [
            row for row in records if row["event"] == "slot_terminal"
        ]
        terminals[1]["payload"]["marker_start_count"] += 1
        terminals[1]["payload"]["marker_end_count"] += 1
        _write_jsonl(path, records)
        _rehash_ledger(path)
        return
    if case == "manifest":
        slot = artifacts["registration"].slots[0]
        path = Path(slot.manifest_path)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["session_id"] = "tampered-session"
        manifest["manifest_hash"] = _manifest_hash(manifest)
        _write_json(path, manifest)

        def update(pool):
            pool["slots"][0]["artifact_hashes"]["manifest_hash"] = manifest[
                "manifest_hash"
            ]
            pool["slots"][0]["artifact_hashes"]["manifest_sha256"] = (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )

        _update_pool_manifest(artifacts, update)
        return
    if case == "manifest_isolation":
        slot = artifacts["registration"].slots[0]
        path = Path(slot.manifest_path)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        communication_path = str(
            artifacts["registration"].communication_config_path
        )
        manifest["pre_session_isolation_hashes"][communication_path][
            "semantic_sha256"
        ] = "f" * 64
        manifest["manifest_hash"] = _manifest_hash(manifest)
        _write_json(path, manifest)

        def update(pool):
            pool["slots"][0]["artifact_hashes"]["manifest_hash"] = manifest[
                "manifest_hash"
            ]
            pool["slots"][0]["artifact_hashes"]["manifest_sha256"] = (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )

        _update_pool_manifest(artifacts, update)
        return
    if case == "trace":
        slot = artifacts["registration"].slots[0]
        path = Path(slot.trace_path)
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        resolution = next(row for row in rows if row["record_type"] == "resolution")
        resolution["selected_action_id"] = "tampered-action"
        _write_jsonl(path, rows)

        def update(pool):
            pool["slots"][0]["artifact_hashes"]["trace_sha256"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

        _update_pool_manifest(artifacts, update)
        return
    if case == "trace_candidate_legality":
        slot = artifacts["registration"].slots[0]
        path = Path(slot.trace_path)
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        proposal = next(row for row in rows if row["record_type"] == "proposed")
        proposal["selected_candidate"]["available"] = False
        _write_jsonl(path, rows)

        def update(pool):
            pool["slots"][0]["artifact_hashes"]["trace_sha256"] = (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )

        _update_pool_manifest(artifacts, update)
        return
    if case == "pool_membership":
        _update_pool_manifest(
            artifacts,
            lambda pool: pool["included_trajectories"].pop(),
        )
        return
    if case == "slot_accounting":
        _update_pool_manifest(
            artifacts,
            lambda pool: pool["slots"][0].update(
                {"excluded_trajectory_count": 0}
            ),
        )
        return
    if case == "unused_export_exclusion":
        _update_pool_manifest(
            artifacts,
            lambda pool: pool["slots"][0]["export_exclusions"].append(
                {
                    "decision_id": "never-proposed",
                    "reason": "confirmation_missing",
                }
            ),
        )
        return
    if case == "terminal_outcome":
        pool = json.loads(artifacts["pool_manifest_path"].read_text(encoding="utf-8"))
        run_file = pool["included_trajectories"][0]["run_file"]
        path = artifacts["runs_root"] / run_file
        outcome = json.loads(path.read_text(encoding="utf-8"))
        outcome["victory"] = not outcome["victory"]
        _write_json(path, outcome)
        return
    if case == "target_probability":
        path = artifacts["target_path"]
        target = json.loads(path.read_text(encoding="utf-8"))
        target["entries"][0]["probabilities"][0]["numerator"] = 1
        target["manifest_hash"] = _self_hash(target, "manifest_hash")
        _write_json(path, target)
        _update_closeout_source(
            artifacts,
            "target_manifest_hash",
            target["manifest_hash"],
        )
        return
    if case == "readiness_diagnostic":
        path = artifacts["readiness_path"]
        readiness = json.loads(path.read_text(encoding="utf-8"))
        readiness["diagnostics"]["effective_sample_size"]["numerator"] += 1
        _write_json(path, readiness)
        _update_closeout_source(
            artifacts,
            "readiness_file_sha256",
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        return
    if case == "estimate":
        path = artifacts["estimate_path"]
        estimate = json.loads(path.read_text(encoding="utf-8"))
        estimate["gates"]["ope_estimate_ready"] = True
        _write_json(path, estimate)
        _update_closeout_source(
            artifacts,
            "estimate_file_sha256",
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        return
    closeout_path = artifacts["closeout_path"]
    closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
    if case == "supported_victory_count":
        closeout["evidence_gate"]["conditions"][
            "minimum_supported_victories"
        ]["observed"] = 99
    elif case == "closeout_gate":
        closeout["evidence_gate"]["outcome_evidence_expansion_ready"] = True
        closeout["gates"]["outcome_evidence_expansion_ready"] = True
        closeout["status"] = "ready"
    elif case == "closeout_shadow_gate":
        closeout["formal_noncombat_rl_training_ready"] = True
    else:
        raise AssertionError(case)
    closeout["closeout_hash"] = _self_hash(closeout, "closeout_hash")
    _write_json(closeout_path, closeout)


def test_verifier_replays_registered_blocked_closeout(tmp_path, monkeypatch):
    artifacts = _build_blocked_study(tmp_path, monkeypatch)

    audit = _verifier().verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )

    assert audit["passed"] is True
    assert audit["closeout_mode"] == "integrity_stop"
    assert audit["study_id"] == STUDY_ID


def test_blocked_verifier_replays_locked_commit_after_checkout_moves(
    tmp_path,
    monkeypatch,
):
    artifacts = _build_blocked_study(tmp_path, monkeypatch)
    _git(
        artifacts["repo_root"],
        "commit",
        "--allow-empty",
        "-m",
        "move checkout after blocked finalization",
    )

    audit = _verifier().verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )

    assert audit["passed"] is True
    assert audit["closeout_mode"] == "integrity_stop"


@pytest.mark.parametrize(
    "case",
    (
        "stop_reason",
        "ledger_without_stop",
        "claim_mode",
        "terminal_slot",
        "source",
        "blocker",
        "gate",
        "limitation",
        "closeout_hash",
        "markdown",
    ),
)
def test_blocked_verifier_rejects_tamper(tmp_path, monkeypatch, case):
    artifacts = _build_blocked_study(tmp_path, monkeypatch)
    _tamper_blocked(artifacts, case)

    with pytest.raises(_verifier().OutcomeEvidenceVerificationError):
        _verifier().verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_blocked_verifier_rejects_each_normal_output(tmp_path, monkeypatch):
    artifacts = _build_blocked_study(tmp_path, monkeypatch)
    output_rules = artifacts["registration"].to_record()["output_rules"]
    forbidden_filenames = (
        output_rules["pool_manifest_filename"],
        output_rules["pool_samples_filename"],
        output_rules["target_manifest_filename"],
        output_rules["readiness_json_filename"],
        output_rules["readiness_markdown_filename"],
        output_rules["estimate_json_filename"],
        output_rules["estimate_markdown_filename"],
    )
    for filename in forbidden_filenames:
        path = artifacts["artifact_root"] / filename
        path.write_text("{}\n", encoding="utf-8", newline="")
        with pytest.raises(
            _verifier().OutcomeEvidenceVerificationError,
            match="forbidden normal artifacts",
        ):
            _verifier().verify_outcome_evidence_expansion(
                artifacts["registration_path"]
            )
        path.unlink()


def test_independent_verifier_replays_registered_study(tmp_path, monkeypatch):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)

    audit = verifier.verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )

    assert audit["passed"] is True
    assert audit["study_id"] == STUDY_ID
    assert audit["recomputed"]["complete_trajectory_count"] == 96
    assert audit["recomputed"]["supported_victory_count"] == 3
    assert audit["recomputed"]["outcome_evidence_expansion_ready"] is False
    included_run_files = {
        row["run_file"]
        for row in json.loads(
            artifacts["pool_manifest_path"].read_text(encoding="utf-8")
        )["included_trajectories"]
    }
    assert audit["terminal_outcome_file_sha256"] == {
        run_file: hashlib.sha256(
            (artifacts["runs_root"] / run_file).read_bytes()
        ).hexdigest()
        for run_file in sorted(included_run_files)
    }
    assert audit["ai_marker_file_sha256"] == hashlib.sha256(
        artifacts["marker_path"].read_bytes()
    ).hexdigest()
    assert audit["conservative_join_run_file_sha256"] == {
        run_file: hashlib.sha256(
            (artifacts["runs_root"] / run_file).read_bytes()
        ).hexdigest()
        for run_file in sorted(included_run_files)
    }
    expected_inventory = sorted(
        included_run_files,
        key=lambda value: int(Path(value).stem),
    )
    assert audit["conservative_run_inventory_sha256"] == hashlib.sha256(
        _canonical_json(expected_inventory).encode("utf-8")
    ).hexdigest()
    assert audit["verifier_implementation_sha256"] == hashlib.sha256(
        Path(verifier.__file__).read_bytes()
    ).hexdigest()


def test_v2_verifier_rejects_missing_release_handshake(tmp_path, monkeypatch):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    slot = artifacts["registration"].slots[0]
    release_path = Path(slot.config_path).with_name(
        f"{slot.session_id}-communication-release.json"
    )
    release_path.unlink()

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="handshake release",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_confirmed_eligible_decision_laundered_as_exclusion(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(
        tmp_path,
        monkeypatch,
        launder_confirmed=True,
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="confirmed eligible proposal was exported as an exclusion",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_joinable_decision_laundered_as_unattributed(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(
        tmp_path,
        monkeypatch,
        launder_unattributed=True,
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="eligible proposal was laundered as unattributed",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_joinable_run_laundered_as_unresolved(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(
        tmp_path,
        monkeypatch,
        omit_joinable_run=True,
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="conservative run join mismatch",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_incorrect_history_exclusion_reason(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(
        tmp_path,
        monkeypatch,
        history_exclusion_reason="selected_candidate_illegal",
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="export exclusion reason mismatch",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_exactly_labeled_history_corruption(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(
        tmp_path,
        monkeypatch,
        history_exclusion_reason="alternative_budget_history_mismatch",
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="normal closeout contains trace export exclusions",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


@pytest.mark.parametrize(
    "tamper_case",
    [
        "registration",
        "run_lock",
        "ledger",
        "ledger_marker_gap",
        "manifest",
        "manifest_isolation",
        "trace",
        "trace_candidate_legality",
        "pool_membership",
        "slot_accounting",
        "unused_export_exclusion",
        "terminal_outcome",
        "target_probability",
        "readiness_diagnostic",
        "estimate",
        "supported_victory_count",
        "closeout_gate",
        "closeout_shadow_gate",
    ],
)
def test_independent_verifier_rejects_tampered_study(
    tmp_path,
    monkeypatch,
    tamper_case,
):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    _tamper(artifacts, tamper_case)

    with pytest.raises(verifier.OutcomeEvidenceVerificationError):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_has_static_import_independence():
    verifier_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )
    tree = ast.parse(verifier_path.read_text(encoding="utf-8"))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert imported_modules.isdisjoint(
        {
            "analysis_scripts.noncombat_outcome_evidence_expansion",
            "scripts.run_noncombat_outcome_evidence_expansion",
            "spirecomm.communication.study_handshake",
        }
    )


def test_verifier_supports_direct_cli_execution():
    verifier_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        [sys.executable, str(verifier_path), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--registration" in completed.stdout


def test_qualification_verifier_cli_requires_isolation_before_argparse(tmp_path):
    verifier_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    marker_path = tmp_path / "argparse-imported.txt"
    (shadow_root / "argparse.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n"
        "raise RuntimeError('shadow argparse executed')\n",
        encoding="utf-8",
        newline="",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(shadow_root)

    completed = subprocess.run(
        [
            sys.executable,
            str(verifier_path),
            "--qualification-request-source",
            str(tmp_path / "request.json"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert completed.returncode == 2
    assert "isolated" in completed.stderr.lower()
    assert not marker_path.exists()


def test_qualification_verifier_rejects_site_enabled_isolated_startup(tmp_path):
    verifier_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(verifier_path),
            "--qualification-request-source",
            str(tmp_path / "request.json"),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 2
    assert "no-site" in completed.stderr.lower()


def test_qualification_verifier_redirects_bytecode_cache_before_imports(
    tmp_path,
):
    verifier_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )
    probe = (
        "import json,runpy,sys; path=sys.argv[1]; "
        "sys.argv=['verifier','--qualification-request-source','request.json']; "
        "runpy.run_path(path, run_name='qualification_verifier_probe'); "
        "print(json.dumps([sys.dont_write_bytecode, sys.pycache_prefix]))"
    )

    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-c", probe, str(verifier_path)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        True,
        os.path.join(os.devnull, "sts-qualification-pycache"),
    ]


def test_qualification_verifier_does_not_import_ordinary_audit_helpers(
    tmp_path,
):
    verifier_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )
    probe = (
        "import json,runpy,sys; path=sys.argv[1]; "
        "sys.argv=['verifier','--qualification-request-source','request.json']; "
        "runpy.run_path(path, run_name='qualification_verifier_probe'); "
        "print(json.dumps([name for name in sys.modules "
        "if name in {'analysis_scripts.verify_noncombat_ope_artifacts',"
        "'analysis_scripts.verify_noncombat_ope_estimates'}]))"
    )

    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-c", probe, str(verifier_path)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_verifier_replay_and_render_are_deterministic(tmp_path, monkeypatch):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)

    first = verifier.verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )
    second = verifier.verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )
    run_lock = json.loads(artifacts["run_lock_path"].read_text(encoding="utf-8"))

    assert second == first
    assert verifier.render_verification_audit(second) == (
        verifier.render_verification_audit(first)
    )
    assert first["source_implementation_sha256"] == {
        row["relative_path"]: row["sha256"]
        for row in run_lock["implementation_files"]
    }
    assert first["verifier_implementation_sha256"] == hashlib.sha256(
        Path(verifier.__file__).read_bytes()
    ).hexdigest()


def test_verifier_audit_binds_complete_numeric_run_inventory(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)

    before = verifier.verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )
    extra_run = artifacts["runs_root"] / "2999999999.run"
    _write_json(
        extra_run,
        {
            "floor_reached": 1,
            "killed_by": "",
            "playtime": 1,
            "victory": False,
        },
    )
    after = verifier.verify_outcome_evidence_expansion(
        artifacts["registration_path"]
    )

    assert after["conservative_run_inventory_sha256"] != before[
        "conservative_run_inventory_sha256"
    ]
    assert after["conservative_join_run_file_sha256"] == before[
        "conservative_join_run_file_sha256"
    ]


def test_verifier_rejects_registered_source_byte_drift(tmp_path, monkeypatch):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    source_path = artifacts["repo_root"] / "main.py"
    source_path.write_bytes(source_path.read_bytes() + b"\n")

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="implementation source drift: main.py",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_git_head_drift_without_source_byte_drift(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    _git(
        artifacts["repo_root"],
        "commit",
        "--allow-empty",
        "-m",
        "move HEAD without changing source bytes",
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="Git HEAD differs from the run lock",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_registered_verifier_byte_drift(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    verifier_path = (
        artifacts["repo_root"]
        / "analysis_scripts"
        / "verify_noncombat_outcome_evidence_expansion.py"
    )
    verifier_path.write_bytes(verifier_path.read_bytes() + b"\n")

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match=(
            "implementation source drift: "
            "analysis_scripts/verify_noncombat_outcome_evidence_expansion.py"
        ),
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_communication_mod_semantic_drift(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    communication_path = Path(
        artifacts["registration"].communication_config_path
    )
    communication_path.write_text(
        "command=python tampered.py\nclientTimeout=30\n",
        encoding="iso-8859-1",
    )

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="CommunicationMod semantic configuration drift",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )


def test_verifier_rejects_checkpoint_inventory_addition(
    tmp_path,
    monkeypatch,
):
    verifier = _verifier()
    artifacts = _build_study(tmp_path, monkeypatch)
    checkpoint_root = Path(artifacts["registration"].checkpoint_root)
    (checkpoint_root / "rl_model_unregistered.pth").write_bytes(b"unexpected")

    with pytest.raises(
        verifier.OutcomeEvidenceVerificationError,
        match="checkpoint inventory drift",
    ):
        verifier.verify_outcome_evidence_expansion(
            artifacts["registration_path"]
        )
