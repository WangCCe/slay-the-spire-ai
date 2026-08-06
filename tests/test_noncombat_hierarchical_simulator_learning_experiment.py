from __future__ import annotations

import copy
import gzip
import hashlib
import importlib
import json
import math
import platform
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import analysis_scripts.noncombat_hierarchical_simulator_learning_experiment as experiment


ROOT = Path(__file__).resolve().parents[1]
PREIMPLEMENTATION = (
    ROOT
    / "reports/noncombat_hierarchical_simulator_learning_successor_20260806_preimplementation.json"
)


def _git_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def test_experiment_contract_freezes_the_proposed_source_only_boundary():
    contract = experiment.experiment_contract()

    assert contract["algorithm"] == {
        "conditional_entropy_coefficient": 0.01,
        "discount": 1.0,
        "family_entropy_coefficient": 0.01,
        "gradient_norm_ceiling": 1.0,
        "learning_rate": 0.001,
        "normalized_returns": True,
        "optimizer": "adam",
        "optimizer_amsgrad": False,
        "optimizer_betas": [0.9, 0.999],
        "optimizer_capturable": False,
        "optimizer_differentiable": False,
        "optimizer_eps": 1e-8,
        "optimizer_foreach": None,
        "optimizer_fused": None,
        "optimizer_maximize": False,
        "optimizer_weight_decay": 0.0,
        "sampling": "family-first-then-conditional-v1",
    }
    assert contract["cohorts"] == {
        "canary_count": 128,
        "holdout_count": 512,
        "selection": "tracked-fixed-tree-ascending-v1",
        "train_count": 1024,
        "train_passes": 4,
    }
    assert contract["environment"] == {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "ascension": 0,
    }
    assert contract["evaluation"]["selection"] == "unique-raw-score-maximum-v1"
    assert contract["evaluation"]["tie_handling"] == "fail-closed"
    assert contract["limits"] == {
        "episodes_per_update": 64,
        "max_decisions_per_episode": 500,
        "max_evaluation_episodes": 2560,
        "max_optimizer_updates": 64,
        "max_total_episodes": 6656,
        "max_training_episodes": 4096,
        "max_wall_seconds": 28800.0,
    }
    assert contract["training_collapse_gate"] == {
        "categories": ["card_reward", "shop"],
        "minimum_multi_family_decisions": 64,
        "required_singleton_max_family_rate": 1.0,
        "window_chunks": 4,
    }
    assert contract["canary_family_gate"] == {
        "categories": ["card_reward", "shop"],
        "maximum_selected_family_rate": 0.95,
        "minimum_multi_family_decisions": 32,
        "minimum_selected_families": 2,
    }
    assert contract["authority"] == experiment.registration_authority()
    assert set(contract["authority"].values()) == {False}


def test_preimplementation_record_is_canonical_and_replayable_from_git():
    raw = PREIMPLEMENTATION.read_bytes()
    record = json.loads(raw)

    assert raw == experiment.canonical_json_bytes(record)
    assert experiment.validate_preimplementation_record(record, ROOT) == record
    assert record["planning"]["commit"] == experiment.PLANNING_COMMIT
    assert set(record["authority"].values()) == {False}
    assert record["contract"]["source_only"] is True
    assert record["contract"]["cohorts_materialized"] is False
    assert record["contract"]["native_loaded"] is False
    assert record["contract"]["seed_accessed"] is False
    assert record["contract"]["training_started"] is False
    assert record["planned_source_files"] == list(experiment.PLANNED_SOURCE_FILES)

    for section in (record["evidence"], record["planning"]["files"]):
        for binding in section.values():
            payload = _git_blob(record["planning"]["commit"], binding["path"])
            assert len(payload) == binding["size_bytes"]
            assert hashlib.sha256(payload).hexdigest() == binding["sha256"]


def test_preimplementation_builder_reproduces_the_checked_in_record():
    expected = json.loads(PREIMPLEMENTATION.read_bytes())

    assert experiment.build_preimplementation_record(ROOT) == expected


def test_preimplementation_validation_rejects_evidence_drift():
    record = json.loads(PREIMPLEMENTATION.read_bytes())
    changed = copy.deepcopy(record)
    changed["evidence"]["consumed_runner"]["sha256"] = "0" * 64

    with pytest.raises(experiment.ExperimentBlocked, match="evidence.*mismatch"):
        experiment.validate_preimplementation_record(changed, ROOT)


def test_preimplementation_publication_is_write_once(tmp_path):
    record = experiment.build_preimplementation_record(ROOT)
    output = tmp_path / "preimplementation.json"

    assert experiment.publish_preimplementation_record(record, output) == output
    assert output.read_bytes() == experiment.canonical_json_bytes(record)

    with pytest.raises(experiment.ExperimentBlocked, match="already exists"):
        experiment.publish_preimplementation_record(record, output)


def test_source_only_control_imports_no_torch_or_native():
    source = (
        "import builtins,json,sys;"
        "original=builtins.__import__;"
        "blocked={'torch','sts_lightspeed_noncombat_adapter'};"
        "builtins.__import__=lambda name,*a,**k: "
        "(_ for _ in ()).throw(RuntimeError('blocked '+name)) "
        "if name.split('.')[0] in blocked else original(name,*a,**k);"
        "import analysis_scripts.noncombat_hierarchical_simulator_learning_experiment as control;"
        "control.current_runtime_identity();"
        "print(json.dumps({'torch':'torch' in sys.modules,"
        "'native':'sts_lightspeed_noncombat_adapter' in sys.modules},sort_keys=True))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {"native": False, "torch": False}


def test_cli_freezes_source_only_commands_and_exact_execution_command():
    parser = experiment.build_parser()
    for command in (
        "preimplementation",
        "inventory",
        "register",
        "registration-preflight",
        "authorize",
        "preflight",
        "execute",
    ):
        with pytest.raises(SystemExit) as result:
            parser.parse_args([command, "--help"])
        assert result.value.code == 0

    registration = _synthetic_registration()
    command = experiment.registered_execution_command(
        registration,
        repo_root=ROOT,
        registration_path=ROOT / experiment.DEFAULT_REGISTRATION_PATH,
        authorization_path=ROOT / experiment.DEFAULT_AUTHORIZATION_PATH,
        output_dir=ROOT / experiment.DEFAULT_OUTPUT_DIRECTORY,
    )

    assert command == [
        registration["runtime_identity"]["executable"],
        (ROOT / experiment.PLANNED_SOURCE_FILES[0]).resolve().as_posix(),
        "execute",
        "--repo-root",
        ROOT.resolve().as_posix(),
        "--registration",
        (ROOT / experiment.DEFAULT_REGISTRATION_PATH).resolve().as_posix(),
        "--authorization",
        (ROOT / experiment.DEFAULT_AUTHORIZATION_PATH).resolve().as_posix(),
        "--output-dir",
        (ROOT / experiment.DEFAULT_OUTPUT_DIRECTORY).resolve().as_posix(),
    ]


def test_execute_never_loads_dependencies_when_source_preflight_fails(
    tmp_path, monkeypatch
):
    registration = _synthetic_registration()
    command = experiment.registered_execution_command(
        registration,
        repo_root=ROOT,
        registration_path=ROOT / experiment.DEFAULT_REGISTRATION_PATH,
        authorization_path=ROOT / experiment.DEFAULT_AUTHORIZATION_PATH,
        output_dir=ROOT / experiment.DEFAULT_OUTPUT_DIRECTORY,
    )
    authorization = _synthetic_authorization(registration, command)
    touched = []
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            experiment.ExperimentBlocked("synthetic preflight failure")
        ),
    )

    with pytest.raises(experiment.ExperimentBlocked, match="preflight failure"):
        experiment.execute_authorized_experiment(
            repo_root=ROOT,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            output_dir=tmp_path / "must-not-exist",
            dependency_loader=lambda value: touched.append(value),
        )

    assert touched == []
    assert not (tmp_path / "must-not-exist").exists()


def test_execute_keeps_setup_failure_preseed_and_repeatable(tmp_path, monkeypatch):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    output = tmp_path / "preseed-failure"
    runtime_module = SimpleNamespace(
        initialize_training_runtime=lambda: (_ for _ in ()).throw(
            RuntimeError("synthetic setup failure")
        )
    )
    dependencies = {
        "environment_type": object,
        "module": SimpleNamespace(),
        "provenance": {},
        "runtime": runtime_module,
    }
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )
    monkeypatch.setattr(
        experiment,
        "_terminalize_execution",
        lambda *args, **kwargs: {"verdict": "unexpected-terminal"},
    )

    with pytest.raises(RuntimeError, match="synthetic setup failure"):
        experiment.execute_authorized_experiment(
            repo_root=ROOT,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            output_dir=output,
            dependency_loader=lambda value: dependencies,
        )

    assert not (output / "evidence_start.json").exists()
    attempts = json.loads((output / "prestart_attempts.json").read_bytes())
    assert attempts["attempts"][-1]["state"] == "prestart_failed"
    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert [record["state"] for record in journal["records"]] == [
        "prestart_owned"
    ]


def test_execute_reconciles_partial_preseed_control_staging(tmp_path, monkeypatch):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    output = tmp_path / "partial-controls"
    original_write = experiment._atomic_write_once_or_same
    failed = False

    def fail_authorization_once(path, payload):
        nonlocal failed
        if path.name == "authorization.json" and not failed:
            failed = True
            raise OSError("synthetic authorization staging failure")
        return original_write(path, payload)

    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )
    monkeypatch.setattr(
        experiment, "_atomic_write_once_or_same", fail_authorization_once
    )

    with pytest.raises(OSError, match="authorization staging failure"):
        experiment.execute_authorized_experiment(
            repo_root=ROOT,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            output_dir=output,
            dependency_loader=lambda value: pytest.fail("loader must not run"),
        )

    assert (output / "registration.json").is_file()
    assert not (output / "authorization.json").exists()
    assert not (output / "execution_journal.json").exists()
    assert not (output / "evidence_start.json").exists()

    monkeypatch.setattr(
        experiment, "_atomic_write_once_or_same", original_write
    )
    with pytest.raises(RuntimeError, match="stop after staging recovery"):
        experiment.execute_authorized_experiment(
            repo_root=ROOT,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            output_dir=output,
            dependency_loader=lambda value: (_ for _ in ()).throw(
                RuntimeError("stop after staging recovery")
            ),
        )

    assert (output / "authorization.json").is_file()
    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert journal["records"][-1]["state"] == "prestart_owned"
    attempts = json.loads((output / "prestart_attempts.json").read_bytes())
    assert [row["attempt_index"] for row in attempts["attempts"]] == [1, 2]


