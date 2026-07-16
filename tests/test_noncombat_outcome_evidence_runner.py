import importlib
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from analysis_scripts.noncombat_outcome_evidence_expansion import (
    LEGACY_REGISTRATION_SCHEMA_VERSION,
    build_registration,
    render_registration_json,
)
from spirecomm.ai.noncombat_exploration import (
    ExplorationConfigurationError,
    create_exploration_session_manifest,
    parse_exploration_config,
)
from spirecomm.communication.study_handshake import (
    HANDSHAKE_ATTEMPT_ENV,
    build_ready_record,
    load_attempt_record,
    publish_record_once as publish_handshake_record_once,
)


STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
SEED_BASE = 2_026_071_500
WINDOWS_PYTHON = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_COMMIT = "a" * 40
RUN_LOCK_HASH = "b" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]


def _module():
    try:
        return importlib.import_module(
            "scripts.run_noncombat_outcome_evidence_expansion"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"outcome evidence runner is missing: {exc}")


def test_runner_supports_direct_script_execution(tmp_path):
    script_path = (
        REPO_ROOT / "scripts" / "run_noncombat_outcome_evidence_expansion.py"
    )
    shadow_root = tmp_path / "shadow"
    shadow_package = shadow_root / "analysis_scripts"
    shadow_package.mkdir(parents=True)
    (shadow_package / "__init__.py").write_text("", encoding="utf-8")
    (shadow_package / "noncombat_outcome_evidence_expansion.py").write_text(
        "raise RuntimeError('shadowed analysis_scripts import')\n",
        encoding="utf-8",
    )
    shadow_archive = tmp_path / "shadow.zip"
    with zipfile.ZipFile(shadow_archive, "w") as archive:
        archive.writestr("analysis_scripts/__init__.py", "")
        archive.writestr(
            "analysis_scripts/noncombat_outcome_evidence_expansion.py",
            "raise RuntimeError('shadowed zipped analysis_scripts import')\n",
        )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(shadow_root), str(shadow_archive), str(REPO_ROOT))
    )

    completed = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "dry-run" in completed.stdout


def test_dry_run_rejects_registration_for_another_checkout(tmp_path):
    module = _module()
    registration = build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "other-checkout",
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="runner checkout",
    ):
        module._dry_run_command(registration_path)


def _legacy_registration_path(tmp_path):
    module = _module()
    registration = build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "legacy-study",
        repo_root=REPO_ROOT,
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
        schema_version=LEGACY_REGISTRATION_SCHEMA_VERSION,
    )
    path = tmp_path / "legacy-registration.json"
    path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    return path


@pytest.mark.parametrize("command_name", ("_start_command", "_run_next_command"))
def test_launch_commands_reject_legacy_v1_before_writing_state(
    tmp_path,
    command_name,
):
    module = _module()
    registration_path = _legacy_registration_path(tmp_path)

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="v1 registration is read-only",
    ):
        getattr(module, command_name)(registration_path)

    artifact_root = tmp_path / "legacy-study"
    assert not (artifact_root / "run-lock.json").exists()
    assert not (artifact_root / "study-ledger.jsonl").exists()


def test_dry_run_keeps_legacy_v1_read_only_support(tmp_path):
    result = _module()._dry_run_command(_legacy_registration_path(tmp_path))

    assert result["launch_count"] == 24


def _study(tmp_path):
    registration = build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=REPO_ROOT,
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )
    run_lock = {
        "registration": {"canonical_hash": registration.registration_hash},
        "run_lock_hash": RUN_LOCK_HASH,
        "source": {"commit": SOURCE_COMMIT},
        "study_id": STUDY_ID,
    }
    return registration, run_lock


