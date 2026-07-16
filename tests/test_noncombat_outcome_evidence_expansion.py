import importlib
import json
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
SEED_BASE = 2_026_071_500
WINDOWS_PYTHON = Path(r"D:\anaconda\envs\stsai\python.exe")
REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ARTIFACT_ROOT = Path(
    r"D:\SteamLibrary\steamapps\common\SlayTheSpire"
    r"\noncombat_outcome_evidence_expansion_20260715"
)
COMMITTED_REGISTRATION_PATH = (
    REPO_ROOT
    / "reports"
    / "noncombat_outcome_evidence_expansion_20260715_registration.json"
)


def _module():
    try:
        return importlib.import_module(
            "analysis_scripts.noncombat_outcome_evidence_expansion"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"outcome evidence expansion module is missing: {exc}")


def _registration(tmp_path):
    module = _module()
    return module.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "repo",
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
    )


def _record(tmp_path):
    return _registration(tmp_path).to_record()


def test_registration_fixes_exact_schedule_behavior_and_command(tmp_path):
    registration = _registration(tmp_path)
    record = registration.to_record()

    assert record["schema_version"] == "noncombat-outcome-evidence-registration-v2"
    assert record["study_id"] == STUDY_ID
    assert record["slot_count"] == 24
    assert record["games_per_slot"] == 25
    assert record["scheduled_attempts"] == 600
    assert record["seed_base"] == SEED_BASE
    assert record["behavior"] == {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "executable_alternatives": {
            "card_reward": "card_reward:skip",
            "shop": "shop:leave",
        },
        "per_run_alternative_budget": 2,
        "shadow_only_categories": ["event", "route"],
    }
    assert record["command"] == {
        "arguments": [
            "--agent",
            "combat_rl",
            "--elite-route",
            "conservative",
            "--max-games",
            "25",
            "--ascension",
            "0",
            "--rl-version",
            "v2",
            "--eval",
        ],
        "main_path": str((tmp_path / "repo" / "main.py").resolve()),
        "python_executable": str(WINDOWS_PYTHON),
    }
    assert record["thresholds"] == {
        "maximum_normalized_weight": {"denominator": 20, "numerator": 1},
        "minimum_arm_decisions_per_category": 50,
        "minimum_complete_trajectories": 575,
        "minimum_ess_fraction": {"denominator": 2, "numerator": 1},
        "minimum_nonzero_weight_fraction": {"denominator": 2, "numerator": 1},
        "minimum_supported_victories": 3,
    }
    assert record["analysis_rules"] == {
        "bootstrap_confidence_level": {"denominator": 100, "numerator": 95},
        "bootstrap_replicates": 10_000,
        "bootstrap_seed": f"{STUDY_ID}:current-deterministic-bootstrap-v1",
        "calibration_artifact_relative_path": (
            "reports/noncombat_ope_estimator_calibration_20260714.json"
        ),
        "target_policy_mode": "current_deterministic",
    }
    assert record["integrity_rules"]["communication_handshake"] == {
        "attempt_suffix": "-communication-attempt.json",
        "orphaned_attempt_global_stop": True,
        "protocol_version": "noncombat-outcome-evidence-handshake-v1",
        "readiness_timeout_seconds": 30,
        "ready_suffix": "-communication-ready.json",
        "release_suffix": "-communication-release.json",
        "release_timeout_seconds": 10,
        "required_before_slot_claim": True,
    }
    assert record["integrity_rules"]["implementation_paths"][-1] == (
        "spirecomm/communication/study_handshake.py"
    )
    assert record["registration_hash"] is not None
    assert len(record["registration_hash"]) == 64

    with pytest.raises(FrozenInstanceError):
        registration.study_id = "changed"


def test_registration_rejects_changed_production_analysis_contract(tmp_path):
    module = _module()
    record = _record(tmp_path)
    record["analysis_rules"]["bootstrap_replicates"] = 9_999
    record["registration_hash"] = module.canonical_registration_hash(record)

    with pytest.raises(
        module.OutcomeEvidenceRegistrationError,
        match="analysis_rules",
    ):
        module.validate_registration(record)