def test_resource_ledger_is_staged_idempotently_and_only_moves_forward(tmp_path):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "resource-ledger"
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        initial = experiment.load_resource_ledger(output, identity=identity)
        assert initial["revision"] == 0
        assert initial["last_event"] is None
        assert initial["resource_use"] == {
            "charged_seconds": 0.0,
            "evaluation_episodes": 0,
            "total_episodes": 0,
            "training_episodes": 0,
        }
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        )

        advanced = experiment.publish_resource_prefix(
            output,
            identity=identity,
            lease=lease,
            resource_use={
                "charged_seconds": 1.5,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            event={
                "kind": "episode_debited",
                "phase": "training",
                "seed": first_seed,
            },
        )
        assert advanced["revision"] == 1
        assert experiment.publish_resource_prefix(
            output,
            identity=identity,
            lease=lease,
            resource_use={
                "charged_seconds": 1.5,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            event={
                "kind": "episode_debited",
                "phase": "training",
                "seed": first_seed,
            },
        ) == advanced

        wall_advanced = experiment.publish_resource_prefix(
            output,
            identity=identity,
            lease=lease,
            resource_use={
                "charged_seconds": 2.0,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            event={
                "kind": "wall_charged",
                "phase": "training",
                "seed": None,
            },
        )
        assert wall_advanced["revision"] == 2

        with pytest.raises(experiment.ExperimentBlocked, match="monotonic"):
            experiment.publish_resource_prefix(
                output,
                identity=identity,
                lease=lease,
                resource_use={
                    "charged_seconds": 1.5,
                    "evaluation_episodes": 0,
                    "optimizer_updates": 0,
                    "total_episodes": 0,
                    "training_episodes": 0,
                },
                event={
                    "kind": "episode_debited",
                    "phase": "training",
                    "seed": first_seed,
                },
            )

    lagging = copy.deepcopy(advanced)
    lagging["resource_use"].update(
        {"total_episodes": 2, "training_episodes": 2}
    )
    with pytest.raises(experiment.ExperimentBlocked, match="revision lags"):
        experiment._validate_resource_ledger(lagging, identity=identity)


def test_resource_ledger_recovers_a_durable_atomic_replacement(tmp_path):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "resource-ledger-recovery"
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        )
        current = experiment.load_resource_ledger(output, identity=identity)
        replacement = {
            "identity": identity,
            "last_event": {
                "kind": "episode_debited",
                "phase": "training",
                "seed": first_seed,
            },
            "resource_use": {
                "charged_seconds": 0.0,
                "evaluation_episodes": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            "revision": current["revision"] + 1,
            "schema_version": experiment.RESOURCE_LEDGER_SCHEMA_VERSION,
        }
        temporary = output / ".resource_use.json.tmp"
        _write_canonical_json(temporary, replacement)

        recovered = experiment.load_resource_ledger(
            output,
            identity=identity,
            lease=lease,
        )

        assert recovered == replacement
        assert not temporary.exists()
        assert experiment.load_resource_ledger(output, identity=identity) == replacement


def test_resource_evidence_without_marker_is_never_preseed_retryable(tmp_path):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "resource-without-marker"
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        with pytest.raises(experiment.ExperimentBlocked, match="evidence marker"):
            experiment.publish_resource_prefix(
                output,
                identity=identity,
                lease=lease,
                resource_use={
                    "charged_seconds": 0.0,
                    "evaluation_episodes": 0,
                    "optimizer_updates": 0,
                    "total_episodes": 1,
                    "training_episodes": 1,
                },
                event={
                    "kind": "episode_debited",
                    "phase": "training",
                    "seed": first_seed,
                },
            )

    forged = json.loads((output / "resource_use.json").read_bytes())
    forged.update(
        {
            "last_event": {
                "kind": "episode_debited",
                "phase": "training",
                "seed": first_seed,
            },
            "resource_use": {
                "charged_seconds": 0.0,
                "evaluation_episodes": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            "revision": 1,
        }
    )
    _write_canonical_json(output / "resource_use.json", forged)

    assert experiment.preseed_retry_allowed(output, identity=identity) is False


def test_evidence_marker_promotes_an_identical_partial_write(tmp_path):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "partial-evidence-marker"
    first_seed = registration["cohorts"]["train"][0]
    marker = {
        **identity,
        "first_seed": first_seed,
        "schema_version": experiment.EVIDENCE_START_SCHEMA_VERSION,
        "state": "evidence_started",
    }

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        temporary = output / ".evidence_start.json.tmp"
        _write_canonical_json(temporary, marker)

        assert experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        ) == marker

    assert json.loads((output / "evidence_start.json").read_bytes()) == marker
    assert not temporary.exists()


def test_resource_ledger_rejects_revision_only_partial_successor(tmp_path):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "resource-revision-only"

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        current = experiment.load_resource_ledger(output, identity=identity)
        candidate = copy.deepcopy(current)
        candidate["revision"] = 1
        candidate["last_event"] = {
            "kind": "wall_charged",
            "phase": "prestart",
            "seed": None,
        }
        temporary = output / ".resource_use.json.tmp"
        temporary.write_bytes(experiment.canonical_json_bytes(candidate))

        with pytest.raises(experiment.ExperimentBlocked, match="does not advance"):
            experiment.load_resource_ledger(
                output,
                identity=identity,
                lease=lease,
            )

    assert temporary.exists()
    assert not (output / "evidence_start.json").exists()


def test_execution_journal_promotes_exactly_one_partial_record(tmp_path):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "partial-execution-journal"
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        current = experiment.initialize_execution_journal(
            output,
            identity=identity,
            lease=lease,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        )
        candidate = copy.deepcopy(current)
        candidate["records"].append(
            {
                "details": {"first_seed": first_seed},
                "sequence": 1,
                "state": "evidence_started",
            }
        )
        temporary = output / ".execution_journal.json.tmp"
        _write_canonical_json(temporary, candidate)

        assert experiment.load_execution_journal(
            output,
            identity=identity,
            lease=lease,
        ) == candidate

    assert json.loads((output / "execution_journal.json").read_bytes()) == candidate
    assert not temporary.exists()


def test_checkpoint_write_failure_keeps_the_advanced_resource_prefix(
    tmp_path, monkeypatch
):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "checkpoint-resource-prefix"

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=registration["cohorts"]["train"][0],
            lease=lease,
        )
        checkpoint = experiment.build_checkpoint_envelope(
            _runtime_checkpoint(0, generator_value=11),
            identity=identity,
            checkpoint_index=1,
            previous_checkpoint_bytes=None,
            training_chunk=_chunk_summary(
                0,
                _generator_hash(0),
                11,
            ),
        )
        original_write = experiment._atomic_write_once_or_same

        def fail_checkpoint(path, payload):
            if path.name == "checkpoint_0001.json":
                raise OSError("synthetic checkpoint publication failure")
            return original_write(path, payload)

        monkeypatch.setattr(
            experiment, "_atomic_write_once_or_same", fail_checkpoint
        )
        with pytest.raises(OSError, match="checkpoint publication failure"):
            experiment.publish_checkpoint(
                output, checkpoint, lease=lease, identity=identity
            )

        assert not (output / "checkpoints/checkpoint_0001.json").exists()
        ledger = experiment.load_resource_ledger(output, identity=identity)
        assert ledger["revision"] == 64
        assert ledger["resource_use"] == {
            "charged_seconds": 1.0,
            "evaluation_episodes": 0,
            "total_episodes": 64,
            "training_episodes": 64,
        }


def test_execute_reconciles_checkpoint_written_before_interruption_journal(
    tmp_path, monkeypatch
):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "checkpoint-ahead"
    chunk = _chunk_summary(0, _generator_hash(0), 11)
    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.initialize_execution_journal(
            output, identity=identity, lease=lease
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=registration["cohorts"]["train"][0],
            lease=lease,
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="prestart_owned",
            state="evidence_started",
            details={"first_seed": registration["cohorts"]["train"][0]},
        )
        checkpoint = experiment.build_checkpoint_envelope(
            _runtime_checkpoint(0, generator_value=11),
            identity=identity,
            checkpoint_index=1,
            previous_checkpoint_bytes=None,
            training_chunk=chunk,
        )
        experiment.publish_checkpoint(
            output, checkpoint, lease=lease, identity=identity
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="evidence_started",
            state="infrastructure_interrupted",
            details={"reason": "checkpoint published before journal update"},
        )

    runtime_state = SimpleNamespace(model={}, next_chunk_index=1)
    runtime_module = SimpleNamespace(
        classify_training_family_saturation=lambda chunks: {
            "category": "card_reward",
            "saturated": True,
        },
        restore_training_runtime_from_checkpoint=lambda checkpoint: runtime_state,
        restore_consumed_resource_prefix=lambda state, resources: resources,
    )
    dependencies = {
        "environment_type": object,
        "module": SimpleNamespace(),
        "provenance": {},
        "runtime": runtime_module,
    }
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )
    monkeypatch.setattr(
        experiment,
        "_terminalize_execution",
        lambda *args, **kwargs: {"verdict": kwargs["verdict"]},
    )

    result = experiment.execute_authorized_experiment(
        repo_root=ROOT,
        registration=registration,
        authorization=authorization,
        expected_command=command,
        output_dir=output,
        dependency_loader=lambda value: dependencies,
    )

    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert [record["state"] for record in journal["records"][-3:]] == [
        "evidence_resumed",
        "training_chunk_completed",
        "training_stopped_family_saturation",
    ]
    assert result["manifest"]["verdict"] == (
        "experiment_stopped_during_training_for_family_saturation"
    )


def test_execute_marks_evidence_immediately_before_first_environment(
    tmp_path, monkeypatch
):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    output = tmp_path / "first-environment"
    first_seed = registration["cohorts"]["train"][0]
    events = []

    def construct_environment(seed, ascension):
        marker = json.loads((output / "evidence_start.json").read_bytes())
        journal = json.loads((output / "execution_journal.json").read_bytes())
        assert marker["first_seed"] == seed == first_seed
        assert journal["records"][-1]["state"] == "evidence_started"
        events.append(("environment", seed, ascension))
        return SimpleNamespace()

    runtime_state = SimpleNamespace(
        charged_seconds=0.0,
        model={},
        next_chunk_index=0,
    )
    _allow_synthetic_bootstrap(
        monkeypatch,
        _bootstrap_runtime_checkpoint(model=runtime_state.model),
    )

    def run_training_chunk(state, *, environment_factory, seeds, **kwargs):
        assert not (output / "evidence_start.json").exists()
        kwargs["on_resource_change"](
            {
                "charged_seconds": 0.0,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            {
                "kind": "episode_debited",
                "phase": "training",
                "seed": seeds[0],
            },
        )
        assert (output / "evidence_start.json").is_file()
        events.append(("resource", seeds[0]))
        environment_factory(seeds[0])
        raise RuntimeError("synthetic algorithm failure")

    runtime_module = SimpleNamespace(
        classify_training_family_saturation=lambda chunks: {"saturated": False},
        encode_checkpoint_state=lambda state: _bootstrap_runtime_checkpoint(
            model=state.model
        ),
        initialize_training_runtime=lambda: runtime_state,
        restore_consumed_resource_prefix=lambda state, resources: resources,
        restore_training_runtime_from_checkpoint=lambda checkpoint: runtime_state,
        run_training_chunk=run_training_chunk,
    )
    dependencies = {
        "environment_type": lambda native, provenance: native,
        "module": SimpleNamespace(Environment=construct_environment),
        "provenance": {},
        "runtime": runtime_module,
    }
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )
    monkeypatch.setattr(
        experiment,
        "_terminalize_execution",
        lambda *args, **kwargs: {"verdict": kwargs["verdict"]},
    )

    result = experiment.execute_authorized_experiment(
        repo_root=ROOT,
        registration=registration,
        authorization=authorization,
        expected_command=command,
        output_dir=output,
        dependency_loader=lambda value: dependencies,
    )

    assert events == [
        ("resource", first_seed),
        ("environment", first_seed, 0),
    ]
    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert [record["state"] for record in journal["records"]] == [
        "prestart_owned",
        "evidence_started",
        "invalid",
    ]
    assert result["manifest"]["verdict"] == "experiment_invalid"


def test_checkpoint_publication_failure_discards_the_advanced_runtime(
    tmp_path, monkeypatch
):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    output = tmp_path / "discard-advanced-runtime"
    captured_models = []

    def initialize_runtime():
        return SimpleNamespace(
            charged_seconds=0.0,
            model={"initial": True},
            next_chunk_index=0,
        )

    _allow_synthetic_bootstrap(
        monkeypatch,
        _bootstrap_runtime_checkpoint(model={"initial": True}),
    )

    def restore_resources(state, resources):
        state.charged_seconds = resources["charged_seconds"]
        return resources

    def run_training_chunk(state, *, environment_factory, seeds, **kwargs):
        kwargs["on_resource_change"](
            {
                "charged_seconds": 0.0,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 64,
                "training_episodes": 64,
            },
            {
                "kind": "episode_debited",
                "phase": "training",
                "seed": seeds[0],
            },
        )
        environment_factory(seeds[0])
        state.model = {"advanced": True}
        state.next_chunk_index = 1
        state.charged_seconds = 1.0
        return _chunk_summary(0, _generator_hash(0), 11)

    def encode_checkpoint(state):
        if state.next_chunk_index == 0:
            return _bootstrap_runtime_checkpoint(model=state.model)
        checkpoint = _runtime_checkpoint(0, generator_value=11)
        checkpoint["states"]["model"] = copy.deepcopy(state.model)
        return checkpoint

    runtime_module = SimpleNamespace(
        classify_training_family_saturation=lambda chunks: {"saturated": False},
        encode_checkpoint_state=encode_checkpoint,
        initialize_training_runtime=initialize_runtime,
        restore_consumed_resource_prefix=restore_resources,
        restore_training_runtime_from_checkpoint=lambda checkpoint: (
            initialize_runtime()
        ),
        run_training_chunk=run_training_chunk,
    )
    dependencies = {
        "environment_type": lambda native, provenance: native,
        "module": SimpleNamespace(Environment=lambda seed, ascension: object()),
        "provenance": {},
        "runtime": runtime_module,
    }
    original_write = experiment._atomic_write_once_or_same

    def fail_checkpoint(path, payload):
        if path.name == "checkpoint_0001.json":
            raise OSError("synthetic checkpoint write failure")
        return original_write(path, payload)

    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )
    monkeypatch.setattr(experiment, "_atomic_write_once_or_same", fail_checkpoint)

    def capture_terminal(*args, **kwargs):
        captured_models.append(copy.deepcopy(kwargs["runtime_state"].model))
        return {"verdict": kwargs["verdict"]}

    monkeypatch.setattr(experiment, "_terminalize_execution", capture_terminal)

    result = experiment.execute_authorized_experiment(
        repo_root=ROOT,
        registration=registration,
        authorization=authorization,
        expected_command=command,
        output_dir=output,
        dependency_loader=lambda value: dependencies,
    )

    assert result["status"] == "terminal"
    assert captured_models == [{"initial": True}]
    assert not (output / "checkpoints/checkpoint_0001.json").exists()
    assert experiment.load_resource_ledger(
        output,
        identity=_execution_identity(registration, authorization),
    )["resource_use"] == {
        "charged_seconds": 1.0,
        "evaluation_episodes": 0,
        "total_episodes": 64,
        "training_episodes": 64,
    }