def _ledger(tmp_path):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    ledger = module.StudyLedger(
        path=tmp_path / "study" / "ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)
    return ledger, registration


class _FakeHandshakeChild:
    def __init__(self, *, pid=321, exit_code=0, initial_returncode=None, on_wait=None):
        self.pid = pid
        self.exit_code = exit_code
        self.returncode = initial_returncode
        self.on_wait = on_wait
        self.terminated = False
        self.killed = False
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if timeout is not None:
            if self.returncode is None:
                raise subprocess.TimeoutExpired("fake-child", timeout)
            return self.returncode
        if self.on_wait is not None:
            callback, self.on_wait = self.on_wait, None
            callback()
        self.returncode = self.exit_code
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def _handshake_slot(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    module.write_slot_config_once(launch)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")
    return module, ledger, registration, run_lock, launch, marker_path


def _publish_ready_from_environment(environment, *, child_pid, mutate=None):
    attempt = load_attempt_record(Path(environment[HANDSHAKE_ATTEMPT_ENV]))
    ready = build_ready_record(
        attempt,
        child_pid=child_pid,
        created_unix_ns=175,
    )
    if mutate is not None:
        ready = mutate(attempt, ready)
    publish_handshake_record_once(Path(attempt["ready_path"]), ready)
    return attempt


def test_slot_launch_uses_exact_registered_eval_command_and_config(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    command_record = registration.to_record()["command"]

    assert list(launch.command) == [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    assert "--max-games" in launch.command
    assert launch.command[launch.command.index("--max-games") + 1] == "25"
    assert "--eval" in launch.command
    assert "--train" not in launch.command
    assert "--model" not in launch.command
    assert launch.environment == {
        "STS_NONCOMBAT_EXPLORATION_CONFIG": launch.config_path
    }
    assert launch.config_record == {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "manifest_path": registration.slots[0].manifest_path,
        "per_run_alternative_budget": 2,
        "schema_version": "noncombat-exploration-config-v1",
        "seed": SEED_BASE + 1,
        "session_id": f"{STUDY_ID}-s01",
        "source_commit": SOURCE_COMMIT,
        "study_id": STUDY_ID,
        "study_registration_hash": registration.registration_hash,
        "study_run_lock_hash": RUN_LOCK_HASH,
        "study_slot_number": 1,
        "trace_path": registration.slots[0].trace_path,
    }


def test_registered_config_binding_survives_runtime_manifest_creation(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 2)
    module.write_slot_config_once(launch)
    config = parse_exploration_config(
        launch.config_record,
        config_path=Path(launch.config_path),
    )

    manifest = create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=str(WINDOWS_PYTHON),
        command=list(launch.command),
        isolation_hashes={"locked": True},
    )

    assert config.study_run_lock_hash == RUN_LOCK_HASH
    assert config.study_registration_hash == registration.registration_hash
    assert manifest["effective_config"]["study_run_lock_hash"] == RUN_LOCK_HASH
    assert manifest["effective_config"]["study_slot_number"] == 2


def test_registered_config_requires_complete_study_binding(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    incomplete = dict(launch.config_record)
    incomplete.pop("study_run_lock_hash")

    with pytest.raises(ExplorationConfigurationError, match="supplied together"):
        parse_exploration_config(incomplete)


@pytest.mark.parametrize(
    "mutated_command",
    [
        lambda command: [*command, "--train"],
        lambda command: [*command, "--model", "other.pth"],
        lambda command: [*command[:-1], "--epsilon", "0.1"],
        lambda command: [
            *command[: command.index("--max-games") + 1],
            "26",
            *command[command.index("--max-games") + 2 :],
        ],
    ],
)
def test_registered_command_rejects_training_or_mutation_flags(
    tmp_path, mutated_command
):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="command"):
        module.validate_registered_command(
            registration,
            mutated_command(list(launch.command)),
        )


def test_ledger_appends_hash_chained_lifecycle_records(tmp_path):
    ledger, registration = _ledger(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    terminal = ledger.finish_slot(
        1,
        process_exit_code=0,
        complete_trajectories=25,
        ended_unix_ns=300,
    )

    lines = ledger.path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert ledger.path.read_bytes().endswith(b"\n")
    assert [record["sequence"] for record in records] == [1, 2, 3]
    assert [record["event"] for record in records] == [
        "study_started",
        "slot_started",
        "slot_terminal",
    ]
    assert records[0]["previous_record_hash"] is None
    assert records[1]["previous_record_hash"] == records[0]["record_hash"]
    assert records[2]["previous_record_hash"] == records[1]["record_hash"]
    assert terminal["terminal_status"] == "completed"


def test_ledger_enforces_order_identity_and_launch_at_most_once(tmp_path):
    ledger, registration = _ledger(tmp_path)

    with pytest.raises(ledger.error_type, match="next.*slot|out of order"):
        ledger.start_slot(2, registration.slots[1].session_id, started_unix_ns=200)
    with pytest.raises(ledger.error_type, match="session"):
        ledger.start_slot(1, "unregistered-session", started_unix_ns=200)

    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    ledger.finish_slot(
        1,
        process_exit_code=0,
        complete_trajectories=25,
        ended_unix_ns=300,
    )
    with pytest.raises(ledger.error_type, match="next.*slot|already launched"):
        ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=400)


def test_early_exit_is_terminally_interrupted_and_cannot_restart(tmp_path):
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    terminal = ledger.finish_slot(
        1,
        process_exit_code=17,
        complete_trajectories=7,
        ended_unix_ns=300,
    )

    assert terminal["terminal_status"] == "interrupted"
    assert ledger.next_slot().slot_number == 2
    with pytest.raises(ledger.error_type, match="next.*slot|already launched"):
        ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=400)


def test_crash_recovery_marks_active_slot_interrupted_without_relaunch(tmp_path):
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)

    recovered = type(ledger)(
        path=ledger.path,
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    terminal = recovered.recover_active_slot(
        reason="runner process disappeared",
        complete_trajectories=3,
        ended_unix_ns=400,
    )

    assert terminal["terminal_status"] == "interrupted"
    assert recovered.next_slot().slot_number == 2


def test_ledger_rejects_duplicate_terminal_and_run_lock_mismatch(tmp_path):
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    ledger.finish_slot(
        1,
        process_exit_code=0,
        complete_trajectories=25,
        ended_unix_ns=300,
    )

    with pytest.raises(ledger.error_type, match="active slot|duplicate"):
        ledger.finish_slot(
            1,
            process_exit_code=0,
            complete_trajectories=25,
            ended_unix_ns=400,
        )
    mismatched = type(ledger)(
        path=ledger.path,
        registration=registration,
        run_lock_hash="c" * 64,
    )
    with pytest.raises(ledger.error_type, match="run lock"):
        mismatched.snapshot()


def test_ledger_rejects_rehashed_registered_session_identity_tamper(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    records = [
        json.loads(line)
        for line in ledger.path.read_text(encoding="utf-8").splitlines()
    ]
    records[1]["session_id"] = registration.slots[1].session_id
    records[1]["record_hash"] = module._record_hash(records[1])
    ledger.path.write_text(
        "".join(module._canonical_json(record) + "\n" for record in records),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(ledger.error_type, match="session"):
        ledger.snapshot()


def test_global_stop_blocks_every_later_launch(tmp_path):
    ledger, registration = _ledger(tmp_path)
    stop = ledger.global_stop(
        reason="checkpoint drift",
        created_unix_ns=200,
    )

    assert stop["reason"] == "checkpoint drift"
    with pytest.raises(ledger.error_type, match="global.*stop"):
        ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=300)


def test_repeated_lock_failure_preserves_first_global_stop(tmp_path):
    module = _module()
    ledger, _registration = _ledger(tmp_path)
    ledger.global_stop(reason="first integrity failure", created_unix_ns=200)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="second failure"):
        module.validate_run_lock_or_stop(
            ledger,
            validator=lambda: (_ for _ in ()).throw(RuntimeError("second failure")),
        )

    assert ledger.snapshot()["global_stop"] == {"reason": "first integrity failure"}


def test_schedule_has_no_post_slot_24_extension(tmp_path):
    ledger, registration = _ledger(tmp_path)
    for slot in registration.slots:
        ledger.start_slot(
            slot.slot_number,
            slot.session_id,
            started_unix_ns=slot.slot_number * 10,
        )
        ledger.finish_slot(
            slot.slot_number,
            process_exit_code=0,
            complete_trajectories=25,
            ended_unix_ns=slot.slot_number * 10 + 1,
        )

    snapshot = ledger.snapshot()
    assert snapshot["all_slots_terminal"] is True
    assert snapshot["terminal_slot_count"] == 24
    with pytest.raises(ledger.error_type, match="schedule.*complete|no later slot"):
        ledger.next_slot()


def test_slot_config_is_create_once_and_byte_stable(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    first = module.write_slot_config_once(launch)

    assert Path(launch.config_path).read_text(encoding="utf-8") == first
    assert first.endswith("\n")
    assert "\r" not in first
    with pytest.raises(module.OutcomeEvidenceRunnerError, match="already exists"):
        module.write_slot_config_once(launch)


def test_run_lock_validation_failure_records_global_stop_before_launch(tmp_path):
    module = _module()
    ledger, _registration = _ledger(tmp_path)
    launched = []

    def fail_validation():
        raise RuntimeError("source file drift")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="validation"):
        module.validate_run_lock_or_stop(
            ledger,
            validator=fail_validation,
        )

    assert launched == []
    assert ledger.snapshot()["global_stop"]["reason"].startswith(
        "run lock validation failed"
    )


def test_existing_ledger_preserves_original_run_lock_binding_on_validation_failure(
    tmp_path,
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    reopened = module.StudyLedger.open_existing(
        path=ledger.path,
        registration=registration,
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="differs"):
        module.validate_run_lock_or_stop(
            reopened,
            validator=lambda: {"run_lock_hash": "c" * 64},
        )

    snapshot = reopened.snapshot()
    assert reopened.run_lock_hash == RUN_LOCK_HASH
    assert "differs from the ledger binding" in snapshot["global_stop"]["reason"]


@pytest.mark.parametrize(
    ("new_markers", "exit_code", "terminal_status"),
    [(25, 0, "completed"), (7, 0, "interrupted"), (25, 3, "interrupted")],
)
def test_execute_slot_uses_ai_marker_delta_for_terminal_status(
    tmp_path, new_markers, exit_code, terminal_status
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")

    def process_runner(_launch):
        with marker_path.open("a", encoding="utf-8") as handle:
            for index in range(new_markers):
                handle.write(f"{100 + index}\n")
        return exit_code

    terminal = module.execute_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_runner=process_runner,
        started_unix_ns=200,
        ended_unix_ns=300,
    )

    assert terminal["complete_trajectories"] == new_markers
    assert terminal["terminal_status"] == terminal_status
    terminal_slot = ledger.snapshot()["terminal_slots"][0]
    assert terminal_slot["marker_start_count"] == 2
    assert terminal_slot["marker_end_count"] == 2 + new_markers


def test_execute_slot_rejects_marker_truncation_as_global_stop(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")

    def process_runner(_launch):
        marker_path.write_text("12\n", encoding="utf-8")
        return 0

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="marker"):
        module.execute_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_runner=process_runner,
            started_unix_ns=200,
            ended_unix_ns=300,
        )

    snapshot = ledger.snapshot()
    assert snapshot["global_stop"] is not None
    assert snapshot["active_slot"] is None


def test_handshaken_slot_claims_only_after_verified_child_readiness(
    tmp_path,
    monkeypatch,
):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    events = []

    def add_complete_markers():
        with marker_path.open("a", encoding="utf-8") as handle:
            for index in range(25):
                handle.write(f"{100 + index}\n")

    child = _FakeHandshakeChild(on_wait=add_complete_markers)
    original_start_slot = ledger.start_slot

    def recording_start_slot(*args, **kwargs):
        events.append("claim")
        return original_start_slot(*args, **kwargs)

    monkeypatch.setattr(ledger, "start_slot", recording_start_slot)

    def recording_publish(path, record):
        schema = record["schema_version"]
        events.append("attempt" if "attempt" in schema else "release")
        publish_handshake_record_once(path, record)

    monkeypatch.setattr(module, "publish_record_once", recording_publish)

    def process_starter(observed_launch, environment):
        events.append("popen")
        assert observed_launch is launch
        assert ledger.snapshot()["active_slot"] is None
        attempt = load_attempt_record(Path(environment[HANDSHAKE_ATTEMPT_ENV]))
        assert attempt["marker_start_count"] == 2
        assert Path(attempt["attempt_path"]).is_file()
        assert not Path(registration.slots[0].manifest_path).exists()
        assert not Path(registration.slots[0].trace_path).exists()
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter((150, 200, 225, 300))
    terminal = module.execute_handshaken_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_starter=process_starter,
        time_ns=lambda: next(timestamps),
    )

    assert events == ["attempt", "popen", "claim", "release"]
    assert child.wait_calls == [None]
    assert terminal == {
        "complete_trajectories": 25,
        "marker_end_count": 27,
        "marker_start_count": 2,
        "process_exit_code": 0,
        "terminal_status": "completed",
    }
    records = [
        json.loads(line)
        for line in ledger.path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[1]["event"] == "slot_started"
    assert records[1]["payload"] == {"marker_start_count": 2}
    attempt = load_attempt_record(
        Path(launch.config_path).with_name(
            f"{launch.session_id}-communication-attempt.json"
        )
    )
    assert Path(attempt["release_path"]).is_file()


def test_handshake_revalidates_run_lock_after_readiness_before_claim(tmp_path):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    def fail_preclaim_validation():
        raise module.OutcomeEvidenceRunnerError("forced run-lock drift")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="forced run-lock drift"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
            preclaim_validator=fail_preclaim_validation,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert "forced run-lock drift" in snapshot["global_stop"]["reason"]


def test_handshake_rejects_child_exit_between_ready_validation_and_claim(
    tmp_path,
    monkeypatch,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    original_validate = module._validate_preclaim_handshake_state

    def exit_after_preclaim_validation(**kwargs):
        original_validate(**kwargs)
        child.returncode = 17

    monkeypatch.setattr(
        module,
        "_validate_preclaim_handshake_state",
        exit_after_preclaim_validation,
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="exited.*slot claim",
    ):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


def test_handshake_rechecks_outputs_after_claim_before_release(
    tmp_path,
    monkeypatch,
):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()
    manifest_path = Path(registration.slots[0].manifest_path)
    release_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-release.json"
    )

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    original_start_slot = ledger.start_slot

    def create_output_after_claim(*args, **kwargs):
        result = original_start_slot(*args, **kwargs)
        manifest_path.write_text("{}\n", encoding="utf-8", newline="")
        return result

    monkeypatch.setattr(ledger, "start_slot", create_output_after_claim)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="gameplay output"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert release_path.exists() is False
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["terminal_slots"][0]["terminal_status"] == "interrupted"
    assert snapshot["global_stop"] is not None


def test_handshake_surfaces_child_cleanup_failure_in_global_stop(tmp_path):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )

    class UnkillableChild(_FakeHandshakeChild):
        def terminate(self):
            raise OSError("terminate denied")

        def kill(self):
            raise OSError("kill denied")

    child = UnkillableChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        Path(registration.slots[0].manifest_path).write_text(
            "{}\n",
            encoding="utf-8",
            newline="",
        )
        return child

    with pytest.raises(module.OutcomeEvidenceRunnerError) as error:
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    assert "child cleanup failed" in str(error.value)
    snapshot = ledger.snapshot()
    assert "child cleanup failed" in snapshot["global_stop"]["reason"]


def test_handshake_timeout_stops_without_claim_or_retry(tmp_path):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()
    starts = []
    clock = [0.0]

    def process_starter(_launch, _environment):
        starts.append(child.pid)
        return child

    def sleep(_seconds):
        clock[0] = 121.0

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="readiness.*deadline"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            sleep=sleep,
        )

    snapshot = ledger.snapshot()
    assert starts == [child.pid]
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert "readiness" in snapshot["global_stop"]["reason"]