def test_registration_slots_have_fixed_ids_seeds_and_distinct_absolute_paths(tmp_path):
    record = _record(tmp_path)
    slots = record["slots"]

    assert len(slots) == 24
    assert slots[0] == {
        "config_path": str(
            (tmp_path / "study" / f"{STUDY_ID}-s01-config.json").resolve()
        ),
        "manifest_path": str(
            (tmp_path / "study" / f"{STUDY_ID}-s01-manifest.json").resolve()
        ),
        "seed": SEED_BASE + 1,
        "session_id": f"{STUDY_ID}-s01",
        "slot_number": 1,
        "trace_path": str(
            (tmp_path / "study" / f"{STUDY_ID}-s01-trace.jsonl").resolve()
        ),
    }
    assert slots[-1]["slot_number"] == 24
    assert slots[-1]["session_id"] == f"{STUDY_ID}-s24"
    assert slots[-1]["seed"] == SEED_BASE + 24
    assert len(
        {
            path
            for slot in slots
            for path in (
                slot["config_path"],
                slot["manifest_path"],
                slot["trace_path"],
            )
        }
    ) == 72


def test_registration_render_and_load_are_byte_stable(tmp_path):
    module = _module()
    registration = _registration(tmp_path)
    first = module.render_registration_json(registration)
    second = module.render_registration_json(
        module.validate_registration(registration.to_record())
    )

    assert first == second
    assert first.endswith("\n")
    assert "\r" not in first

    path = tmp_path / "registration.json"
    path.write_text(first, encoding="utf-8", newline="")
    loaded = module.load_registration(path)
    assert loaded == registration
    assert module.render_registration_json(loaded) == first


def test_committed_production_registration_matches_canonical_bytes():
    module = _module()
    expected = module.build_registration(
        study_id=STUDY_ID,
        artifact_root=PRODUCTION_ARTIFACT_ROOT,
        repo_root=REPO_ROOT,
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        schema_version=module.LEGACY_REGISTRATION_SCHEMA_VERSION,
    )
    expected_bytes = module.render_registration_json(expected).encode("utf-8")
    actual_bytes = COMMITTED_REGISTRATION_PATH.read_bytes()

    assert actual_bytes == expected_bytes
    assert module.load_registration(COMMITTED_REGISTRATION_PATH) == expected


def test_legacy_registration_is_read_only_and_byte_distinct_from_v2(tmp_path):
    module = _module()
    legacy = module.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "repo",
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        schema_version=module.LEGACY_REGISTRATION_SCHEMA_VERSION,
    )
    current = _registration(tmp_path)

    legacy_record = legacy.to_record()
    assert legacy_record["schema_version"] == (
        "noncombat-outcome-evidence-registration-v1"
    )
    assert "communication_handshake" not in legacy_record["integrity_rules"]
    assert legacy_record["integrity_rules"]["implementation_paths"] == list(
        module.LEGACY_RUN_LOCK_IMPLEMENTATION_PATHS
    )
    assert module.validate_registration(legacy_record) == legacy
    assert module.render_registration_json(legacy) != module.render_registration_json(
        current
    )


def test_launch_guard_accepts_v2_and_rejects_v1(tmp_path):
    module = _module()
    current = _registration(tmp_path)
    legacy = module.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "legacy-study",
        repo_root=tmp_path / "repo",
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        schema_version=module.LEGACY_REGISTRATION_SCHEMA_VERSION,
    )

    assert module.require_launchable_registration(current) == current
    with pytest.raises(
        module.OutcomeEvidenceRegistrationError,
        match="v1 registration is read-only",
    ):
        module.require_launchable_registration(legacy)


def test_run_lock_controlled_paths_are_forced_to_lf():
    module = _module()
    controlled_paths = [
        *module.RUN_LOCK_IMPLEMENTATION_PATHS,
        "reports/noncombat_outcome_evidence_expansion_20260715_registration.json",
        "reports/noncombat_outcome_evidence_expansion_20260715_registration_review.md",
    ]

    completed = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", *controlled_paths],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    observed = {}
    for line in completed.stdout.splitlines():
        path, attribute, value = line.split(": ", 2)
        observed[(path, attribute)] = value
    for path in controlled_paths:
        assert observed[(path, "text")] == "set"
        assert observed[(path, "eol")] == "lf"