def test_execute_terminalizes_a_second_restart_before_checkpoint_one(
    tmp_path, monkeypatch
):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / "second-restart-before-checkpoint"
    bootstrap = _bootstrap_runtime_checkpoint(model={"initial": True})
    _allow_synthetic_bootstrap(monkeypatch, bootstrap)
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        experiment.publish_bootstrap_runtime(
            output,
            bootstrap,
            identity=identity,
            lease=lease,
        )
        experiment.initialize_execution_journal(
            output,
            identity=identity,
            lease=lease,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="prestart_owned",
            state="evidence_started",
            details={"first_seed": first_seed},
        )
        experiment.publish_resource_prefix(
            output,
            identity=identity,
            lease=lease,
            resource_use={
                "charged_seconds": 1.0,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 64,
                "training_episodes": 64,
            },
            event={
                "kind": "episode_debited",
                "phase": "training",
                "seed": first_seed,
            },
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="evidence_started",
            state="infrastructure_interrupted",
            details={"phase": "training", "reason": "checkpoint write failed"},
        )

    captured = []

    def restore_runtime(checkpoint):
        assert checkpoint == bootstrap
        return SimpleNamespace(
            charged_seconds=0.0,
            model=copy.deepcopy(checkpoint["states"]["model"]),
            next_chunk_index=0,
        )

    def restore_resources(state, resources):
        state.charged_seconds = resources["charged_seconds"]
        return resources

    runtime_module = SimpleNamespace(
        restore_consumed_resource_prefix=restore_resources,
        restore_training_runtime_from_checkpoint=restore_runtime,
    )
    dependencies = {
        "environment_type": lambda native, provenance: native,
        "module": SimpleNamespace(
            Environment=lambda seed, ascension: pytest.fail(
                "second restart must not consume another seed"
            )
        ),
        "provenance": {},
        "runtime": runtime_module,
    }
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )

    def capture_terminal(*args, **kwargs):
        captured.append(copy.deepcopy(kwargs["runtime_state"].model))
        return {"verdict": kwargs["verdict"]}

    monkeypatch.setattr(experiment, "_terminalize_execution", capture_terminal)

    result = experiment.execute_authorized_experiment(
        repo_root=ROOT,
        registration=registration,
        authorization=authorization,
        expected_command=command,
        output_dir=output,
        dependency_loader=lambda value: dependencies,
    )

    assert result["status"] == "terminal"
    assert result["manifest"]["verdict"] == "experiment_blocked"
    assert captured == [{"initial": True}]


@pytest.mark.parametrize(
    ("terminal_state", "details", "expected_verdict"),
    [
        (
            "invalid",
            {"reason": "post-seed interruption lacks a checkpoint"},
            "experiment_invalid",
        ),
        (
            "training_stopped_family_saturation",
            {"classification": {"category": "card_reward", "saturated": True}},
            "experiment_stopped_during_training_for_family_saturation",
        ),
    ],
)
def test_execute_finishes_a_durable_preintent_terminal_state(
    tmp_path,
    monkeypatch,
    terminal_state,
    details,
    expected_verdict,
):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    output = tmp_path / terminal_state
    bootstrap = _bootstrap_runtime_checkpoint(model={"initial": True})
    _allow_synthetic_bootstrap(monkeypatch, bootstrap)
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        experiment.publish_bootstrap_runtime(
            output,
            bootstrap,
            identity=identity,
            lease=lease,
        )
        experiment.initialize_execution_journal(
            output,
            identity=identity,
            lease=lease,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="prestart_owned",
            state="evidence_started",
            details={"first_seed": first_seed},
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="evidence_started",
            state=terminal_state,
            details=details,
        )

    runtime_state = SimpleNamespace(
        charged_seconds=0.0,
        model={"initial": True},
        next_chunk_index=0,
    )
    runtime_module = SimpleNamespace(
        restore_consumed_resource_prefix=lambda state, resources: resources,
        restore_training_runtime_from_checkpoint=lambda checkpoint: runtime_state,
    )
    dependencies = {
        "environment_type": lambda native, provenance: native,
        "module": SimpleNamespace(
            Environment=lambda seed, ascension: pytest.fail(
                "durable terminal state must not consume another seed"
            )
        ),
        "provenance": {},
        "runtime": runtime_module,
    }
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )
    captured = []

    def capture_terminal(*args, **kwargs):
        captured.append(kwargs["verdict"])
        return {"verdict": kwargs["verdict"]}

    monkeypatch.setattr(experiment, "_terminalize_execution", capture_terminal)

    result = experiment.execute_authorized_experiment(
        repo_root=ROOT,
        registration=registration,
        authorization=authorization,
        expected_command=command,
        output_dir=output,
        dependency_loader=lambda value: dependencies,
    )

    assert result["status"] == "terminal"
    assert captured == [expected_verdict]


def test_execution_dependency_loader_loads_native_before_torch_runtime(monkeypatch):
    registration = _synthetic_registration()
    provenance = {
        "build": {
            "adapter_api_version": "synthetic-v3",
            "python": platform.python_version(),
        }
    }
    registration["native_identity"]["provenance"] = provenance
    registration["native_identity"]["provenance_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(provenance)
    ).hexdigest()
    registration = experiment.validate_registration(registration)
    calls = []
    native_module = SimpleNamespace(
        build_info_json=lambda: json.dumps(
            {"adapter_api_version": "synthetic-v3"}, sort_keys=True
        )
    )
    adapter = SimpleNamespace(
        __file__=(ROOT / "analysis_scripts/noncombat_simulator_adapter.py").as_posix(),
        NativeSimulatorEnvironment=object,
        load_native_module=lambda *args, **kwargs: calls.append("native")
        or native_module,
        validate_provenance=lambda value: copy.deepcopy(value),
    )
    runtime_module = SimpleNamespace(
        __file__=(
            ROOT
            / "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py"
        ).as_posix(),
        runtime_metadata=lambda: {
            "adapter_api_version": registration["contract"]["environment"][
                "adapter_api_version"
            ],
            "algorithm": registration["contract"]["algorithm"],
            "device": "cpu",
            "evaluation_selection": registration["contract"]["evaluation"][
                "selection"
            ],
        }
    )

    def fake_import(name):
        calls.append(name)
        if name == "analysis_scripts.noncombat_simulator_adapter":
            return adapter
        if name == "analysis_scripts.noncombat_hierarchical_simulator_learning_runtime":
            return runtime_module
        raise AssertionError(name)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.delitem(
        sys.modules, "sts_lightspeed_noncombat_adapter", raising=False
    )
    monkeypatch.setattr(experiment.importlib, "import_module", fake_import)
    monkeypatch.setattr(
        experiment,
        "external_file_binding",
        lambda path: copy.deepcopy(registration["native_identity"]["module"]),
    )

    dependencies = experiment._load_execution_dependencies(registration)

    assert calls == [
        "analysis_scripts.noncombat_simulator_adapter",
        "native",
        "analysis_scripts.noncombat_hierarchical_simulator_learning_runtime",
    ]

    runtime_module.__file__ = "C:/unregistered/runtime.py"
    with pytest.raises(experiment.ExperimentBlocked, match="outside the registered repo"):
        experiment._load_execution_dependencies(registration)
    assert dependencies["module"] is native_module
    assert dependencies["runtime"] is runtime_module


def test_seed_inventory_always_excludes_the_consumed_untouched_holdout():
    inventory = experiment.build_seed_exclusion_inventory(
        {"reports/historical.json": [0, 2, 4]},
        repository_commit="c" * 40,
    )

    reserved_name = "reserved:consumed_state_conditioned_unvisited_holdout"
    assert inventory["sources"][reserved_name] == list(range(71152, 71664))
    assert all(seed in inventory["excluded_seeds"] for seed in range(71152, 71664))
    assert inventory["authority"] == experiment.registration_authority()


def test_fresh_cohorts_use_the_only_fixed_ascending_selection():
    inventory = experiment.build_seed_exclusion_inventory(
        {"reports/historical.json": [0, 2, 4]},
        repository_commit="c" * 40,
    )

    cohorts = experiment.materialize_fresh_cohorts(inventory)

    assert len(cohorts["train"]) == 1024
    assert len(cohorts["canary"]) == 128
    assert len(cohorts["holdout"]) == 512
    flattened = cohorts["train"] + cohorts["canary"] + cohorts["holdout"]
    assert len(flattened) == len(set(flattened))
    assert not set(flattened).intersection(inventory["excluded_seeds"])
    assert flattened == sorted(flattened)
    assert experiment.validate_fresh_cohorts(inventory, cohorts) == cohorts

    changed = copy.deepcopy(cohorts)
    changed["holdout"][0] = changed["train"][0]
    with pytest.raises(experiment.ExperimentBlocked, match="exact|overlap"):
        experiment.validate_fresh_cohorts(inventory, changed)


def test_preseed_failure_can_retry_only_before_durable_evidence_start(tmp_path):
    output = tmp_path / "experiment"
    identity = {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "hierarchical-test-identity",
        "registration_sha256": "b" * 64,
    }

    with experiment.ExecutionLease(output, identity=identity) as lease:
        attempt = experiment.record_prestart_failure(
            output,
            identity=identity,
            lease=lease,
            reason="synthetic native load failure",
        )

        assert attempt["attempt_index"] == 1
        assert experiment.preseed_retry_allowed(output, identity=identity) is True
        marker = experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=12345,
            lease=lease,
        )
    assert marker["first_seed"] == 12345
    assert experiment.preseed_retry_allowed(output, identity=identity) is False
    with experiment.ExecutionLease(output, identity=identity) as lease:
        with pytest.raises(experiment.ExperimentBlocked, match="already started"):
            experiment.mark_evidence_start(
                output,
                identity=identity,
                first_seed=12345,
                lease=lease,
            )


def test_preseed_retry_rejects_identity_drift(tmp_path):
    output = tmp_path / "experiment"
    identity = {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "hierarchical-test-identity",
        "registration_sha256": "b" * 64,
    }
    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.record_prestart_failure(
            output,
            identity=identity,
            lease=lease,
            reason="synthetic process isolation failure",
        )
    changed = {**identity, "registration_sha256": "c" * 64}

    with pytest.raises(experiment.ExperimentBlocked, match="identity mismatch"):
        experiment.preseed_retry_allowed(output, identity=changed)


def test_postseed_resume_requires_same_identity_infrastructure_and_checkpoint():
    identity = {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "hierarchical-test-identity",
        "registration_sha256": "b" * 64,
    }
    marker = {
        **identity,
        "first_seed": 12345,
        "schema_version": experiment.EVIDENCE_START_SCHEMA_VERSION,
        "state": "evidence_started",
    }
    checkpoint = {
        "complete": True,
        "identity": identity,
        "runtime": {"coordinates": {"next_chunk_index": 3}},
        "schema_version": "synthetic-checkpoint-v1",
    }

    assert experiment.validate_same_identity_resume(
        marker,
        checkpoint,
        identity=identity,
        interruption_class="infrastructure",
    )["runtime"]["coordinates"]["next_chunk_index"] == 3
    with pytest.raises(experiment.ExperimentBlocked, match="not resumable"):
        experiment.validate_same_identity_resume(
            marker,
            checkpoint,
            identity=identity,
            interruption_class="algorithm",
        )
    with pytest.raises(experiment.ExperimentBlocked, match="checkpoint.*complete"):
        experiment.validate_same_identity_resume(
            marker,
            {**checkpoint, "complete": False},
            identity=identity,
            interruption_class="infrastructure",
        )


def test_active_output_root_cannot_be_read():
    with pytest.raises(experiment.ExperimentBlocked, match="active output"):
        experiment.assert_output_read_allowed(process_alive=True)

    experiment.assert_output_read_allowed(process_alive=False)


def test_execution_lease_is_exclusive_and_identity_bound(tmp_path):
    output = tmp_path / "experiment"
    identity = {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "hierarchical-test-identity",
        "registration_sha256": "b" * 64,
    }

    with experiment.ExecutionLease(output, identity=identity) as lease:
        assert lease.held is True
        with pytest.raises(experiment.ExperimentBlocked, match="lease.*held"):
            with experiment.ExecutionLease(output, identity=identity):
                pass
    assert lease.held is False

    changed = {**identity, "authorization_sha256": "c" * 64}
    with pytest.raises(experiment.ExperimentBlocked, match="lease identity mismatch"):
        with experiment.ExecutionLease(output, identity=changed):
            pass


def test_execution_lease_blocks_a_second_process(tmp_path):
    output = tmp_path / "experiment"
    identity = {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "hierarchical-test-identity",
        "registration_sha256": "b" * 64,
    }
    source = (
        "from analysis_scripts.noncombat_hierarchical_simulator_learning_experiment "
        "import ExecutionLease,ExperimentBlocked;"
        f"output={str(output)!r};identity={identity!r};"
        "result='acquired';"
        "\ntry:\n"
        "  with ExecutionLease(output,identity=identity): pass\n"
        "except ExperimentBlocked:\n"
        "  result='blocked'\n"
        "print(result)"
    )

    with experiment.ExecutionLease(output, identity=identity):
        completed = subprocess.run(
            [sys.executable, "-c", source],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    assert completed.stdout.strip() == "blocked"


def test_execution_journal_is_canonical_sequential_and_identity_bound(tmp_path):
    output = tmp_path / "experiment"
    identity = {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "hierarchical-test-identity",
        "registration_sha256": "b" * 64,
    }

    with experiment.ExecutionLease(output, identity=identity) as lease:
        journal = experiment.initialize_execution_journal(
            output,
            identity=identity,
            lease=lease,
        )
        assert journal["records"] == [
            {"details": {}, "sequence": 0, "state": "prestart_owned"}
        ]
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=12345,
            lease=lease,
        )
        journal = experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="prestart_owned",
            state="evidence_started",
            details={"first_seed": 12345},
        )
        assert journal["records"][-1] == {
            "details": {"first_seed": 12345},
            "sequence": 1,
            "state": "evidence_started",
        }
        with pytest.raises(experiment.ExperimentBlocked, match="previous state"):
            experiment.append_execution_journal(
                output,
                identity=identity,
                lease=lease,
                expected_previous_state="prestart_owned",
                state="training_chunk_completed",
                details={"chunk_index": 0},
            )

    raw = (output / "execution_journal.json").read_bytes()
    assert raw == experiment.canonical_json_bytes(json.loads(raw))
    assert experiment.validate_execution_journal(json.loads(raw), identity=identity) == journal