@pytest.mark.parametrize("ready_at", (120.0, 121.0))
def test_handshake_rejects_ready_at_or_after_readiness_deadline(
    tmp_path,
    ready_at,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()
    clock = [0.0]
    attempt_environment = {}

    def process_starter(_launch, environment):
        attempt_environment.update(environment)
        return child

    def publish_late_ready(_seconds):
        clock[0] = ready_at
        _publish_ready_from_environment(
            attempt_environment,
            child_pid=child.pid,
        )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="readiness.*deadline"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            sleep=publish_late_ready,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert "readiness" in snapshot["global_stop"]["reason"]


def test_handshake_early_child_exit_stops_before_claim(tmp_path):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild(initial_returncode=17)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="exited.*readiness"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=lambda _launch, _environment: child,
        )

    snapshot = ledger.snapshot()
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


@pytest.mark.parametrize(
    "failure_mode",
    ("malformed", "pid_mismatch", "marker_growth", "manifest", "trace"),
)
def test_handshake_rejects_invalid_preclaim_evidence(
    tmp_path,
    failure_mode,
):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        attempt = load_attempt_record(Path(environment[HANDSHAKE_ATTEMPT_ENV]))
        if failure_mode == "malformed":
            Path(attempt["ready_path"]).write_text("{broken\n", encoding="utf-8")
            return child
        ready_pid = child.pid + 1 if failure_mode == "pid_mismatch" else child.pid
        _publish_ready_from_environment(environment, child_pid=ready_pid)
        if failure_mode == "marker_growth":
            with marker_path.open("a", encoding="utf-8") as handle:
                handle.write("12\n")
        elif failure_mode == "manifest":
            Path(registration.slots[0].manifest_path).write_text(
                "{}\n",
                encoding="utf-8",
            )
        elif failure_mode == "trace":
            Path(registration.slots[0].trace_path).write_text(
                "{}\n",
                encoding="utf-8",
            )
        return child

    with pytest.raises(module.OutcomeEvidenceRunnerError):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


