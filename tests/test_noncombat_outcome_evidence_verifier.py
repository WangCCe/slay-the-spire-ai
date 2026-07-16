import ast
import hashlib
import importlib
import json
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


def _verifier():
    try:
        return importlib.import_module(
            "analysis_scripts.verify_noncombat_outcome_evidence_expansion"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"outcome evidence verifier is missing: {exc}")


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