def test_tracked_seed_inventory_reads_one_fixed_tree_and_replays(monkeypatch):
    commit = "d" * 40
    tracked = {
        "reports/a.json": experiment.canonical_json_bytes(
            {"seed": 7, "nested": {"holdout_seeds": [8, 9]}}
        ),
        "reports/cohorts.json": experiment.canonical_json_bytes(
            {"cohorts": {"train": [10], "canary": [11], "holdout": [12]}}
        ),
        "reports/no-seeds.json": experiment.canonical_json_bytes(
            {"value": 99}
        ),
    }
    requested: list[list[str]] = []

    def fake_git_text(root, *args):
        assert args == (
            "ls-tree",
            "-r",
            "--name-only",
            commit,
            "--",
            "reports",
        )
        return "\n".join(
            [
                "reports/a.json",
                "reports/cohorts.json",
                "reports/no-seeds.json",
                experiment.DEFAULT_SEED_INVENTORY_PATH,
                experiment.DEFAULT_REGISTRATION_PATH,
                f"{experiment.DEFAULT_OUTPUT_DIRECTORY}/metrics.json",
                "reports/not-json.txt",
            ]
        )

    def fake_git_blob_batch(root, *, repository_commit, paths):
        assert repository_commit == commit
        requested.append(list(paths))
        return {path: tracked[path] for path in paths}

    monkeypatch.setattr(experiment, "_git_text", fake_git_text)
    monkeypatch.setattr(experiment, "_git_blob_batch", fake_git_blob_batch)

    inventory = experiment.build_tracked_seed_exclusion_inventory(
        ROOT, repository_commit=commit
    )

    assert requested == [
        ["reports/a.json", "reports/cohorts.json", "reports/no-seeds.json"]
    ]
    assert inventory["sources"]["reports/a.json"] == [7, 8, 9]
    assert inventory["sources"]["reports/cohorts.json"] == [10, 11, 12]
    assert "reports/no-seeds.json" not in inventory["sources"]
    assert experiment.verify_tracked_seed_exclusion_inventory(inventory, ROOT) == inventory

    changed = copy.deepcopy(inventory)
    changed["excluded_seeds"].append(999999)
    changed["excluded_seed_count"] += 1
    with pytest.raises(experiment.ExperimentBlocked, match="recomputation|counts"):
        experiment.verify_tracked_seed_exclusion_inventory(changed, ROOT)


def _binding(path: str, fill: str) -> dict[str, object]:
    return {"path": path, "sha256": fill * 64, "size_bytes": 123}


def _synthetic_registration_inputs():
    historical_payload = experiment.canonical_json_bytes(
        {"seeds": [0, 2, 4]}
    )
    inventory = experiment.build_seed_exclusion_inventory(
        {"reports/historical.json": [0, 2, 4]},
        repository_commit="e" * 40,
        source_payloads={"reports/historical.json": historical_payload},
    )
    cohorts = experiment.materialize_fresh_cohorts(inventory)
    implementation = {
        "source_files": [
            _binding(path, format(index + 1, "x")[-1])
            for index, path in enumerate(experiment.PLANNED_SOURCE_FILES)
        ],
        "source_sha256": "f" * 64,
    }
    runtime_identity = {
        "device": "cpu",
        "executable": "D:/anaconda/envs/stsai/python.exe",
        "platform": "win32",
        "python_version": "3.10.18",
        "torch_version": "2.5.1",
    }
    native_identity = {
        "dll_directories": ["D:/native/bin"],
        "module": {
            "path": "D:/native/sts_lightspeed_noncombat_adapter.pyd",
            "sha256": "1" * 64,
            "size_bytes": 456,
        },
        "provenance": {"build": {"adapter_api_version": "v3"}},
    }
    native_identity["provenance_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(native_identity["provenance"])
    ).hexdigest()
    isolation_identity = {
        "communication_mod_config": {
            "path": "C:/Users/test/CommunicationMod/config.properties",
            "sha256": "3" * 64,
            "size_bytes": 789,
        },
        "production_checkpoints": {
            "file_count": 5,
            "root": "D:/checkpoints",
            "sha256": "4" * 64,
            "size_bytes": 1000,
        },
    }
    return {
        "cohorts": cohorts,
        "implementation": implementation,
        "inventory": inventory,
        "isolation_identity": isolation_identity,
        "native_identity": native_identity,
        "runtime_identity": runtime_identity,
    }


def _synthetic_registration():
    values = _synthetic_registration_inputs()
    return experiment.build_source_only_registration(
        repository_commit="e" * 40,
        logical_experiment_id="noncombat-hierarchical-test-r1",
        preimplementation_binding=_binding(
            experiment.DEFAULT_PREIMPLEMENTATION_PATH,
            "5",
        ),
        seed_inventory=values["inventory"],
        seed_inventory_binding=_binding(
            experiment.DEFAULT_SEED_INVENTORY_PATH,
            "6",
        ),
        cohorts=values["cohorts"],
        implementation=values["implementation"],
        runtime_identity=values["runtime_identity"],
        native_identity=values["native_identity"],
        isolation_identity=values["isolation_identity"],
    )


def _synthetic_authorization(registration, command):
    registration_bytes = experiment.canonical_json_bytes(registration)
    return experiment.build_execution_authorization(
        registration,
        registration_binding={
            "path": experiment.DEFAULT_REGISTRATION_PATH,
            "sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "size_bytes": len(registration_bytes),
        },
        registration_commit="d" * 40,
        command=command,
    )


def test_registration_freezes_every_source_only_control():
    registration = _synthetic_registration()

    assert experiment.validate_registration(registration) == registration
    assert set(registration["authority"].values()) == {False}
    assert registration["contract"] == experiment.experiment_contract()
    assert registration["cohorts"]["selection"] == {
        "canary_count": 128,
        "holdout_count": 512,
        "train_count": 1024,
        "train_passes": 4,
    }
    assert registration["limits"] == experiment.experiment_contract()["limits"]
    assert registration["output_directory"] == experiment.DEFAULT_OUTPUT_DIRECTORY
    assert registration["output_inventory"] == experiment.registered_output_inventory()
    assert registration["native_identity"]["dll_directories"] == ["D:/native/bin"]
    assert registration["isolation_identity"]["production_checkpoints"]["root"] == (
        "D:/checkpoints"
    )

    changed = copy.deepcopy(registration)
    changed["contract"]["algorithm"]["family_entropy_coefficient"] = 0.02
    with pytest.raises(experiment.ExperimentBlocked, match="contract mismatch"):
        experiment.validate_registration(changed)

    changed = copy.deepcopy(registration)
    changed["cohorts"]["holdout"][0] = changed["cohorts"]["train"][0]
    with pytest.raises(experiment.ExperimentBlocked, match="cohort"):
        experiment.validate_registration(changed)


def test_authorization_enables_only_the_exact_simulator_execution_boundary():
    registration = _synthetic_registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    registration_binding = {
        "path": experiment.DEFAULT_REGISTRATION_PATH,
        "sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "size_bytes": len(registration_bytes),
    }
    command = [
        "D:/anaconda/envs/stsai/python.exe",
        "analysis_scripts/noncombat_hierarchical_simulator_learning_experiment.py",
        "execute",
        "--registration",
        experiment.DEFAULT_REGISTRATION_PATH,
        "--authorization",
        experiment.DEFAULT_AUTHORIZATION_PATH,
    ]

    authorization = experiment.build_execution_authorization(
        registration,
        registration_binding=registration_binding,
        registration_commit="d" * 40,
        command=command,
    )

    assert experiment.validate_execution_authorization(
        authorization,
        registration,
        expected_command=command,
    ) == authorization
    assert authorization["implementation_commit"] == registration["repository_commit"]
    assert authorization["registration_commit"] == "d" * 40
    enabled = {
        name for name, value in authorization["authority"].items() if value
    }
    assert enabled == {
        "environment_construction_authorized",
        "execution_authorized",
        "fresh_evidence_authorized",
        "model_fitting_authorized",
        "native_loading_authorized",
        "seed_access_authorized",
        "training_authorized",
    }
    for forbidden in (
        "communication_mod_authorized",
        "formal_rl_authorized",
        "gameplay_authorized",
        "policy_loading_authorized",
        "production_checkpoint_mutation_authorized",
        "promotion_authorized",
        "qualification_authorized",
    ):
        assert authorization["authority"][forbidden] is False

    changed = copy.deepcopy(authorization)
    changed["command"][-1] = "reports/other_authorization.json"
    with pytest.raises(experiment.ExperimentBlocked, match="command mismatch"):
        experiment.validate_execution_authorization(
            changed,
            registration,
            expected_command=command,
        )


def test_implementation_binding_uses_only_the_fixed_git_tree(monkeypatch):
    commit = "f" * 40
    blobs = {
        path: f"payload:{path}".encode("utf-8")
        for path in experiment.PLANNED_SOURCE_FILES
    }

    def fake_git_blob_batch(root, *, repository_commit, paths):
        assert repository_commit == commit
        assert list(paths) == list(experiment.PLANNED_SOURCE_FILES)
        return {path: blobs[path] for path in paths}

    monkeypatch.setattr(experiment, "_git_blob_batch", fake_git_blob_batch)

    implementation = experiment.build_git_implementation_binding(
        ROOT,
        repository_commit=commit,
    )

    assert [row["path"] for row in implementation["source_files"]] == list(
        experiment.PLANNED_SOURCE_FILES
    )
    for row in implementation["source_files"]:
        payload = blobs[row["path"]]
        assert row["sha256"] == hashlib.sha256(payload).hexdigest()
        assert row["size_bytes"] == len(payload)
    assert experiment.validate_implementation_binding(implementation) == implementation


def test_runtime_identity_uses_package_metadata_without_importing_torch(monkeypatch):
    monkeypatch.setattr(experiment.importlib_metadata, "version", lambda name: "9.9.9")

    identity = experiment.current_runtime_identity()

    assert identity["device"] == "cpu"
    assert identity["executable"] == Path(sys.executable).resolve().as_posix()
    assert identity["torch_version"] == "9.9.9"


def test_source_only_preflight_replays_clean_pushed_identity_without_runtime_import(
    monkeypatch,
):
    torch_before = sys.modules.get("torch")
    registration = _synthetic_registration()
    command = [
        "D:/anaconda/envs/stsai/python.exe",
        "analysis_scripts/noncombat_hierarchical_simulator_learning_experiment.py",
        "execute",
        "--registration",
        experiment.DEFAULT_REGISTRATION_PATH,
        "--authorization",
        experiment.DEFAULT_AUTHORIZATION_PATH,
    ]
    authorization = _synthetic_authorization(registration, command)
    pushed_commit = "f" * 40

    def fake_git_text(root, *args):
        if args == ("rev-parse", "HEAD"):
            return pushed_commit
        if args == ("rev-parse", "origin/master"):
            return pushed_commit
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        if args[:2] == ("merge-base", "--is-ancestor"):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(experiment, "_git_text", fake_git_text)
    monkeypatch.setattr(
        experiment,
        "build_git_implementation_binding",
        lambda root, repository_commit: copy.deepcopy(registration["implementation"]),
    )
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization_bytes = experiment.canonical_json_bytes(authorization)

    def fake_git_blobs(root, *, repository_commit, paths):
        path = tuple(paths)[0]
        if repository_commit == authorization["registration_commit"]:
            return {path: registration_bytes}
        if repository_commit == pushed_commit:
            return {path: authorization_bytes}
        raise AssertionError((repository_commit, paths))

    monkeypatch.setattr(experiment, "_git_blob_batch", fake_git_blobs)
    monkeypatch.setattr(
        experiment,
        "verify_tracked_seed_exclusion_inventory",
        lambda inventory, root: copy.deepcopy(inventory),
    )
    monkeypatch.setattr(
        experiment,
        "current_runtime_identity",
        lambda: copy.deepcopy(registration["runtime_identity"]),
    )

    def fake_external_binding(path):
        normalized = str(path).replace("\\", "/")
        if normalized == registration["native_identity"]["module"]["path"]:
            return copy.deepcopy(registration["native_identity"]["module"])
        return copy.deepcopy(
            registration["isolation_identity"]["communication_mod_config"]
        )

    monkeypatch.setattr(experiment, "external_file_binding", fake_external_binding)
    monkeypatch.setattr(
        experiment,
        "snapshot_production_checkpoints",
        lambda root: copy.deepcopy(
            registration["isolation_identity"]["production_checkpoints"]
        ),
    )

    report = experiment.source_only_preflight(
        ROOT,
        registration,
        authorization,
        expected_command=command,
    )

    assert set(report["authority"].values()) == {False}
    assert set(report["checks"].values()) == {True}
    assert report["repository_commit"] == registration["repository_commit"]
    assert report["pushed_commit"] == pushed_commit
    assert report["logical_experiment_id"] == registration["logical_experiment_id"]
    assert sys.modules.get("torch") is torch_before


def test_source_only_preflight_rejects_tracked_worktree_drift(monkeypatch):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)

    monkeypatch.setattr(
        experiment,
        "_git_text",
        lambda root, *args: (
            " M analysis_scripts/drift.py"
            if args == ("status", "--porcelain", "--untracked-files=no")
            else registration["repository_commit"]
        ),
    )

    with pytest.raises(experiment.ExperimentBlocked, match="tracked worktree"):
        experiment.source_only_preflight(
            ROOT,
            registration,
            authorization,
            expected_command=command,
        )