@pytest.mark.parametrize("artifact", ("attempt", "ready", "release"))
def test_stale_handshake_artifact_is_an_orphaned_global_stop_without_popen(
    tmp_path,
    artifact,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    suffix = {
        "attempt": "-communication-attempt.json",
        "ready": "-communication-ready.json",
        "release": "-communication-release.json",
    }[artifact]
    stale_path = Path(launch.config_path).with_name(f"{launch.session_id}{suffix}")
    stale_path.write_text("{}\n", encoding="utf-8")
    starts = []

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="handshake artifact"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=lambda *_args: starts.append(True),
        )

    assert starts == []
    snapshot = ledger.snapshot()
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


def test_release_publication_failure_consumes_claimed_slot_and_stops(
    tmp_path,
    monkeypatch,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    def fail_release(path, record):
        if "release" in record["schema_version"]:
            raise module.OutcomeEvidenceRunnerError("forced release publication failure")
        publish_handshake_record_once(path, record)

    monkeypatch.setattr(module, "publish_record_once", fail_release)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="release"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["terminal_slots"][0]["terminal_status"] == "interrupted"
    assert snapshot["terminal_slots"][0]["marker_start_count"] == 2
    assert snapshot["terminal_slots"][0]["marker_end_count"] == 2
    assert "release" in snapshot["global_stop"]["reason"]


def test_host_recovery_consumes_active_handshaken_slot_before_global_stop(tmp_path):
    module, ledger, registration, _run_lock, _launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    ledger.start_slot(
        1,
        registration.slots[0].session_id,
        marker_start_count=2,
        started_unix_ns=200,
    )
    with marker_path.open("a", encoding="utf-8") as handle:
        handle.write("12\n")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="active slot recovery"):
        module._recover_active_slot_after_host_failure(
            ledger=ledger,
            marker_path=marker_path,
            ended_unix_ns=300,
        )

    snapshot = ledger.snapshot()
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["terminal_slots"][0]["complete_trajectories"] == 1
    assert snapshot["terminal_slots"][0]["marker_start_count"] == 2
    assert snapshot["terminal_slots"][0]["marker_end_count"] == 3
    assert snapshot["global_stop"] is not None