def test_registration_load_rejects_duplicate_json_keys(tmp_path):
    module = _module()
    path = tmp_path / "registration.json"
    path.write_text(
        '{"schema_version":"noncombat-outcome-evidence-registration-v1",'
        '"schema_version":"duplicate"}\n',
        encoding="utf-8",
    )

    with pytest.raises(module.OutcomeEvidenceRegistrationError, match="duplicate"):
        module.load_registration(path)


def test_registration_rejects_hash_tampering_and_unknown_fields(tmp_path):
    module = _module()
    tampered_hash = _record(tmp_path)
    tampered_hash["registration_hash"] = "0" * 64

    with pytest.raises(module.OutcomeEvidenceRegistrationError, match="hash"):
        module.validate_registration(tampered_hash)

    unknown = _record(tmp_path)
    unknown["unexpected"] = True
    with pytest.raises(module.OutcomeEvidenceRegistrationError, match="fields"):
        module.validate_registration(unknown)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda record: record["behavior"]["category_rates_bps"].update(
                card_reward=301
            ),
            "card_reward",
        ),
        (
            lambda record: record["behavior"].update(
                enabled_categories=["card_reward", "shop", "event"]
            ),
            "enabled_categories",
        ),
        (
            lambda record: record["behavior"].update(
                per_run_alternative_budget=1
            ),
            "alternative budget",
        ),
        (
            lambda record: record["thresholds"].update(
                minimum_complete_trajectories=574
            ),
            "minimum_complete_trajectories",
        ),
        (
            lambda record: record["slots"][1].update(slot_number=1),
            "slot_number",
        ),
        (
            lambda record: record["slots"][1].update(
                session_id=record["slots"][0]["session_id"]
            ),
            "session_id",
        ),
    ],
)
def test_registration_rejects_changed_fixed_contract(tmp_path, mutate, message):
    module = _module()
    record = _record(tmp_path)
    mutate(record)

    with pytest.raises(module.OutcomeEvidenceRegistrationError, match=message):
        module.validate_registration(record)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("slot_count",), True, "slot_count"),
        (("games_per_slot",), 25.0, "games_per_slot"),
        (("seed_base",), str(SEED_BASE), "seed_base"),
        (
            ("thresholds", "minimum_supported_victories"),
            3.0,
            "minimum_supported_victories",
        ),
        (("slots", 0, "seed"), True, "seed"),
    ],
)
def test_registration_rejects_coercible_non_integer_exact_fields(
    tmp_path, path, value, message
):
    module = _module()
    record = _record(tmp_path)
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(module.OutcomeEvidenceRegistrationError, match=message):
        module.validate_registration(record)


def test_registration_json_is_canonical_independent_of_input_key_order(tmp_path):
    module = _module()
    record = _record(tmp_path)
    reordered = json.loads(json.dumps(record, sort_keys=False))
    reordered = {key: reordered[key] for key in reversed(tuple(reordered))}

    validated = module.validate_registration(reordered)
    assert module.render_registration_json(validated) == module.render_registration_json(
        _registration(tmp_path)
    )