def test_registration_preflight_replays_the_pushed_implementation(monkeypatch):
    torch_before = sys.modules.get("torch")
    registration = _synthetic_registration()

    def fake_git_text(root, *args):
        if args in {
            ("rev-parse", "HEAD"),
            ("rev-parse", "origin/master"),
        }:
            return registration["repository_commit"]
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(experiment, "_git_text", fake_git_text)
    monkeypatch.setattr(
        experiment,
        "build_git_implementation_binding",
        lambda root, repository_commit: copy.deepcopy(
            registration["implementation"]
        ),
    )
    monkeypatch.setattr(
        experiment,
        "verify_tracked_seed_exclusion_inventory",
        lambda inventory, root: copy.deepcopy(inventory),
    )
    monkeypatch.setattr(
        experiment,
        "current_runtime_identity",
        lambda: copy.deepcopy(registration["runtime_identity"]),
    )

    def fake_external_binding(path):
        normalized = str(path).replace("\\", "/")
        if normalized == registration["native_identity"]["module"]["path"]:
            return copy.deepcopy(registration["native_identity"]["module"])
        return copy.deepcopy(
            registration["isolation_identity"]["communication_mod_config"]
        )

    monkeypatch.setattr(experiment, "external_file_binding", fake_external_binding)
    monkeypatch.setattr(
        experiment,
        "snapshot_production_checkpoints",
        lambda root: copy.deepcopy(
            registration["isolation_identity"]["production_checkpoints"]
        ),
    )

    report = experiment.source_only_registration_preflight(ROOT, registration)

    assert report["repository_commit"] == registration["repository_commit"]
    assert set(report["authority"].values()) == {False}
    assert set(report["checks"].values()) == {True}
    assert sys.modules.get("torch") is torch_before


def _execution_identity(registration, authorization):
    return {
        "authorization_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(authorization)
        ).hexdigest(),
        "logical_execution_id": registration["logical_experiment_id"],
        "registration_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(registration)
        ).hexdigest(),
    }


def _generator_hash(value: int | str) -> str:
    if isinstance(value, str):
        return value
    return hashlib.sha256(bytes([value])).hexdigest()


def _training_row(
    index: int, before: int | str, after: int | str, *, seed: int
) -> dict[str, object]:
    return {
        "action_generator_state_sha256": {
            "after_conditional": _generator_hash(after),
            "after_family": hashlib.sha256(
                f"{before}:family".encode("ascii")
            ).hexdigest(),
            "before_family": _generator_hash(before),
        },
        "candidate_scores": {"action-0": 0.0},
        "candidates": [{"action_id": "action-0", "kind": "choose"}],
        "category": "event",
        "chunk_index": index,
        "conditional_probabilities": {"action-0": 1.0},
        "decision_id": f"seed-{seed}:decision-0",
        "decision_index": 0,
        "entropies": {
            "expected_conditional": 0.0,
            "family": 0.0,
            "joint": 0.0,
        },
        "family_order": ["choose"],
        "family_probabilities": {"choose": 1.0},
        "family_score_margin": None,
        "formal_reward": {
            "floor_progress": 0.0,
            "scalar_reward": 0.0,
            "terminal_victory": 0,
        },
        "joint_probabilities": {"action-0": 1.0},
        "joint_probability_max_action_ids": ["action-0"],
        "legal_action_ids": ["action-0"],
        "multi_family": False,
        "raw_score_max_action_ids": ["action-0"],
        "raw_score_max_family_ids": ["choose"],
        "schema_version": (
            "noncombat-hierarchical-simulator-learning-training-row-v1"
        ),
        "score_greedy_action_ids": ["action-0"],
        "score_greedy_family_ids": ["choose"],
        "score_margin": None,
        "seed": seed,
        "selected_action_id": "action-0",
        "selected_family": "choose",
        "selected_terms": {
            "conditional_log_probability": 0.0,
            "family_log_probability": 0.0,
            "joint_log_probability": 0.0,
        },
        "selection_mode": "family-first-then-conditional-v1",
        "state_effect": {
            "actual_scores": [0.0],
            "max_abs_relative_score_change": 0.0,
            "nonzero": False,
            "relative_order_changed": False,
            "zero_state_scores": [0.0],
        },
    }


def _chunk_summary(
    index: int, before: int | str, after: int | str
) -> dict[str, object]:
    completed_episodes = (index + 1) * 64
    train = _synthetic_registration()["cohorts"]["train"] * 4
    episode_seeds = train[index * 64 : (index + 1) * 64]
    return {
        "chunk_index": index,
        "complete": True,
        "conditional_entropy_coefficient": 0.01,
        "decisions": 1,
        "categories": ["event"],
        "diagnostic_rows": [
            _training_row(
                index,
                before,
                after,
                seed=episode_seeds[0],
            )
        ],
        "episode_seeds": episode_seeds,
        "episodes": 64,
        "family_diagnostics": {
            "categories": {
                category: {
                    "decisions": 1 if category == "event" else 0,
                    "family_opportunities": (
                        {"choose": 1} if category == "event" else {}
                    ),
                    "multi_family_decisions": 0,
                    "raw_score_max_family_sets": {},
                    "selected_families": {},
                }
                for category in ("card_reward", "event", "route", "shop")
            }
        },
        "family_entropy_coefficient": 0.01,
        "gradient_norm_after_clip": 0.0,
        "gradient_norm_before_clip": 0.0,
        "loss": 0.0,
        "mean_expected_conditional_entropy": 0.0,
        "mean_family_entropy": 0.0,
        "normalized_return_mean": 0.0,
        "normalized_return_std": 0.0,
        "optimizer_update": index + 1,
        "policy_loss": 0.0,
        "resource_use": {
            "charged_seconds": float(index + 1),
            "completed_decisions": index + 1,
            "evaluation_episodes": 0,
            "optimizer_updates": index + 1,
            "total_episodes": completed_episodes,
            "training_episodes": completed_episodes,
        },
        "schema_version": (
            "noncombat-hierarchical-simulator-learning-chunk-summary-v1"
        ),
    }


def _encoded_state_value(value):
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [_encoded_state_value(item) for item in value]}
    if isinstance(value, list):
        return {"type": "list", "items": [_encoded_state_value(item) for item in value]}
    if isinstance(value, dict):
        items = [
            {
                "key": _encoded_state_value(key),
                "value": _encoded_state_value(item),
            }
            for key, item in value.items()
        ]
        items.sort(key=lambda item: experiment.canonical_json_bytes(item["key"]))
        return {"type": "mapping", "items": items}
    return {"type": "scalar", "value": value}


def _encoded_mapping_value(encoded: dict[str, object], key: object):
    encoded_key = _encoded_state_value(key)
    return next(
        item["value"] for item in encoded["items"] if item["key"] == encoded_key
    )


def _runtime_checkpoint(
    index: int, *, generator_value: int | None = None
) -> dict[str, object]:
    completed_updates = index + 1
    completed_episodes = completed_updates * 64
    encoded_generator_value = (
        completed_updates if generator_value is None else generator_value
    )
    return {
        "algorithm": {
            "conditional_entropy_coefficient": 0.01,
            "family_entropy_coefficient": 0.01,
            "sampling": "family-first-then-conditional-v1",
        },
        "coordinates": {
            "completed_decisions": completed_updates,
            "completed_episodes": completed_episodes,
            "next_chunk_index": completed_updates,
            "optimizer_updates": completed_updates,
        },
        "model_architecture": {
            "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
            "candidate_input_dim": 1024,
            "device": "cpu",
            "dtype": "float32",
            "hidden_dim": 64,
            "state_conditioned": True,
            "state_input_dim": 1024,
        },
        "resource_use": {
            "charged_seconds": float(completed_updates),
            "evaluation_episodes": 0,
            "optimizer_updates": completed_updates,
            "total_episodes": completed_episodes,
            "training_episodes": completed_episodes,
        },
        "schema_version": (
            "noncombat-hierarchical-simulator-learning-runtime-checkpoint-v1"
        ),
        "states": {
            "action_generator": {
                "dtype": "uint8",
                "shape": [1],
                "values": [encoded_generator_value],
            },
            "model": {"weight": {"dtype": "float32", "shape": [1], "values": [0.0]}},
            "optimizer": _encoded_state_value(
                {
                    "param_groups": [
                        {
                            "amsgrad": False,
                            "betas": (0.9, 0.999),
                            "capturable": False,
                            "differentiable": False,
                            "eps": 1e-8,
                            "foreach": None,
                            "fused": None,
                            "lr": 0.001,
                            "maximize": False,
                            "params": [0],
                            "weight_decay": 0.0,
                        }
                    ],
                    "state": {},
                }
            ),
            "python_rng": _encoded_state_value(random.Random(0).getstate()),
        },
    }


def _bootstrap_runtime_checkpoint(
    *, model: dict[str, object] | None = None
) -> dict[str, object]:
    checkpoint = _runtime_checkpoint(0, generator_value=0)
    checkpoint["coordinates"] = {
        "completed_decisions": 0,
        "completed_episodes": 0,
        "next_chunk_index": 0,
        "optimizer_updates": 0,
    }
    checkpoint["resource_use"] = {
        "charged_seconds": 0.0,
        "evaluation_episodes": 0,
        "optimizer_updates": 0,
        "total_episodes": 0,
        "training_episodes": 0,
    }
    if model is not None:
        checkpoint["states"]["model"] = copy.deepcopy(model)
    return checkpoint


def _allow_synthetic_bootstrap(monkeypatch, checkpoint) -> None:
    digest = hashlib.sha256(
        experiment.canonical_json_bytes(checkpoint)
    ).hexdigest()
    monkeypatch.setattr(experiment, "INITIAL_RUNTIME_SHA256", digest)
    independent_verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    monkeypatch.setattr(
        independent_verifier,
        "INITIAL_RUNTIME_SHA256",
        digest,
    )


def _publish_synthetic_bootstrap(
    output,
    *,
    identity,
    lease,
    monkeypatch,
    model: dict[str, object] | None = None,
):
    checkpoint = _bootstrap_runtime_checkpoint(model=model)
    _allow_synthetic_bootstrap(monkeypatch, checkpoint)
    experiment.publish_bootstrap_runtime(
        output,
        checkpoint,
        identity=identity,
        lease=lease,
    )
    return checkpoint


def test_checkpoint_chain_and_compressed_training_rows_bind_canonical_bytes(
    tmp_path, monkeypatch
):
    output = tmp_path / "experiment"
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    chunks = [
        _chunk_summary(0, _generator_hash(0), 2),
        _chunk_summary(1, 2, 3),
    ]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=registration["cohorts"]["train"][0],
            lease=lease,
        )
        previous = None
        for index, chunk in enumerate(chunks):
            checkpoint = experiment.build_checkpoint_envelope(
                _runtime_checkpoint(index, generator_value=2 + index),
                identity=identity,
                checkpoint_index=index + 1,
                previous_checkpoint_bytes=previous,
                training_chunk=chunk,
            )
            checkpoint_path = experiment.publish_checkpoint(
                output, checkpoint, lease=lease, identity=identity
            )
            previous = checkpoint_path.read_bytes()
        training_binding = experiment.publish_training_rows(
            output,
            chunks,
            lease=lease,
            identity=identity,
        )

    chain = experiment.validate_checkpoint_chain(
        output,
        identity=identity,
        registration=registration,
    )
    stored = (output / "training_rows.json.gz").read_bytes()
    canonical = gzip.decompress(stored)
    value = json.loads(canonical)

    assert [row["checkpoint_index"] for row in chain] == [1, 2]
    assert value["chunks"] == chunks
    assert canonical == experiment.canonical_json_bytes(value)
    assert training_binding["canonical_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert training_binding["sha256"] == hashlib.sha256(stored).hexdigest()
    assert training_binding["canonical_size_bytes"] == len(canonical)
    assert training_binding["size_bytes"] == len(stored)

    drifted = copy.deepcopy(chunks)
    drifted[1]["diagnostic_rows"][0]["action_generator_state_sha256"][
        "before_family"
    ] = _generator_hash(99)
    with pytest.raises(experiment.ExperimentBlocked, match="generator.*chain"):
        experiment.build_training_rows_artifact(drifted)

    first_checkpoint_path = output / "checkpoints/checkpoint_0001.json"
    first_checkpoint = json.loads(first_checkpoint_path.read_bytes())
    first_checkpoint["training_chunk"]["diagnostic_rows"][0][
        "action_generator_state_sha256"
    ]["before_family"] = _generator_hash(99)
    _write_canonical_json(first_checkpoint_path, first_checkpoint)
    with pytest.raises(experiment.ExperimentBlocked, match="bootstrap anchor"):
        experiment.validate_checkpoint_chain(
            output,
            identity=identity,
            registration=registration,
        )


def test_checkpoint_recovery_rejects_registered_seed_order_drift(
    tmp_path, monkeypatch
):
    output = tmp_path / "checkpoint-seed-drift"
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    chunk = _chunk_summary(0, _generator_hash(0), 2)

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=registration["cohorts"]["train"][0],
            lease=lease,
        )
        checkpoint = experiment.build_checkpoint_envelope(
            _runtime_checkpoint(0, generator_value=2),
            identity=identity,
            checkpoint_index=1,
            previous_checkpoint_bytes=None,
            training_chunk=chunk,
        )
        path = experiment.publish_checkpoint(
            output,
            checkpoint,
            lease=lease,
            identity=identity,
        )

    changed = json.loads(path.read_bytes())
    seeds = changed["training_chunk"]["episode_seeds"]
    seeds[0], seeds[1] = seeds[1], seeds[0]
    _write_canonical_json(path, changed)

    with pytest.raises(experiment.ExperimentBlocked, match="seed order"):
        experiment.validate_checkpoint_chain(
            output,
            identity=identity,
            registration=registration,
        )