def test_run_next_recovers_active_slot_before_revalidating_run_lock(
    tmp_path,
    monkeypatch,
):
    module, ledger, registration, _run_lock, _launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    ledger.start_slot(
        1,
        registration.slots[0].session_id,
        marker_start_count=2,
        started_unix_ns=200,
    )
    validation_calls = []

    monkeypatch.setattr(
        module,
        "_load_runner_registration",
        lambda _path: registration,
    )
    monkeypatch.setattr(
        module,
        "_require_launchable_runner_registration",
        lambda value: value,
    )
    monkeypatch.setattr(module, "_registered_command", lambda _value: ["python"])
    monkeypatch.setattr(module, "_run_lock_path", lambda _value: tmp_path / "lock")
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        classmethod(lambda cls, **_kwargs: ledger),
    )

    def unexpected_run_lock_validation(*_args, **_kwargs):
        validation_calls.append(True)
        pytest.fail("run lock validation ran before active-slot recovery")

    monkeypatch.setattr(
        module,
        "validate_run_lock_or_stop",
        unexpected_run_lock_validation,
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="active slot recovery"):
        module._run_next_command(tmp_path / "registration.json")

    snapshot = ledger.snapshot()
    assert validation_calls == []
    assert marker_path.read_text(encoding="utf-8") == "10\n11\n"
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["global_stop"] is not None


@pytest.mark.parametrize(
    "subcommand",
    ["start", "dry-run", "run-next", "monitor", "finalize"],
)
def test_cli_exposes_only_registered_study_subcommands(tmp_path, subcommand):
    module = _module()
    registration_path = tmp_path / "registration.json"
    args = module.parse_args(
        [subcommand, "--registration", str(registration_path)]
    )

    assert args.subcommand == subcommand
    assert args.registration == registration_path


def test_run_next_cli_keeps_audit_json_off_communication_stdout(
    tmp_path, monkeypatch, capsys
):
    module = _module()
    registration_path = tmp_path / "registration.json"
    result = {"slot_number": 1, "status": "completed"}
    monkeypatch.setattr(module, "_run_next_command", lambda _path: result)

    assert module.main(
        ["run-next", "--registration", str(registration_path)]
    ) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def test_finalize_command_replays_every_registered_slot_and_runs_pipeline(
    tmp_path, monkeypatch
):
    module = _module()
    registration, run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
    )
    ledger_snapshot = {
        "all_slots_terminal": True,
        "global_stop": None,
        "terminal_slots": [
            {
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
                "terminal_status": "completed",
            }
            for slot in registration.slots
        ],
    }
    sessions = tuple(object() for _slot in registration.slots)
    pool = object()
    finalization = {
        "closeout": {"status": "ready"},
        "paths": {"closeout_json": "closeout.json"},
        "study_id": STUDY_ID,
    }
    calls = {}

    class FakeLedger:
        run_lock_hash = RUN_LOCK_HASH

        def snapshot(self):
            return ledger_snapshot

    monkeypatch.setattr(module, "load_registration", lambda _path: registration)
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        lambda **_kwargs: FakeLedger(),
    )
    monkeypatch.setattr(module, "_load_run_lock_record", lambda _path: run_lock)

    def validate_lock(**kwargs):
        calls["validate_lock"] = kwargs
        return run_lock

    def collect(registration_value, **kwargs):
        assert registration_value is registration
        calls["collect"] = kwargs
        return sessions

    def build_pool(registration_value, **kwargs):
        assert registration_value is registration
        assert kwargs["sessions"] is sessions
        calls["pool"] = kwargs
        return pool

    def finalize(registration_value, **kwargs):
        assert registration_value is registration
        assert kwargs["pool"] is pool
        calls["finalize"] = kwargs
        return finalization

    monkeypatch.setattr(module, "validate_run_lock", validate_lock)
    monkeypatch.setattr(module, "collect_registered_session_evidence", collect)
    monkeypatch.setattr(module, "build_registered_pool", build_pool)
    monkeypatch.setattr(module, "finalize_registered_outcome_evidence", finalize)

    result = module._finalize_gate_command(registration_path)

    assert result is finalization
    assert calls["collect"]["run_lock"] is run_lock
    assert calls["collect"]["ledger_snapshot"] is ledger_snapshot
    assert calls["pool"] == {
        "ledger_snapshot": ledger_snapshot,
        "run_lock_hash": RUN_LOCK_HASH,
        "sessions": sessions,
    }
    assert calls["finalize"] == {
        "ledger_snapshot": ledger_snapshot,
        "pool": pool,
        "run_lock_hash": RUN_LOCK_HASH,
    }


def test_finalize_command_writes_blocked_closeout_after_global_stop(
    tmp_path, monkeypatch
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    snapshot = {
        "active_slot": None,
        "all_slots_terminal": False,
        "global_stop": {"reason": "checkpoint drift"},
        "initialized": True,
        "terminal_slot_count": 0,
        "terminal_slots": [],
    }
    blocked = {
        "closeout": {"status": "blocked"},
        "paths": {"closeout_json": "closeout.json"},
        "study_id": STUDY_ID,
    }
    calls = {}

    class FakeLedger:
        run_lock_hash = RUN_LOCK_HASH

        def snapshot(self):
            return snapshot

    monkeypatch.setattr(module, "load_registration", lambda _path: registration)
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        lambda **_kwargs: FakeLedger(),
    )

    def finalize(registration_value, **kwargs):
        assert registration_value is registration
        calls.update(kwargs)
        return blocked

    monkeypatch.setattr(module, "finalize_registered_integrity_stop", finalize)
    monkeypatch.setattr(
        module,
        "collect_registered_session_evidence",
        lambda *_args, **_kwargs: pytest.fail("blocked closeout must not pool"),
    )

    result = module._finalize_gate_command(registration_path)

    assert result is blocked
    assert calls == {
        "ledger_snapshot": snapshot,
        "run_lock_hash": RUN_LOCK_HASH,
    }