def _run_lock_fixture(tmp_path, monkeypatch, *, python_executable=WINDOWS_PYTHON):
    module = _module()
    repo_root = tmp_path / "repo"
    artifact_root = tmp_path / "study"
    communication_config_path = tmp_path / "config.properties"
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    registration = module.build_registration(
        study_id=STUDY_ID,
        artifact_root=artifact_root,
        repo_root=repo_root,
        seed_base=SEED_BASE,
        python_executable=python_executable,
        communication_config_path=communication_config_path,
        checkpoint_root=checkpoint_root,
    )
    registration_path = repo_root / "reports" / "registration.json"
    registration_path.parent.mkdir(parents=True)
    registration_path.write_text(
        module.render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )

    for relative_path in module.RUN_LOCK_IMPLEMENTATION_PATHS:
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"implementation:{relative_path}\n", encoding="utf-8", newline=""
        )

    communication_config_path.write_text(
        "command=python main.py\nclientTimeout=30\n",
        encoding="iso-8859-1",
    )
    checkpoint_path = checkpoint_root / "rl_combat_model_ep5.pth"
    checkpoint_path.write_bytes(b"checkpoint-v1")
    command_record = registration.to_record()["command"]
    child_command = [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    source_state = module.GitSourceSnapshot(
        commit="a" * 40,
        tracked_clean=True,
        tracked_status="",
    )
    monkeypatch.setattr(module, "_inspect_git_source", lambda _root: source_state)
    monkeypatch.setattr(module, "_git_repository_root", lambda root: root.resolve())
    monkeypatch.setattr(
        module,
        "_head_blob_bytes",
        lambda root, relative_path: (root / relative_path).read_bytes(),
    )
    return {
        "module": module,
        "registration_path": registration_path,
        "lock_path": artifact_root / "run-lock.json",
        "repo_root": repo_root,
        "child_command": child_command,
        "communication_config_path": communication_config_path,
        "checkpoint_root": checkpoint_root,
        "checkpoint_paths": [checkpoint_path],
    }


def _create_run_lock(inputs):
    module = inputs["module"]
    return module.create_run_lock(
        registration_path=inputs["registration_path"],
        lock_path=inputs["lock_path"],
        repo_root=inputs["repo_root"],
        child_command=inputs["child_command"],
        created_unix_ns=1_750_000_000_000_000_000,
    )


def _validate_run_lock(inputs):
    module = inputs["module"]
    return module.validate_run_lock(
        lock_path=inputs["lock_path"],
        registration_path=inputs["registration_path"],
        repo_root=inputs["repo_root"],
        child_command=inputs["child_command"],
    )


def test_run_lock_rejects_tracked_dirty_start(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    module = inputs["module"]
    monkeypatch.setattr(
        module,
        "_inspect_git_source",
        lambda _root: module.GitSourceSnapshot(
            commit="a" * 40,
            tracked_clean=False,
            tracked_status=" M main.py",
        ),
    )

    with pytest.raises(module.OutcomeEvidenceRunLockError, match="tracked.*dirty"):
        _create_run_lock(inputs)
    assert not inputs["lock_path"].exists()


def test_run_lock_rejects_registration_byte_tampering(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    _create_run_lock(inputs)
    with inputs["registration_path"].open("a", encoding="utf-8", newline="") as handle:
        handle.write("\n")

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="registration bytes",
    ):
        _validate_run_lock(inputs)


def test_run_lock_rejects_unsupported_python_path(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(
        tmp_path,
        monkeypatch,
        python_executable=tmp_path / "python.exe",
    )

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="Windows Python",
    ):
        _create_run_lock(inputs)


def test_run_lock_rejects_command_drift(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    inputs["child_command"][-1] = "--train"

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="command",
    ):
        _create_run_lock(inputs)


def test_run_lock_rejects_source_file_hash_drift(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    _create_run_lock(inputs)
    source_path = (
        inputs["repo_root"] / inputs["module"].RUN_LOCK_IMPLEMENTATION_PATHS[0]
    )
    source_path.write_text("changed\n", encoding="utf-8")

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="source file",
    ):
        _validate_run_lock(inputs)


def test_run_lock_rejects_filter_equivalent_raw_byte_drift_before_publish(
    tmp_path, monkeypatch
):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    module = inputs["module"]
    relative_path = Path(module.RUN_LOCK_IMPLEMENTATION_PATHS[0])
    source_path = inputs["repo_root"] / relative_path
    source_path.write_bytes(source_path.read_bytes().replace(b"\n", b"\r\n"))

    def head_blob_bytes(repo_root, candidate_path):
        working_bytes = (repo_root / candidate_path).read_bytes()
        if candidate_path == relative_path:
            return working_bytes.replace(b"\r\n", b"\n")
        return working_bytes

    monkeypatch.setattr(module, "_head_blob_bytes", head_blob_bytes)
    monkeypatch.setattr(
        module,
        "_filtered_working_blob_oid",
        lambda *_args: "f" * 40,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_git_blob_oid",
        lambda *_args: "f" * 40,
        raising=False,
    )

    with pytest.raises(
        module.OutcomeEvidenceRunLockError,
        match="implementation file.*bytes differ from HEAD",
    ):
        _create_run_lock(inputs)
    assert not inputs["lock_path"].exists()


def test_run_lock_rejects_communication_mod_semantic_drift(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    _create_run_lock(inputs)
    inputs["communication_config_path"].write_text(
        "clientTimeout=31\ncommand=python main.py\n",
        encoding="iso-8859-1",
    )

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="CommunicationMod",
    ):
        _validate_run_lock(inputs)


def test_run_lock_ignores_communication_mod_comments_and_order(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    created = _create_run_lock(inputs)
    inputs["communication_config_path"].write_text(
        "# startup rewrite\nclientTimeout=30\ncommand=python main.py\n",
        encoding="iso-8859-1",
    )

    assert _validate_run_lock(inputs) == created


def test_run_lock_rejects_checkpoint_drift(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    _create_run_lock(inputs)
    inputs["checkpoint_paths"][0].write_bytes(b"checkpoint-v2")

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="checkpoint",
    ):
        _validate_run_lock(inputs)


def test_run_lock_rejects_added_checkpoint_in_registered_inventory(
    tmp_path, monkeypatch
):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    _create_run_lock(inputs)
    (inputs["checkpoint_root"] / "rl_combat_model_ep6.pth").write_bytes(
        b"unexpected-checkpoint"
    )

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="checkpoint",
    ):
        _validate_run_lock(inputs)


def test_run_lock_is_create_once_for_one_study(tmp_path, monkeypatch):
    inputs = _run_lock_fixture(tmp_path, monkeypatch)
    _create_run_lock(inputs)

    with pytest.raises(
        inputs["module"].OutcomeEvidenceRunLockError,
        match="already exists",
    ):
        _create_run_lock(inputs)


def _git(repo_root, *arguments):
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "untracked_controlled_path",
    ["reports/registration.json", "analysis_scripts/noncombat_exploration_evidence.py"],
)
def test_run_lock_rejects_untracked_controlled_file_in_real_git_repo(
    tmp_path, untracked_controlled_path
):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    artifact_root = tmp_path / "study"
    communication_config_path = tmp_path / "config.properties"
    communication_config_path.write_text("command=python main.py\n", encoding="iso-8859-1")
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    (checkpoint_root / "rl_combat_model_ep5.pth").write_bytes(b"checkpoint")
    registration = module.build_registration(
        study_id=STUDY_ID,
        artifact_root=artifact_root,
        repo_root=repo_root,
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=communication_config_path,
        checkpoint_root=checkpoint_root,
    )
    for relative_path in module.RUN_LOCK_IMPLEMENTATION_PATHS:
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"implementation:{relative_path}\n", encoding="utf-8", newline=""
        )
    registration_path = repo_root / "reports" / "registration.json"
    registration_path.parent.mkdir(parents=True)
    registration_path.write_text(
        module.render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "codex@example.invalid")
    _git(repo_root, "config", "user.name", "Codex Test")
    for relative_path in module.RUN_LOCK_IMPLEMENTATION_PATHS:
        if relative_path != untracked_controlled_path:
            _git(repo_root, "add", "--", relative_path)
    if untracked_controlled_path != "reports/registration.json":
        _git(repo_root, "add", "--", "reports/registration.json")
    _git(repo_root, "commit", "-m", "commit all but one controlled file")
    command_record = registration.to_record()["command"]
    child_command = [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]

    message = (
        "registration.*committed|committed.*registration"
        if untracked_controlled_path == "reports/registration.json"
        else "implementation file.*committed"
    )
    with pytest.raises(module.OutcomeEvidenceRunLockError, match=message):
        module.create_run_lock(
            registration_path=registration_path,
            lock_path=artifact_root / "run-lock.json",
            repo_root=repo_root,
            child_command=child_command,
            created_unix_ns=1_750_000_000_000_000_000,
        )