def test_zero_checkpoint_terminal_model_is_bound_to_bootstrap_runtime(
    tmp_path, monkeypatch
):
    output = tmp_path / "zero-checkpoint-terminal"
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    bootstrap = _bootstrap_runtime_checkpoint()
    _allow_synthetic_bootstrap(monkeypatch, bootstrap)

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        experiment.publish_bootstrap_runtime(
            output,
            bootstrap,
            identity=identity,
            lease=lease,
        )
        experiment.initialize_execution_journal(
            output,
            identity=identity,
            lease=lease,
        )
        first_seed = registration["cohorts"]["train"][0]
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=first_seed,
            lease=lease,
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="prestart_owned",
            state="evidence_started",
            details={"first_seed": first_seed},
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="evidence_started",
            state="infrastructure_interrupted",
            details={"phase": "training", "reason": "synthetic interruption"},
        )
        binding = experiment.publish_training_rows(
            output,
            [],
            lease=lease,
            identity=identity,
        )

        with pytest.raises(experiment.ExperimentBlocked, match="bootstrap"):
            experiment.publish_experiment_terminal(
                output,
                registration=registration,
                authorization=authorization,
                expected_command=command,
                identity=identity,
                lease=lease,
                training_rows_binding=binding,
                evaluation=None,
                final_model={"advanced": True},
                resource_use=bootstrap["resource_use"],
                isolation_post=registration["isolation_identity"],
                verdict="experiment_blocked",
                terminal_reason="synthetic infrastructure interruption",
            )

        manifest = experiment.publish_experiment_terminal(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            identity=identity,
            lease=lease,
            training_rows_binding=binding,
            evaluation=None,
            final_model=bootstrap["states"]["model"],
            resource_use=bootstrap["resource_use"],
            isolation_post=registration["isolation_identity"],
            verdict="experiment_blocked",
            terminal_reason="synthetic infrastructure interruption",
        )

    assert manifest["verdict"] == "experiment_blocked"
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    verified = verifier.verify_artifact_output(output)
    assert verified["checkpoint_count"] == 0
    assert verified["verdict"] == "experiment_blocked"


def test_interrupted_terminal_publication_is_manifest_last_and_all_false(
    tmp_path, monkeypatch
):
    output = tmp_path / "experiment"
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    chunk = _chunk_summary(0, _generator_hash(0), 11)

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.initialize_execution_journal(
            output, identity=identity, lease=lease
        )
        experiment.mark_evidence_start(
            output, identity=identity, first_seed=100, lease=lease
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="prestart_owned",
            state="evidence_started",
            details={"first_seed": 100},
        )
        checkpoint = experiment.build_checkpoint_envelope(
            _runtime_checkpoint(0, generator_value=11),
            identity=identity,
            checkpoint_index=1,
            previous_checkpoint_bytes=None,
            training_chunk=chunk,
        )
        experiment.publish_checkpoint(
            output, checkpoint, lease=lease, identity=identity
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="evidence_started",
            state="training_chunk_completed",
            details={"checkpoint_index": 1},
        )
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state="training_chunk_completed",
            state="infrastructure_interrupted",
            details={"reason": "synthetic interruption"},
        )
        training_binding = experiment.publish_training_rows(
            output, [chunk], lease=lease, identity=identity
        )
        manifest = experiment.publish_experiment_terminal(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            identity=identity,
            lease=lease,
            training_rows_binding=training_binding,
            evaluation=None,
            final_model=_runtime_checkpoint(0)["states"]["model"],
            resource_use=_runtime_checkpoint(0)["resource_use"],
            isolation_post=registration["isolation_identity"],
            verdict="experiment_blocked",
            terminal_reason="synthetic infrastructure interruption",
        )

    manifest_path = output / "artifact_manifest.json"
    assert manifest_path.read_bytes() == experiment.canonical_json_bytes(manifest)
    assert set(manifest["authority"].values()) == {False}
    assert manifest["verdict"] == "experiment_blocked"
    assert (output / "terminal.json").is_file()
    assert (output / "evaluation.json").is_file()
    assert json.loads((output / "evaluation.json").read_bytes())["evaluation"] is None
    assert json.loads((output / "execution_journal.json").read_bytes())[
        "records"
    ][-1]["state"] == "terminal"
    assert [row["path"] for row in manifest["artifacts"]] == sorted(
        row["path"] for row in manifest["artifacts"]
    )
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
        assert len(payload) == binding["size_bytes"]


def _prepare_interrupted_terminal_publication(output: Path, monkeypatch):
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    chunk = _chunk_summary(0, _generator_hash(0), 11)
    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.initialize_execution_journal(
            output, identity=identity, lease=lease
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=registration["cohorts"]["train"][0],
            lease=lease,
        )
        state = "prestart_owned"
        for next_state in (
            "evidence_started",
            "training_chunk_completed",
            "infrastructure_interrupted",
        ):
            experiment.append_execution_journal(
                output,
                identity=identity,
                lease=lease,
                expected_previous_state=state,
                state=next_state,
                details=(
                    {"checkpoint_index": 1}
                    if next_state == "training_chunk_completed"
                    else {}
                ),
            )
            state = next_state
        checkpoint = experiment.build_checkpoint_envelope(
            _runtime_checkpoint(0, generator_value=11),
            identity=identity,
            checkpoint_index=1,
            previous_checkpoint_bytes=None,
            training_chunk=chunk,
        )
        experiment.publish_checkpoint(
            output, checkpoint, lease=lease, identity=identity
        )
        training_binding = experiment.publish_training_rows(
            output, [chunk], lease=lease, identity=identity
        )
    return {
        "authorization": authorization,
        "command": command,
        "identity": identity,
        "registration": registration,
        "training_binding": training_binding,
    }


@pytest.mark.parametrize(
    ("failure_name", "expected_state"),
    [
        ("metrics.json", "infrastructure_interrupted"),
        ("artifact_manifest.json", "terminal"),
    ],
)
def test_terminal_publication_recovers_from_each_commit_boundary(
    tmp_path, monkeypatch, failure_name, expected_state
):
    output = tmp_path / failure_name.replace(".json", "")
    prepared = _prepare_interrupted_terminal_publication(output, monkeypatch)
    original_write = experiment._atomic_write_once_or_same
    failed = False

    def fail_once(path, payload):
        nonlocal failed
        if path.name == failure_name and not failed:
            failed = True
            raise OSError(f"synthetic {failure_name} interruption")
        return original_write(path, payload)

    monkeypatch.setattr(experiment, "_atomic_write_once_or_same", fail_once)
    with experiment.ExecutionLease(
        output, identity=prepared["identity"]
    ) as lease:
        with pytest.raises(OSError, match="synthetic"):
            experiment.publish_experiment_terminal(
                output,
                registration=prepared["registration"],
                authorization=prepared["authorization"],
                expected_command=prepared["command"],
                identity=prepared["identity"],
                lease=lease,
                training_rows_binding=prepared["training_binding"],
                evaluation=None,
                final_model=_runtime_checkpoint(0)["states"]["model"],
                resource_use=_runtime_checkpoint(0)["resource_use"],
                isolation_post=prepared["registration"]["isolation_identity"],
                verdict="experiment_blocked",
                terminal_reason="synthetic infrastructure interruption",
            )
    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert journal["records"][-1]["state"] == expected_state

    monkeypatch.setattr(
        experiment, "_atomic_write_once_or_same", original_write
    )
    with experiment.ExecutionLease(
        output, identity=prepared["identity"]
    ) as lease:
        manifest = experiment.publish_experiment_terminal(
            output,
            registration=prepared["registration"],
            authorization=prepared["authorization"],
            expected_command=prepared["command"],
            identity=prepared["identity"],
            lease=lease,
            training_rows_binding=prepared["training_binding"],
            evaluation=None,
            final_model=_runtime_checkpoint(0)["states"]["model"],
            resource_use=_runtime_checkpoint(0)["resource_use"],
            isolation_post=prepared["registration"]["isolation_identity"],
            verdict="experiment_blocked",
            terminal_reason="synthetic infrastructure interruption",
        )

    assert manifest["verdict"] == "experiment_blocked"
    assert (output / "artifact_manifest.json").is_file()


def test_execute_completes_terminal_intent_before_dependency_loading(
    tmp_path, monkeypatch
):
    output = tmp_path / "terminal-intent-recovery"
    prepared = _prepare_interrupted_terminal_publication(output, monkeypatch)
    original_write = experiment._atomic_write_once_or_same

    def fail_manifest(path, payload):
        if path.name == "artifact_manifest.json":
            raise OSError("synthetic manifest interruption")
        return original_write(path, payload)

    monkeypatch.setattr(experiment, "_atomic_write_once_or_same", fail_manifest)
    with experiment.ExecutionLease(
        output, identity=prepared["identity"]
    ) as lease:
        with pytest.raises(OSError, match="manifest interruption"):
            experiment.publish_experiment_terminal(
                output,
                registration=prepared["registration"],
                authorization=prepared["authorization"],
                expected_command=prepared["command"],
                identity=prepared["identity"],
                lease=lease,
                training_rows_binding=prepared["training_binding"],
                evaluation=None,
                final_model=_runtime_checkpoint(0)["states"]["model"],
                resource_use=_runtime_checkpoint(0)["resource_use"],
                isolation_post=prepared["registration"]["isolation_identity"],
                verdict="experiment_blocked",
                terminal_reason="synthetic infrastructure interruption",
            )

    touched = []
    monkeypatch.setattr(
        experiment, "_atomic_write_once_or_same", original_write
    )
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda *args, **kwargs: {"checks": {"synthetic": True}},
    )

    result = experiment.execute_authorized_experiment(
        repo_root=ROOT,
        registration=prepared["registration"],
        authorization=prepared["authorization"],
        expected_command=prepared["command"],
        output_dir=output,
        dependency_loader=lambda value: touched.append(value),
    )

    assert result["status"] == "terminal"
    assert touched == []
    assert (output / "artifact_manifest.json").is_file()


def test_terminal_publication_invalidates_changed_production_isolation(
    tmp_path, monkeypatch
):
    output = tmp_path / "experiment"
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    chunk = _chunk_summary(0, _generator_hash(0), 11)
    isolation_post = copy.deepcopy(registration["isolation_identity"])
    isolation_post["communication_mod_config"]["sha256"] = "1" * 64

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        _publish_synthetic_bootstrap(
            output,
            identity=identity,
            lease=lease,
            monkeypatch=monkeypatch,
        )
        experiment.initialize_execution_journal(
            output, identity=identity, lease=lease
        )
        experiment.mark_evidence_start(
            output,
            identity=identity,
            first_seed=registration["cohorts"]["train"][0],
            lease=lease,
        )
        state = "prestart_owned"
        for next_state in (
            "evidence_started",
            "training_chunk_completed",
            "infrastructure_interrupted",
        ):
            experiment.append_execution_journal(
                output,
                identity=identity,
                lease=lease,
                expected_previous_state=state,
                state=next_state,
                details=(
                    {"checkpoint_index": 1}
                    if next_state == "training_chunk_completed"
                    else {}
                ),
            )
            state = next_state
        checkpoint = experiment.build_checkpoint_envelope(
            _runtime_checkpoint(0, generator_value=11),
            identity=identity,
            checkpoint_index=1,
            previous_checkpoint_bytes=None,
            training_chunk=chunk,
        )
        experiment.publish_checkpoint(
            output, checkpoint, lease=lease, identity=identity
        )
        training_binding = experiment.publish_training_rows(
            output, [chunk], lease=lease, identity=identity
        )
        manifest = experiment.publish_experiment_terminal(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            identity=identity,
            lease=lease,
            training_rows_binding=training_binding,
            evaluation=None,
            final_model=_runtime_checkpoint(0)["states"]["model"],
            resource_use=_runtime_checkpoint(0)["resource_use"],
            isolation_post=isolation_post,
            verdict="experiment_blocked",
            terminal_reason="synthetic interruption",
        )

    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert [row["state"] for row in journal["records"][-2:]] == [
        "invalid",
        "terminal",
    ]
    assert manifest["verdict"] == "experiment_invalid"
    assert json.loads((output / "evaluation.json").read_bytes())["evaluation"] is None
    assert json.loads((output / "isolation.json").read_bytes())["unchanged"] is False