@pytest.mark.parametrize(
    "validation_result",
    [
        pytest.param(RuntimeError("source drift"), id="validation-error"),
        pytest.param({"run_lock_hash": "c" * 64}, id="ledger-hash-mismatch"),
    ],
)
def test_finalize_command_converts_late_run_lock_failure_to_blocked_closeout(
    tmp_path, monkeypatch, validation_result
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    terminal_slots = [
        {
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "terminal_status": "completed",
        }
        for slot in registration.slots
    ]

    class FakeLedger:
        run_lock_hash = RUN_LOCK_HASH

        def __init__(self):
            self.stop = None

        def snapshot(self):
            return {
                "all_slots_terminal": True,
                "global_stop": self.stop,
                "initialized": True,
                "terminal_slot_count": len(terminal_slots),
                "terminal_slots": terminal_slots,
            }

        def global_stop(self, *, reason):
            self.stop = {"reason": reason}

    ledger = FakeLedger()
    blocked = {"closeout": {"status": "blocked"}}
    calls = {}

    monkeypatch.setattr(module, "load_registration", lambda _path: registration)
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        lambda **_kwargs: ledger,
    )

    def validate_lock(**_kwargs):
        if isinstance(validation_result, Exception):
            raise validation_result
        return validation_result

    def finalize(registration_value, **kwargs):
        assert registration_value is registration
        calls.update(kwargs)
        return blocked

    monkeypatch.setattr(module, "validate_run_lock", validate_lock)
    monkeypatch.setattr(module, "finalize_registered_integrity_stop", finalize)
    monkeypatch.setattr(
        module,
        "collect_registered_session_evidence",
        lambda *_args, **_kwargs: pytest.fail("failed lock must not pool"),
    )

    result = module._finalize_gate_command(registration_path)

    assert result is blocked
    assert calls["run_lock_hash"] == RUN_LOCK_HASH
    assert calls["ledger_snapshot"]["global_stop"]["reason"].startswith(
        "run lock validation failed"
    )


def _structural_observation(slot, **extra):
    observation = {
        "candidate_legal_records": 4,
        "config_exists": True,
        "config_sha256": "1" * 64,
        "confirmed_records": 4,
        "handshake_attempt_exists": True,
        "handshake_attempt_sha256": "5" * 64,
        "handshake_ready_exists": True,
        "handshake_ready_sha256": "6" * 64,
        "handshake_release_exists": True,
        "handshake_release_sha256": "7" * 64,
        "isolation_verified": True,
        "manifest_exists": True,
        "manifest_hash": "2" * 64,
        "manifest_sha256": "3" * 64,
        "proposed_records": 5,
        "replay_valid_records": 4,
        "run_join_complete_count": 1,
        "session_id": slot.session_id,
        "slot_number": slot.slot_number,
        "trace_exists": True,
        "trace_sha256": "4" * 64,
    }
    observation.update(extra)
    return observation


def test_blinded_monitor_drops_outcome_and_policy_evaluation_fields(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    forbidden_values = {
        "victory": "SECRET_VICTORY",
        "floor_reached": "SECRET_FLOOR",
        "killed_by": "SECRET_KILLER",
        "target_weight": "SECRET_WEIGHT",
        "ess": "SECRET_ESS",
        "ope_estimate": "SECRET_OPE",
        "bootstrap": "SECRET_BOOTSTRAP",
        "influence": "SECRET_INFLUENCE",
        "policy_comparison": "SECRET_COMPARISON",
    }
    observation = _structural_observation(slot, **forbidden_values)

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[observation],
    )
    rendered_json = module.render_blinded_monitor_json(monitor)
    rendered_markdown = module.render_blinded_monitor_markdown(monitor)
    combined = rendered_json + rendered_markdown

    for field, value in forbidden_values.items():
        assert f'"{field}":' not in rendered_json
        assert value not in combined
    assert monitor["slots"][0]["confirmed_records"] == 4
    assert monitor["slots"][0]["lifecycle"] == "active"


def test_blinded_monitor_reports_only_structural_validity_and_process_exit(
    tmp_path,
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    ledger.finish_slot(
        1,
        process_exit_code=7,
        complete_trajectories=3,
        ended_unix_ns=300,
    )

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        run_lock_valid=True,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[_structural_observation(slot)],
    )

    assert monitor["registration_valid"] is True
    assert monitor["run_lock_valid"] is True
    assert monitor["slots"][0]["process_exit_code"] == 7
    assert "| 7 |" in module.render_blinded_monitor_markdown(monitor)

    blocked = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        run_lock_valid=False,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[_structural_observation(slot)],
    )
    assert blocked["integrity_valid"] is False
    assert "run_lock_invalid" in blocked["blockers"]