def _publish_verifier_fixture(
    output: Path,
    monkeypatch,
    *,
    interrupt_during_holdout: bool = False,
) -> Path:
    registration = _synthetic_registration()
    command = ["python.exe", "runner.py", "execute"]
    authorization = _synthetic_authorization(registration, command)
    identity = _execution_identity(registration, authorization)
    bootstrap = _bootstrap_runtime_checkpoint()
    _allow_synthetic_bootstrap(monkeypatch, bootstrap)
    chunks = [
        _chunk_summary(0, _generator_hash(0), 21),
        _chunk_summary(1, 21, 22),
    ]
    first_seed = registration["cohorts"]["train"][0]

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.stage_execution_controls(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            lease=lease,
            identity=identity,
        )
        experiment.publish_bootstrap_runtime(
            output,
            bootstrap,
            identity=identity,
            lease=lease,
        )
        experiment.initialize_execution_journal(
            output, identity=identity, lease=lease
        )
        experiment.mark_evidence_start(
            output, identity=identity, first_seed=first_seed, lease=lease
        )
        state = "prestart_owned"
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state=state,
            state="evidence_started",
            details={"first_seed": first_seed},
        )
        state = "evidence_started"
        previous = None
        for index, chunk in enumerate(chunks):
            checkpoint = experiment.build_checkpoint_envelope(
                _runtime_checkpoint(index, generator_value=21 + index),
                identity=identity,
                checkpoint_index=index + 1,
                previous_checkpoint_bytes=previous,
                training_chunk=chunk,
            )
            path = experiment.publish_checkpoint(
                output, checkpoint, lease=lease, identity=identity
            )
            previous = path.read_bytes()
            experiment.append_execution_journal(
                output,
                identity=identity,
                lease=lease,
                expected_previous_state=state,
                state="training_chunk_completed",
                details={"checkpoint_index": index + 1},
            )
            state = "training_chunk_completed"
        if interrupt_during_holdout:
            for next_state in (
                "training_completed",
                "canary_started",
                "canary_completed",
                "holdout_started",
            ):
                experiment.append_execution_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    expected_previous_state=state,
                    state=next_state,
                    details={},
                )
                state = next_state
        experiment.append_execution_journal(
            output,
            identity=identity,
            lease=lease,
            expected_previous_state=state,
            state="infrastructure_interrupted",
            details={
                "phase": "holdout" if interrupt_during_holdout else "training",
                "reason": "synthetic interruption",
            },
        )
        binding = experiment.publish_training_rows(
            output, chunks, lease=lease, identity=identity
        )
        terminal_resources = copy.deepcopy(_runtime_checkpoint(1)["resource_use"])
        terminal_resources.update(
            {
                "charged_seconds": 3.0,
                "evaluation_episodes": 4,
                "total_episodes": 132,
            }
        )
        experiment.publish_experiment_terminal(
            output,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            identity=identity,
            lease=lease,
            training_rows_binding=binding,
            evaluation=None,
            final_model=_runtime_checkpoint(1)["states"]["model"],
            resource_use=terminal_resources,
            isolation_post=registration["isolation_identity"],
            verdict="experiment_blocked",
            terminal_reason="synthetic infrastructure interruption",
            holdout_accessed=interrupt_during_holdout,
        )
    return output


def _write_canonical_json(path: Path, value: dict[str, object]) -> None:
    path.write_bytes(experiment.canonical_json_bytes(value))


def _rebind_manifest_artifact(
    output: Path,
    relative: str,
    *,
    canonical_payload: bytes | None = None,
) -> None:
    manifest_path = output / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    payload = (output / relative).read_bytes()
    binding = next(row for row in manifest["artifacts"] if row["path"] == relative)
    binding["sha256"] = hashlib.sha256(payload).hexdigest()
    binding["size_bytes"] = len(payload)
    if canonical_payload is not None:
        binding["canonical_sha256"] = hashlib.sha256(canonical_payload).hexdigest()
        binding["canonical_size_bytes"] = len(canonical_payload)
    _write_canonical_json(manifest_path, manifest)


def _independent_verifier_evaluation(verifier) -> dict[str, object]:
    diagnostics = []
    decision_index = 0
    for category, families, count in (
        ("card_reward", ("take", "skip"), 32),
        ("shop", ("buy", "leave"), 32),
        ("event", ("choose", "choose"), 4),
        ("route", ("choose", "choose"), 4),
    ):
        for index in range(count):
            selected_family = families[index % 2]
            alternative_family = families[(index + 1) % 2]
            selected_action = f"{category}-{index}-selected"
            alternative_action = f"{category}-{index}-alternative"
            candidates = [
                {"action_id": selected_action, "kind": selected_family},
                {"action_id": alternative_action, "kind": alternative_family},
            ]
            family_order = sorted({selected_family, alternative_family})
            family_logits = {
                family: max(
                    score
                    for score, candidate in zip((1.0, 0.0), candidates, strict=True)
                    if candidate["kind"] == family
                )
                for family in family_order
            }
            maximum_logit = max(family_logits.values())
            family_weights = {
                family: math.exp(logit - maximum_logit)
                for family, logit in family_logits.items()
            }
            family_denominator = sum(family_weights.values())
            family_probabilities = {
                family: weight / family_denominator
                for family, weight in family_weights.items()
            }
            conditional_probabilities = {}
            for family in family_order:
                members = [
                    (candidate["action_id"], score)
                    for candidate, score in zip(candidates, (1.0, 0.0), strict=True)
                    if candidate["kind"] == family
                ]
                maximum_score = max(score for _, score in members)
                weights = [math.exp(score - maximum_score) for _, score in members]
                denominator = sum(weights)
                for (action_id, _), weight in zip(members, weights, strict=True):
                    conditional_probabilities[action_id] = weight / denominator
            joint_probabilities = {
                candidate["action_id"]: (
                    family_probabilities[candidate["kind"]]
                    * conditional_probabilities[candidate["action_id"]]
                )
                for candidate in candidates
            }
            family_entropy = -sum(
                probability * math.log(probability)
                for probability in family_probabilities.values()
            )
            conditional_entropy = sum(
                family_probabilities[family]
                * -sum(
                    conditional_probabilities[candidate["action_id"]]
                    * math.log(conditional_probabilities[candidate["action_id"]])
                    for candidate in candidates
                    if candidate["kind"] == family
                )
                for family in family_order
            )
            joint_entropy = -sum(
                probability * math.log(probability)
                for probability in joint_probabilities.values()
            )
            diagnostics.append(
                {
                    "candidate_scores": {
                        selected_action: 1.0,
                        alternative_action: 0.0,
                    },
                    "candidates": candidates,
                    "category": category,
                    "chunk_index": None,
                    "conditional_probabilities": conditional_probabilities,
                    "decision_id": f"seed-7:decision-{decision_index}",
                    "decision_index": decision_index,
                    "entropies": {
                        "expected_conditional": conditional_entropy,
                        "family": family_entropy,
                        "joint": joint_entropy,
                    },
                    "family_order": family_order,
                    "family_probabilities": family_probabilities,
                    "family_score_margin": (
                        1.0 if len(family_order) > 1 else None
                    ),
                    "formal_reward": {
                        "floor_progress": 0.0,
                        "scalar_reward": 0.0,
                        "terminal_victory": 0,
                    },
                    "joint_probabilities": joint_probabilities,
                    "joint_probability_max_action_ids": [selected_action],
                    "legal_action_ids": [selected_action, alternative_action],
                    "multi_family": len(set(families)) > 1,
                    "raw_score_max_action_ids": [selected_action],
                    "raw_score_max_family_ids": [selected_family],
                    "schema_version": verifier.TRAINING_ROW_SCHEMA,
                    "score_greedy_action_ids": [selected_action],
                    "score_greedy_family_ids": [selected_family],
                    "score_margin": 1.0,
                    "seed": 7,
                    "selected_action_id": selected_action,
                    "selected_family": selected_family,
                    "selected_terms": {
                        "conditional_log_probability": math.log(
                            conditional_probabilities[selected_action]
                        ),
                        "family_log_probability": math.log(
                            family_probabilities[selected_family]
                        ),
                        "joint_log_probability": math.log(
                            joint_probabilities[selected_action]
                        ),
                    },
                    "selection_mode": verifier.EVALUATION_SELECTION,
                    "state_effect": {
                        "actual_scores": [1.0, 0.0],
                        "max_abs_relative_score_change": 1.0,
                        "nonzero": True,
                        "relative_order_changed": True,
                        "zero_state_scores": [0.0, 1.0],
                    },
                }
            )
            decision_index += 1

    def policy(floor_progress: float) -> dict[str, object]:
        episode = {
            "categories": list(verifier.TARGET_CATEGORIES),
            "decisions": len(diagnostics),
            "floor_progress": floor_progress,
            "formal_return": 0.0,
            "seed": 7,
            "terminal_victory": 0,
            "unsupported_reason": None,
        }
        return {
            "categories": list(verifier.TARGET_CATEGORIES),
            "cohort": "canary",
            "diagnostic_rows": copy.deepcopy(diagnostics),
            "episode_rows": [copy.deepcopy(episode)],
            "episodes": 1,
            "floor_progress": floor_progress,
            "replay_diagnostic_rows": copy.deepcopy(diagnostics),
            "replay_episode_rows": [copy.deepcopy(episode)],
            "replay_exact": True,
            "schema_version": verifier.EVALUATION_SCHEMA,
            "unsupported_episodes": 0,
            "victories": 0,
        }

    return {
        "cohort": "canary",
        "evaluation_episodes": 4,
        "floor_difference_ci": verifier._paired_bootstrap_interval([1.0]),
        "initial": policy(1.0),
        "paired_rows": [
            {
                "floor_difference": 1.0,
                "initial_floor_progress": 1.0,
                "seed": 7,
                "trained_floor_progress": 2.0,
            }
        ],
        "schema_version": verifier.EVALUATION_SCHEMA,
        "trained": policy(2.0),
        "unsupported_rate": 0.0,
        "unsupported_rate_denominator": 2,
    }


def test_independent_verifier_recomputes_evaluation_evidence():
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    evaluation = _independent_verifier_evaluation(verifier)

    result = verifier._canary_gate(
        evaluation, expected_cohort="canary", expected_seeds=[7]
    )

    assert result["passed"] is True
    assert result["blockers"] == []

    mutations = [
        lambda value: value["floor_difference_ci"].__setitem__("resamples", 9_999),
        lambda value: value["trained"].__setitem__("unsupported_episodes", 1),
        lambda value: value["trained"]["replay_episode_rows"][0].__setitem__(
            "floor_progress", 3.0
        ),
        lambda value: value["paired_rows"][0].__setitem__(
            "floor_difference", 0.5
        ),
        lambda value: value["initial"].__setitem__("victories", 1),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(evaluation)
        mutate(changed)
        with pytest.raises(verifier.VerificationError):
            verifier._canary_gate(
                changed, expected_cohort="canary", expected_seeds=[7]
            )


def test_independent_verifier_replays_three_stage_git_identity(
    tmp_path, monkeypatch
):
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    registration = _synthetic_registration()
    source_payloads = {
        path: f"source:{path}".encode()
        for path in experiment.PLANNED_SOURCE_FILES
    }
    source_rows = list(source_payloads.items())
    registration["implementation"] = {
        "source_files": [
            {
                "path": path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
            for path, payload in source_rows
        ],
        "source_sha256": experiment._hash_named_bytes(source_rows),
    }
    native_path = tmp_path / "native.pyd"
    native_payload = b"synthetic-native"
    native_path.write_bytes(native_payload)
    registration["native_identity"]["module"] = {
        "path": native_path.resolve().as_posix(),
        "sha256": hashlib.sha256(native_payload).hexdigest(),
        "size_bytes": len(native_payload),
    }
    registration["runtime_identity"] = {
        "device": "cpu",
        "executable": Path(sys.executable).resolve().as_posix(),
        "platform": sys.platform,
        "python_version": platform.python_version(),
        "torch_version": "synthetic-torch",
    }
    preimplementation_payload = b"preimplementation"
    inventory_payload = experiment.canonical_json_bytes(
        registration["seed_inventory"]
    )
    historical_seed_payload = experiment.canonical_json_bytes(
        {"seeds": [0, 2, 4]}
    )
    registration["preimplementation_binding"].update(
        {
            "sha256": hashlib.sha256(preimplementation_payload).hexdigest(),
            "size_bytes": len(preimplementation_payload),
        }
    )
    registration["seed_inventory_binding"].update(
        {
            "sha256": hashlib.sha256(inventory_payload).hexdigest(),
            "size_bytes": len(inventory_payload),
        }
    )
    registration_payload = experiment.canonical_json_bytes(registration)
    command = experiment.registered_execution_command(
        registration,
        repo_root=ROOT,
        registration_path=ROOT / experiment.DEFAULT_REGISTRATION_PATH,
        authorization_path=ROOT / experiment.DEFAULT_AUTHORIZATION_PATH,
        output_dir=ROOT / experiment.DEFAULT_OUTPUT_DIRECTORY,
    )
    authorization = _synthetic_authorization(registration, command)
    authorization_payload = experiment.canonical_json_bytes(authorization)
    pushed_commit = "f" * 40

    def fake_git_text(root, *args):
        if args in {
            ("rev-parse", "HEAD"),
            ("rev-parse", "origin/master"),
        }:
            return pushed_commit
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        if args[:2] == ("merge-base", "--is-ancestor"):
            return ""
        if args == (
            "ls-tree",
            "-r",
            "--name-only",
            registration["repository_commit"],
            "--",
            "reports",
        ):
            return "reports/historical.json"
        raise AssertionError(args)

    def fake_git_bytes(root, commit, path):
        if path in source_payloads:
            return source_payloads[path]
        if path == verifier.DEFAULT_REGISTRATION_PATH:
            return registration_payload
        if path == verifier.DEFAULT_AUTHORIZATION_PATH:
            return authorization_payload
        if path == verifier.DEFAULT_PREIMPLEMENTATION_PATH:
            return preimplementation_payload
        if path == verifier.DEFAULT_INVENTORY_PATH:
            return inventory_payload
        if path == "reports/historical.json":
            return historical_seed_payload
        raise AssertionError((commit, path))

    monkeypatch.setattr(verifier, "_git_text", fake_git_text)
    monkeypatch.setattr(verifier, "_git_bytes", fake_git_bytes)
    monkeypatch.setattr(
        verifier.importlib_metadata, "version", lambda name: "synthetic-torch"
    )

    verifier._verify_repository_identity(
        ROOT,
        registration=registration,
        registration_payload=registration_payload,
        authorization=authorization,
        authorization_payload=authorization_payload,
    )

    original_git_text = fake_git_text

    def fake_git_text_with_omitted_source(root, *args):
        if args == (
            "ls-tree",
            "-r",
            "--name-only",
            registration["repository_commit"],
            "--",
            "reports",
        ):
            return "reports/historical.json\nreports/omitted.json"
        return original_git_text(root, *args)

    original_git_bytes = fake_git_bytes

    def fake_git_bytes_with_omitted_source(root, commit, path):
        if path == "reports/omitted.json":
            return experiment.canonical_json_bytes({"seed": 999_999})
        return original_git_bytes(root, commit, path)

    monkeypatch.setattr(verifier, "_git_text", fake_git_text_with_omitted_source)
    monkeypatch.setattr(verifier, "_git_bytes", fake_git_bytes_with_omitted_source)
    with pytest.raises(verifier.VerificationError, match="fixed Git tree"):
        verifier._verify_repository_identity(
            ROOT,
            registration=registration,
            registration_payload=registration_payload,
            authorization=authorization,
            authorization_payload=authorization_payload,
        )

    monkeypatch.setattr(verifier, "_git_text", fake_git_text)
    monkeypatch.setattr(verifier, "_git_bytes", fake_git_bytes)

    source_payloads[experiment.PLANNED_SOURCE_FILES[0]] += b"-drift"
    with pytest.raises(verifier.VerificationError, match="implementation Git tree"):
        verifier._verify_repository_identity(
            ROOT,
            registration=registration,
            registration_payload=registration_payload,
            authorization=authorization,
            authorization_payload=authorization_payload,
        )


def test_independent_verifier_accepts_terminal_without_importing_runtime(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(tmp_path / "verified", monkeypatch)
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )

    with pytest.raises(verifier.VerificationError, match="repository root"):
        verifier.verify_output(output, repo_root=None)

    result = verifier.verify_artifact_output(output)

    assert result["verification"] == "artifact_verified"
    assert result["verdict"] == "experiment_blocked"
    source = (
        "import builtins,json,sys;"
        "original=builtins.__import__;"
        "blocked={'torch','sts_lightspeed_noncombat_adapter',"
        "'analysis_scripts.noncombat_hierarchical_simulator_learning_experiment',"
        "'analysis_scripts.noncombat_hierarchical_simulator_learning_runtime'};"
        "builtins.__import__=lambda name,*a,**k: "
        "(_ for _ in ()).throw(RuntimeError('blocked '+name)) "
        "if name in blocked or name.split('.')[0] in {'torch','sts_lightspeed_noncombat_adapter'} "
        "else original(name,*a,**k);"
        "import analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment "
        "as verifier;"
        f"verifier.INITIAL_RUNTIME_SHA256={verifier.INITIAL_RUNTIME_SHA256!r};"
        "verify_artifact_output=verifier.verify_artifact_output;"
        f"result=verify_artifact_output({str(output)!r});"
        "print(json.dumps({'verification':result['verification'],"
        "'torch':'torch' in sys.modules,'runtime':"
        "'analysis_scripts.noncombat_hierarchical_simulator_learning_runtime' in sys.modules,"
        "'control':'analysis_scripts.noncombat_hierarchical_simulator_learning_experiment' "
        "in sys.modules},sort_keys=True))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {
        "control": False,
        "runtime": False,
        "torch": False,
        "verification": "artifact_verified",
    }


def test_independent_verifier_preserves_interrupted_holdout_access(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(
        tmp_path / "holdout-interrupted",
        monkeypatch,
        interrupt_during_holdout=True,
    )
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )

    result = verifier.verify_artifact_output(output)

    terminal = json.loads((output / "terminal.json").read_bytes())
    assert result["verdict"] == "experiment_blocked"
    assert terminal["holdout_accessed"] is True


def test_independent_verifier_holds_and_respects_the_execution_lease(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(
        tmp_path / "active-output", monkeypatch
    )
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    registration = json.loads((output / "registration.json").read_bytes())
    authorization = json.loads((output / "authorization.json").read_bytes())
    identity = _execution_identity(registration, authorization)

    with experiment.ExecutionLease(output, identity=identity):
        with pytest.raises(
            verifier.VerificationError, match="active execution"
        ):
            verifier.verify_artifact_output(output)


def test_independent_verifier_rejects_rebound_semantic_mutations(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(tmp_path / "mutations", monkeypatch)
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    original = {
        path.relative_to(output).as_posix(): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }

    def restore() -> None:
        for relative, payload in original.items():
            (output / relative).write_bytes(payload)

    def mutate_json(relative: str, mutation) -> None:
        path = output / relative
        value = json.loads(path.read_bytes())
        mutation(value)
        _write_canonical_json(path, value)
        _rebind_manifest_artifact(output, relative)

    mutations = [
        lambda: mutate_json(
            "metrics.json",
            lambda value: value["authority"].__setitem__("formal_rl_authorized", True),
        ),
        lambda: mutate_json(
            "registration.json",
            lambda value: value["cohorts"]["holdout"].__setitem__(
                0, value["cohorts"]["train"][0]
            ),
        ),
        lambda: mutate_json(
            "checkpoints/checkpoint_0002.json",
            lambda value: value["runtime"]["algorithm"].__setitem__(
                "family_entropy_coefficient", 0.02
            ),
        ),
        lambda: mutate_json(
            "checkpoints/checkpoint_0002.json",
            lambda value: _encoded_mapping_value(
                _encoded_mapping_value(
                    value["runtime"]["states"]["optimizer"], "param_groups"
                )["items"][0],
                "maximize",
            ).__setitem__("value", True),
        ),
        lambda: mutate_json(
            "execution_journal.json",
            lambda value: value["records"].pop(),
        ),
        lambda: mutate_json(
            "isolation.json",
            lambda value: value["post"]["production_checkpoints"].__setitem__(
                "sha256", "9" * 64
            ),
        ),
        lambda: mutate_json(
            "terminal.json",
            lambda value: value.__setitem__("holdout_accessed", True),
        ),
        lambda: mutate_json(
            "metrics.json",
            lambda value: value["resource_use"].__setitem__(
                "total_episodes", 999999
            ),
        ),
        lambda: mutate_json(
            "resource_use.json",
            lambda value: value["resource_use"].__setitem__(
                "training_episodes",
                value["resource_use"]["training_episodes"] + 1,
            ),
        ),
        lambda: mutate_json(
            "resource_use.json",
            lambda value: value.__setitem__("revision", 1),
        ),
        lambda: mutate_json(
            "bootstrap_runtime.json",
            lambda value: value["runtime"]["states"]["model"]["weight"][
                "values"
            ].__setitem__(0, 1.0),
        ),
        lambda: mutate_json(
            "terminal.json",
            lambda value: value.__setitem__(
                "verdict", "experiment_valid_with_floor_only_signal"
            ),
        ),
    ]

    def mutate_generator_chain() -> None:
        path = output / "training_rows.json.gz"
        value = json.loads(gzip.decompress(path.read_bytes()))
        value["chunks"][1]["diagnostic_rows"][0][
            "action_generator_state_sha256"
        ]["before_family"] = "8" * 64
        canonical = experiment.canonical_json_bytes(value)
        path.write_bytes(experiment._deterministic_gzip(canonical))
        terminal_path = output / "terminal.json"
        terminal = json.loads(terminal_path.read_bytes())
        binding = terminal["training_rows_binding"]
        binding["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
        binding["canonical_size_bytes"] = len(canonical)
        binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        binding["size_bytes"] = len(path.read_bytes())
        _write_canonical_json(terminal_path, terminal)
        _rebind_manifest_artifact(
            output, "training_rows.json.gz", canonical_payload=canonical
        )
        _rebind_manifest_artifact(output, "terminal.json")

    mutations.append(mutate_generator_chain)

    def mutate_bound_generator(
        chunk_index: int,
        field: str,
        replacement,
    ) -> None:
        checkpoint_relative = f"checkpoints/checkpoint_{chunk_index + 1:04d}.json"
        checkpoint_path = output / checkpoint_relative
        checkpoint = json.loads(checkpoint_path.read_bytes())
        checkpoint_hashes = checkpoint["training_chunk"]["diagnostic_rows"][0][
            "action_generator_state_sha256"
        ]
        checkpoint_hashes[field] = replacement(checkpoint_hashes)
        _write_canonical_json(checkpoint_path, checkpoint)
        _rebind_manifest_artifact(output, checkpoint_relative)

        path = output / "training_rows.json.gz"
        value = json.loads(gzip.decompress(path.read_bytes()))
        training_hashes = value["chunks"][chunk_index]["diagnostic_rows"][0][
            "action_generator_state_sha256"
        ]
        training_hashes[field] = replacement(training_hashes)
        canonical = experiment.canonical_json_bytes(value)
        path.write_bytes(experiment._deterministic_gzip(canonical))
        terminal_path = output / "terminal.json"
        terminal = json.loads(terminal_path.read_bytes())
        binding = terminal["training_rows_binding"]
        binding["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
        binding["canonical_size_bytes"] = len(canonical)
        binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        binding["size_bytes"] = len(path.read_bytes())
        _write_canonical_json(terminal_path, terminal)
        _rebind_manifest_artifact(
            output,
            "training_rows.json.gz",
            canonical_payload=canonical,
        )
        _rebind_manifest_artifact(output, "terminal.json")

    mutations.extend(
        [
            lambda: mutate_bound_generator(
                1,
                "after_family",
                lambda hashes: hashes["before_family"],
            ),
            lambda: mutate_bound_generator(
                0,
                "before_family",
                lambda hashes: "7" * 64,
            ),
        ]
    )

    for mutate in mutations:
        restore()
        mutate()
        with pytest.raises(verifier.VerificationError):
            verifier.verify_artifact_output(output)

    restore()
    manifest_path = output / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["artifacts"].pop()
    manifest["artifact_count"] -= 1
    _write_canonical_json(manifest_path, manifest)
    with pytest.raises(verifier.VerificationError):
        verifier.verify_artifact_output(output)


def test_terminal_control_and_verifier_reject_unreconciled_temporary(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(tmp_path / "temporary", monkeypatch)
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )
    terminal = json.loads((output / "terminal.json").read_bytes())
    temporary = output / ".resource_use.json.tmp"
    temporary.write_bytes(b"partial")

    with pytest.raises(experiment.ExperimentBlocked, match="unreconciled temporary"):
        experiment._terminal_artifact_inventory(
            output,
            training_rows_binding=terminal["training_rows_binding"],
        )
    with pytest.raises(verifier.VerificationError, match="unreconciled temporary"):
        verifier.verify_artifact_output(output)


def test_independent_verifier_rejects_rebound_training_seed_order(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(tmp_path / "seed-order", monkeypatch)
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )

    checkpoint_path = output / "checkpoints/checkpoint_0002.json"
    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint_seeds = checkpoint["training_chunk"]["episode_seeds"]
    checkpoint_seeds[0], checkpoint_seeds[1] = (
        checkpoint_seeds[1],
        checkpoint_seeds[0],
    )
    _write_canonical_json(checkpoint_path, checkpoint)
    _rebind_manifest_artifact(output, "checkpoints/checkpoint_0002.json")

    training_path = output / "training_rows.json.gz"
    training = json.loads(gzip.decompress(training_path.read_bytes()))
    training["chunks"][1]["episode_seeds"] = copy.deepcopy(checkpoint_seeds)
    canonical = experiment.canonical_json_bytes(training)
    training_path.write_bytes(experiment._deterministic_gzip(canonical))
    terminal_path = output / "terminal.json"
    terminal = json.loads(terminal_path.read_bytes())
    binding = terminal["training_rows_binding"]
    binding["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
    binding["canonical_size_bytes"] = len(canonical)
    binding["sha256"] = hashlib.sha256(training_path.read_bytes()).hexdigest()
    binding["size_bytes"] = len(training_path.read_bytes())
    _write_canonical_json(terminal_path, terminal)
    _rebind_manifest_artifact(
        output,
        "training_rows.json.gz",
        canonical_payload=canonical,
    )
    _rebind_manifest_artifact(output, "terminal.json")

    with pytest.raises(verifier.VerificationError, match="seed order"):
        verifier.verify_artifact_output(output)


def test_independent_verifier_recomputes_training_diagnostic_semantics(
    tmp_path, monkeypatch
):
    output = _publish_verifier_fixture(
        tmp_path / "diagnostic-semantics", monkeypatch
    )
    verifier = importlib.import_module(
        "analysis_scripts.verify_noncombat_hierarchical_simulator_learning_experiment"
    )

    checkpoint_path = output / "checkpoints/checkpoint_0002.json"
    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint["training_chunk"]["diagnostic_rows"][0]["selected_terms"][
        "joint_log_probability"
    ] = 1.0
    _write_canonical_json(checkpoint_path, checkpoint)
    _rebind_manifest_artifact(output, "checkpoints/checkpoint_0002.json")

    training_path = output / "training_rows.json.gz"
    training = json.loads(gzip.decompress(training_path.read_bytes()))
    training["chunks"][1]["diagnostic_rows"][0]["selected_terms"][
        "joint_log_probability"
    ] = 1.0
    canonical = experiment.canonical_json_bytes(training)
    training_path.write_bytes(experiment._deterministic_gzip(canonical))
    terminal_path = output / "terminal.json"
    terminal = json.loads(terminal_path.read_bytes())
    binding = terminal["training_rows_binding"]
    binding["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
    binding["canonical_size_bytes"] = len(canonical)
    binding["sha256"] = hashlib.sha256(training_path.read_bytes()).hexdigest()
    binding["size_bytes"] = len(training_path.read_bytes())
    _write_canonical_json(terminal_path, terminal)
    _rebind_manifest_artifact(
        output,
        "training_rows.json.gz",
        canonical_payload=canonical,
    )
    _rebind_manifest_artifact(output, "terminal.json")

    with pytest.raises(
        verifier.VerificationError,
        match="selected joint log probability differs from recomputation",
    ):
        verifier.verify_artifact_output(output)