def test_blinded_monitor_reports_unlaunched_handshake_artifact_progress(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    module.write_slot_config_once(launch)
    attempt_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-attempt.json"
    )
    ready_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-ready.json"
    )
    release_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-release.json"
    )
    attempt_bytes = b'{"stage":"attempt"}\n'
    attempt_path.write_bytes(attempt_bytes)
    ledger.global_stop(reason="orphaned preclaim attempt", created_unix_ns=200)

    observations = module.collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
    )
    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )

    assert monitor["schema_version"] == (
        "noncombat-outcome-evidence-blinded-monitor-v2"
    )
    assert len(observations) == 1
    slot = monitor["slots"][0]
    assert slot["lifecycle"] == "unlaunched"
    assert slot["handshake_status"] == "attempted"
    assert slot["handshake_attempt_path"] == str(attempt_path.resolve())
    assert slot["handshake_attempt_exists"] is True
    assert slot["handshake_attempt_sha256"] == hashlib.sha256(
        attempt_bytes
    ).hexdigest()
    assert slot["handshake_ready_path"] == str(ready_path.resolve())
    assert slot["handshake_ready_exists"] is False
    assert slot["handshake_ready_sha256"] is None
    assert slot["handshake_release_path"] == str(release_path.resolve())
    assert slot["handshake_release_exists"] is False
    assert slot["handshake_release_sha256"] is None
    rendered = module.render_blinded_monitor_json(monitor)
    assert '"victory":' not in rendered
    assert '"ope_estimate":' not in rendered
    assert "| attempted |" in module.render_blinded_monitor_markdown(monitor)


def test_blinded_monitor_is_byte_stable_under_observation_reordering(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    for slot in registration.slots[:2]:
        ledger.start_slot(
            slot.slot_number,
            slot.session_id,
            started_unix_ns=slot.slot_number * 100,
        )
        ledger.finish_slot(
            slot.slot_number,
            process_exit_code=0,
            complete_trajectories=25,
            ended_unix_ns=slot.slot_number * 100 + 1,
        )
    observations = [
        _structural_observation(registration.slots[0]),
        _structural_observation(registration.slots[1]),
    ]

    first = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )
    second = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=list(reversed(observations)),
    )

    assert module.render_blinded_monitor_json(first) == (
        module.render_blinded_monitor_json(second)
    )
    assert module.render_blinded_monitor_markdown(first) == (
        module.render_blinded_monitor_markdown(second)
    )


@pytest.mark.parametrize("failure_mode", ["missing", "malformed", "unregistered"])
def test_blinded_monitor_fails_closed_on_structural_input_errors(
    tmp_path, failure_mode
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    if failure_mode == "missing":
        observations = []
    elif failure_mode == "malformed":
        observations = [_structural_observation(slot, confirmed_records="four")]
    else:
        observations = [
            _structural_observation(
                slot,
                slot_number=99,
                session_id="unregistered-session",
            )
        ]

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )

    assert monitor["integrity_valid"] is False
    assert monitor["blockers"]
    assert "four" not in module.render_blinded_monitor_json(monitor)


def test_blinded_monitor_redacts_global_stop_reason(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    ledger.global_stop(
        reason="victory=SECRET_STOP_OUTCOME",
        created_unix_ns=200,
    )

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[],
    )
    rendered = module.render_blinded_monitor_json(monitor)

    assert monitor["global_integrity_stop"] is True
    assert monitor["integrity_valid"] is False
    assert "SECRET_STOP_OUTCOME" not in rendered
    assert "victory" not in rendered


def test_blinded_monitor_artifacts_are_atomically_replaced_with_exact_bytes(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[],
    )
    json_path = tmp_path / "monitor.json"
    markdown_path = tmp_path / "monitor.md"
    json_path.write_text("stale", encoding="utf-8")
    markdown_path.write_text("stale", encoding="utf-8")

    result = module.write_blinded_monitor_artifacts(
        monitor,
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert result == {
        "json_path": str(json_path.resolve()),
        "markdown_path": str(markdown_path.resolve()),
    }
    assert json_path.read_text(encoding="utf-8") == (
        module.render_blinded_monitor_json(monitor)
    )
    assert markdown_path.read_text(encoding="utf-8") == (
        module.render_blinded_monitor_markdown(monitor)
    )


def test_structural_scanner_fails_closed_on_malformed_artifact_without_echo(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    Path(slot.config_path).parent.mkdir(parents=True, exist_ok=True)
    Path(slot.config_path).write_text(
        '{"victory":"SECRET_ARTIFACT_OUTCOME"}\n',
        encoding="utf-8",
    )

    observations = module.collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
    )
    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )
    rendered = module.render_blinded_monitor_json(monitor)

    assert monitor["integrity_valid"] is False
    assert "SECRET_ARTIFACT_OUTCOME" not in rendered
    assert '"victory":' not in rendered


def test_manifest_pre_isolation_matches_registered_run_lock_semantically(tmp_path):
    module = _module()
    communication_path = str((tmp_path / "config.properties").resolve())
    checkpoint_path = str((tmp_path / "checkpoints" / "model.pth").resolve())
    run_lock = {
        "checkpoints": {
            "files": [{"path": checkpoint_path, "sha256": "1" * 64, "size": 7}],
            "patterns": ["*.pth"],
            "root": str((tmp_path / "checkpoints").resolve()),
        },
        "communication_mod": {
            "path": communication_path,
            "semantic_sha256": "2" * 64,
        },
    }
    manifest = {
        "pre_session_isolation_hashes": {
            checkpoint_path: {
                "exists": True,
                "is_file": True,
                "mtime_ns": 123,
                "sha256": "1" * 64,
                "size": 7,
            },
            communication_path: {
                "exists": True,
                "is_file": True,
                "mtime_ns": 456,
                "semantic_sha256": "2" * 64,
                "sha256": "3" * 64,
                "size": 99,
            },
        }
    }

    assert module.manifest_isolation_matches_run_lock(manifest, run_lock) is True
    manifest["pre_session_isolation_hashes"][checkpoint_path]["sha256"] = "4" * 64
    assert module.manifest_isolation_matches_run_lock(manifest, run_lock) is False


def test_conservative_run_join_count_requires_unique_nearby_run_files():
    module = _module()

    assert module.conservative_run_join_count(
        marker_timestamps=[100, 200],
        run_timestamps=[97, 198],
        tolerance_seconds=10,
    ) == 2
    assert module.conservative_run_join_count(
        marker_timestamps=[100, 200],
        run_timestamps=[98, 99, 198],
        tolerance_seconds=10,
    ) == 1


def test_structural_scanner_joins_only_registered_slot_marker_slice(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")
    run_dir = tmp_path / "runs" / "IRONCLAD"
    run_dir.mkdir()

    def process_runner(_launch):
        with marker_path.open("a", encoding="utf-8") as handle:
            handle.write("100\n200\n")
        (run_dir / "97.run").write_text("{}", encoding="utf-8")
        (run_dir / "198.run").write_text("{}", encoding="utf-8")
        (run_dir / "10.run").write_text("{}", encoding="utf-8")
        return 0

    module.execute_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_runner=process_runner,
        started_unix_ns=200,
        ended_unix_ns=300,
    )

    observations = module.collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
    )
    assert observations[0]["run_join_complete_count"] == 2


def test_ledger_rejects_rehashed_marker_bound_tamper(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n", encoding="utf-8")

    def process_runner(_launch):
        with marker_path.open("a", encoding="utf-8") as handle:
            handle.write("20\n")
        return 0

    module.execute_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_runner=process_runner,
        started_unix_ns=200,
        ended_unix_ns=300,
    )
    records = [
        json.loads(line)
        for line in ledger.path.read_text(encoding="utf-8").splitlines()
    ]
    records[-1]["payload"]["marker_end_count"] = 99
    records[-1]["record_hash"] = module._record_hash(records[-1])
    ledger.path.write_text(
        "".join(module._canonical_json(record) + "\n" for record in records),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(ledger.error_type, match="marker"):
        ledger.snapshot()


def test_no_game_dry_run_enumerates_exact_registered_24_slot_plan(
    tmp_path, monkeypatch
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    monkeypatch.setattr(
        module.subprocess,
        "check_output",
        lambda *_args, **_kwargs: SOURCE_COMMIT,
    )
    monkeypatch.setattr(
        module.subprocess,
        "call",
        lambda *_args, **_kwargs: pytest.fail("dry-run launched a child process"),
    )

    plan = module._dry_run_command(registration_path)

    assert plan["launch_count"] == 24
    assert [launch["slot_number"] for launch in plan["launches"]] == list(
        range(1, 25)
    )
    assert len({launch["session_id"] for launch in plan["launches"]}) == 24
    assert len({launch["config_path"] for launch in plan["launches"]}) == 24
    for expected_slot, launch in enumerate(plan["launches"], start=1):
        assert launch["config_record"]["seed"] == SEED_BASE + expected_slot
        assert launch["config_record"]["category_rates_bps"] == {
            "card_reward": 300,
            "shop": 1000,
        }
        assert launch["config_record"]["per_run_alternative_budget"] == 2
        assert launch["environment"] == {
            "STS_NONCOMBAT_EXPLORATION_CONFIG": launch["config_path"]
        }
        session_id = launch["session_id"]
        artifact_root = Path(registration.artifact_root)
        assert launch["handshake"] == {
            "attempt_path": str(
                (artifact_root / f"{session_id}-communication-attempt.json").resolve()
            ),
            "protocol_version": "noncombat-outcome-evidence-handshake-v1",
            "readiness_timeout_seconds": 120,
            "ready_path": str(
                (artifact_root / f"{session_id}-communication-ready.json").resolve()
            ),
            "release_path": str(
                (artifact_root / f"{session_id}-communication-release.json").resolve()
            ),
            "release_timeout_seconds": 10,
        }
        assert "--max-games" in launch["command"]
        assert launch["command"][launch["command"].index("--max-games") + 1] == "25"
        assert "--eval" in launch["command"]
        assert "--train" not in launch["command"]
        assert "--model" not in launch["command"]


def test_existing_study_dry_run_revalidates_lock_against_ledger(
    tmp_path, monkeypatch
):
    module = _module()
    registration, run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    artifact_root.mkdir(parents=True)
    (artifact_root / "run-lock.json").write_text(
        json.dumps(run_lock),
        encoding="utf-8",
    )
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)
    validation_calls = []

    def validate_lock(**kwargs):
        validation_calls.append(kwargs)
        return run_lock

    monkeypatch.setattr(module, "validate_run_lock", validate_lock)
    monkeypatch.setattr(
        module.subprocess,
        "call",
        lambda *_args, **_kwargs: pytest.fail("dry-run launched a child process"),
    )

    plan = module._dry_run_command(registration_path)

    assert plan["launch_count"] == 24
    assert len(validation_calls) == 1
    assert ledger.snapshot()["global_stop"] is None


def test_existing_study_dry_run_missing_lock_records_global_stop(
    tmp_path, monkeypatch
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)
    monkeypatch.setattr(
        module.subprocess,
        "call",
        lambda *_args, **_kwargs: pytest.fail("dry-run launched a child process"),
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="run lock"):
        module._dry_run_command(registration_path)

    assert ledger.snapshot()["global_stop"] is not None


def test_monitor_records_malformed_run_lock_and_writes_blocked_artifact(tmp_path):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    artifact_root.mkdir(parents=True)
    (artifact_root / "run-lock.json").write_text("{malformed", encoding="utf-8")
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)

    monitor = module._monitor_command(registration_path)

    assert monitor["phase"] == "blocked"
    assert monitor["run_lock_valid"] is False
    assert "run_lock_invalid" in monitor["blockers"]
    assert ledger.snapshot()["global_stop"] is not None
    assert (artifact_root / "blinded-monitor.json").is_file()
    assert (artifact_root / "blinded-monitor.md").is_file()


def test_monitor_keeps_ledger_binding_when_run_lock_hash_is_replaced(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    artifact_root.mkdir(parents=True)
    replaced = dict(run_lock)
    replaced["run_lock_hash"] = "c" * 64
    (artifact_root / "run-lock.json").write_text(
        json.dumps(replaced),
        encoding="utf-8",
    )
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)

    monitor = module._monitor_command(registration_path)

    assert monitor["run_lock_valid"] is False
    assert monitor["run_lock_hash"] == RUN_LOCK_HASH
